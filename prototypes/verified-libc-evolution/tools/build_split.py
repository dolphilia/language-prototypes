"""Generate and execute the checked caller only after E3a/E5 are complete."""
import json
import re
import subprocess
from config import ROOT,BUILD,opam_command,environment,digest
from build import run,words
from call_artifacts import call_object,linked
from audit_calls import verification
from audit_m1 import validate_inputs


def prerequisites():
    r=verification()
    audit=json.loads((ROOT/'reports/m2/calls-audit.json').read_text())
    if not r['phase_complete'] or not audit['complete']:raise RuntimeError('E5 completion audit required')
    validate_inputs(audit['evidence_sha256'])
    region=json.loads((ROOT/'reports/m2/regions.json').read_text())
    if not region['complete'] or region['region_theorems']!=26:raise RuntimeError('E3a completion required')
    validate_inputs(region['proof']['inputs'])
    return r,region


def prepare():
    prerequisites()
    for module in ['generator','calls','split']:
        source=ROOT/'generator'/('main.ml' if module=='generator' else module+'.ml')
        run(opam_command(['ocamlc','-I',BUILD,'-c','-o',BUILD/(module+'.cmo'),source]))
    run(opam_command(['ocamlc','-I',BUILD,*[BUILD/(m+'.cmo') for m in ['generator','calls','split']],
        '-o',BUILD/'generate_split']))
    run([BUILD/'generate_split',BUILD]);name='vp2_copy_split'
    run(['xcrun','clang','-arch','arm64','-c',BUILD/(name+'.S'),'-o',BUILD/(name+'.o')])
    template=words(BUILD/(name+'.template.words'));obj=call_object(BUILD/(name+'.o'),name,template)
    if len(template)!=80 or obj['call_offset']!=52:raise RuntimeError('unexpected checked-caller layout')
    run(['xcrun','clang','-arch','arm64','-c',ROOT/'tests/split_abi.S','-o',BUILD/'split_abi.o'])
    run(['xcrun','clang','-arch','arm64','-c',ROOT/'tests/call_stack.S','-o',BUILD/'split_stack.o'])
    target=BUILD/'test_split'
    run(['xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror','-fno-builtin','-fno-lto',
        '-I',ROOT/'include',BUILD/(name+'.o'),BUILD/'vp2_memcpy_chunk8.o',ROOT/'tests/split.c',
        BUILD/'split_abi.o',BUILD/'split_stack.o','-o',target])
    layout=linked(target,name,obj,template,'split')
    output=subprocess.check_output([str(target)],cwd=ROOT,env=environment(),text=True)
    match=re.search(r'native copy-split: (\d+) checks passed',output)
    if match is None or int(match[1])<150000:raise RuntimeError('checked-caller coverage missing')
    layout['native_checks']=int(match[1]);layout['native_output']=output.strip()
    prerequisites()
    result=dict(status='native/link observations; formal proofs and mutations pending',object=obj,layout=layout)
    (BUILD/'split-layout.json').write_text(json.dumps(result,indent=2)+'\n')
    print('checked caller:',len(template),'bytes;',layout['native_checks'],'native checks',flush=True)
    return result


if __name__=='__main__':prepare()
