let ve_exact_count =
 `if (n:int64) = word 8 then
   if word_and (word_or (dst:int64) src) (word 7) = word 0 then 8 else 48
  else 5*val n+5`;;

let ve_exact_resource_tac mc exec scalar scalar_thm =
 let scalar_call =
  ENSURES_INIT_TAC "s0" THEN
  ve_n_subroutine_tac (mc,exec,32,scalar,scalar_thm)
   [`dst:int64`;`src:int64`;`n:int64`;`pc+32`;`returnaddress:int64`;`read events s`] 1 `0` THEN
  TRY(ASM_REWRITE_TAC[ADD_CLAUSES] THEN NO_TAC) THEN
  ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC ve_count_rewrites THEN ARITH_TAC in
 REWRITE_TAC[SOME_FLAGS;fst exec] THEN REPEAT GEN_TAC THEN STRIP_TAC THEN
 ASM_CASES_TAC `n:int64 = word 8` THENL
 [UNDISCH_TAC `n:int64 = word 8` THEN DISCH_THEN SUBST_ALL_TAC THEN
  RULE_ASSUM_TAC(CONV_RULE(DEPTH_CONV WORD_NUM_RED_CONV)) THEN
  CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN
  ASM_CASES_TAC `word_and (word_or dst src) (word 7):int64 = word 0` THEN ASM_REWRITE_TAC[] THENL
  [SUBGOAL_THEN `aligned 8 (dst:int64) /\ aligned 8 (src:int64)` STRIP_ASSUME_TAC THENL
   [MP_TAC(SPECL [`dst:int64`;`src:int64`] VE_FAST_GUARD) THEN ASM_REWRITE_TAC[];ALL_TAC] THEN
   ARM_SIM_TAC exec (1--8) THEN ASM_REWRITE_TAC ve_count_rewrites THEN ARITH_TAC;
   SUBGOAL_THEN `~(val(word_and (word_or dst src) (word 7):int64) = 0)` ASSUME_TAC THENL
   [ASM_REWRITE_TAC[VAL_EQ_0];ALL_TAC] THEN
   ENSURES_N_SEQUENCE_TAC `pc+32`
    `\s. read X0 s = dst /\ read X1 s = src /\ read X2 s = word 8 /\ read X30 s = returnaddress /\
      read events s = CONS(EventJump(word(pc+16),word(pc+32)))
       (CONS(EventJump(word(pc+4),word(pc+8))) e)` `5` `43` THEN
   REPEAT CONJ_TAC THENL
   [ARM_SIM_TAC exec (1--5);
    ENSURES_INIT_TAC "s0" THEN
    ve_n_subroutine_tac (mc,exec,32,scalar,scalar_thm)
     [`dst:int64`;`src:int64`;`word 8:int64`;`pc+32`;`returnaddress:int64`;`read events s`] 1 `0` THEN
    TRY(ASM_REWRITE_TAC[ADD_CLAUSES] THEN NO_TAC) THEN
    ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC ve_count_rewrites THEN ARITH_TAC;
    CONV_TAC NUM_REDUCE_CONV]];
  ASM_REWRITE_TAC[] THEN
  SUBGOAL_THEN `~(val(word_sub (n:int64) (word 8)) = 0)` ASSUME_TAC THENL
  [ASM_REWRITE_TAC[VAL_EQ_0;WORD_SUB_EQ_0];ALL_TAC] THEN
  ENSURES_N_SEQUENCE_TAC `pc+32`
   `\s. read X0 s = dst /\ read X1 s = src /\ read X2 s = n /\ read X30 s = returnaddress /\
     read events s = CONS(EventJump(word(pc+4),word(pc+32))) e`
   `2` `5*val(n:int64)+3` THEN REPEAT CONJ_TAC THENL
  [ARM_SIM_TAC exec (1--2);scalar_call;ARITH_TAC]];;
