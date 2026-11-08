"""A real finite out-of-bounds trace for the frozen wrong-threshold candidate."""
import json
from config import ROOT, BUILD


def prepare():
    row=next(r for r in json.loads((ROOT/'reports/m3/candidates.json').read_text())['candidates']
             if r['name']=='ve_opt_u2_bad')
    name=row['name'];upper=name.upper();mc=name+'_mc';steps=11;n=8
    post='~memaccess_inbounds (read events s) [word 12288,8] [word 8192,8]'
    out=['loadt '+json.dumps(str(ROOT/'proofs/witnesses.ml'))+';;',
         f'let {mc}=define_assert_from_elf "{mc}" '+json.dumps(str(BUILD/(name+'.o')))+' ['+';'.join(row['words'])+'];;',
         f'let {upper}_EXEC=ARM_MK_EXEC_RULE {mc};;',
         f'let {name}_pre=ve_pre `{mc}` `{n}` `pc:num`;;',
         f'let {name}_initial=mk_comb(vsubst [`4096`,`pc:num`] {name}_pre,`ve_initial {mc} {n}`);;',
         f'let {upper}_INITIAL=prove({name}_initial,ve_witness_tac {mc});;',
         f'let {name}_numeric=ve_numeric_pre `{mc}` `{n}`;;',
         f'let {upper}_NUMERIC=prove({name}_numeric,ve_numeric_tac [{mc}]);;',
         f'let {upper}_SIDE=prove(`nonoverlapping (word 4096:int64,88) (word 8192,64)`,ve_numeric_tac []);;',
         f'let {name}_prefix=mk_forall(`pc:num`,mk_imp(`nonoverlapping (word pc:int64,88) (word 8192,64)`, '
         f'list_mk_comb(`ensures_n arm`,[{name}_pre;`\\s:armstate. {post}`;'
         f'`\\s:armstate t:armstate. T`;`\\s:armstate. {steps}`])));;',
         f'let {upper}_PREFIX=prove({name}_prefix,REPEAT STRIP_TAC THEN REWRITE_TAC[C_ARGUMENTS] THEN '
         f'ARM_SIM_TAC {upper}_EXEC (1--{steps}) THEN CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN '
         'REWRITE_TAC[] THEN ve_bad_access_tac);;',
         f'let {name}_execution=ve_execution {upper}_PREFIX {upper}_SIDE {upper}_INITIAL;;',
         f'let {name}_execution_spec=list_mk_comb(`eventually_n arm`,[`{steps}`;'
         f'`\\s:armstate. {post}`;`ve_initial {mc} {n}`]);;']
    checks=[]
    for label,spec,theorem in [('initial',name+'_initial',upper+'_INITIAL'),
                               ('numeric',name+'_numeric',upper+'_NUMERIC'),
                               ('prefix',name+'_prefix',upper+'_PREFIX'),
                               ('execution',name+'_execution_spec',name+'_execution')]:
        check='search:bad:'+label;checks.append(check)
        out.append(f've_check "{check}" {spec} {theorem};;')
    path=BUILD/'search-bad.ml';path.write_text('\n'.join(out)+'\n')
    return path,checks


if __name__=='__main__':prepare()
