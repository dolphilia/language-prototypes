"""Linked checked-caller declaration and independent public specifications."""
import json
from config import BUILD


def prepare(report):
    l=report['layout'];literal=';'.join(hex(w) for w in l['bundle_words'])
    if l['caller_offset']!=0:raise RuntimeError('checked caller proof currently supports caller-first layout only')
    lines=['loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/linked_span.ml");;',
        'loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/split_specs.ml");;',
        'loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/split_success.ml");;',
        f'let ve_split_mc = ve_define_linked_span "ve_split_mc" {json.dumps(l["path"])} '
        f'{l["bundle_file_offset"]} {l["bundle_bytes"]} [{literal}];;',
        'let VE_SPLIT_EXEC = ARM_MK_EXEC_RULE ve_split_mc;;',
        f'let ve_split_call_success_spec = ve_split_require_guard (ve_split_call_contract `ve_split_mc` {l["caller_offset"]});;',
        f'let VE_SPLIT_CALL_SUCCESS = prove(ve_split_call_success_spec,ve_split_success_tac ve_split_mc VE_SPLIT_EXEC {l["caller_offset"]} {l["callee_offset"]});;',
        've_check "split:success" ve_split_call_success_spec VE_SPLIT_CALL_SUCCESS;;',
        'loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/split_public.ml");;',
        'let ve_split_call_spec = ve_split_call_contract `ve_split_mc` 0;;',
        'let VE_SPLIT_CALL_CORRECT = prove(ve_split_call_spec,ve_split_public_tac VE_SPLIT_EXEC VE_SPLIT_CALL_SUCCESS);;',
        've_check "split:public" ve_split_call_spec VE_SPLIT_CALL_CORRECT;;']
    lines += ['loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/split_trace.ml");;',
        'loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/split_access.ml");;',
        'let ve_split_access_success_spec = ve_split_require_guard (ve_split_access_contract `ve_split_mc` 0);;',
        f'let VE_SPLIT_CALL_ACCESS_SUCCESS = prove(ve_split_access_success_spec,ve_split_access_success_tac ve_split_mc VE_SPLIT_EXEC 0 {l["callee_offset"]});;',
        've_check "split:success-access" ve_split_access_success_spec VE_SPLIT_CALL_ACCESS_SUCCESS;;',
        'let ve_split_access_spec = ve_split_access_contract `ve_split_mc` 0;;',
        'let VE_SPLIT_CALL_ACCESSES = prove(ve_split_access_spec,ve_split_access_public_tac VE_SPLIT_EXEC VE_SPLIT_CALL_ACCESS_SUCCESS);;',
        've_check "split:access" ve_split_access_spec VE_SPLIT_CALL_ACCESSES;;']
    lines += ['loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/split_protocol.ml");;',
        'let ve_split_protocol_call_spec = ve_split_protocol_contract `ve_split_mc` 0;;',
        'let VE_SPLIT_CALL_PROTOCOL = prove(ve_split_protocol_call_spec,ve_split_protocol_tac VE_SPLIT_CALL_CORRECT ve_split_call_spec);;',
        've_check "split:machine-protocol" ve_split_protocol_call_spec VE_SPLIT_CALL_PROTOCOL;;']
    path=BUILD/'split-proof.ml';path.write_text('\n'.join(lines)+'\n')
    return path,['split:success','split:public','split:trace-root','split:success-access','split:access',
                 'split:region-protocol','split:machine-protocol']


if __name__=='__main__':prepare(json.loads((BUILD/'split-layout.json').read_text()))
