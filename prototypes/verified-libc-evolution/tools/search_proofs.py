"""Untrusted certificate scripts for the frozen candidates; contracts stay independent."""
import json
import re
from config import ROOT, BUILD
from blocks import prepare as blocks
from search_build import prepare as build
from search_witnesses import prepare as bad

SOURCES=['chunk_tail.ml','chunk_bulk.ml','memcpy_chunk8.ml',
         'chunk_tail_access.ml','chunk_bulk_access.ml','chunk_access.ml']


def namespace(text,name):
    text=re.sub(r'^loadt .*?;;\n','',text,flags=re.M)
    text=text.replace('vp2_memcpy_chunk8',name).replace('VP2_MEMCPY_CHUNK8',name.upper())
    tokens=set(re.findall(r'\b(?:ve_chunk_\w+|VE_CHUNK_\w+|ve_tail_access\w*|VE_TAIL_ACCESS|ve_bulk_access\w*|VE_BULK_ACCESS|ve_open_trace)\b',text))
    for token in sorted(tokens,key=len,reverse=True):
        prefix=name.upper() if token[0].isupper() else name
        text=re.sub(r'\b'+token+r'\b',prefix+'_'+token,text)
    return text.replace('"chunk8:',f'"search:{name}:')


def coordinates(text):
    offsets={44:56,48:60,52:64,64:76,68:80,72:84,40:52}
    text=re.sub(r'\b76\b','88',text)
    text=re.sub(r'pc\s*\+\s*(44|48|52|64|68|72|40)\b',lambda m:'pc+'+str(offsets[int(m[1])]),text)
    return text.replace(',52,',',64,')


def bulk_math(text):
    return (text.replace('n DIV 8','n DIV 16').replace('8*(n DIV 16)','16*(n DIV 16)')
       .replace('8*i','16*i').replace('8*(i+1)','16*(i+1)')
       .replace('`n:num`;`8`','`n:num`;`16`').replace('n < 8','n < 16')
       .replace(')+8',')+16').replace('`8 <= n-','`16 <= n-').replace('~(8 <= n-','~(16 <= n-').replace('8 <= n <=>','16 <= n <=>'))


