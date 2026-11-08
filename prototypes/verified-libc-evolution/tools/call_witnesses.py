"""Closed initial-state and finite-execution witnesses for caller violations."""
import json
from config import ROOT,BUILD


def prepare(report,mutations):
    lines=['loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/witnesses.ml");;',
           'loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/call_witnesses.ml");;']
    checks=[]
    for l in report['layouts']:
        lower='ve_call_'+l['label'];upper=lower.upper();entry=l['caller_offset']
        lines += [f'let {lower}_initial_spec = mk_comb(ve_call_pre `{lower}_mc` {entry} `4096`,`ve_call_initial {lower}_mc {entry}`);;',
            f'let {upper}_INITIAL = prove({lower}_initial_spec,ve_call_witness_tac {lower}_mc);;',
            f've_check "calls:{l["label"]}:initial" {lower}_initial_spec {upper}_INITIAL;;',
            f'let {lower}_numeric_spec = `ve_call_geometry {lower}_mc 4096 (word 32768) (word 8192) (word 12288) (word 0)`;;',
            f'let {upper}_NUMERIC = prove({lower}_numeric_spec,ve_call_numeric_tac {lower}_mc);;',
            f've_check "calls:{l["label"]}:numeric" {lower}_numeric_spec {upper}_NUMERIC;;']
        checks += [f'calls:{l["label"]}:{n}' for n in ['initial','numeric']]
    for r in mutations['results']:
        lower='ve_call_mut_'+r['name'];upper=lower.upper();entry=r['caller_offset']
        if entry!=0:raise RuntimeError('mutation witness requires caller first')
        literal=';'.join(hex(w) for w in r['bundle_words'])
        steps=2 if r['name']=='stack' else 17
        post={'stack':'~memaccess_inbounds (read events s) [word 12288,0;word 32752,16] [word 8192,0;word 32752,16]',
              'register':'read PC s = word 16384 /\\ ~(read X19 s = word 19)',
              'return':'~(read PC s = word 16384) /\\ read SP s = word 32768'}[r['name']]
        lines += [f'let {lower}_mc = ve_define_linked_span "{lower}_mc" {json.dumps(r["path"])} '
                  f'{r["bundle_file_offset"]} {r["bundle_bytes"]} [{literal}];;',
            f'let {upper}_EXEC = ARM_MK_EXEC_RULE {lower}_mc;;',
            f'let {lower}_initial_spec = mk_comb(ve_call_pre `{lower}_mc` 0 `4096`,`ve_call_initial {lower}_mc 0`);;',
            f'let {upper}_INITIAL = prove({lower}_initial_spec,ve_call_witness_tac {lower}_mc);;',
            f've_check "call-mut:{r["name"]}:initial" {lower}_initial_spec {upper}_INITIAL;;',
            f'let {lower}_side pc = vsubst [pc,`pc:num`] '
            f'`nonoverlapping (word pc:int64,LENGTH {lower}_mc) (word 32736,8) /\\ '
            f'nonoverlapping (word pc:int64,LENGTH {lower}_mc) (word 32752,8) /\\ '
            f'aligned 16 (word 32736:int64) /\\ aligned 16 (word 32752:int64) /\\ '
            f'aligned 8 (word 32736:int64) /\\ aligned 8 (word 32752:int64)`;;',
            f'let {lower}_numeric_spec = mk_conj(`ve_call_geometry {lower}_mc 4096 (word 32768) (word 8192) (word 12288) (word 0)`,{lower}_side `4096`);;',
            f'let {upper}_NUMERIC = prove({lower}_numeric_spec,ve_call_numeric_tac {lower}_mc);;',
            f've_check "call-mut:{r["name"]}:numeric" {lower}_numeric_spec {upper}_NUMERIC;;',
            f'let {lower}_prefix_spec = mk_forall(`pc:num`,mk_imp({lower}_side `pc:num`,',
            f'  list_mk_comb(`ensures_n arm`,[ve_call_pre `{lower}_mc` 0 `pc:num`;`\\s:armstate. {post}`;`\\s:armstate t:armstate. T`;`\\s:armstate. {steps}`])));;',
            f'let {upper}_PREFIX = prove({lower}_prefix_spec,REWRITE_TAC[fst {upper}_EXEC] THEN REPEAT GEN_TAC THEN STRIP_TAC THEN '
            f'REWRITE_TAC[C_ARGUMENTS;ADD_CLAUSES] THEN ARM_SIM_TAC {upper}_EXEC (1--{steps}) '
            f'THEN TRY(CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV)) THEN TRY(ve_bad_access_tac) THEN TRY ve_call_finish_numeric);;',
            f'let {upper}_EXECUTION = ve_execution {upper}_PREFIX (CONJUNCT2 {upper}_NUMERIC) {upper}_INITIAL;;',
            f'let {lower}_execution_spec = `eventually_n arm {steps} (\\s:armstate. {post}) (ve_call_initial {lower}_mc 0)`;;',
            f've_check "call-mut:{r["name"]}:execution" {lower}_execution_spec {upper}_EXECUTION;;']
        checks += [f'call-mut:{r["name"]}:{n}' for n in ['initial','numeric','execution']]
    path=BUILD/'call-witnesses.ml';path.write_text('\n'.join(lines)+'\n')
    return path,checks


if __name__=='__main__':prepare(json.loads((BUILD/'calls-layouts.json').read_text()),
                              json.loads((BUILD/'call-mutations.json').read_text()))
