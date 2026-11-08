"""Linked-byte declarations and independently fixed caller contracts."""
import json
from config import ROOT,BUILD


def declarations(report):
    lines=['loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/linked_span.ml");;',
           'loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/call_specs.ml");;',
           'loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/calls.ml");;']
    checks=[]
    for layout in report['layouts']:
        lower='ve_call_'+layout['label'];upper=lower.upper()
        literal=';'.join(hex(w) for w in layout['bundle_words'])
        lines += [f'let {lower}_mc = ve_define_linked_span "{lower}_mc" '
            f'{json.dumps(layout["path"])} {layout["bundle_file_offset"]} {layout["bundle_bytes"]} [{literal}];;',
            f'let {upper}_EXEC = ARM_MK_EXEC_RULE {lower}_mc;;',
            f'let {lower}_embedding_spec = `SUB_LIST ({layout["callee_offset"]},76) {lower}_mc = vp2_memcpy_chunk8_mc`;;',
            f'let {upper}_EMBEDDING = prove({lower}_embedding_spec,REWRITE_TAC[{lower}_mc;vp2_memcpy_chunk8_mc] THEN CONV_TAC(LAND_CONV SUB_LIST_CONV) THEN REFL_TAC);;',
            f've_check "calls:{layout["label"]}:embedding" {lower}_embedding_spec {upper}_EMBEDDING;;',
            f'let {lower}_spec = ve_call_contract `{lower}_mc` {layout["caller_offset"]};;',
            f'let {upper}_CORRECT = prove({lower}_spec,ve_call_tac {lower}_mc {upper}_EXEC '
            f'{layout["caller_offset"]} {layout["callee_offset"]});;',
            f've_check "calls:{layout["label"]}:functional" {lower}_spec {upper}_CORRECT;;',
            f'let {lower}_access_spec = ve_call_access_contract `{lower}_mc` {layout["caller_offset"]};;',
            f'let {upper}_ACCESSES = prove({lower}_access_spec,ve_call_access_tac {lower}_mc {upper}_EXEC '
            f'{layout["caller_offset"]} {layout["callee_offset"]});;',
            f've_check "calls:{layout["label"]}:access" {lower}_access_spec {upper}_ACCESSES;;']
        checks += [f'calls:{layout["label"]}:{n}' for n in ['embedding','functional','access']]
    path=BUILD/'calls-proof.ml';path.write_text('\n'.join(lines)+'\n')
    return path,checks


if __name__=='__main__': declarations(json.loads((BUILD/'calls-layouts.json').read_text()))