BULK2_BODY=r'''
  SUBGOAL_THEN `16*i+16 <= n /\ 16*i <= n /\ 16 <= n-16*i /\ 16*i < 2 EXP 64`
   STRIP_ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN VAL_INT64_TAC `16*i` THEN
  SUBGOAL_THEN `16*i+8 < 2 EXP 64` ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  VAL_INT64_TAC `16*i+8` THEN
  SUBGOAL_THEN `val(word_sub (word n) (word(16*i)):int64) = n-16*i`
   ASSUME_TAC THENL [ASM_REWRITE_TAC[VAL_WORD_SUB_CASES];ALL_TAC] THEN
  SUBGOAL_THEN `aligned 8 (word_add (src:int64) (word(16*i))) /\
                aligned 8 (word_add (dst:int64) (word(16*i)))`
   STRIP_ASSUME_TAC THENL
  [CONJ_TAC THEN MATCH_MP_TAC ALIGNED_WORD_ADD THEN
   ASM_SIMP_TAC[ALIGNED_WORD;DIMINDEX_64;DIVIDES_RMUL;DIVIDES_REFL;
     ARITH_RULE `!i:num. 16*i=8*(2*i)`] THEN
   CONV_TAC NUM_REDUCE_CONV THEN CONV_TAC DIVIDES_CONV;ALL_TAC] THEN
  ENSURES_INIT_TAC "s0" THEN
  ABBREV_TAC `b0:int64 = read (memory :> bytes64 (word_add src (word(16*i)))) s0` THEN
  ABBREV_TAC `b1:int64 = read (memory :> bytes64 (word_add src (word(16*i+8)))) s0` THEN
  ARM_STEPS_TAC VP2_MEMCPY_CHUNK8_EXEC (1--6) THEN
  RULE_ASSUM_TAC(REWRITE_RULE[GSYM WORD_ADD]) THEN
  ARM_STEPS_TAC VP2_MEMCPY_CHUNK8_EXEC (7--9) THEN
  SUBGOAL_THEN `!r. r<8 ==> read (memory :> bytes8 (word_add dst (word(16*i+r)))) s9 = input(16*i+r)`
   (LABEL_TAC "low-bytes") THENL
  [MP_TAC(SPECL [`word_add dst (word(16*i)):int64`;`word_add src (word(16*i)):int64`;
                 `s9:armstate`;`s9:armstate`] VE_BYTES64_EQ) THEN ASM_REWRITE_TAC[] THEN
   REWRITE_TAC[WORD_RULE `word_add (word_add a (word b)) (word c) = word_add a (word(b+c))`] THEN
   DISCH_TAC THEN X_GEN_TAC `r:num` THEN DISCH_TAC THEN
   ASM_MESON_TAC[ARITH_RULE `16*i+16<=n /\ r<8 ==> 16*i+r<n`];ALL_TAC] THEN
  SUBGOAL_THEN `!r. r<8 ==> read (memory :> bytes8 (word_add dst (word(16*i+8+r)))) s9 = input(16*i+8+r)`
   (LABEL_TAC "high-bytes") THENL
  [MP_TAC(SPECL [`word_add dst (word(16*i+8)):int64`;`word_add src (word(16*i+8)):int64`;
                 `s9:armstate`;`s9:armstate`] VE_BYTES64_EQ) THEN ASM_REWRITE_TAC[] THEN
   REWRITE_TAC[WORD_RULE `word_add (word_add a (word b)) (word c) = word_add a (word(b+c))`;GSYM ADD_ASSOC] THEN
   DISCH_TAC THEN X_GEN_TAC `r:num` THEN DISCH_TAC THEN
   ASM_MESON_TAC[ARITH_RULE `16*i+16<=n /\ r<8 ==> 16*i+8+r<n`];ALL_TAC] THEN
  ENSURES_FINAL_STATE_TAC THEN
  ASM_REWRITE_TAC[GSYM WORD_ADD;ARITH_RULE `!i:num. (16*i+8)+8=16*(i+1)`;ARITH_RULE `!i:num. 16*i+16=16*(i+1)`] THEN
  X_GEN_TAC `j:num` THEN DISCH_TAC THEN ASM_CASES_TAC `j < 16*i` THENL
  [ASM_MESON_TAC[];
   ASM_CASES_TAC `j < 16*i+8` THENL
   [SUBGOAL_THEN `j-16*i<8 /\ 16*i+(j-16*i)=j` STRIP_ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
    USE_THEN "low-bytes" (fun th -> MATCH_ACCEPT_TAC(REWRITE_RULE[ASSUME `16*i+(j-16*i)=j`]
      (MATCH_MP(SPEC `j-16*i` th)(ASSUME `j-16*i<8`))));
    SUBGOAL_THEN `j-(16*i+8)<8 /\ 16*i+8+(j-(16*i+8))=j` STRIP_ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
    USE_THEN "high-bytes" (fun th -> MATCH_ACCEPT_TAC(REWRITE_RULE[ASSUME `16*i+8+(j-(16*i+8))=j`]
      (MATCH_MP(SPEC `j-(16*i+8)` th)(ASSUME `j-(16*i+8)<8`))))]]
'''

ACCESS2_BODY=r'''
  SUBGOAL_THEN `16*i+16 <= n /\ 16*i <= n /\ 16 <= n-16*i /\ 16*i < 2 EXP 64`
   STRIP_ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN VAL_INT64_TAC `16*i` THEN
  SUBGOAL_THEN `16*i+8 < 2 EXP 64` ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  VAL_INT64_TAC `16*i+8` THEN
  SUBGOAL_THEN `val(word_sub (word n) (word(16*i)):int64) = n-16*i`
   ASSUME_TAC THENL [ASM_REWRITE_TAC[VAL_WORD_SUB_CASES];ALL_TAC] THEN
  SUBGOAL_THEN `aligned 8 (word_add (src:int64) (word(16*i))) /\
                aligned 8 (word_add (dst:int64) (word(16*i)))`
   STRIP_ASSUME_TAC THENL
  [CONJ_TAC THEN MATCH_MP_TAC ALIGNED_WORD_ADD THEN
   ASM_SIMP_TAC[ALIGNED_WORD;DIMINDEX_64;DIVIDES_RMUL;DIVIDES_REFL;
     ARITH_RULE `!i:num. 16*i=8*(2*i)`] THEN
   CONV_TAC NUM_REDUCE_CONV THEN CONV_TAC DIVIDES_CONV;ALL_TAC] THEN
  ARM_SIM_TAC ~preprocess_tac:(ve_open_trace "trace") VP2_MEMCPY_CHUNK8_EXEC (1--9) THEN
  RULE_ASSUM_TAC(REWRITE_RULE[GSYM WORD_ADD]) THEN REWRITE_TAC[GSYM WORD_ADD;ARITH_RULE `!i:num. (16*i+8)+8=16*(i+1)`;ARITH_RULE `!i:num. 16*i+16=16*(i+1)`] THEN
  EXISTS_TAC `APPEND [EventStore(word_add dst (word(16*i+8)),8);
    EventLoad(word_add src (word(16*i+8)),8);EventStore(word_add dst (word(16*i)),8);
    EventLoad(word_add src (word(16*i)),8);EventJump(word(pc+24),word(pc+28))] trace` THEN
  ONCE_REWRITE_TAC[MEMACCESS_INBOUNDS_APPEND] THEN
  RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
  ASM_REWRITE_TAC[APPEND;memaccess_inbounds;ALL;EX] THEN
  ASM_REWRITE_TAC[VAL_WORD_ADD;CONTAINED_MODULO_LMOD;DIMINDEX_64] THEN
  REPEAT CONJ_TAC THEN MATCH_MP_TAC CONTAINED_MODULO_OFFSET_SIMPLE THEN ASM_ARITH_TAC
'''


