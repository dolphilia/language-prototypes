"""Fresh HOL sessions; actual checked theorem names must match the request."""
import json
import re
import secrets
import subprocess
import time
from config import ROOT, BASE, DEPS, BUILD, environment, opam_command, validate_dependencies, digest
from pathlib import Path


class ProofInfrastructureError(RuntimeError):
    pass


def run_session(stem, body, checks, timeout=1800, *, load_arm=True, inputs=()):
    validate_dependencies()
    BUILD.mkdir(exist_ok=True)
    receipt=BUILD/f'proof-{stem}.json'
    receipt.unlink(missing_ok=True)
    paths=[Path(__file__).resolve(),ROOT/'tools/config.py',ROOT/'proofs/checks.ml',
           ROOT/'deps.lock',BASE/'deps.lock',BASE/'opam-switch.export',
           DEPS/'hol-light/ocaml-hol',DEPS/'s2n-bignum/arm/generic/word_max.o',
           *map(Path,inputs)]
    try:
        input_hashes={str(p):digest(p) for p in paths}
    except OSError as error:
        raise ProofInfrastructureError(f'proof input missing: {error}') from error
    nonce=secrets.token_hex(24)
    expected={'nonce':nonce,'checks':checks}
    names='['+';'.join(json.dumps(n) for n in checks)+']'
    driver=f'''
use_file_raise_failure := true;;
set_color_printer false;;
loadt {json.dumps(str(ROOT/'proofs/checks.ml'))};;
{'needs "arm/proofs/base.ml";;' if load_arm else ''}
Printf.printf "VE_LOAD_CPU %.9f\\n%!" (Sys.time());;
{body}
if List.rev !ve_checks <> {names} then failwith "VE: missing or reordered theorem checks";;
check_axioms ();;
let out = open_out {json.dumps(str(receipt))} in
output_string out {json.dumps(json.dumps(expected))}; close_out out;;
exit 0;;
'''
    command=opam_command([DEPS/'hol-light/ocaml-hol','-init',DEPS/'hol-light/hol.ml',
                           '-I',DEPS/'hol-light'])
    log=BUILD/f'proof-{stem}.log'
    started=time.monotonic()
    try:
        with log.open('w') as stream:
            proc=subprocess.run(command,cwd=DEPS/'s2n-bignum',env=environment(),
                input=driver,text=True,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
        output=re.sub(r'\x1b\[[0-9;]*m','',log.read_text())
        if proc.returncode or re.search(r'(^|\n)[# \t]*(Exception:|Error:|Error in included file|Fatal error:)',output):
            raise ProofInfrastructureError(f'HOL session failed: {log}')
        if not receipt.exists() or json.loads(receipt.read_text())!=expected:
            raise ProofInfrastructureError(f'fresh receipt missing or inconsistent: {log}')
        if {str(p):digest(p) for p in paths}!=input_hashes:
            raise ProofInfrastructureError('proof inputs changed during verification')
        validate_dependencies()
    except BaseException:
        receipt.unlink(missing_ok=True)
        raise
    elapsed=time.monotonic()-started
    timings=[{'name':n,'cpu_seconds':float(t)} for n,t in
             re.findall(r'VE_TIMING (\S+) ([0-9.]+)',output)]
    result={**expected,'inputs':input_hashes,'elapsed_seconds':elapsed,'timings':timings,
            'load_cpu_seconds':float(re.search(r'VE_LOAD_CPU ([0-9.]+)',output)[1])}
    receipt.write_text(json.dumps(result,indent=2)+'\n')
    print(f'{stem}: {len(checks)} checked closed theorems, no extra axioms, {elapsed:.1f}s',flush=True)
    return result
