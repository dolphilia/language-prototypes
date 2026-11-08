"""Actual linked-byte finite witnesses, independent from tactic failures."""
import json
from config import BUILD


def prepare(report,mutations):
    lines=['loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/witnesses.ml");;',
           'loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/split_witnesses.ml");;']
    checks=[]
    for row in [None,*mutations['results']]:
        positive=row is None;name='positive' if positive else row['name']
        lower='ve_split' if positive else 've_split_mut_'+name.replace('-','_')
        upper=lower.upper();split=8 if positive else row['split'];n=1 if positive else row['n']
        label='split:positive' if positive else 'split-mut:'+name
        if not positive:
            l=row['layout'];literal=';'.join(hex(w) for w in l['bundle_words'])
            lines += [f'let {lower}_mc = ve_define_linked_span "{lower}_mc" {json.dumps(l["path"])} '
                f'{l["bundle_file_offset"]} {l["bundle_bytes"]} [{literal}];;',
                f'let {upper}_EXEC = ARM_MK_EXEC_RULE {lower}_mc;;']
        code_cells=' /\\ '.join(f'nonoverlapping (word pc:int64,LENGTH {lower}_mc) (word {a},1)' for a in range(8192,8224))
        stack_cells=' /\\ '.join(f'nonoverlapping (word 32752:int64,8) (word {a},1)' for a in range(8192,8224))
        lines += [f'let {lower}_initial_spec = mk_comb(ve_split_witness_pre `{lower}_mc` {split} {n} `4096`, '
                  f'`ve_split_initial {lower}_mc {split} {n}`);;',
            f'let {upper}_INITIAL = prove({lower}_initial_spec,ve_split_witness_tac {lower}_mc);;',
            f've_check "{label}:initial" {lower}_initial_spec {upper}_INITIAL;;',
            f'let {lower}_side pc = vsubst [pc,`pc:num`] '
            f'`nonoverlapping (word pc:int64,LENGTH {lower}_mc) (word 8192,32) /\\ '
            f'nonoverlapping (word pc:int64,LENGTH {lower}_mc) (word 32752,16) /\\ '
            f'nonoverlapping (word 8192:int64,1) (word 8200,1) /\\ '
            f'nonoverlapping (word 8200:int64,1) (word 8192,1) /\\ '
            f'aligned 16 (word 32752:int64) /\\ aligned 8 (word 32752:int64) /\\ {code_cells} /\\ {stack_cells}`;;',
            f'let {lower}_numeric_spec = mk_conj(`ve_split_geometry {lower}_mc 4096 (word 32768) (word 8192) (word 16)`, '
                  f'{lower}_side `4096`);;',
            f'let {upper}_NUMERIC = prove({lower}_numeric_spec,ve_split_numeric_tac {lower}_mc);;',
            f've_check "{label}:numeric" {lower}_numeric_spec {upper}_NUMERIC;;']
        checks += [label+':initial',label+':numeric']
        if positive:continue
        post='~(read X0 s = word 1) /\\ read PC s = word 16384' if name in ['split-range','input-length'] else \
             'read PC s = word 16384 /\\ ~(read (memory :> bytes8 (word 8200)) s = word 0)' if name=='overlap-target' else \
             '~memaccess_inbounds (read events s) [word 8192,16;word 32752,16] [word 8192,16;word 32752,16]'
        steps=row['steps']
        lines += [f'let {lower}_prefix_spec = mk_forall(`pc:num`,mk_imp({lower}_side `pc:num`,'
            f'list_mk_comb(`ensures_n arm`,[ve_split_witness_pre `{lower}_mc` {split} {n} `pc:num`;'
            f'`\\s:armstate. {post}`;`\\s:armstate t:armstate. T`;`\\s:armstate. {steps}`])));;',
            f'let {upper}_PREFIX = prove({lower}_prefix_spec,REWRITE_TAC[fst {upper}_EXEC] THEN '
            f'REPEAT GEN_TAC THEN STRIP_TAC THEN REWRITE_TAC[C_ARGUMENTS] THEN '
            f'ARM_SIM_TAC {upper}_EXEC (1--{steps}) THEN TRY(CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV)) '
            f'THEN TRY ve_bad_access_tac THEN TRY ve_split_finish_numeric);;',
            f'let {upper}_EXECUTION = ve_execution {upper}_PREFIX (CONJUNCT2 {upper}_NUMERIC) {upper}_INITIAL;;',
            f'let {lower}_execution_spec = `eventually_n arm {steps} (\\s:armstate. {post}) '
            f'(ve_split_initial {lower}_mc {split} {n})`;;',
            f've_check "{label}:execution" {lower}_execution_spec {upper}_EXECUTION;;']
        checks.append(label+':execution')
    path=BUILD/'split-witnesses.ml';path.write_text('\n'.join(lines)+'\n')
    return path,checks


if __name__=='__main__':prepare(json.loads((BUILD/'split-layout.json').read_text()),
                              json.loads((BUILD/'split-mutations.json').read_text()))
