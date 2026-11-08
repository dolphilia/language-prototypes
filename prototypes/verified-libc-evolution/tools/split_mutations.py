"""Five actual checked-caller mutations, including guarded native overflows."""
import json
import resource
import signal
import struct
import subprocess
from config import ROOT,BUILD,digest,environment
from build import MachO,words,run
from call_artifacts import call_object,linked

EDITS=[('split-range',8,0xd503201f,17,0,'functional',25),
       ('input-length',16,0xd503201f,4,8,'functional',65),
       ('output-length',28,0xd503201f,12,8,'access',42),
       ('wrong-subtraction',20,0xcb010044,12,8,'access',42),
       ('overlap-target',44,0xaa0003e0,8,1,'functional',33)]


def execute(path,mode):
    def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    return subprocess.run([str(path),mode],cwd=ROOT,env=environment(),preexec_fn=no_core,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5).returncode


def prepare():
    original=BUILD/'vp2_copy_split.o';template=words(BUILD/'vp2_copy_split.template.words')
    original_record=call_object(original,'vp2_copy_split',template)
    parsed=MachO(original);section=parsed.sections[0]
    common=['xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror','-fno-builtin','-fno-lto',
        '-I',ROOT/'include']
    control=BUILD/'split_control'
    run([*common,original,BUILD/'vp2_memcpy_chunk8.o',ROOT/'tests/split_negative.c','-o',control])
    control_record=linked(control,'vp2_copy_split',original_record,template,'control')
    paths=[ROOT/'tools/split_mutations.py',ROOT/'tests/split_negative.c',ROOT/'include/vp2_split.h',
        original,BUILD/'vp2_memcpy_chunk8.o',ROOT/'tools/call_artifacts.py']
    before={str(p):digest(p) for p in paths};rows=[]
    for name,offset,opcode,split,n,kind,steps in EDITS:
        data=bytearray(original.read_bytes());body=bytearray(template)
        struct.pack_into('<I',data,section.offset+offset,opcode);struct.pack_into('<I',body,offset,opcode)
        obj=BUILD/('split-mut-'+name+'.o');obj.write_bytes(data)
        record=call_object(obj,'vp2_copy_split',bytes(body))
        executable=BUILD/('split-mut-'+name)
        run([*common,obj,BUILD/'vp2_memcpy_chunk8.o',ROOT/'tests/split_negative.c','-o',executable])
        layout=linked(executable,'vp2_copy_split',record,bytes(body),name)
        normal=execute(control,name);observed=execute(executable,name)
        allowed={-signal.SIGBUS,-signal.SIGSEGV} if kind=='access' else {0}
        if normal!=4 or observed not in allowed:
            raise RuntimeError(f'checked-caller mutation/control failed: {name} {normal} {observed}')
        rows.append(dict(name=name,split=split,n=n,kind=kind,steps=steps,layout=layout,
            object=str(obj),object_sha256=digest(obj),normal_control_returncode=normal,mutation_returncode=observed))
    if before!={str(p):digest(p) for p in paths}:raise RuntimeError('split mutation inputs changed')
    report=dict(inputs=before,control=control_record,results=rows,
        scope='native observations; model initial states and finite executions are checked separately')
    (BUILD/'split-mutations.json').write_text(json.dumps(report,indent=2)+'\n')
    print('checked-caller mutations: 5; all unmodified controls passed',flush=True)
    return report


if __name__=='__main__':prepare()
