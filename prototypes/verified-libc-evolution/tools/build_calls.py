"""Generate the one-call object and two concrete executable layouts."""
import json
import re
import subprocess
from config import ROOT,BUILD,opam_command,environment
from build import run,words
from call_artifacts import call_object,linked
from verify_regions import require_m1


def prepare():
    require_m1()
    run(opam_command(['ocamlc','-c','-o',BUILD/'generator.cmo',ROOT/'generator/main.ml']))
    run(opam_command(['ocamlc','-I',BUILD,'-c','-o',BUILD/'calls.cmo',ROOT/'generator/calls.ml']))
    run(opam_command(['ocamlc','-I',BUILD,BUILD/'generator.cmo',BUILD/'calls.cmo','-o',BUILD/'generate_calls']))
    run([BUILD/'generate_calls',BUILD])
    name='vp2_call_copy'
    run(['xcrun','clang','-arch','arm64','-c',BUILD/(name+'.S'),'-o',BUILD/(name+'.o')])
    template=words(BUILD/(name+'.template.words'))
    record=call_object(BUILD/(name+'.o'),name,template)
    padding=BUILD/'vp2_link_padding.S'
    padding.write_text('.text\n.p2align 2\n.globl _vp2_link_padding\n_vp2_link_padding:\n.rept 64\nnop\n.endr\n.globl _vp2_link_padding_end\n.private_extern _vp2_link_padding_end\n_vp2_link_padding_end:\n.subsections_via_symbols\n')
    for source,target in [(padding,BUILD/'vp2_link_padding.o'),(ROOT/'tests/abi.S',BUILD/'abi_calls.o'),
                          (ROOT/'tests/call_stack.S',BUILD/'call_stack.o')]:
        run(['xcrun','clang','-arch','arm64','-c',source,'-o',target])
    common=['xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror','-fno-builtin','-fno-lto',
            '-I',ROOT/'include','-c',ROOT/'tests/calls.c','-o',BUILD/'calls_test.o']
    run(common)
    layouts=[]
    for label,objects in [('a',[name,'vp2_memcpy_chunk8']),
                          ('b',['vp2_memcpy_chunk8','vp2_link_padding',name])]:
        target=BUILD/('test_calls_'+label)
        run(['xcrun','clang','-arch','arm64',*[BUILD/(n+'.o') for n in objects],
             BUILD/'calls_test.o',BUILD/'abi_calls.o',BUILD/'call_stack.o','-o',target])
        layout=linked(target,name,record,template,label)
        output=subprocess.check_output([str(target)],cwd=ROOT,env=environment(),text=True)
        count=re.search(r'native call-copy: (\d+) checks passed',output)
        if count is None or int(count[1])<10000:raise RuntimeError('call/stack native coverage missing')
        layout['native_checks']=int(count[1]);layout['native_output']=output.strip();layouts.append(layout)
    if len({(l['caller_offset'],l['callee_offset'],l['displacement']) for l in layouts})!=2:
        raise RuntimeError('two genuinely different call layouts required')
    report=dict(status='link/native observations only; E5 formal and rejection gates pending',
                object=record,layouts=layouts)
    (BUILD/'calls-layouts.json').write_text(json.dumps(report,indent=2)+'\n')
    print('call layouts:',[(l['label'],l['bundle_bytes'],l['displacement'],l['native_checks']) for l in layouts],flush=True)
    return report


if __name__=='__main__': prepare()
