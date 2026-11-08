from pathlib import Path
import json,struct,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'build';sys.path.insert(0,str(ROOT/'tools'))
from config import environment
from build import MachO
rows={backend:[json.loads(l) for l in (B/f'e6a-{backend}-cases.jsonl').open()] for backend in ['qemu','native']}
words=sorted({r['word'] for r in rows['qemu']})
head=['let ve_diff_sparse_initial = new_definition',r''' `ve_diff_sparse_initial (code:byte list) pc mem (gpr_image:5 word->int64) flag_bits (byte_image:byte list) =
 armstate_RECORD (word pc) gpr_image
 (\r:5 word. word 0:int128) (word flag_bits:4 word)
 (\a:int64. if pc <= val a /\ val a < pc+LENGTH code then EL (val a-pc) code
  else if mem <= val a /\ val a < mem+LENGTH byte_image then EL (val a-mem) byte_image else word 0) []`;;''',
r'''let VE_DIFF_SPARSE_COMPONENTS = prove
 (`!code pc mem gpr_image flag_bits byte_image.
   read PC (ve_diff_sparse_initial code pc mem gpr_image flag_bits byte_image) = word pc /\
   read registers (ve_diff_sparse_initial code pc mem gpr_image flag_bits byte_image) = gpr_image /\
   read flags (ve_diff_sparse_initial code pc mem gpr_image flag_bits byte_image) = (word flag_bits:4 word) /\
   read memory (ve_diff_sparse_initial code pc mem gpr_image flag_bits byte_image) =
    (\a:int64. if pc <= val a /\ val a < pc+LENGTH code then EL (val a-pc) code
     else if mem <= val a /\ val a < mem+LENGTH byte_image then EL (val a-mem) byte_image else word 0)`,
  REWRITE_TAC[ve_diff_sparse_initial;armstate_COMPONENTS]);;''',
r'''let ve_diff_witness_tac mc =
 REWRITE_TAC[mc;aligned_bytes_loaded;bytes_loaded;LENGTH] THEN
 CONV_TAC NUM_REDUCE_CONV THEN CONV_TAC(DEPTH_CONV BYTELIST_EXPAND_CONV) THEN
 CONV_TAC(DEPTH_CONV EXPAND_CASES_CONV) THEN
 REWRITE_TAC[READ_MEMORY_BYTESIZED_SPLIT;
 X0;X1;X2;X3;X4;X5;X6;X7;X8;X9;X10;X11;X12;X13;X14;X15;
 X16;X17;X18;X19;X20;X21;X22;X23;X24;X25;X26;X27;X28;X29;X30;XREG;SP;NF;ZF;CF;VF] THEN
 REWRITE_TAC[BYTES8_ELEMENT;READ_COMPONENT_COMPOSE;VE_DIFF_SPARSE_COMPONENTS;READ_ELEMENT;READ_BITELEMENT;LENGTH] THEN
 CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN CONV_TAC NUM_REDUCE_CONV THEN
 REWRITE_TAC[READ_COMPONENT_COMPOSE;VE_DIFF_SPARSE_COMPONENTS;READ_ELEMENT;READ_BITELEMENT] THEN
 CONV_TAC(DEPTH_CONV EL_CONV) THEN CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN
 CONV_TAC NUM_REDUCE_CONV THEN CONV_TAC(DEPTH_CONV EL_CONV) THEN
 CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN CONV_TAC NUM_REDUCE_CONV THEN
 REWRITE_TAC[] THEN CONV_TAC DIVIDES_CONV;;''',
r'''let ve_diff_numeric_tac =
 REWRITE_TAC[NONOVERLAPPING_CLAUSES;aligned] THEN
 CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN CONV_TAC NUM_REDUCE_CONV THEN
 CONV_TAC(DEPTH_CONV DIVIDES_CONV) THEN REWRITE_TAC[] THEN REPEAT CONJ_TAC THEN
 MATCH_MP_TAC NONOVERLAPPING_MODULO_SIMPLE THEN CONV_TAC NUM_REDUCE_CONV;;''']
