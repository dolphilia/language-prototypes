let ve_tail_resource_spec code offset =
 vsubst [code,`code:byte list`;mk_small_numeral offset,`off:num`]
 `!dst src n a pc returnaddress e.
   a <= n /\ n < 2 EXP 64 /\
   nonoverlapping (word pc,LENGTH code) (dst,n) /\
   nonoverlapping (src,n) (dst,n)
   ==> ensures_n arm
    (\s. aligned_bytes_loaded s (word pc) code /\ read PC s = word(pc+off) /\
         read X30 s = returnaddress /\ read X0 s = dst /\ read X1 s = src /\
         read X2 s = word n /\ read X3 s = word a /\ read events s = e)
    (\s. read PC s = returnaddress /\ read X0 s = dst /\
         ve_read_bytes(read events s) = ve_read_bytes e + (n-a) /\
         ve_write_bytes(read events s) = ve_write_bytes e + (n-a))
    (MAYCHANGE [PC;X3;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
     MAYCHANGE [memory :> bytes(dst,n)]) (\s:armstate. 5*(n-a)+3)`;;

let ve_tail_resource_tac exec offset =
 let at k = mk_binop `(+):num->num->num` `pc:num` (mk_small_numeral(offset+k)) in
 REWRITE_TAC[SOME_FLAGS;fst exec] THEN REPEAT GEN_TAC THEN STRIP_TAC THEN
 VAL_INT64_TAC `n:num` THEN
 SUBGOAL_THEN `a < 2 EXP 64` ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
 VAL_INT64_TAC `a:num` THEN
 ASM_CASES_TAC `a:num = n` THENL
 [ASM_REWRITE_TAC[SUB_REFL] THEN CONV_TAC NUM_REDUCE_CONV THEN
  ARM_SIM_TAC exec (1--3) THEN ASM_REWRITE_TAC ve_count_rewrites;
  ALL_TAC] THEN
 SUBGOAL_THEN `a < n /\ ~(n <= a)` STRIP_ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
 ENSURES_N_WHILE_AUP_TAC `a:num` `n:num` (at 8) (at 20)
 `\i s. read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
   read X30 s = returnaddress /\ read X3 s = word i /\
   (?trace. read events s = trace /\
      ve_read_bytes trace = ve_read_bytes e+(i-a) /\
      ve_write_bytes trace = ve_write_bytes e+(i-a))`
 `\i:num. 3` `2` `2` `3` THEN
 ASM_REWRITE_TAC[] THEN REPEAT CONJ_TAC THENL
 [ARM_SIM_TAC exec (1--2) THEN TRY(EXISTS_TAC `read events s2`) THEN
  ASM_REWRITE_TAC (SUB_REFL::ve_count_rewrites);
  X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
  ARM_SIM_TAC ~preprocess_tac:ve_open_cost_trace exec (1--3) THEN
  REWRITE_TAC[GSYM WORD_ADD] THEN TRY(EXISTS_TAC `read events s3`) THEN
  ASM_REWRITE_TAC ve_count_rewrites THEN ASM_ARITH_TAC;
  X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
  ARM_SIM_TAC ~preprocess_tac:ve_open_cost_trace exec (1--2) THEN
  TRY(EXISTS_TAC `read events s2`) THEN ASM_REWRITE_TAC ve_count_rewrites;
  ARM_SIM_TAC ~preprocess_tac:ve_open_cost_trace exec (1--3) THEN
  ASM_REWRITE_TAC ve_count_rewrites;
  ASM_SIMP_TAC[NSUM_CONST_NUMSEG;ARITH_RULE `!a n:num. a<n ==> ((n-1)+1)-a=n-a`] THEN
  ASM_ARITH_TAC];;
