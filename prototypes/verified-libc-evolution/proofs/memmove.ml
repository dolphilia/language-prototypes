(* Entry dispatch uses unsigned machine-address order. Equal pointers return
   without data access; the two loop theorems cover the remaining cases. *)
let ve_move_call_loop theorem =
 ENSURES_INIT_TAC "s0" THEN ARM_STEPS_TAC VP2_MEMMOVE_EXEC (1--4) THEN
 ARM_SUBROUTINE_SIM_TAC
  (vp2_memmove_mc,VP2_MEMMOVE_EXEC,0,vp2_memmove_mc,theorem)
  [`dst:int64`;`src:int64`;`val(n:int64)`;`pc:num`;`returnaddress:int64`;`input:num->byte`] 5 THEN
 TRY(ASM_REWRITE_TAC[WORD_VAL] THEN NO_TAC) THEN
 ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[];;

let ve_move_public_tac =
 REWRITE_TAC[fst VP2_MEMMOVE_EXEC;C_ARGUMENTS;SOME_FLAGS] THEN
 REPEAT GEN_TAC THEN STRIP_TAC THEN
 ASM_CASES_TAC `val(n:int64) = 0` THENL
 [SUBGOAL_THEN `n:int64 = word 0` SUBST_ALL_TAC THENL
   [ASM_MESON_TAC[VAL_EQ_0];ALL_TAC] THEN
  ASM_REWRITE_TAC[VAL_WORD_0;LT] THEN ARM_SIM_TAC VP2_MEMMOVE_EXEC (1--2);
  ALL_TAC] THEN
 ASM_CASES_TAC `dst:int64 = src` THENL
 [ASM_REWRITE_TAC[] THEN ARM_SIM_TAC VP2_MEMMOVE_EXEC (1--4) THEN ASM_MESON_TAC[];ALL_TAC] THEN
 SUBGOAL_THEN `~(val(dst:int64) = val(src:int64))` ASSUME_TAC THENL
  [ASM_REWRITE_TAC[VAL_EQ];ALL_TAC] THEN
 SUBGOAL_THEN `~(val(word_sub (dst:int64) src) = 0)` ASSUME_TAC THENL
  [ASM_REWRITE_TAC[VAL_WORD_SUB_EQ_0];ALL_TAC] THEN
 SUBGOAL_THEN `0 < val(n:int64) /\ val(n:int64) < 2 EXP 64` STRIP_ASSUME_TAC THENL
  [CONJ_TAC THENL [ASM_ARITH_TAC;SIMP_TAC[VAL_BOUND_64]];ALL_TAC] THEN
 ASM_CASES_TAC `val(dst:int64) < val(src:int64)` THENL
 [SUBGOAL_THEN `~(val(src:int64) <= val(dst:int64))` ASSUME_TAC THENL
   [ASM_ARITH_TAC;ve_move_call_loop VE_MOVE_FORWARD];
  SUBGOAL_THEN `val(src:int64) < val(dst:int64) /\ val(src:int64) <= val(dst:int64)` STRIP_ASSUME_TAC THENL
   [ASM_ARITH_TAC;ve_move_call_loop VE_MOVE_BACKWARD]];;

let VP2_MEMMOVE_CORRECT = prove(ve_move_contract `vp2_memmove_mc`,ve_move_public_tac);;
ve_check "memmove:public" (ve_move_contract `vp2_memmove_mc`) VP2_MEMMOVE_CORRECT;;
