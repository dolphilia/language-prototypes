"""Tane: natural-number counters, structured loops, and console output."""

import re
import sys
from collections import defaultdict


class TaneError(Exception):
    pass


def compile_source(source):
    """Validate the whole source and link matching while/end instructions."""
    code, loops = [], []
    for line_number, line in enumerate(source.splitlines(), 1):
        words = line.split("#", 1)[0].split()
        if not words:
            continue
        if words == ["end"]:
            if not loops:
                raise TaneError(f"line {line_number}: end without while")
            start, _ = loops.pop()
            code.append(["end", None, start])
            code[start][2] = len(code)
        elif (len(words) == 2 and words[0] in ("inc", "dec", "while", "print")
              and re.fullmatch(r"[a-z][a-z0-9_]*", words[1])):
            if words[0] == "while":
                loops.append((len(code), line_number))
            code.append([words[0], words[1], None])
        else:
            raise TaneError(f"line {line_number}: invalid instruction")
    if loops:
        raise TaneError(f"line {loops[-1][1]}: while without end")
    return code


def run(code, output=None):
    """Execute compiled code with fresh, initially zero counters."""
    if hasattr(sys, "set_int_max_str_digits"):
        sys.set_int_max_str_digits(0)
    counters = defaultdict(int)
    pc = 0
    while pc < len(code):
        operation, name, target = code[pc]
        if operation == "inc":
            counters[name] += 1
        elif operation == "dec":
            counters[name] = max(0, counters[name] - 1)
        elif operation == "print":
            print(counters[name], file=output, flush=True)
        elif operation == "while" and counters[name] == 0:
            pc = target
            continue
        elif operation == "end":
            pc = target
            continue
        pc += 1
    return dict(counters)


def main():
    if len(sys.argv) != 2:
        print("usage: python3 tane.py SOURCE.tane", file=sys.stderr)
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as source:
            code = compile_source(source.read())
        run(code)
    except (OSError, UnicodeError, TaneError) as error:
        print(f"{sys.argv[1]}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
