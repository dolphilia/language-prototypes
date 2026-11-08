let ve_move_access_frame =
 `MAYCHANGE [PC;X3;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
  MAYCHANGE [memory :> bytes(dst,val(n:int64))]`;;
let ve_move_access_strong =
 let vars,body=strip_forall(ve_move_access_contract `vp2_memmove_mc`) in
 let pre,goal=dest_imp body in
 list_mk_forall(vars,mk_imp(pre,mk_comb(rator goal,ve_move_access_frame)));;

let ve_move_access_loop theorem trace target =
 ENSURES_INIT_TAC "s0" THEN ARM_STEPS_TAC VP2_MEMMOVE_EXEC (1--4) THEN
 ARM_SUBROUTINE_SIM_TAC
  (vp2_memmove_mc,VP2_MEMMOVE_EXEC,0,vp2_memmove_mc,theorem)
  [`dst:int64`;`src:int64`;`val(n:int64)`;`pc:num`;`returnaddress:int64`;`read events s`] 5 THEN
 TRY(ASM_REWRITE_TAC[WORD_VAL] THEN NO_TAC) THEN
 ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[] THEN
 EXISTS_TAC (mk_binop `APPEND:uarch_event list->uarch_event list->uarch_event list` trace
  (vsubst [target,`target:num`]
   `[EventJump(word(pc+12),word(pc+target));EventJump(word(pc+8),word(pc+12));
     EventJump(word pc,word(pc+4))]`)) THEN
 ONCE_REWRITE_TAC[MEMACCESS_INBOUNDS_APPEND] THEN
 RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
 ASM_REWRITE_TAC[APPEND;GSYM APPEND_ASSOC;memaccess_inbounds;ALL];;

let ve_move_access_tac =
 REWRITE_TAC[fst VP2_MEMMOVE_EXEC;C_ARGUMENTS;SOME_FLAGS] THEN
 REPEAT GEN_TAC THEN STRIP_TAC THEN
 ASM_CASES_TAC `val(n:int64) = 0` THENL
 [SUBGOAL_THEN `n:int64 = word 0` SUBST_ALL_TAC THENL
   [ASM_MESON_TAC[VAL_EQ_0];ALL_TAC] THEN
  ASM_REWRITE_TAC[VAL_WORD_0;LT] THEN ARM_SIM_TAC VP2_MEMMOVE_EXEC (1--2) THEN
  EXISTS_TAC `[EventJump(word(pc+64),returnaddress);EventJump(word pc,word(pc+64))]` THEN
  REWRITE_TAC[APPEND;memaccess_inbounds;ALL];ALL_TAC] THEN
 ASM_CASES_TAC `dst:int64 = src` THENL
 [ASM_REWRITE_TAC[] THEN ARM_SIM_TAC VP2_MEMMOVE_EXEC (1--4) THEN
  EXISTS_TAC `[EventJump(word(pc+64),returnaddress);EventJump(word(pc+8),word(pc+64));
              EventJump(word pc,word(pc+4))]` THEN
  REWRITE_TAC[APPEND;memaccess_inbounds;ALL];ALL_TAC] THEN
 SUBGOAL_THEN `~(val(dst:int64) = val(src:int64))` ASSUME_TAC THENL
  [ASM_REWRITE_TAC[VAL_EQ];ALL_TAC] THEN
 SUBGOAL_THEN `~(val(word_sub (dst:int64) src) = 0)` ASSUME_TAC THENL
  [ASM_REWRITE_TAC[VAL_WORD_SUB_EQ_0];ALL_TAC] THEN
 SUBGOAL_THEN `0 < val(n:int64) /\ val(n:int64) < 2 EXP 64` STRIP_ASSUME_TAC THENL
  [CONJ_TAC THENL [ASM_ARITH_TAC;SIMP_TAC[VAL_BOUND_64]];ALL_TAC] THEN
 ASM_CASES_TAC `val(dst:int64) < val(src:int64)` THENL
 [SUBGOAL_THEN `~(val(src:int64) <= val(dst:int64))` ASSUME_TAC THENL
   [ASM_ARITH_TAC;ve_move_access_loop VE_MOVE_FORWARD_ACCESS `forward_trace:uarch_event list` `16`];
  SUBGOAL_THEN `val(src:int64) <= val(dst:int64)` ASSUME_TAC THENL
   [ASM_ARITH_TAC;ve_move_access_loop VE_MOVE_BACKWARD_ACCESS `backward_trace:uarch_event list` `44`]];;

let VP2_MEMMOVE_ACCESSES_STRONG = prove(ve_move_access_strong,ve_move_access_tac);;
let VP2_MEMMOVE_ACCESSES = prove(ve_move_access_contract `vp2_memmove_mc`,
 REPEAT STRIP_TAC THEN MATCH_MP_TAC ENSURES_FRAME_SUBSUMED THEN
 EXISTS_TAC ve_move_access_frame THEN CONJ_TAC THENL
 [REWRITE_TAC[subsumed];MATCH_MP_TAC VP2_MEMMOVE_ACCESSES_STRONG THEN ASM_REWRITE_TAC[]]);;
ve_check "memmove:access-strong" ve_move_access_strong VP2_MEMMOVE_ACCESSES_STRONG;;
ve_check "memmove:access" (ve_move_access_contract `vp2_memmove_mc`) VP2_MEMMOVE_ACCESSES;;
