"""P0 checks for the actual native object, executable, and extraction failures."""
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from macho import MachO, MachOError
from check_artifacts import check_function, FUNCTIONS, expected_bytes


class ArtifactChecks(unittest.TestCase):
    def test_native_ret_bytes(self):
        obj = MachO(ROOT / 'build/probe_ret.o').function('vp_probe_ret', object_only=True)
        exe = MachO(ROOT / 'build/probe_ret').function('vp_probe_ret')
        self.assertEqual(obj, bytes.fromhex('c0035fd6'))
        self.assertEqual(obj, exe)

    def test_malformed_files_fail(self):
        original = (ROOT / 'build/probe_ret.o').read_bytes()
        variants = [b'', original[:31], original[:-1]]
        for offset, value in [(0, 0), (8, 2), (20, 0x7FFFFFFF), (36, 0)]:
            changed = bytearray(original)
            struct.pack_into('<I', changed, offset, value)
            variants.append(changed)
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as folder:
            for index, contents in enumerate(variants):
                path = Path(folder) / f'bad-{index}'
                path.write_bytes(contents)
                with self.subTest(index=index), self.assertRaises((MachOError, UnicodeError)):
                    MachO(path).function('vp_probe_ret', object_only=True)

    def test_changed_object_and_executable_are_rejected(self):
        expected = MachO(ROOT / 'build/probe_ret.o').function('vp_probe_ret', object_only=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as folder:
            for filename in ['probe_ret.o', 'probe_ret']:
                source = MachO(ROOT / 'build' / filename)
                start = source.symbol('_vp_probe_ret')
                section = source.sections[start.section - 1]
                changed = bytearray(source.data)
                changed[section.offset + start.address - section.address] ^= 1
                path = Path(folder) / filename
                path.write_bytes(changed)
                with self.subTest(filename=filename):
                    with self.assertRaises(MachOError):
                        check_function(path, 'vp_probe_ret', expected,
                                       object_only=filename.endswith('.o'))

    def test_wrong_symbol_fails(self):
        with self.assertRaises(MachOError):
            MachO(ROOT / 'build/probe_ret').function('missing')

    def test_section_header_cannot_redirect_mapped_code(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as folder:
            for filename in ['probe_ret.o', 'probe_ret']:
                source = MachO(ROOT / 'build' / filename)
                start = source.symbol('_vp_probe_ret')
                section = source.sections[start.section - 1]
                changed = bytearray(source.data)
                struct.pack_into('<I', changed, section.header_offset + 48, section.offset + 4)
                path = Path(folder) / filename
                path.write_bytes(changed)
                with self.subTest(filename=filename), self.assertRaises(MachOError):
                    MachO(path).function('vp_probe_ret')

    def test_changed_primitive_objects_and_linked_functions(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as folder:
            for name in FUNCTIONS:
                for filename in [name + '.o', 'test_memory']:
                    source = MachO(ROOT / 'build' / filename)
                    start = source.symbol('_' + name)
                    section = source.sections[start.section - 1]
                    changed = bytearray(source.data)
                    changed[section.offset + start.address - section.address] ^= 1
                    path = Path(folder) / (name + '-' + filename)
                    path.write_bytes(changed)
                    with self.subTest(name=name, filename=filename), self.assertRaises(MachOError):
                        check_function(path, name, expected_bytes(name),
                                       object_only=filename.endswith('.o'))

    def test_object_is_not_a_linked_executable(self):
        with self.assertRaisesRegex(MachOError,'MH_EXECUTE'):
            check_function(ROOT/'build/probe_ret.o','vp_probe_ret',bytes.fromhex('c0035fd6'))

    def fixture(self,folder,body,suffix=''):
        source=Path(folder)/'fixture.S';obj=Path(folder)/'fixture.o'
        source.write_text('.text\n.p2align 2\n.globl _vp_probe_ret\n_vp_probe_ret:\n'+
            body+'\n.globl _vp_probe_ret_end\n_vp_probe_ret_end:\n'+suffix+'\n')
        subprocess.run(['xcrun','clang','-arch','arm64','-c',str(source),'-o',str(obj)],check=True)
        return obj

    def test_extra_data_section_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder:
            obj=self.fixture(folder,'ret','.section __TEXT,__const\n.quad 123')
            with self.assertRaisesRegex(MachOError,'another nonempty section'):
                MachO(obj).function('vp_probe_ret',object_only=True)

    def test_external_call_relocation_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as folder:
            obj=self.fixture(folder,'bl _missing_external\nret')
            with self.assertRaisesRegex(MachOError,'relocations'):
                MachO(obj).function('vp_probe_ret',object_only=True)


if __name__ == '__main__':
    unittest.main()