for w in words:
 name=f've_diff_word_{w:08x}';p=B/(name+'.S')
 p.write_text(f'.text\n.p2align 2\n.globl _{name}\n_{name}:\n.long {hex(w)}\n.globl _{name}_end\n.private_extern _{name}_end\n_{name}_end:\n.subsections_via_symbols\n')
 subprocess.run(['xcrun','clang','-arch','arm64','-c',str(p),'-o',str(p.with_suffix('.o'))],cwd=ROOT,env=environment(),check=True)
 if MachO(p.with_suffix('.o')).function(name)!=struct.pack('<I',w):raise RuntimeError('instruction object differs')
 head += [f'let {name}_mc = define_assert_from_elf "{name}_mc" {json.dumps(str(p.with_suffix(".o")))} [{hex(w)}];;',
          f'let {name.upper()}_EXEC = ARM_MK_EXEC_RULE {name}_mc;;']
(B/'e6a-hol-base.ml').write_text('\n'.join(head)+'\n')
def registers(values):return ' /\\ '.join(f'read {"X"+str(i) if i<31 else "SP"} s = word {v}' for i,v in enumerate(values))
def flags(value):return ' /\\ '.join(f'read {r} s = {"T" if value&(1<<k) else "F"}' for k,r in [(3,'NF'),(2,'ZF'),(1,'CF'),(0,'VF')])
def fragment(c,backend):
 w=c['word'];form=c['form'];name=f've_diff_word_{w:08x}';pc=c['pc'];mem=c['memory_base'];after=c['after']
 memory=form.startswith(('LDR','STR'));width=1 if form.startswith(('LDRB','STRB')) else 8
 off=c.get('effective_offset') or 0;effective=mem+off
 side=f'nonoverlapping (word pc:int64,4) (word {mem},512)'
 if memory:side+=f' /\\ nonoverlapping (word pc:int64,4) (word {effective},{width}) /\\ aligned {width} (word {effective}:int64)'
 rn=(w>>5)&31;rm=(w>>16)&31;rt=w&31
 used=[]
 if form in ['EOR_X','ORR_X','SUB_X_REG','CMP_X_REG']:used=[rn,rm]
 elif form in ['ADD_X_IMM','CMP_X_IMM','TST_X_IMM','RET']:used=[rn]
 elif form=='CBZ_X':used=[rt]
 elif memory:used=[rn]+([rm] if form.endswith('_REG') else [])+([rt] if form.startswith('STR') else [])
 used=sorted(set(used)-{31})
 changed=[rt] if form in ['MOVZ_X','EOR_X','ORR_X','ADD_X_IMM','SUB_X_REG'] or form.startswith('LDR') else []
 changes_flags=form.startswith('CMP_') or form=='TST_X_IMM'
 pre=f'\\s:armstate. aligned_bytes_loaded s (word pc) {name}_mc /\\ read PC s = word pc'
 for i in used:pre+=f' /\\ read X{i} s = word {c["registers"][i]}'
 if form.startswith('B_COND_'):pre+=' /\\ '+flags(c['nzcv'])
 if form.startswith('LDR'):
  value=int.from_bytes(bytes.fromhex(c['memory'])[off:off+width],'little')
  pre+=f' /\\ read (memory :> bytes{width*8} (word {effective})) s = word {value}'
 if form=='RET':nextpc=f'word {after["pc"]}'
 else:
  delta=(after['pc']-pc)%(1<<64);delta=delta-(1<<64) if delta>=(1<<63) else delta
  nextpc=f'word(pc+{delta})' if delta>=0 else f'word_sub (word pc) (word {-delta})'
 post=f'\\s:armstate. read PC s = ({nextpc}:int64)'
 for i in changed:post+=f' /\\ read X{i} s = word {after["registers"][i]}'
 if changes_flags:post+=' /\\ '+flags(after['nzcv'])
 if form.startswith('STR'):
  value=int.from_bytes(bytes.fromhex(after['memory'])[off:off+width],'little')
  post+=f' /\\ read (memory :> bytes{width*8} (word {effective})) s = word {value}'
 change=['PC']
 if form in ['MOVZ_X','EOR_X','ORR_X','ADD_X_IMM','SUB_X_REG'] or form.startswith('LDR'):change.append('X'+str(w&31))
 frame='MAYCHANGE ['+';'.join(change)+']'
 if form.startswith('CMP_') or form=='TST_X_IMM':frame+=' ,, MAYCHANGE SOME_FLAGS'
 if form.startswith('STR'):frame+=f' ,, MAYCHANGE [memory :> bytes{width*8} (word {effective})]'
 frame+=' ,, MAYCHANGE [events]'
 reglist='\\r:5 word. '+''.join(f'if r = word {i} then word {c["registers"][i]} else ' for i in used)+'word 0';data=';'.join('word '+str(b) for b in bytes.fromhex(c['memory'])[off:off+width]) if memory else ''; initial_mem=effective if memory else 0
 label=f'e6a:{backend}:{form}:{c["index"]}'
 return f'''let () =
 let pre = `{pre}` and post = `{post}` and frame = `{frame}` in
 let side = `{side}` in
 let spec = mk_forall(`pc:num`,mk_imp(side,list_mk_comb(`ensures_n arm`,[pre;post;frame;`\\s:armstate. 1`]))) in
 let correct = prove(spec,REWRITE_TAC[SOME_FLAGS;fst {name.upper()}_EXEC] THEN REPEAT GEN_TAC THEN STRIP_TAC THEN
  ARM_SIM_TAC {name.upper()}_EXEC [1] THEN TRY(CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV)) THEN
  TRY(CONV_TAC NUM_REDUCE_CONV) THEN RULE_ASSUM_TAC(CONV_RULE(DEPTH_CONV WORD_NUM_RED_CONV)) THEN ASM_REWRITE_TAC[] THEN TRY(CONV_TAC WORD_BLAST)) in
 ve_check "{label}:universal" spec correct;
 let initial = `ve_diff_sparse_initial {name}_mc {pc} {initial_mem} ({reglist}) {c['nzcv']} [{data}]` in
 let witness_spec = mk_comb(vsubst [`{pc}`,`pc:num`] pre,initial) in
 let witness = prove(witness_spec,ve_diff_witness_tac {name}_mc) in
 ve_check "{label}:initial" witness_spec witness;
 let numeric_spec = vsubst [`{pc}`,`pc:num`] side in
 let numeric = prove(numeric_spec,ve_diff_numeric_tac) in
 ve_check "{label}:numeric" numeric_spec numeric;
 let states = REWRITE_RULE[ensures_n] (MP (SPEC `{pc}` correct) numeric) in
 let finite = REWRITE_RULE[] (MP (REWRITE_RULE[] (SPEC initial states)) (REWRITE_RULE[] witness)) in
 let post = vsubst [`{pc}`,`pc:num`] post and frame = vsubst [`{pc}`,`pc:num`] frame in
 let s = `s:armstate` in
 let goalpost = mk_abs(s,mk_conj(mk_comb(post,s),list_mk_comb(frame,[initial;s]))) in
 let expected = list_mk_comb(`eventually_n arm`,[`1`;goalpost;initial]) in
 let expected = rand(concl(REWRITE_CONV[] expected)) in
 ve_check "{label}:execution" expected finite;;
'''
forms=sys.argv[1:] or sorted({c['form'] for c in rows['qemu']})
indices=list(range(288))
selected=[(backend,c) for backend,cases in rows.items() for c in cases if c['form'] in forms and c['index'] in indices]
parts=['loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/build/e6a-hol-base.ml");;']
parts += [fragment(c,b) for b,c in selected]
(B/'e6a-hol-cases.ml').write_text('\n'.join(parts))
(B/'e6a-checks.json').write_text(json.dumps([f'e6a:{b}:{c["form"]}:{c["index"]}:{kind}' for b,c in selected for kind in ['universal','initial','numeric','execution']],indent=2)+'\n')
print('generated HOL comparisons:',len(selected),flush=True)
