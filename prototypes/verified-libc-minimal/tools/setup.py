"""Explicit network-enabled dependency setup; verify never calls this script."""
from pathlib import Path
import json
import os
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=ROOT, env=None):
    subprocess.run(list(map(str, args)), cwd=cwd, env=env, check=True)


def setup():
    if (platform.system(), platform.machine()) != ('Darwin', 'arm64'):
        raise SystemExit('this prototype currently requires native macOS arm64')
    deps = ROOT / '.deps'
    deps.mkdir(exist_ok=True)
    lock = json.loads((ROOT / 'deps.lock').read_text())
    env = os.environ.copy()
    # The system OCaml compiler invokes clang by name. Prefer Apple's clang,
    # and explicitly expose the SDK so its C stubs and native linker work.
    env['PATH'] = '/usr/bin:/bin:/opt/homebrew/bin:/opt/homebrew/sbin:' + env.get('PATH', '')
    env['SDKROOT'] = subprocess.check_output(['xcrun', '--show-sdk-path'], text=True).strip()
    env['OPAMROOT'] = str(deps / 'opam-root')
    version = subprocess.check_output(['ocamlc', '-version'], env=env, text=True).strip()
    if version != lock['ocaml-system']:
        raise SystemExit(f'expected system OCaml {lock["ocaml-system"]}, found {version}')
    for name in ['hol-light', 's2n-bignum']:
        target = deps / name
        pinned = lock[name]
        if not target.exists():
            target.mkdir()
            run('git', 'init', '--quiet', cwd=target)
            run('git', 'remote', 'add', 'origin', pinned['url'], cwd=target)
            run('git', 'fetch', '--depth', '1', 'origin', pinned['commit'], cwd=target)
            run('git', 'checkout', '--detach', 'FETCH_HEAD', cwd=target)
        actual = subprocess.check_output(['git', '-C', str(target), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != pinned['commit']:
            raise SystemExit(f'{name}: existing checkout does not match deps.lock')
        run('git', 'diff', '--exit-code', 'HEAD', cwd=target)
    if not (deps / 'opam-root/config').exists():
        run('opam', 'init', '--bare', '--disable-sandboxing', '--no-setup', '--yes',
            'default', 'https://opam.ocaml.org', env=env)
    switch = deps / 'ocaml'
    if not (switch / '_opam').exists():
        run('opam', 'switch', 'create', switch, 'ocaml-system.' + lock['ocaml-system'], '--yes', env=env)
    run('opam', 'switch', 'import', '--switch', switch, '--yes', ROOT / 'opam-switch.export', env=env)
    run('opam', 'exec', '--switch', switch, '--', 'make', '-C', deps / 'hol-light',
        'HOLLIGHT_USE_MODULE=0', env=env)
    print('Dependencies installed inside .deps; run make p0 next.')


if __name__ == '__main__':
    setup()
