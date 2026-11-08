"""Predeclared offset/scratch/frame edits for Copy16 and Copy32."""
import json
import struct
import time
from config import ROOT,BUILD,digest,opam_command
from build import run,words,check_span
from proof_text import timed_declarations


def prepare():
    started=time.monotonic()
    run(opam_command(['ocamlc','-I',BUILD,'-c','-o',BUILD/'edits.cmo',ROOT/'generator/edits.ml']))
    run(opam_command(['ocamlc','-o',BUILD/'generate-edits',BUILD/'generator.cmo',BUILD/'edits.cmo']))
    run([BUILD/'generate-edits',BUILD])
    out=['loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/edit_specs.ml");;']
    records=[];checks=[];rejects=[]
    for width in [16,32]:
        for family in ['offset','scratch','frame']:
            name=f'vp2_edit_{family}{width}';upper=name.upper()
            offsets=[0 if family=='offset' and j==1 else j*8 for j in range(width//8)]
            scratch=[3 if family=='scratch' and j==0 else 4 for j in range(width//8)]
            data=words(BUILD/(name+'.words'))
            run(['xcrun','clang','-arch','arm64','-c',BUILD/(name+'.S'),'-o',BUILD/(name+'.o')])
            check_span(BUILD/(name+'.o'),name,data)
            direct=name+'_direct'
            # Independent literal instruction printer; does not call the OCaml IR.
            assembly=f'.text\n.p2align 2\n.globl _{direct}\n_{direct}:\n'
            for off,reg in zip(offsets,scratch):
                assembly+=f' ldr x{reg}, [x1, #{off}]\n str x{reg}, [x0, #{off}]\n'
            assembly+=f' ret\n.globl _{direct}_end\n.private_extern _{direct}_end\n_{direct}_end:\n.subsections_via_symbols\n'
            (BUILD/(direct+'.S')).write_text(assembly)
            run(['xcrun','clang','-arch','arm64','-c',BUILD/(direct+'.S'),'-o',BUILD/(direct+'.o')])
            check_span(BUILD/(direct+'.o'),direct,data)
            literal=';'.join(hex(w) for w in struct.unpack('<'+'I'*(len(data)//4),data))
            children=[]
            for off,reg in zip(offsets,scratch):
                child=f'vp2_block_copy8_{off}' if reg==4 else 'vp2_block_copy8_x3'
                children.append(f'({off//8},Ve_block.code {child}_block,Ve_block.theorem {child}_block)')
            args='['+';'.join(children)+']'
            for variant in ['composed','direct']:
                symbol=name if variant=='composed' else direct
                lower=symbol;theorem=upper+'_'+variant.upper()
                out += [f'let {lower}_mc=define_assert_from_elf "{lower}_mc" '
                    f'(Sys.getenv "VP_EVOLUTION_ROOT" ^ "/build/{symbol}.o") [{literal}];;',
                    f'let {theorem}_EXEC=ARM_MK_EXEC_RULE {lower}_mc;;']
                permitted='~scratch:[`X3`;`X4`] ' if family=='scratch' else ''
                out.append(f'let {lower}_spec=ve_fixedcopy_spec {permitted}`{lower}_mc` {width};;')
                if variant=='composed':
                    tactic=f've_edit_composed_tac {lower}_mc {theorem}_EXEC {args}'
                else:
                    tactic=f'REWRITE_TAC[fst {theorem}_EXEC] THEN CONV_TAC(DEPTH_CONV EXPAND_CASES_CONV) THEN '
                    tactic+=f'CONV_TAC NUM_REDUCE_CONV THEN REWRITE_TAC[WORD_ADD_0] THEN REPEAT STRIP_TAC THEN '
                    tactic+=f'ARM_SIM_TAC {theorem}_EXEC (1--{width//4+1}) THEN REWRITE_TAC[APPEND]'
                label=f'edit:{family}{width}:{variant}'
                if family=='offset':
                    out.append(f've_edit_reject "{label}" (fun () -> prove({lower}_spec,{tactic}));;')
                    rejects.append(label)
                else:
                    out += [f'let {theorem} = prove({lower}_spec,{tactic});;',
                        f've_check "{label}" {lower}_spec {theorem};;']
                    checks.append(label)
                if family=='scratch':
                    bad_spec=f've_fixedcopy_spec `{lower}_mc` {width}'
                    bad_label=f'edit:frame-before-repair{width}:{variant}'
                    out.append(f've_edit_reject "{bad_label}" (fun () -> prove({bad_spec},{tactic}));;')
                    rejects.append(bad_label)
            records.append(dict(family=family,width=width,offsets=offsets,scratch=scratch,
                direct_and_composed_identical=True,body_bytes=len(data),
                source_files=[str(BUILD/(name+'.S')),str(BUILD/(direct+'.S'))],
                proof_children=[str((off,reg)) for off,reg in zip(offsets,scratch)],
                new_child_theorems=0,manual_per_edit_hints=0,
                classification='native counterexample + rejected proof attempts' if family=='offset' else 'closed proofs'))
    out.append('if List.rev !ve_edit_rejections <> '+
        '['+';'.join(json.dumps(n) for n in rejects)+'] then failwith "missing edit rejection";;')
    path=BUILD/'edit-experiments.ml';path.write_text(timed_declarations(out))
    result=dict(initial_automated_prepare_seconds=time.monotonic()-started,
        scope='automated initial edit/build operation, not human development time',
        source_sha256={str(ROOT/p):digest(ROOT/p) for p in ['generator/edits.ml','proofs/edit_specs.ml','tools/edit_experiments.py']},
        experiments=records,expected_rejections=rejects,expected_checks=checks)
    (BUILD/'edit-experiments.json').write_text(json.dumps(result,indent=2)+'\n')
    return path,checks


if __name__=='__main__': prepare()
