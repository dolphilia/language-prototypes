"""Isolated actual-code violations, each with an unmodified normal control."""
import json
import resource
import signal
import subprocess
from config import ROOT,BUILD,digest,environment
from build import run,check_span,MachO
from move_mutations import EDITS


def execute(path,name):
    def no_core(): resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    return subprocess.run([str(path),name],cwd=ROOT,env=environment(),preexec_fn=no_core,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5).returncode


def verify():
    records=json.loads((BUILD/'move-mutations.json').read_text())
    if [r['name'] for r in records]!=[r[0] for r in EDITS]:raise RuntimeError('mutation manifest incomplete')
    inputs=[ROOT/'tools/native_move_mutations.py',ROOT/'tools/move_mutations.py',
            ROOT/'tests/move_negative.c',BUILD/'vp2_memmove.o',*[r['object'] for r in records]]
    before={str(p):digest(p) for p in inputs}
    common=['xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror','-fno-builtin','-fno-lto',
            ROOT/'tests/move_negative.c']
    control=BUILD/'move_control';run([*common,BUILD/'vp2_memmove.o','-o',control])
    check_span(control,'vp2_memmove',MachO(BUILD/'vp2_memmove.o').function('vp2_memmove'),object_only=False)
    results=[]
    for r in records:
        if digest(r['object'])!=r['sha256']:raise RuntimeError('mutation object changed')
        target=BUILD/('move_negative_'+r['name'])
        run([*common,r['object'],'-o',target])
        check_span(target,'vp2_memmove',MachO(r['object']).function('vp2_memmove'),object_only=False)
        normal=execute(control,r['name']);observed=execute(target,r['name'])
        if normal!=4:raise RuntimeError('normal control failed: '+r['name'])
        allowed={0} if r['kind']=='functional' else {-signal.SIGBUS,-signal.SIGSEGV}
        if observed not in allowed:raise RuntimeError('expected violation missing: '+r['name']+' '+str(observed))
        results.append(dict(name=r['name'],kind=r['kind'],normal_control_returncode=normal,
            mutation_returncode=observed,object_sha256=digest(r['object']),executable_sha256=digest(target)))
    if {str(p):digest(p) for p in inputs}!=before:raise RuntimeError('mutation inputs changed during native observations')
    folder=ROOT/'reports/m2';folder.mkdir(exist_ok=True)
    report=dict(results=results,inputs=before,scope='native observations, not a negation of a HOL Hoare theorem')
    (folder/'memmove-native-mutations.json').write_text(json.dumps(report,indent=2)+'\n')
    print('memmove native mutation witnesses: 8; all unmodified controls passed',flush=True)
    return report


if __name__=='__main__': verify()
