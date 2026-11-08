let ve_bulk_resource_spec code unroll =
 let block=8*unroll and tail=44+12*(unroll-1) in
 vsubst [code,`code:byte list`;mk_small_numeral block,`block:num`;
         mk_small_numeral tail,`tail:num`;mk_small_numeral(3*unroll+4),`iteration:num`]
 `!dst src n pc e.
   n < 2 EXP 64 /\ aligned 8 dst /\ aligned 8 src /\
   nonoverlapping (word pc,LENGTH code) (dst,n) /\ nonoverlapping (src,n) (dst,n)
   ==> ensures_n arm
    (\s. aligned_bytes_loaded s (word pc) code /\ read PC s = word(pc+16) /\
         read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
         read X3 s = word 0 /\ read events s = e)
    (\s. read PC s = word(pc+tail) /\ read X0 s = dst /\ read X1 s = src /\
         read X2 s = word n /\ read X3 s = word(block*(n DIV block)) /\
         ve_read_bytes(read events s) = ve_read_bytes e+block*(n DIV block) /\
         ve_write_bytes(read events s) = ve_write_bytes e+block*(n DIV block))
    (MAYCHANGE [PC;X3;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
     MAYCHANGE [memory :> bytes(dst,n)])
    (\s:armstate. iteration*(n DIV block)+3)`;;

let ve_bulk_resource_tac exec unroll =
 let block=mk_small_numeral(8*unroll) in
 let sub tm=vsubst [block,`block:num`] tm in
 REWRITE_TAC[SOME_FLAGS;fst exec] THEN REPEAT GEN_TAC THEN STRIP_TAC THEN
 VAL_INT64_TAC `n:num` THEN
 SUBGOAL_THEN (sub `block*(n DIV block) <= n /\ n < block*(n DIV block)+block`)
  STRIP_ASSUME_TAC THENL
 [MP_TAC(SPECL [`n:num`;block] DIVISION) THEN CONV_TAC NUM_REDUCE_CONV THEN ARITH_TAC;
  ALL_TAC] THEN
 ASM_CASES_TAC (sub `n DIV block = 0`) THENL
 [SUBGOAL_THEN (sub `n < block`) ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  ASM_REWRITE_TAC[MULT_CLAUSES] THEN CONV_TAC NUM_REDUCE_CONV THEN
  ARM_SIM_TAC exec (1--3) THEN
  ASM_REWRITE_TAC (WORD_SUB_0::ve_count_rewrites) THEN ASM_ARITH_TAC;
  ALL_TAC] THEN
 ENSURES_N_WHILE_UP_TAC (sub `n DIV block`) `pc+16`
  (mk_binop `(+):num->num->num` `pc:num` (mk_small_numeral(40+12*(unroll-1))))
 (sub `\i s. read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
    read X3 s = word(block*i) /\
    (?trace. read events s = trace /\
      ve_read_bytes trace = ve_read_bytes e+block*i /\
      ve_write_bytes trace = ve_write_bytes e+block*i)`)
 (mk_abs(`i:num`,mk_small_numeral(3+3*unroll))) `0` `1` `4` THEN
 ASM_REWRITE_TAC[MULT_CLAUSES] THEN REPEAT CONJ_TAC THENL
 [ENSURES_INIT_TAC "s0" THEN ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[] THEN
  EXISTS_TAC `read events s0` THEN ASM_REWRITE_TAC[ADD_CLAUSES];
  X_GEN_TAC `i:num` THEN STRIP_TAC THEN
  SUBGOAL_THEN (sub `block*i+block <= n /\ block*i < 2 EXP 64 /\
    block*i <= n /\ block <= n-block*i`) STRIP_ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  VAL_INT64_TAC (sub `block*i`) THEN
  SUBGOAL_THEN (sub `val(word_sub (word n) (word(block*i)):int64) = n-block*i`)
   ASSUME_TAC THENL [ASM_REWRITE_TAC[VAL_WORD_SUB_CASES];ALL_TAC] THEN
  SUBGOAL_THEN (sub `aligned 8 (word_add (src:int64) (word(block*i))) /\
                      aligned 8 (word_add (dst:int64) (word(block*i)))`)
   STRIP_ASSUME_TAC THENL
  [CONJ_TAC THEN MATCH_MP_TAC ALIGNED_WORD_ADD THEN
   ASM_SIMP_TAC[ALIGNED_WORD;DIMINDEX_64;DIVIDES_RMUL;DIVIDES_REFL;
     ARITH_RULE `!i:num. 16*i=8*(2*i)`] THEN
   CONV_TAC NUM_REDUCE_CONV THEN CONV_TAC DIVIDES_CONV;ALL_TAC] THEN
  ARM_SIM_TAC ~preprocess_tac:ve_open_cost_trace exec (1--(3+3*unroll)) THEN
  RULE_ASSUM_TAC(REWRITE_RULE[GSYM WORD_ADD]) THEN REWRITE_TAC[GSYM WORD_ADD;ARITH_RULE(sub `!i:num. block*i+block=block*(i+1)`)] THEN
  TRY(EXISTS_TAC (mk_var("s"^string_of_int(3+3*unroll),`:armstate`)
    |> fun s -> mk_comb(`read events:armstate->uarch_event list`,s))) THEN
  ASM_REWRITE_TAC ve_count_rewrites THEN ASM_ARITH_TAC;
  X_GEN_TAC `i:num` THEN STRIP_TAC THEN
  ARM_SIM_TAC ~preprocess_tac:ve_open_cost_trace exec [1] THEN
  TRY(EXISTS_TAC `read events s1`) THEN ASM_REWRITE_TAC ve_count_rewrites;
  SUBGOAL_THEN (sub `block*(n DIV block) < 2 EXP 64`) ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  VAL_INT64_TAC (sub `block*(n DIV block)`) THEN
  SUBGOAL_THEN (sub `val(word_sub (word n) (word(block*(n DIV block))):int64) = n-block*(n DIV block)`)
   ASSUME_TAC THENL [ASM_REWRITE_TAC[VAL_WORD_SUB_CASES];ALL_TAC] THEN
  SUBGOAL_THEN (sub `~(block <= n-block*(n DIV block))`) ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  ARM_SIM_TAC ~preprocess_tac:ve_open_cost_trace exec (1--4) THEN
  ASM_REWRITE_TAC ve_count_rewrites;
  ASM_SIMP_TAC[NSUM_CONST_NUMSEG;ARITH_RULE `~(q=0) ==> q-1+1=q`] THEN ASM_ARITH_TAC];;
