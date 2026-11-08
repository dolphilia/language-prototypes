"""Dispatch implemented units; a missing later unit always fails closed."""
import importlib
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: entry.py phase-target')
    targets={'verify-m2':('phase_m2','verify'),'measure-m2':('phase_m2','measure'),
             'verify-m3':('phase_m3','verify'),'measure-m3':('phase_m3','measure'),
             'verify-all':('phase_all','verify')}
    target=sys.argv[1]
    if target not in targets:raise SystemExit('unknown phase target: '+target)
    module,action=targets[target]
    if not Path(__file__).with_name(module+'.py').is_file():
        raise SystemExit(f'{target}: incomplete; missing {module}.py (no successful phase result produced)')
    getattr(importlib.import_module(module),action)()


if __name__ == '__main__':
    main()
