(* Failure paths never decrement SP, form a subregion address, or call copy. *)
let ve_split_failure_tac exec finish =
 REWRITE_TAC[C_ARGUMENTS;SOME_FLAGS;fst exec;ADD_CLAUSES] THEN
 ASM_CASES_TAC `split:int64 = word 0` THENL
 [ASM_REWRITE_TAC[] THEN ARM_SIM_TAC exec (1--3) THEN finish 0;ALL_TAC] THEN
 SUBGOAL_THEN `~(val(split:int64) = 0)` ASSUME_TAC THENL
  [ASM_REWRITE_TAC[VAL_EQ_0];ALL_TAC] THEN
 ASM_CASES_TAC `val(capacity:int64) <= val(split:int64)` THENL
 [ARM_SIM_TAC exec (1--5) THEN finish 1;ALL_TAC] THEN
 ASM_CASES_TAC `val(split:int64) < val(n:int64)` THENL
 [SUBGOAL_THEN `val(split:int64) <= val(n:int64) /\ ~(val(word_sub n split) = 0)`
    ASSUME_TAC THENL [ASM_REWRITE_TAC[VE_SPLIT_HIGHER];ALL_TAC] THEN
  ARM_SIM_TAC exec (1--7) THEN finish 2;ALL_TAC] THEN
 SUBGOAL_THEN `val(split:int64) < val(capacity:int64) /\
   val(split:int64) <= val(capacity:int64) /\ 0 < val(split:int64) /\
   val(n:int64) <= val(split:int64) /\ val(capacity:int64)-val(split:int64) < val(n:int64)`
   STRIP_ASSUME_TAC THENL
  [UNDISCH_TAC `~ve_split_guard (val(capacity:int64)) (val(split:int64)) (val(n:int64))` THEN
   REWRITE_TAC[ve_split_guard] THEN ASM_ARITH_TAC;ALL_TAC] THEN
 SUBGOAL_THEN `val(word_sub (capacity:int64) split) = val capacity - val split` ASSUME_TAC THENL
  [ASM_SIMP_TAC[VAL_WORD_SUB_CASES];ALL_TAC] THEN
 SUBGOAL_THEN
  `~(val(split:int64) <= val(n:int64) /\ ~(val(word_sub n split) = 0)) /\
    (val(word_sub (capacity:int64) split) <= val n /\
       ~(val(word_sub n (word_sub capacity split)) = 0))` STRIP_ASSUME_TAC THENL
  [ASM_REWRITE_TAC[VE_SPLIT_HIGHER] THEN ASM_ARITH_TAC;ALL_TAC] THEN
 SUBGOAL_THEN
  `val(capacity:int64)-val(split:int64) <= val(n:int64) /\
      ~(val(word_sub n (word_sub capacity split)) = 0)` ASSUME_TAC THENL
  [MP_TAC(SPECL [`n:int64`;`word_sub (capacity:int64) split`] VE_SPLIT_HIGHER) THEN
   ASM_REWRITE_TAC[] THEN ASM_ARITH_TAC;ALL_TAC] THEN
 ARM_SIM_TAC exec (1--10) THEN finish 3;;

let ve_split_public_tac exec success =
 REPEAT GEN_TAC THEN DISCH_TAC THEN
 ASM_CASES_TAC `ve_split_guard (val(capacity:int64)) (val(split:int64)) (val(n:int64))` THENL
 [MATCH_MP_TAC success THEN ASM_REWRITE_TAC[];
  ASM_REWRITE_TAC[] THEN ve_split_failure_tac exec (fun _ -> ALL_TAC)];;
