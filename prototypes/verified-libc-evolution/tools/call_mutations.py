"""Actual caller mutations, separately linked and executed in child processes."""
import json
import resource
import signal
import subprocess
from config import ROOT,BUILD,digest,environment
from build import run


EDITS={
 'stack':('sub sp, sp, #32','str x30, [sp]','ldr x30, [sp]','add sp, sp, #32',''),
 'register':('sub sp, sp, #16','str x30, [sp]','ldr x30, [sp]','add sp, sp, #16','mov x19, #0'),
 'return':('sub sp, sp, #16','str x30, [sp]','ldr x30, [sp]','add sp, sp, #16','mov x30, #0')}


def execute(path,mode):
    def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    return subprocess.run([str(path),mode],cwd=ROOT,env=environment(),preexec_fn=no_core,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5).returncode


def prepare():
    from build import MachO
    from call_artifacts import linked,call_object
    from build import words
    inputs=[ROOT/'tools/call_mutations.py',ROOT/'tests/call_negative.c',
        ROOT/'tests/call_stack.S',ROOT/'tests/abi.S',BUILD/'vp2_call_copy.o',BUILD/'vp2_memcpy_chunk8.o']
    before={str(p):digest(p) for p in inputs}
    common=['xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror','-fno-builtin','-fno-lto',
        '-I',ROOT/'include',ROOT/'tests/call_negative.c']
    tail=[BUILD/'vp2_memcpy_chunk8.o',BUILD/'abi_calls.o',BUILD/'call_stack.o']
    control=BUILD/'call_control';run([*common,BUILD/'vp2_call_copy.o',*tail,'-o',control])
    template=words(BUILD/'vp2_call_copy.template.words')
    obj_record=call_object(BUILD/'vp2_call_copy.o','vp2_call_copy',template)
    control_artifact=linked(control,'vp2_call_copy',obj_record,template,'control')
    rows=[]
    for mode,(sub,store,load,add,extra) in EDITS.items():
        source=BUILD/('call-mut-'+mode+'.S');obj=source.with_suffix('.o')
        lines=[sub,store,'bl _vp2_memcpy_chunk8',load,add]+([extra] if extra else [])+['ret']
        source.write_text('.text\n.p2align 2\n.globl _vp2_call_copy\n_vp2_call_copy:\n'+
            '\n'.join('    '+l for l in lines)+'\n.globl _vp2_call_copy_end\n.private_extern _vp2_call_copy_end\n_vp2_call_copy_end:\n.subsections_via_symbols\n')
        run(['xcrun','clang','-arch','arm64','-c',source,'-o',obj])
        executable=BUILD/('call-mut-'+mode);run([*common,obj,*tail,'-o',executable])
        p=MachO(executable);a=p.symbol('_vp2_call_copy');b=p.symbol('_vp2_memcpy_chunk8');section=p.sections[a.section-1]
        base=min(a.address,b.address);end=max(p.symbol('_vp2_call_copy_end').address,p.symbol('_vp2_memcpy_chunk8_end').address)
        offset=section.offset+base-section.address;data=p.span(offset,end-base)
        import struct
        instruction=struct.unpack_from('<I',data,a.address-base+8)[0]
        immediate=instruction&0x3ffffff
        if immediate&(1<<25):immediate-=1<<26
        if a.address+8+immediate*4!=b.address:raise RuntimeError('mutation unexpectedly calls a different target')
        if p.function('vp2_memcpy_chunk8')!=MachO(BUILD/'vp2_memcpy_chunk8.o').function('vp2_memcpy_chunk8'):
            raise RuntimeError('mutation changed callee')
        normal=execute(control,mode);observed=execute(executable,mode)
        if normal!=4 or observed not in ({-signal.SIGBUS,-signal.SIGSEGV} if mode=='return' else {0}):
            raise RuntimeError(f'mutation/control did not expose violation: {mode} {normal} {observed}')
        rows.append(dict(name=mode,path=str(executable),sha256=digest(executable),object=str(obj),object_sha256=digest(obj),
            bundle_file_offset=offset,bundle_bytes=len(data),caller_offset=a.address-base,callee_offset=b.address-base,
            bundle_words=list(struct.unpack('<'+'I'*(len(data)//4),data)),
            normal_control_returncode=normal,mutation_returncode=observed))
    if {str(p):digest(p) for p in inputs}!=before:raise RuntimeError('call mutation inputs changed')
    result=dict(results=rows,inputs=before,control=control_artifact,
        scope='native finite violations; HOL witnesses are checked separately')
    (BUILD/'call-mutations.json').write_text(json.dumps(result,indent=2)+'\n')
    print('call native mutations: 3; all normal controls passed',flush=True)
    return result


if __name__=='__main__':prepare()
