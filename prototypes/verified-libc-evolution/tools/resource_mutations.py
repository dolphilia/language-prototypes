"""Real add/delete mutations, valid initial states, exact finite cost witnesses."""
import json
import struct
from config import ROOT, BUILD
from build import run, MachO


def prepare():
    text=(ROOT/'proofs/witnesses.ml').read_text()
    initial=text[text.index('let ve_initial ='):text.index('let ve_pre code')]
    initial=initial.replace('ve_initial','ve_cost_initial').replace('word 16384','word 4096')
    out=['loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/witnesses.ml");;',initial]
    records=[];checks=[]
    for kind,n,old,new in [('add',0,3,4),('delete',1,8,7)]:
        name='ve_cost_'+kind
        code=['mov x3,#0']
        if kind=='add': code+=['cbz x2,Lend']
        code+=['Lloop:','ldrb w4,[x1,x3]','strb w4,[x0,x3]',
               'add x3,x3,#1','cmp x3,x2','b.lo Lloop','Lend:']
        if kind=='add':code+=['nop']
        code+=['ret']
        assembly='\n'.join(['.text','.p2align 2',f'.globl _{name}',f'_{name}:',*code,
              f'.globl _{name}_end',f'.private_extern _{name}_end',f'_{name}_end:',
              '.subsections_via_symbols',''])
        (BUILD/(name+'.S')).write_text(assembly)
        run(['xcrun','clang','-arch','arm64','-c',BUILD/(name+'.S'),'-o',BUILD/(name+'.o')])
        data=MachO(BUILD/(name+'.o')).function(name)
        literal=';'.join(hex(w) for w in struct.unpack('<'+'I'*(len(data)//4),data))
        upper=name.upper();mc=name+'_mc'
        out += [f'let {mc}=define_assert_from_elf "{mc}" '+json.dumps(str(BUILD/(name+'.o')))+f' [{literal}];;',
                f'let {upper}_EXEC=ARM_MK_EXEC_RULE {mc};;',
                f'let {name}_pre=subst [`word pc:int64`,`word 16384:int64`] (ve_pre `{mc}` `{n}` `pc:num`);;',
                f'let {name}_initial=mk_comb(vsubst [`4096`,`pc:num`] {name}_pre,`ve_cost_initial {mc} {n}`);;',
                f'let {upper}_INITIAL=prove({name}_initial,REWRITE_TAC[ve_cost_initial] THEN ve_witness_tac {mc});;',
                f'let {name}_numeric=ve_numeric_pre `{mc}` `{n}`;;',
                f'let {upper}_NUMERIC=prove({name}_numeric,ve_numeric_tac [{mc}]);;',
                f'let {upper}_SIDE=prove(`nonoverlapping (word 4096:int64,{len(data)}) (word 8192,64)`,ve_numeric_tac []);;']
        for label,steps,post in [('old',old,'~(read PC s = word pc)'),('new',new,'read PC s = word pc')]:
            prefix=name+'_'+label
            out += [f'let {prefix}_spec=mk_forall(`pc:num`,mk_imp('
                f'`nonoverlapping (word pc:int64,{len(data)}) (word 8192,64)`, '
                f'list_mk_comb(`ensures_n arm`,[{name}_pre;`\\s:armstate. {post}`;'
                f'`\\s:armstate t:armstate. T`;`\\s:armstate. {steps}`])));;',
                f'let {prefix.upper()}=prove({prefix}_spec,REPEAT STRIP_TAC THEN REWRITE_TAC[C_ARGUMENTS] THEN '
                f'ARM_SIM_TAC {upper}_EXEC (1--{steps}) THEN TRY(CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV)) THEN '
                'REWRITE_TAC[WORD_ADD] THEN TRY(GEN_REWRITE_TAC RAND_CONV [GSYM WORD_SUB_EQ_0] THEN '
                'REWRITE_TAC[WORD_RULE `word_sub (word_add (a:int64) b) a = b`] THEN '
                'CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN REWRITE_TAC[]));;',
                f'let {prefix}_execution=ve_execution {prefix.upper()} {upper}_SIDE {upper}_INITIAL;;',
                f'let {prefix}_execution_spec=list_mk_comb(`eventually_n arm`,[`{steps}`;'
                f'vsubst [`4096`,`pc:num`] `\\s:armstate. {post}`;`ve_cost_initial {mc} {n}`]);;']
            for suffix,spec,theorem in [('prefix',prefix+'_spec',prefix.upper()),
                                       ('execution',prefix+'_execution_spec',prefix+'_execution')]:
                check=f'cost-mutation:{kind}:{label}:{suffix}'
                out.append(f've_check "{check}" {spec} {theorem};;');checks.append(check)
        for suffix,spec,theorem in [('initial',name+'_initial',upper+'_INITIAL'),
                                   ('numeric',name+'_numeric',upper+'_NUMERIC')]:
            check=f'cost-mutation:{kind}:{suffix}'
            out.append(f've_check "{check}" {spec} {theorem};;');checks.append(check)
        records.append(dict(name=name,n=n,old_steps=old,actual_return_steps=new,
                            old_endpoint_violates_return=True,returnaddress=4096,
                            object=str(BUILD/(name+'.o')),
                            evidence_kind='HOL finite execution; not a failed tactic'))
    path=BUILD/'resource-mutations.ml';path.write_text('\n'.join(out)+'\n')
    (BUILD/'resource-mutations.json').write_text(json.dumps(records,indent=2)+'\n')
    return path,checks


if __name__=='__main__':prepare()