def unroll2(text,source):
    text=coordinates(text)
    if source in ['chunk_bulk.ml','chunk_bulk_access.ml']:
        start=text.index('  SUBGOAL_THEN `8*i+8 <= n',text.index('  X_GEN_TAC `i:num`'))
        end=text.index(';\n  X_GEN_TAC `i:num`',start)
        body=BULK2_BODY if source=='chunk_bulk.ml' else ACCESS2_BODY
        text=bulk_math(text[:start])+body+bulk_math(text[end:])
    elif source in ['memcpy_chunk8.ml','chunk_access.ml']:
        text=bulk_math(text)
    return text


def prepare(selected=None):
    manifest=build();b,bc=blocks()
    lines=['loadt '+json.dumps(str(ROOT.parent/'verified-libc-minimal/proofs/specs.ml'))+';;',
           'loadt '+json.dumps(str(b))+';;',
           'loadt '+json.dumps(str(ROOT/'proofs/memory.ml'))+';;']
    for source in ['costs.ml','resource_tail.ml','resource_bulk.ml','resource_composition.ml','resource_chunk.ml']:
        lines.append('loadt '+json.dumps(str(ROOT/'proofs'/source))+';;')
    paths=[b];checks=list(bc)
    for candidate in manifest['candidates']:
        if candidate['name'].endswith('_bad') or (selected and candidate['name']!=selected):continue
        name=candidate['name'];u=candidate['unroll']
        for source in SOURCES:
            text=(ROOT/'proofs'/source).read_text()
            if u==2:text=unroll2(text,source)
            text=namespace(text,name)
            if source=='chunk_tail.ml':
                start=text.index('let '+name+'_mc =');end=text.index(';;',start)+2
                text=text[:start]+f'let {name}_mc=define_assert_from_elf "{name}_mc" '+json.dumps(str(BUILD/(name+'.o')))+' ['+';'.join(candidate['words'])+'];;'+text[end:]
            path=BUILD/(name+'-'+source);path.write_text(text)
            lines.append('loadt '+json.dumps(str(path))+';;');paths.append(path)
            checks += re.findall(r've_check "([^"]+)"',text)
        resource=[]
        for kind,formula,tactic in [
            ('resource-tail',f've_tail_resource_spec `{name}_mc` {44+12*(u-1)}',f've_tail_resource_tac {name.upper()}_EXEC {44+12*(u-1)}'),
            ('resource-bulk',f've_bulk_resource_spec `{name}_mc` {u}',f've_bulk_resource_tac {name.upper()}_EXEC {u}'),
            ('resource-public',f've_resource_contract `{name}_mc` (ve_chunk_count {u}) false',f've_chunk_resource_tac {name}_mc {name.upper()}_EXEC {u} {name.upper()}_RESOURCE_BULK {name.upper()}_RESOURCE_TAIL')]:
            local=kind.replace('-','_');label=f'search:{name}:{kind}'
            resource += [f'let {name}_{local}_spec={formula};;',
                         f'let {name.upper()}_{local.upper()}=prove({name}_{local}_spec,{tactic});;',
                         f've_check "{label}" {name}_{local}_spec {name.upper()}_{local.upper()};;']
            checks.append(label)
        rp=BUILD/(name+'-resources.ml');rp.write_text('\n'.join(resource)+'\n');paths.append(rp)
        lines.append('loadt '+json.dumps(str(rp))+';;')
    negative,nc=bad();paths.append(negative);checks+=nc;lines.append('loadt '+json.dumps(str(negative))+';;')
    path=BUILD/('search-selected-proofs.ml' if selected else 'search-proofs.ml');path.write_text('\n'.join(lines)+'\n')
    return path,checks,paths


if __name__=='__main__':
    p,c,_=prepare();print('prepared candidate certificate checks:',len(c),flush=True)
