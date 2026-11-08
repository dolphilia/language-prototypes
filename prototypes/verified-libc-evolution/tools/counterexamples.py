"""Build HOL inputs for actual-byte finite violation witnesses."""
import json
from config import ROOT, BUILD
from build import mutations


def prepare():
    records=mutations()
    chunks=['loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/witnesses.ml");;']
    checks=[]
    for r in records:
        name=r['name']; lower='ve_mut_'+name; upper='VE_MUT_'+name.upper()
        chunks += [f'let {lower}_mc = define_assert_from_elf "{lower}_mc" '+json.dumps(r['object'])+
            ' ['+';'.join(hex(w) for w in r['words'])+'];;',
            f'let {upper}_EXEC = ARM_MK_EXEC_RULE {lower}_mc;;',
            f'let {lower}_pre = ve_pre `{lower}_mc` `{r["n"]}` `pc:num`;;',
            f'let {lower}_witness_spec = mk_comb(ve_initial_pre `{lower}_mc` `{r["n"]}`,'
                f'`ve_initial {lower}_mc {r["n"]}`);;',
            f'let {upper}_WITNESS = prove({lower}_witness_spec,ve_witness_tac {lower}_mc);;',
            f've_check "{name}:initial" {lower}_witness_spec {upper}_WITNESS;;']
        checks.append(name+':initial')
        if name=='self_branch':
            post=f'aligned_bytes_loaded s (word pc) {lower}_mc /\\ read PC s = word(pc+28)'
        elif name=='return':
            post='read PC s = word 16384 /\\ read X0 s = word 0 /\\ ~(read X0 s = word 8192)'
        elif name=='callee':
            post='read PC s = word 16384 /\\ read X19 s = word 0 /\\ ~(read X19 s = word 19)'
        else:
            post=f'~memaccess_inbounds (read events s) [word 12288,{r["n"]}] [word 8192,{r["n"]}]'
        chunks += [f'let {lower}_prefix_spec = mk_forall(`pc:num`,mk_imp('
            f'`nonoverlapping (word pc:int64,{len(r["words"])*4}) (word {8193 if name=="overwrite" else 8192},{1 if name=="overwrite" else 64})`, '
            f'list_mk_comb(`ensures_n arm`,[{lower}_pre;`\\s:armstate. {post}`;'
            f'`\\s:armstate t:armstate. T`;`\\s:armstate. {r["steps"]}`])));;',
            f'let {upper}_PREFIX = prove({lower}_prefix_spec, REPEAT STRIP_TAC THEN '
            f'REWRITE_TAC[C_ARGUMENTS] THEN ARM_SIM_TAC {upper}_EXEC (1--{r["steps"]}) THEN '
            'CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN REWRITE_TAC[] THEN TRY ve_bad_access_tac);;',
            f've_check "{name}:prefix" {lower}_prefix_spec {upper}_PREFIX;;']
        checks.append(name+':prefix')
        write_address=8193 if name=='overwrite' else 8192
        write_size=1 if name=='overwrite' else 64
        chunks += [f'let {lower}_numeric_spec = ve_numeric_pre `{lower}_mc` `{r["n"]}`;;',
            f'let {upper}_NUMERIC = prove({lower}_numeric_spec,ve_numeric_tac [{lower}_mc]);;',
            f'let {upper}_SIDE = prove('
            f'`nonoverlapping (word 4096:int64,{len(r["words"])*4}) (word {write_address},{write_size})`,'
            've_numeric_tac []);;',
            f'let {upper}_EXECUTION = ve_execution {upper}_PREFIX {upper}_SIDE {upper}_WITNESS;;',
            f'let {lower}_execution_spec = list_mk_comb(`eventually_n arm`, '
            f'[`{r["steps"]}`;vsubst [`4096`,`pc:num`] `(\\s:armstate. {post})`;'
            f'`ve_initial {lower}_mc {r["n"]}`]);;',
            f've_check "{name}:numeric" {lower}_numeric_spec {upper}_NUMERIC;;',
            f've_check "{name}:execution" {lower}_execution_spec {upper}_EXECUTION;;']
        checks += [name+':numeric',name+':execution']
    path=BUILD/'counterexamples.ml'
    path.write_text('\n'.join(chunks)+'\n')
    return path,checks


if __name__=='__main__':
    prepare()
