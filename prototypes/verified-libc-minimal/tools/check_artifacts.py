"""Compare exact function spans in an object and a linked Mach-O artifact."""
from pathlib import Path
import argparse
import hashlib
import json
import struct

from macho import MachO, MachOError

ROOT = Path(__file__).resolve().parents[1]


def check_function(path, name, expected, *, object_only=False):
    parsed = MachO(path)
    if not object_only and parsed.kind != 2:
        raise MachOError('expected a linked MH_EXECUTE artifact')
    actual = parsed.function(name, object_only=object_only)
    if actual != expected:
        raise MachOError(f'{path}: {name}: function bytes differ from proof target')
    return {'name': name, 'bytes': len(actual), 'sha256': hashlib.sha256(actual).hexdigest()}


def check_probe():
    expected = struct.pack('<I', 0xD65F03C0)
    records = [check_function(ROOT / 'build/probe_ret.o', 'vp_probe_ret', expected, object_only=True),
               check_function(ROOT / 'build/probe_ret', 'vp_probe_ret', expected)]
    (ROOT / 'build/artifacts-probe.json').write_text(json.dumps(records, indent=2) + '\n')
    print('P0: object and linked function both equal the proof target (4 bytes)')


FUNCTIONS = ['vp_memcpy_scalar', 'vp_memcpy', 'vp_memset']


def expected_bytes(name):
    words = (ROOT / 'build' / (name + '.words')).read_text().splitlines()
    if not words or any(len(w) != 8 or any(c not in '0123456789abcdef' for c in w)
                        for w in words):
        raise MachOError('invalid expected instruction list')
    return b''.join(struct.pack('<I', int(w, 16)) for w in words)


def check_primitives(executables=('test_memory',)):
    records = []
    for name in FUNCTIONS:
        expected = expected_bytes(name)
        record = check_function(ROOT / 'build' / (name + '.o'), name,
                                expected, object_only=True)
        for executable in executables:
            check_function(ROOT / 'build' / executable, name, expected)
        records.append(record)
    (ROOT / 'build/artifacts-primitives.json').write_text(json.dumps(records, indent=2)+'\n')
    print('objects and linked functions: exact spans match (' +
          ', '.join(f'{r["name"]}={r["bytes"]} bytes' for r in records) + ')')
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--probe', action='store_true')
    modes.add_argument('--primitives', action='store_true')
    args = parser.parse_args()
    check_probe() if args.probe else check_primitives()
