"""Actual-byte definitions plus fixed independent block specifications."""
import struct
from config import ROOT, BUILD
from build import words
from proof_text import timed_declarations


def prepare():
    out=['loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/blocks.ml");;']
    checks=[]
    names=[(f'vp2_block_copy8_{k}',k,'X4') for k in [0,8,16,24]]
    names += [('vp2_block_copy8_x3',0,'X3'),('vp2_block_copy8_indexed',8,None),
              ('vp2_block_copybyte_indexed',1,None)]
    for name,offset,scratch in names:
        lower=name+'_mc';upper=name.upper()
        data=words(BUILD/(name+'.words'))
        literal=';'.join(hex(w) for w in struct.unpack('<'+'I'*(len(data)//4),data))
        out += [f'let {lower} = define_assert_from_elf "{lower}" '
            f'(Sys.getenv "VP_EVOLUTION_ROOT" ^ "/build/{name}.o") [{literal}];;',
            f'let {upper}_EXEC = ARM_MK_EXEC_RULE {lower};;']
        spec=f've_copy8_block_spec `{lower}` {offset} `{scratch}`' if scratch else f've_indexed_block_spec `{lower}` {offset}'
        kind=f'Ve_block.Fixed8({offset},`{scratch}`)' if scratch else f'Ve_block.Indexed {offset}'
        out += [f'let {name}_spec = {spec};;',
            f'let {upper}_CORRECT = prove({name}_spec,REWRITE_TAC[WORD_ADD_0] THEN REPEAT STRIP_TAC THEN '+
            ('VAL_INT64_TAC `i:num` THEN ' if scratch is None else '')+
            f'ARM_SIM_TAC {upper}_EXEC (1--2) THEN REWRITE_TAC[APPEND] THEN TRY(CONV_TAC WORD_BLAST));;',
            f'let {name}_block = Ve_block.create {lower} ({kind}) {upper}_CORRECT;;',
            f've_check "{name}" {name}_spec {upper}_CORRECT;;']
        checks.append(name)
    path=BUILD/'blocks.ml'
    path.write_text(timed_declarations(out))
    return path,checks


if __name__=='__main__': prepare()
