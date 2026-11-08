"""Fixed compositions share actual RET-free child bytes and HOL theorems."""
import struct
from config import BUILD
from build import words
from proof_text import timed_declarations


def prepare():
    out=['loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/composition.ml");;']
    checks=[]
    for width in [16,32]:
        name=f'vp2_copy{width}';upper=name.upper()
        data=words(BUILD/(name+'.words'))
        literal=';'.join(hex(w) for w in struct.unpack('<'+'I'*(len(data)//4),data))
        children='['+';'.join(f'(Ve_block.code vp2_block_copy8_{k}_block,Ve_block.theorem vp2_block_copy8_{k}_block)' for k in range(0,width,8))+']'
        out += [f'let {name}_mc = define_assert_from_elf "{name}_mc" '
            f'(Sys.getenv "VP_EVOLUTION_ROOT" ^ "/build/{name}.o") [{literal}];;',
            f'let {upper}_EXEC = ARM_MK_EXEC_RULE {name}_mc;;',
            f'let {name}_spec = ve_fixedcopy_spec `{name}_mc` {width};;',
            f'let {upper}_COMPOSED = prove({name}_spec,ve_fixedcopy_composed_tac {name}_mc {upper}_EXEC {children});;',
            f've_check "{name}:composed" {name}_spec {upper}_COMPOSED;;']
        checks.append(name+':composed')
        direct=name+'_direct'
        out += [f'let {direct}_mc = define_assert_from_elf "{direct}_mc" '
            f'(Sys.getenv "VP_EVOLUTION_ROOT" ^ "/build/{direct}.o") [{literal}];;',
            f'let {upper}_DIRECT_EXEC = ARM_MK_EXEC_RULE {direct}_mc;;',
            f'let {direct}_spec = ve_fixedcopy_spec `{direct}_mc` {width};;',
            f'let {upper}_DIRECT = prove({direct}_spec,REWRITE_TAC[fst {upper}_DIRECT_EXEC] THEN '
            'CONV_TAC(DEPTH_CONV EXPAND_CASES_CONV) THEN CONV_TAC NUM_REDUCE_CONV THEN '
            f'REWRITE_TAC[WORD_ADD_0] THEN REPEAT STRIP_TAC THEN ARM_SIM_TAC {upper}_DIRECT_EXEC (1--{width//4+1}) THEN REWRITE_TAC[APPEND]);;',
            f've_check "{name}:direct" {direct}_spec {upper}_DIRECT;;']
        checks.append(name+':direct')
    name='vp2_copy16_x3';upper=name.upper()
    data=words(BUILD/(name+'.words'))
    literal=';'.join(hex(w) for w in struct.unpack('<'+'I'*(len(data)//4),data))
    out += [f'let {name}_mc = define_assert_from_elf "{name}_mc" '
        f'(Sys.getenv "VP_EVOLUTION_ROOT" ^ "/build/{name}.o") [{literal}];;',
        f'let {upper}_EXEC = ARM_MK_EXEC_RULE {name}_mc;;',
        f'let {name}_spec = ve_fixedcopy_spec ~scratch:[`X3`;`X4`] `{name}_mc` 16;;',
        f'let {upper}_COMPOSED = prove({name}_spec,ve_fixedcopy_composed_tac {name}_mc {upper}_EXEC '
        '[(Ve_block.code vp2_block_copy8_x3_block,Ve_block.theorem vp2_block_copy8_x3_block);'
        '(Ve_block.code vp2_block_copy8_8_block,Ve_block.theorem vp2_block_copy8_8_block)]);;',
        f've_check "{name}:composed" {name}_spec {upper}_COMPOSED;;']
    checks.append(name+':composed')
    path=BUILD/'composition.ml';path.write_text(timed_declarations(out))
    return path,checks


if __name__=='__main__': prepare()
