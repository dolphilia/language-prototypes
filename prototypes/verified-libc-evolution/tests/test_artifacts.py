import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build import BUILD,check_span,words


class ArtifactChecks(unittest.TestCase):
    def test_only_expected_bytes_changed_is_rejected(self):
        name='vp2_equivalent_copy'
        actual=words(BUILD/(name+'.words'))
        changed=struct.pack('<I',0xd2800000)+actual[4:]
        with self.assertRaises(RuntimeError):
            check_span(BUILD/(name+'.o'),name,changed)

    def test_wrong_function_or_missing_file_is_rejected(self):
        with self.assertRaises(Exception):
            check_span(BUILD/'vp2_memset.o','vp2_memcpy_chunk8',words(BUILD/'vp2_memcpy_chunk8.words'))
        with self.assertRaises(OSError):
            check_span(BUILD/'missing.o','missing',b'')

    def test_direct_compositions_match_every_byte(self):
        for n in [16,32]:
            check_span(BUILD/f'vp2_copy{n}_direct.o',f'vp2_copy{n}_direct',words(BUILD/f'vp2_copy{n}.words'))


if __name__=='__main__': unittest.main()
