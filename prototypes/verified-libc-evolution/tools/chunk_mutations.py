"""New-kernel mutations with concrete HOL violation witnesses."""
import json
import struct
from config import ROOT,BUILD
from build import MachO


def prepare():
    definitions=[('short-word',20,0xf100109f,4,8,'access'),
        ('extra-word',20,0xf100009f,8,15,'access'),
        ('missing-tail',24,0x54000183,1,8,'content'),
        ('return',0,0xd2800000,0,10,'return'),
        ('frame',0,0xd2800013,0,10,'frame'),
        ('decrease',36,0xd1002063,8,15,'access')]
    out=['loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/witnesses.ml");;']
    checks=[];records=[]
    for name,offset,replacement,n,steps,kind in definitions:
        parsed=MachO(BUILD/'vp2_memcpy_chunk8.o');sym=parsed.symbol('_vp2_memcpy_chunk8')
        sec=parsed.sections[sym.section-1];data=bytearray(parsed.data)
        struct.pack_into('<I',data,sec.offset+sym.address-sec.address+offset,replacement)
        target=BUILD/('chunk_mut_'+name+'.o');target.write_bytes(data)
        actual=MachO(target).function('vp2_memcpy_chunk8',object_only=True)
        if actual[offset:offset+4]!=struct.pack('<I',replacement): raise RuntimeError('missing mutation')
        literal=';'.join(hex(w) for w in struct.unpack('<'+'I'*(len(actual)//4),actual))
        lower='ve_chunk_mut_'+name.replace('-','_');upper=lower.upper()
        out += [f'let {lower}_mc = define_assert_from_elf "{lower}_mc" '+json.dumps(str(target))+f' [{literal}];;',
            f'let {upper}_EXEC=ARM_MK_EXEC_RULE {lower}_mc;;',
            f'let {lower}_pre = ve_pre `{lower}_mc` `{n}` `pc:num`;;']
        if kind in {'return','frame'}:
            out += [f'let {lower}_pre = let s=`s:armstate` in mk_abs(s,mk_conj('
                f'mk_comb({lower}_pre,s),`read X3 s = word 0`));;']
        if kind=='content':
            out += [f'let {lower}_pre = let s=`s:armstate` in mk_abs(s,mk_conj('
                f'mk_comb({lower}_pre,s),`read (memory :> bytes8 (word 8192)) s = word 170`));;']
            post='read PC s = word 16384 /\\ read (memory :> bytes8 (word 8192)) s = word 170 /\\ ~(read (memory :> bytes8 (word 8192)) s = word 85)'
        elif kind=='return':
            post='read PC s = word 16384 /\\ read X0 s = word 0 /\\ ~(read X0 s = word 8192)'
        elif kind=='frame':
            post='read PC s = word 16384 /\\ read X19 s = word 0 /\\ ~(read X19 s = word 19)'
        else:
            post=f'~memaccess_inbounds (read events s) [word 12288,{n}] [word 8192,{n}]'
        out += [f'let {lower}_witness_spec=mk_comb(vsubst [`4096`,`pc:num`] {lower}_pre,`ve_initial {lower}_mc {n}`);;',
            f'let {upper}_WITNESS=prove({lower}_witness_spec,ve_witness_tac {lower}_mc);;',
            f'let {lower}_numeric_spec=ve_numeric_pre `{lower}_mc` `{n}`;;',
            f'let {upper}_NUMERIC=prove({lower}_numeric_spec,ve_numeric_tac [{lower}_mc]);;',
            f'let {lower}_prefix_spec=mk_forall(`pc:num`,mk_imp('
            '`nonoverlapping (word pc:int64,76) (word 8192,64)`,'
            f'list_mk_comb(`ensures_n arm`,[{lower}_pre;`\\s:armstate. {post}`;`\\s:armstate t:armstate. T`;`\\s:armstate. {steps}`])));;',
            f'let {upper}_PREFIX=prove({lower}_prefix_spec,REPEAT STRIP_TAC THEN REWRITE_TAC[C_ARGUMENTS] THEN '
            f'ARM_SIM_TAC {upper}_EXEC (1--{steps}) THEN CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN REWRITE_TAC[] THEN TRY ve_bad_access_tac);;',
            f'let {upper}_SIDE=prove(`nonoverlapping (word 4096:int64,76) (word 8192,64)`,ve_numeric_tac []);;',
            f'let {upper}_EXECUTION=ve_execution {upper}_PREFIX {upper}_SIDE {upper}_WITNESS;;',
            f'let {lower}_execution_spec=list_mk_comb(`eventually_n arm`,[`{steps}`;vsubst [`4096`,`pc:num`] `\\s:armstate. {post}`;`ve_initial {lower}_mc {n}`]);;']
        for label,spec,theorem in [('initial',lower+'_witness_spec',upper+'_WITNESS'),
            ('numeric',lower+'_numeric_spec',upper+'_NUMERIC'),('execution',lower+'_execution_spec',upper+'_EXECUTION')]:
            check='chunk-mut:'+name+':'+label
            out.append(f've_check "{check}" {spec} {theorem};;');checks.append(check)
        records.append(dict(name=name,object=str(target),n=n,steps=steps,property=kind,
                            evidence_kind='hol_execution'))
    path=BUILD/'chunk-mutations.ml';path.write_text('\n'.join(out)+'\n')
    (BUILD/'chunk-mutations.json').write_text(json.dumps(records,indent=2)+'\n')
    return path,checks


if __name__=='__main__': prepare()
