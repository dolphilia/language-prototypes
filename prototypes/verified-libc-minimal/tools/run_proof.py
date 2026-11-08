"""Run a fresh HOL Light session and accept only checked, closed theorems.

The HOL-side driver checks theorem terms (not just their printed names), rejects
additional axioms, and writes a fresh nonce-bound result only after these checks.
"""
from pathlib import Path
import argparse
import json
import os
import re
import secrets
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def environment():
    env = os.environ.copy()
    env['SDKROOT'] = subprocess.check_output(['xcrun', '--show-sdk-path'], text=True).strip()
    env['PATH'] = '/usr/bin:/bin:/opt/homebrew/bin:/opt/homebrew/sbin:' + env.get('PATH', '')
    env['OPAMROOT'] = str(ROOT / '.deps/opam-root')
    env['VP_ROOT'] = str(ROOT)
    env['HOLLIGHT_DIR'] = str(ROOT / '.deps/hol-light')
    env['HOLLIGHT_USE_MODULE'] = '0'
    env['OCAMLRUNPARAM'] = 'l=1000000000'
    return env


def opam_command(command):
    return ['opam', 'exec', '--switch', str(ROOT / '.deps/ocaml'), '--', *map(str, command)]


def run_session(stem, body, expected_names, timeout=1800):
    build = ROOT / 'build'
    build.mkdir(exist_ok=True)
    result = build / ('proof-' + stem + '.json')
    result.unlink(missing_ok=True)
    nonce = secrets.token_hex(24)
    theorem_names = [n for n in expected_names if not n.startswith('rejected:')]
    rejections = [n.removeprefix('rejected:') for n in expected_names if n.startswith('rejected:')]
    output = json.dumps({'nonce': nonce, 'theorems': theorem_names, 'rejected': rejections})
    # JSON string literals also quote these ASCII-only OCaml string values.
    driver = f'''
use_file_raise_failure := true;;
set_color_printer false;;
loadt {json.dumps(str(ROOT / 'proofs/checks.ml'))};;
{body}
check_axioms ();;
let vp_result = open_out {json.dumps(str(result))} in
output_string vp_result {json.dumps(output)}; close_out vp_result;;
exit 0;;
'''
    log = build / ('proof-' + stem + '.log')
    command = opam_command([ROOT / '.deps/hol-light/ocaml-hol',
                            '-init', ROOT / '.deps/hol-light/hol.ml',
                            '-I', ROOT / '.deps/hol-light'])
    started = time.monotonic()
    with log.open('w') as stream:
        proc = subprocess.run(command, cwd=ROOT / '.deps/s2n-bignum',
                              env=environment(), input=driver, text=True,
                              stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
    text = log.read_text()
    # HOL's OCaml toplevel can continue after a failed phrase. Never trust exit
    # status or a last success-looking log line alone.
    plain_text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    errors = re.search(r'(^|\n)[# \t]*(?:Exception:|Error:|Error in included file|Fatal error:)',
                       plain_text)
    if proc.returncode or errors or not result.exists():
        result.unlink(missing_ok=True)
        raise RuntimeError(f'HOL Light proof failed; see {log}')
    checked = json.loads(result.read_text())
    if checked != json.loads(output):
        result.unlink(missing_ok=True)
        raise RuntimeError('proof result does not match this fresh session')
    print(f'{stem}: checked {len(theorem_names)} closed theorems, '
          f'{len(rejections)} expected rejections in '
          f'{time.monotonic() - started:.1f}s; no additional axioms',flush=True)
    return checked


def run_probe(timeout=1800):
    body = f'''
loadt {json.dumps(str(ROOT / 'proofs/probe_ret.ml'))};;
needs "arm/proofs/word_max.ml";;
vp_check_closed vp_probe_ret_spec VP_PROBE_RET_CORRECT;;
if hyp WORD_MAX_SUBROUTINE_CORRECT <> [] then failwith "VP: open upstream theorem";;
'''
    return run_session('probe', body, ['VP_PROBE_RET_CORRECT',
                                      'WORD_MAX_SUBROUTINE_CORRECT'], timeout)


def run_primitives(timeout=1800, *, extra_body='', extra_names=()):
    body = f'''
loadt {json.dumps(str(ROOT / 'proofs/macros.ml'))};;
loadt {json.dumps(str(ROOT / 'proofs/memset.ml'))};;
loadt {json.dumps(str(ROOT / 'proofs/memcpy.ml'))};;
loadt {json.dumps(str(ROOT / 'proofs/accesses.ml'))};;
loadt {json.dumps(str(ROOT / 'proofs/optimized.ml'))};;
loadt {json.dumps(str(ROOT / 'proofs/boundaries.ml'))};;
loadt {json.dumps(str(ROOT / 'proofs/witness.ml'))};;
loadt {json.dumps(str(ROOT / 'proofs/probe_ret.ml'))};;
needs "arm/proofs/word_max.ml";;
vp_check_closed vp_probe_ret_spec VP_PROBE_RET_CORRECT;;
if hyp WORD_MAX_SUBROUTINE_CORRECT <> [] then failwith "VP: open upstream theorem";;
vp_check_closed vp_contract_witness VP_CONTRACT_WITNESS;;
vp_check_closed vp_fast_guard_spec VP_FAST_GUARD;;
vp_check_closed vp_memcpy_zero_spec VP_MEMCPY_ZERO;;
vp_check_closed vp_memcpy_scalar_zero_spec VP_MEMCPY_SCALAR_ZERO;;
vp_check_closed vp_memset_zero_spec VP_MEMSET_ZERO;;
vp_check_closed (vp_fill_contract `vp_memset_mc`) VP_MEMSET_CORRECT;;
vp_check_closed (vp_copy_contract `vp_memcpy_scalar_mc`) VP_MEMCPY_SCALAR_CORRECT;;
vp_check_closed (vp_fill_access_contract `vp_memset_mc`) VP_MEMSET_ACCESSES;;
vp_check_closed (vp_copy_access_contract `vp_memcpy_scalar_mc`) VP_MEMCPY_SCALAR_ACCESSES;;
vp_check_closed (vp_copy_contract `vp_memcpy_mc`) VP_MEMCPY_CORRECT;;
vp_check_closed (vp_copy_access_contract `vp_memcpy_mc`) VP_MEMCPY_ACCESSES;;
List.iter (fun th -> if hyp th <> [] then failwith "VP: open macro theorem")
  [VP_COPYBYTE_CORRECT;VP_FILLBYTE_CORRECT;VP_COPY8_CORRECT;
   VP_COPYBYTE_INDEXED_CORRECT;VP_FILLBYTE_INDEXED_CORRECT];;
'''
    return run_session('primitives', body+'\n'+extra_body,
        ['VP_PROBE_RET_CORRECT', 'WORD_MAX_SUBROUTINE_CORRECT', 'VP_CONTRACT_WITNESS',
         'VP_FAST_GUARD', 'VP_MEMCPY_ZERO', 'VP_MEMCPY_SCALAR_ZERO', 'VP_MEMSET_ZERO',
         'VP_COPYBYTE_CORRECT', 'VP_FILLBYTE_CORRECT', 'VP_COPY8_CORRECT',
         'VP_COPYBYTE_INDEXED_CORRECT', 'VP_FILLBYTE_INDEXED_CORRECT',
         'VP_MEMSET_CORRECT', 'VP_MEMCPY_SCALAR_CORRECT',
         'VP_MEMSET_ACCESSES', 'VP_MEMCPY_SCALAR_ACCESSES',
         'VP_MEMCPY_CORRECT', 'VP_MEMCPY_ACCESSES', *extra_names], timeout)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--probe', action='store_true')
    modes.add_argument('--primitives', action='store_true')
    args = parser.parse_args()
    run_probe() if args.probe else run_primitives()
