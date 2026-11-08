"""Run new-kernel mutants in separate processes with core dumps disabled."""
import json
import resource
import signal
import subprocess
from config import ROOT,BUILD,environment
from build import check_span,MachO


def no_core():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))


def verify():
    common=['xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror',
            '-fno-builtin','-fno-lto','-Iinclude']
    subprocess.run([*common,'-c','tests/invoke_zero.S','-o',str(BUILD/'invoke_zero.o')],
        cwd=ROOT,env=environment(),check=True)
    records=[]
    definitions=json.loads((BUILD/'chunk-mutations.json').read_text())
    control=BUILD/'native_mut_control'
    subprocess.run([*common,'tests/chunk_negative.c',str(BUILD/'abi.o'),
        str(BUILD/'invoke_zero.o'),str(BUILD/'vp2_memcpy_chunk8.o'),'-o',str(control)],
        cwd=ROOT,env=environment(),check=True)
    for r in definitions:
        expected_control={'return':4,'frame':5,'missing-tail':6}.get(r['name'],7)
        correct=subprocess.run([str(control),r['name']],cwd=ROOT,timeout=10,preexec_fn=no_core)
        if correct.returncode!=expected_control:
            raise RuntimeError('unmodified-kernel control failed: '+r['name'])
        target=BUILD/('native_mut_'+r['name'])
        subprocess.run([*common,'tests/chunk_negative.c',str(BUILD/'abi.o'),
            str(BUILD/'invoke_zero.o'),r['object'],'-o',str(target)],cwd=ROOT,env=environment(),check=True)
        actual=MachO(r['object']).function('vp2_memcpy_chunk8',object_only=True)
        check_span(target,'vp2_memcpy_chunk8',actual,object_only=False)
        proc=subprocess.run([str(target),r['name']],cwd=ROOT,text=True,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10,preexec_fn=no_core)
        guard=r['name'] in {'short-word','extra-word','decrease'}
        if guard:
            if proc.returncode not in (-signal.SIGBUS,-signal.SIGSEGV):
                raise RuntimeError(f'{r["name"]}: expected isolated memory fault, got {proc.returncode}')
            outcome=signal.Signals(-proc.returncode).name
        else:
            if proc.returncode: raise RuntimeError(f'{r["name"]}: witness not reproduced')
            outcome=proc.stdout.strip()
        records.append({'name':r['name'],'outcome':outcome,'control_return':correct.returncode,
                        'evidence_kind':'native_supplement'})
    (BUILD/'native-mutations.json').write_text(json.dumps(records,indent=2)+'\n')
    print('new-kernel native mutation witnesses: '+str(len(records)),flush=True)
    return records


if __name__=='__main__': verify()
