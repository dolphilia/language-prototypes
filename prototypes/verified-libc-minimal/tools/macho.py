"""Strict reader for the thin arm64 Mach-O subset used by this prototype.

This parser is part of the unverified artifact-extraction trusted base.
All ranges are bounds checked. Fat binaries, arm64e, and ambiguous symbols fail.
"""
from dataclasses import dataclass
from pathlib import Path
import struct


class MachOError(ValueError):
    pass


@dataclass(frozen=True)
class Section:
    name: str
    segment: str
    address: int
    size: int
    offset: int
    relocations: int
    flags: int
    segment_mapping: tuple
    header_offset: int


@dataclass(frozen=True)
class Symbol:
    name: str
    section: int
    address: int
    kind: int


class MachO:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        magic, cpu, subtype, kind, ncmds, cmdsize, _, _ = self.unpack('<IiiIIIII', 0)
        if magic != 0xFEEDFACF or cpu != 0x0100000C or subtype & 0xFFFFFF != 0:
            raise MachOError('expected thin little-endian arm64 (not arm64e) Mach-O')
        if kind not in (1, 2):
            raise MachOError('expected MH_OBJECT or MH_EXECUTE')
        self.kind = kind
        if ncmds > cmdsize // 8:
            raise MachOError('invalid load-command count')
        commands_end = 32 + cmdsize
        self.span(32, cmdsize)
        self.sections = []
        self.symbols = []
        symtab = None
        cursor = 32
        for _ in range(ncmds):
            command, size = self.unpack('<II', cursor)
            if size < 8 or size % 8 or cursor + size > commands_end:
                raise MachOError('invalid load-command range')
            if command == 0x19:
                if size < 72:
                    raise MachOError('short LC_SEGMENT_64')
                fields = self.unpack('<II16sQQQQiiII', cursor)
                nsects = fields[9]
                if size != 72 + 80 * nsects:
                    raise MachOError('inconsistent segment section count')
                for index in range(nsects):
                    section_header = cursor + 72 + index * 80
                    values = self.unpack('<16s16sQQIIIIIIII', section_header)
                    name, segment, address, length, offset, _, _, nreloc, flags, _, _, _ = values
                    # Only file-backed instruction sections are later read.
                    self.sections.append(Section(self.cstring(name), self.cstring(segment),
                                                 address, length, offset, nreloc, flags,
                                                 fields[3:7] + (fields[8],), section_header))
            elif command == 2:
                if size != 24 or symtab is not None:
                    raise MachOError('invalid or duplicate LC_SYMTAB')
                symtab = self.unpack('<IIIIII', cursor)[2:]
            cursor += size
        if cursor != commands_end or symtab is None:
            raise MachOError('missing symbol table or inconsistent load commands')
        symoff, nsyms, stroff, strsize = symtab
        strings = self.span(stroff, strsize)
        self.span(symoff, nsyms * 16)
        for i in range(nsyms):
            string_index, symtype, section, _, address = self.unpack('<IBBHQ', symoff + i * 16)
            if string_index >= strsize:
                raise MachOError('invalid symbol string index')
            end = strings.find(b'\0', string_index)
            if end < 0:
                raise MachOError('unterminated symbol name')
            name = strings[string_index:end].decode('ascii', errors='strict')
            if symtype & 0xE0:  # debugging symbol
                continue
            if section > len(self.sections):
                raise MachOError('invalid symbol section')
            self.symbols.append(Symbol(name, section, address, symtype & 0x0E))

    @staticmethod
    def cstring(value):
        return value.split(b'\0', 1)[0].decode('ascii', errors='strict')

    def span(self, offset, size):
        if offset < 0 or size < 0 or offset > len(self.data) or size > len(self.data) - offset:
            raise MachOError('file range out of bounds')
        return self.data[offset:offset + size]

    def unpack(self, fmt, offset):
        return struct.unpack(fmt, self.span(offset, struct.calcsize(fmt)))

    def symbol(self, name):
        matches = [s for s in self.symbols if s.name == name]
        if len(matches) != 1 or matches[0].kind != 0x0E or not matches[0].section:
            raise MachOError(f'expected unique defined section symbol {name}')
        return matches[0]

    def function(self, name, *, object_only=False):
        if object_only and self.kind != 1:
            raise MachOError('expected relocatable object')
        start = self.symbol('_' + name)
        end = self.symbol('_' + name + '_end')
        if start.section != end.section:
            raise MachOError('function boundary symbols are in different sections')
        section = self.sections[start.section - 1]
        if (section.name, section.segment) != ('__text', '__TEXT') or not section.flags & 0x80000400:
            raise MachOError('function is not in the expected instruction section')
        vmaddr, vmsize, fileoff, filesize, protection = section.segment_mapping
        delta = section.address - vmaddr
        if (not protection & 4 or delta < 0 or delta + section.size > vmsize or
                section.offset != fileoff + delta or delta + section.size > filesize):
            raise MachOError('section bytes disagree with the executable segment mapping')
        self.span(fileoff, filesize)
        length = end.address - start.address
        relative = start.address - section.address
        if start.address % 4 or length <= 0 or length % 4 or relative < 0 or relative + length > section.size:
            raise MachOError('invalid function range')
        if section.relocations:
            raise MachOError('instruction section contains relocations')
        if object_only:
            if relative != 0 or length != section.size:
                raise MachOError('object must contain exactly one function in __text')
            if any(s.kind == 0 and s.name for s in self.symbols):
                raise MachOError('object contains undefined symbols')
            if any(s.size for s in self.sections if s != section):
                raise MachOError('object contains another nonempty section (no data/constant tables allowed)')
        return self.span(section.offset + relative, length)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path')
    parser.add_argument('function')
    parser.add_argument('--object', action='store_true')
    args = parser.parse_args()
    code = MachO(args.path).function(args.function, object_only=args.object)
    print(' '.join(f'{word:08x}' for word in struct.unpack('<' + 'I' * (len(code) // 4), code)))
