"""Build the frozen five candidates and check real object/executable spans."""
import importlib.util
import json
import resource
import signal
import struct
import subprocess
import time
from config import ROOT, BASE, BUILD, environment, digest
from build import MachO, check_span

FROZEN=ROOT/'reports/m3/candidates.json'


def run(args, **kwargs):
    return subprocess.run(list(map(str,args)),cwd=ROOT,env=environment(),check=True,**kwargs)


def prepare():
    started=time.monotonic()
    path=ROOT/'generator/candidates.py'
    spec=importlib.util.spec_from_file_location('ve_candidates',path)
    generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)
    generator.generate(BUILD)
    rows=[]
    for name,u,init,k,kind in generator.CANDIDATES:
        run(['xcrun','clang','-arch','arm64','-c',BUILD/(name+'.S'),'-o',BUILD/(name+'.o')])
        data=MachO(BUILD/(name+'.o')).function(name)
        words=struct.unpack('<'+'I'*(len(data)//4),data)
        (BUILD/(name+'.words')).write_text(''.join(f'{w:08x}\n' for w in words))
        if len(data)+28>256:raise RuntimeError('candidate exceeds the M1 body budget')
        rows.append(dict(name=name,unroll=u,initialization=init,threshold=k,kind=kind,
                         bytes=len(data),words=[hex(w) for w in words],object_sha256=digest(BUILD/(name+'.o'))))
    frozen=dict(generator_sha256=digest(path),protocol_sha256=digest(ROOT/'reports/m3/search-protocol.md'),
                candidates=rows,measured=False)
    if json.loads(FROZEN.read_text()) != frozen:
        raise RuntimeError('candidate set changed after the protocol was frozen')
    if MachO(BUILD/'ve_opt_u1_mov.o').function('ve_opt_u1_mov') != MachO(BUILD/'vp2_memcpy_chunk8.o').function('vp2_memcpy_chunk8'):
        raise RuntimeError('original candidate is not the original M1 body')
    result=dict(seconds=time.monotonic()-started,frozen_sha256=digest(FROZEN),candidates=rows)
    (BUILD/'search-preparation.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def native(names=None, *, tag='pool'):
    frozen=json.loads(FROZEN.read_text())
    names=names or [r['name'] for r in frozen['candidates'] if r['threshold']==8*r['unroll']]
    common=['xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror',
            '-fno-builtin','-fno-lto','-Iinclude']
    run([*common,'-c',ROOT/'tests/abi.S','-o',BUILD/'search-abi.o'])
    results=[]
    for name in names:
        target=BUILD/(name+'-'+tag+'-native')
        run([*common,'-Dvp2_memcpy_chunk8='+name,ROOT/'tests/memory.c',BUILD/'search-abi.o',
             BASE/'build/vp_memcpy_scalar.o',BASE/'build/vp_memcpy.o',BUILD/'vp2_memset.o',
             BUILD/(name+'.o'),'-o',target])
        body=MachO(BUILD/(name+'.o')).function(name)
        check_span(target,name,body,object_only=False)
        result=run([target],text=True,stdout=subprocess.PIPE).stdout.strip()
        results.append(dict(name=name,result=result,executable_sha256=digest(target)))
        print(name+': '+result,flush=True)
    # A concrete wrong-threshold witness and its normal control at n=8.
    run([*common,'-c',ROOT/'tests/invoke_zero.S','-o',BUILD/'search-invoke.o'])
    outcomes=[]
    for name in ['ve_opt_u2_mov','ve_opt_u2_bad']:
        target=BUILD/(name+'-'+tag+'-negative')
        run([*common,'-Dvp2_memcpy_chunk8='+name,ROOT/'tests/chunk_negative.c',
             BUILD/'search-abi.o',BUILD/'search-invoke.o',BUILD/(name+'.o'),'-o',target])
        check_span(target,name,MachO(BUILD/(name+'.o')).function(name),object_only=False)
        def no_core(): resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        proc=subprocess.run([str(target),'extra-word'],cwd=ROOT,env=environment(),
                            timeout=5,preexec_fn=no_core)
        if name.endswith('_bad'):
            if proc.returncode not in [-signal.SIGBUS,-signal.SIGSEGV]:
                raise RuntimeError('wrong threshold did not reproduce a guard violation')
        elif proc.returncode!=7:raise RuntimeError('normal threshold control failed')
        outcomes.append(dict(name=name,returncode=proc.returncode,executable_sha256=digest(target)))
    result=dict(positive=results,negative=outcomes,evidence_kind='finite native observations only')
    (BUILD/('search-native-'+tag+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    prepare();native()
