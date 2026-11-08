"""Rebuild, prove in a new process, and verify all M1 runtime artifacts."""
from datetime import datetime,timezone
import json
import subprocess
import time
import re
import sys
from config import ROOT,BASE,BUILD,digest,validate_dependencies,environment
from build import prepare,run,words,check_span
from verify_core import verify as prove
from measure_m1 import build as benchmarks
from native import verify as native
from native_mutations import verify as native_mutations
from artifacts import verify as artifacts


def snapshot():
    paths=[]
    for folder in ['generator','proofs','tools','tests','include','benchmarks']:
        paths += [p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts
                  and p.suffix not in {'.cmi','.cmo'}]
    paths += [ROOT/'deps.lock',ROOT/'Makefile',BASE/'proofs/specs.ml']
    return {str(p):digest(p) for p in paths}


def verify():
    started=time.monotonic();BUILD.mkdir(exist_ok=True)
    result=BUILD/'verification-m1.json';result.unlink(missing_ok=True)
    validate_dependencies()
    baseline=json.loads((ROOT/'reports/baseline.json').read_text())
    for name,expected in baseline['source_identity'].items():
        if digest(BASE/name)!=expected: raise RuntimeError('baseline source changed: '+name)
    before=snapshot()
    prepare()
    proof=prove('m1-verify')
    sizes=benchmarks()
    normal=native();mutants=native_mutations()
    run(['xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror','-fno-builtin','-fno-lto',
         ROOT/'tests/composition.c',BUILD/'abi.o',BUILD/'vp2_copy16.o',BUILD/'vp2_copy32.o',
         BUILD/'vp2_copy16_x3.o','-o',BUILD/'test_composition'])
    fixed_output=subprocess.check_output([str(BUILD/'test_composition')],cwd=ROOT,text=True)
    print(fixed_output.strip(),flush=True)
    fixed_count=re.search(r'native fixed compositions: (\d+)',fixed_output)
    if fixed_count is None or int(fixed_count[1])<192: raise RuntimeError('fixed-size native cases missing')
    for name in ['vp2_copy16','vp2_copy32','vp2_copy16_x3']:
        check_span(BUILD/'test_composition',name,words(BUILD/(name+'.words')),object_only=False)
    runtime=artifacts()
    tests={}
    for label,directory,pattern,minimum in [
        ('results','tests','test_results.py',3),('artifacts','tests','test_artifacts.py',3),
        ('proof_driver','tests','test_driver.py',5),
        ('baseline_artifacts',BASE/'tests','test_artifacts.py',9)]:
        log=BUILD/('m1-'+label+'.log')
        with log.open('w') as stream:
            subprocess.run([sys.executable,'-m','unittest','discover','-s',str(directory),'-p',pattern],
                cwd=ROOT,env=environment(),stdout=stream,stderr=subprocess.STDOUT,check=True)
        matched=re.search(r'Ran (\d+) tests?',log.read_text())
        if matched is None or int(matched[1])<minimum:
            raise RuntimeError('required tests missing: '+label)
        tests[label]=int(matched[1])
    after=snapshot()
    if after!=before: raise RuntimeError('M1 inputs changed during verification')
    report=dict(timestamp=datetime.now(timezone.utc).isoformat(),seconds=time.monotonic()-started,
        python=sys.version,python_executable=sys.executable,
        verification_passed=True,phase_complete=False,
        remaining_evaluation='proof-costs and performance reports must pass the M1 audit',
        source_files=after,proof=proof,native=normal,native_mutations=mutants,
        linked_artifacts=runtime,sizes=sizes,
        tests=tests|{'fixed_native_cases':int(fixed_count[1])})
    result.write_text(json.dumps(report,indent=2)+'\n')
    folder=ROOT/'reports/m1';folder.mkdir(exist_ok=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    (folder/'core-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    from registry import build_registry
    (folder/'candidates.json').write_text(json.dumps(build_registry(proof),indent=2)+'\n')
    print(f'M1 verification gates passed in {report["seconds"]:.1f}s; evaluation audit still required',flush=True)
    return report


if __name__=='__main__': verify()
