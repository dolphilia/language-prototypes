"""Offline end-to-end verification, fresh proofs, native tests, failure gates."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json
import os
import platform
import re
import signal
import subprocess
import sys
import time
from run_proof import ROOT,environment,run_primitives
from check_artifacts import check_probe,check_primitives,FUNCTIONS
from negative_proofs import prepare
from macho import MachO


def run(*args,**kwargs):
    return subprocess.run(list(map(str,args)),cwd=ROOT,check=True,**kwargs)


def output(*args,**kwargs):
    return subprocess.check_output(list(map(str,args)),cwd=ROOT,text=True,**kwargs).strip()


def dependencies():
    if (platform.system(),platform.machine()) != ('Darwin','arm64'):
        raise RuntimeError('native macOS arm64 is required')
    lock=json.loads((ROOT/'deps.lock').read_text())
    for name in ['hol-light','s2n-bignum']:
        path=ROOT/'.deps'/name
        if output('git','-C',path,'rev-parse','HEAD') != lock[name]['commit']:
            raise RuntimeError(name+': pinned commit mismatch')
        if output('git','-C',path,'status','--porcelain','--untracked-files=no'):
            raise RuntimeError(name+': modified dependency source')
    env=environment()
    packages=output('opam','list','--switch',ROOT/'.deps/ocaml','--installed',
                    '--columns=name,version','--short','--color=never',env=env)
    actual={'.'.join(line.split()) for line in packages.splitlines()}
    exported=re.search(r'\ninstalled: \[(.*?)\n\]',(ROOT/'opam-switch.export').read_text(),re.S)
    expected=set(re.findall(r'"([^"\n]+)"',exported[1]))
    if actual!=expected:
        raise RuntimeError('installed OCaml packages differ from opam-switch.export')
    if output('ocamlc','-version',env=env)!=lock['ocaml-system']:
        raise RuntimeError('system OCaml mismatch')
    return dict(platform=platform.platform(),python=sys.version,
        compiler=output('xcrun','clang','--version'),sdk=output('xcrun','--show-sdk-version'),
        dependencies=lock,ocaml_packages=packages.splitlines())


def snapshot():
    paths=[ROOT/'Makefile',ROOT/'deps.lock',ROOT/'opam-switch.export']
    for folder in ['generator','proofs','tools','tests','include','benchmarks']:
        paths += [p for p in (ROOT/folder).rglob('*') if p.is_file()
                  and '__pycache__' not in p.parts and p.suffix not in ('.cmi','.cmo')]
    paths += [ROOT/'build'/f'{n}.o' for n in FUNCTIONS]
    paths += [ROOT/'build'/f'{n}.words' for n in FUNCTIONS]
    paths += list((ROOT/'build').glob('vp_macro_*.o'))
    paths += list((ROOT/'build').glob('mut_*.o'))
    paths += [ROOT/'build/negative-proofs.ml',ROOT/'build/scalar/vp_memcpy.o',
              ROOT/'.deps/hol-light/ocaml-hol',
              ROOT/'.deps/s2n-bignum/arm/generic/word_max.o']
    paths += [ROOT/'build'/p for p in ['test_memory','probe_ret','probe_ret.o','benchmark',
                                     'size_scalar','size_optimized','guard_control',
                                     'guard_overread','guard_overwrite']]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def independent_symbols():
    for filename in [*(name+'.o' for name in FUNCTIONS),'test_memory','benchmark']:
        path=ROOT/'build'/filename
        listing=output('xcrun','llvm-objdump','--macho','--syms',path)
        (ROOT/'build'/(filename+'.symbols.txt')).write_text(listing+'\n')
        parsed=MachO(path)
        names=[filename[:-2]] if filename.endswith('.o') else FUNCTIONS
        for name in names:
            for suffix in ['', '_end']:
                symbol='_'+name+suffix
                found=re.findall(r'^([0-9a-f]+)\s+.*?\s'+re.escape(symbol)+r'$',listing,re.M)
                if len(found)!=1 or int(found[0],16)!=parsed.symbol(symbol).address:
                    raise RuntimeError('LLVM symbol listing disagrees with extraction: '+symbol)
        disasm=output('xcrun','llvm-objdump','--macho','--disassemble',path)
        (ROOT/'build'/(filename+'.disassembly.txt')).write_text(disasm+'\n')


def build_guard_tests():
    for name,obj in [('control','vp_memcpy_scalar.o'),('overread','mut_overread.o'),
                     ('overwrite','mut_overwrite.o')]:
        run('xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror',
            '-fno-builtin','-fno-lto','-Iinclude','tests/guard_negative.c',
            ROOT/'build'/obj,'-o',ROOT/'build'/('guard_'+name))


def guard_negatives():
    run(ROOT/'build/guard_control')
    results={}
    for name in ['overread','overwrite']:
        proc=subprocess.run([str(ROOT/'build'/('guard_'+name))],cwd=ROOT)
        if proc.returncode not in (-signal.SIGSEGV,-signal.SIGBUS):
            raise RuntimeError(f'guard {name}: expected memory fault, got {proc.returncode}')
        results[name]=signal.Signals(-proc.returncode).name
    print('native guard negatives rejected: '+str(results),flush=True)
    return results


def main():
    started=time.monotonic()
    result=ROOT/'build/verification.json'
    result.unlink(missing_ok=True)
    env=dependencies()
    run('make','p1-objects','p2-objects','build/test_memory','build/probe_ret',
        '.deps/s2n-bignum/arm/generic/word_max.o','bench-build')
    check_probe();check_primitives(('test_memory','benchmark'))
    independent_symbols()
    negative,names=prepare()
    build_guard_tests()
    before=snapshot()
    proof=run_primitives(extra_body=f'loadt {json.dumps(str(negative))};;',
                         extra_names=['rejected:'+n for n in names])
    if snapshot()!=before: raise RuntimeError('sources/artifacts changed during proof')
    check_probe();check_primitives(('test_memory','benchmark'))
    run(ROOT/'build/probe_ret')
    native=output(ROOT/'build/test_memory'); print(native,flush=True)
    guards=guard_negatives()
    run(sys.executable,'-m','unittest','discover','-s','tests','-p','test_artifacts.py')
    run(sys.executable,'-m','unittest','discover','-s','tests','-p','test_proof_driver.py')
    if snapshot()!=before: raise RuntimeError('sources/artifacts changed during native checks')
    report=dict(timestamp=datetime.now(timezone.utc).isoformat(),
        seconds=time.monotonic()-started,environment=env,files=before,proof=proof,
        native=native,semantic_negatives=names,guard_negatives=guards,
        artifact_tests=9,proof_driver_tests=5)
    result.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f'verify: all gates passed in {report["seconds"]:.1f}s; {result}',flush=True)


if __name__=='__main__': main()
