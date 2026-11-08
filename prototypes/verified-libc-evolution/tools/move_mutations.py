"""Actual object edits with concrete, public-contract-valid overlap witnesses."""
import json
import struct
from config import ROOT,BUILD,digest
from build import MachO,words,check_span

EDITS=[
    ('always-forward',3,0xd503201f,8193,8192,2,16,8194,0,1),
    ('always-backward',3,0x14000008,8192,8193,2,14,8192,2,1),
    ('reverse-direction',3,0x54000103,8193,8192,2,16,8194,0,1),
    ('missing-first',4,0xd2800023,8192,8193,2,11,8192,0,1),
    ('missing-last',9,0xd503201f,8192,8193,2,11,8193,1,2),
    ('zero-decrement',0,0x1400000b,8193,8192,0,4,None,None,None),
    ('overread',5,0xf8636824,8192,8200,1,6,None,None,None),
    ('overwrite',14,0xf8236804,8200,8192,1,8,None,None,None)]


def prepare():
    original=BUILD/'vp2_memmove.o';parsed=MachO(original)
    symbol=parsed.symbol('_vp2_memmove');section=parsed.sections[symbol.section-1]
    position=section.offset+symbol.address-section.address
    expected=words(BUILD/'vp2_memmove.words')
    check_span(original,'vp2_memmove',expected)
    records=[];chunks=['loadt '+json.dumps(str(ROOT/'proofs/witnesses.ml'))+';;',
                      'loadt '+json.dumps(str(ROOT/'proofs/memmove_witnesses.ml'))+';;']
    checks=[]
    for name,index,replacement,dst,src,n,steps,address,observed,wanted in EDITS:
        path=BUILD/('move_mut_'+name.replace('-','_')+'.o')
        data=bytearray(original.read_bytes());struct.pack_into('<I',data,position+4*index,replacement)
        path.write_bytes(data);body=bytearray(expected);struct.pack_into('<I',body,4*index,replacement)
        check_span(path,'vp2_memmove',body)
        record=dict(name=name,object=str(path),sha256=digest(path),changed_word=index,
            dst=dst,src=src,n=n,steps=steps,kind='functional' if address is not None else 'access',
            address=address,observed=observed,wanted=wanted)
        records.append(record)
        lower='ve_move_mut_'+name.replace('-','_');upper=lower.upper()
        encoding=struct.unpack('<'+'I'*(len(body)//4),body)
        code='['+';'.join(hex(w) for w in encoding)+']'
        cells=' /\\ '.join(f'read (memory :> bytes8 (word {a})) s = word {a%256}' for a in range(8184,8217))
        pre=(f'\\s:armstate. aligned_bytes_loaded s (word pc) {lower}_mc /\\ read PC s = word pc /\\ '
             f'read X30 s = word 16384 /\\ C_ARGUMENTS [word {dst};word {src};word {n}] s /\\ '
             'read events s = [] /\\ '+
             f'(!i. i < {n} ==> read (memory :> bytes8 (word_add (word {src}) (word i))) s = word (({src}+i) MOD 256)) /\\ '+cells)
        if address is not None:
            post=f'read PC s = word 16384 /\\ read (memory :> bytes8 (word {address})) s = word {observed} /\\ ~(read (memory :> bytes8 (word {address})) s = word {wanted})'
        else:
            post=f'~memaccess_inbounds (read events s) [word {src},{n}] [word {dst},{n}]'
        numeric=(f'~(word {dst}:int64 = word 0) /\\ ~(word {src}:int64 = word 0) /\\ '
            f'val(word {dst}:int64)+val(word {n}:int64) <= 2 EXP 64 /\\ '
            f'val(word {src}:int64)+val(word {n}:int64) <= 2 EXP 64 /\\ '
            f'nonoverlapping (word 4096:int64,68) (word {dst},val(word {n}:int64))')
        side=' /\\ '.join(f'nonoverlapping (word pc:int64,68) (word {a},{width})'
                           for a,width in [(dst,32),(dst,1),(dst+1,1),(dst,8)])
        chunks += [f'let {lower}_mc = define_assert_from_elf "{lower}_mc" {json.dumps(str(path))} {code};;',
            f'let {upper}_EXEC = ARM_MK_EXEC_RULE {lower}_mc;;',
            f'let {lower}_pre = `{pre}`;;',
            f'let {lower}_initial_spec = mk_comb(vsubst [`4096`,`pc:num`] {lower}_pre,`ve_move_initial {lower}_mc {dst} {src} {n}`);;',
            f'let {upper}_INITIAL = prove({lower}_initial_spec,ve_move_witness_tac {lower}_mc);;',
            f've_check "move-mut:{name}:initial" {lower}_initial_spec {upper}_INITIAL;;',
            f'let {lower}_numeric_spec = `{numeric}`;;',
            f'let {upper}_NUMERIC = prove({lower}_numeric_spec,ve_numeric_tac []);;',
            f've_check "move-mut:{name}:numeric" {lower}_numeric_spec {upper}_NUMERIC;;',
            f'let {lower}_prefix_spec = `!pc. {side} ==> '
            f'ensures_n arm ({pre}) (\\s:armstate. {post}) (\\s:armstate t:armstate. T) (\\s:armstate. {steps})`;;',
            f'let {upper}_PREFIX = prove({lower}_prefix_spec,REPEAT STRIP_TAC THEN REWRITE_TAC[C_ARGUMENTS] THEN '
            'ASSUME_TAC(prove(`nonoverlapping (word 8192:int64,1) (word 8193,1)`,ve_numeric_tac [])) THEN '
            'ASSUME_TAC(prove(`nonoverlapping (word 8193:int64,1) (word 8192,1)`,ve_numeric_tac [])) THEN '
            f'ARM_SIM_TAC {upper}_EXEC (1--{steps}) THEN CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN REWRITE_TAC[] THEN TRY ve_bad_access_tac);;',
            f'let {upper}_SIDE = prove(`{side.replace("word pc:int64","word 4096:int64")}`,ve_numeric_tac []);;',
            f'let {upper}_EXECUTION = REWRITE_RULE[] (MP (SPEC `ve_move_initial {lower}_mc {dst} {src} {n}` '
            f'(REWRITE_RULE[ensures_n] (MP (SPEC `4096` {upper}_PREFIX) {upper}_SIDE))) (BETA_RULE {upper}_INITIAL));;',
            f'let {lower}_execution_spec = list_mk_comb(`eventually_n arm`,[`{steps}`;'
            f'vsubst [`4096`,`pc:num`] `(\\s:armstate. {post})`;`ve_move_initial {lower}_mc {dst} {src} {n}`]);;',
            f've_check "move-mut:{name}:execution" {lower}_execution_spec {upper}_EXECUTION;;']
        checks += [f'move-mut:{name}:{part}' for part in ['initial','numeric','execution']]
    target=BUILD/'move-mutations.ml';target.write_text('\n'.join(chunks)+'\n')
    (BUILD/'move-mutations.json').write_text(json.dumps(records,indent=2)+'\n')
    return target,checks


if __name__=='__main__': prepare()
