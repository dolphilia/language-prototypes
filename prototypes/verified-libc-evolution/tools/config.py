"""Paths and the pinned, shared proof environment; no network operations."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / 'verified-libc-minimal'
DEPS = BASE / '.deps'
BUILD = ROOT / 'build'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def environment():
    env = os.environ.copy()
    env['SDKROOT'] = subprocess.check_output(['xcrun', '--show-sdk-path'], text=True).strip()
    env['PATH'] = '/usr/bin:/bin:/opt/homebrew/bin:/opt/homebrew/sbin:' + env.get('PATH', '')
    env['OPAMROOT'] = str(DEPS / 'opam-root')
    env['VP_ROOT'] = str(BASE)
    env['VP_EVOLUTION_ROOT'] = str(ROOT)
    env['HOLLIGHT_DIR'] = str(DEPS / 'hol-light')
    env['HOLLIGHT_USE_MODULE'] = '0'
    env['OCAMLRUNPARAM'] = 'l=1000000000'
    return env


def opam_command(command):
    return ['opam', 'exec', '--switch', str(DEPS / 'ocaml'), '--', *map(str, command)]


def validate_dependencies():
    own=json.loads((ROOT/'deps.lock').read_text())
    if digest(BASE/'deps.lock')!=own['baseline_lock_sha256'] or \
       digest(BASE/'opam-switch.export')!=own['ocaml_export_sha256']:
        raise RuntimeError('shared dependency pin/export changed')
    lock = json.loads((BASE / 'deps.lock').read_text())
    for name in ['hol-light', 's2n-bignum']:
        repo = DEPS / name
        revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        changed = subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain', '--untracked-files=no'], text=True).strip()
        if revision != lock[name]['commit'] or changed:
            raise RuntimeError(f'{name}: dependency differs from the pinned clean source')
    packages=subprocess.check_output(['opam','list','--switch',str(DEPS/'ocaml'),
        '--installed','--columns=name,version','--short','--color=never'],env=environment(),text=True)
    actual={'.'.join(line.split()) for line in packages.splitlines()}
    exported=re.search(r'\ninstalled: \[(.*?)\n\]',(BASE/'opam-switch.export').read_text(),re.S)
    if exported is None or actual!=set(re.findall(r'"([^"\n]+)"',exported[1])):
        raise RuntimeError('OCaml package environment differs from the pinned export')
    return lock
