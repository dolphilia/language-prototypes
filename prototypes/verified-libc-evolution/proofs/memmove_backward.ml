(* Backward copying preserves the unread source prefix and copied suffix. *)
let ve_move_backward_spec =
 `!dst src n pc returnaddress (input:num->byte).
    0 < n /\ n < 2 EXP 64 /\ val src < val dst /\
    val dst+n <= 2 EXP 64 /\ val src+n <= 2 EXP 64 /\
    nonoverlapping (word pc,68) (dst,n)
    ==> ensures arm
     (\s. aligned_bytes_loaded s (word pc) vp2_memmove_mc /\
          read PC s = word(pc+44) /\ read X30 s = returnaddress /\
          read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
          (!j. j < n ==> read (memory :> bytes8 (word_add src (word j))) s = input j))
     (\s. read PC s = returnaddress /\ read X0 s = dst /\
          (!j. j < n ==> read (memory :> bytes8 (word_add dst (word j))) s = input j))
     (MAYCHANGE [PC;X3;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
      MAYCHANGE [memory :> bytes(dst,n)])`;;

let ve_move_backward_tac =
 REWRITE_TAC[SOME_FLAGS] THEN REPEAT GEN_TAC THEN STRIP_TAC THEN
 VAL_INT64_TAC `n:num` THEN
 SUBGOAL_THEN `~(n = 0)` ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
 ENSURES_WHILE_DOWN_TAC `n:num` `pc+48` `pc+60`
 `\i s. read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
        read X30 s = returnaddress /\ read X3 s = word i /\
        (!j. j < i ==> read (memory :> bytes8 (word_add src (word j))) s = input j) /\
        (!j. i <= j /\ j < n ==>
             read (memory :> bytes8 (word_add dst (word j))) s = input j)` THEN
 ASM_REWRITE_TAC[LT] THEN REPEAT CONJ_TAC THENL
 [ARM_SIM_TAC VP2_MEMMOVE_EXEC [1] THEN ASM_ARITH_TAC;
  X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
  SUBGOAL_THEN `i+1 <= n` ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  SUBGOAL_THEN
   `nonoverlapping (src:int64,i+1) (word_add (dst:int64) (word i),1)`
   ASSUME_TAC THENL
   [MATCH_MP_TAC(SPECL [`dst:int64`;`src:int64`;`n:num`;`i:num`] VE_MOVE_BACKWARD_RANGE) THEN
    ASM_REWRITE_TAC[];ALL_TAC] THEN
  SUBGOAL_THEN `word_sub (word(i+1):int64) (word 1) = word i` ASSUME_TAC THENL
   [REWRITE_TAC[GSYM WORD_ADD] THEN CONV_TAC WORD_RULE;ALL_TAC] THEN
  ENSURES_INIT_TAC "s0" THEN ARM_STEPS_TAC VP2_MEMMOVE_EXEC [1] THEN
  SUBGOAL_THEN `read (memory :> bytes8 (word_add src (word i))) s1 = input i`
   ASSUME_TAC THENL [ASM_MESON_TAC[ARITH_RULE `i < i+1`];ALL_TAC] THEN
  ARM_SUBROUTINE_SIM_TAC
   (vp2_memmove_mc,VP2_MEMMOVE_EXEC,52,
    vp2_block_copybyte_indexed_mc,REWRITE_RULE[VE_MOVE_ALIGNED1] VP2_BLOCK_COPYBYTE_INDEXED_CORRECT)
   [`input(i:num):byte`;`dst:int64`;`src:int64`;`n:num`;`i:num`;
    `pc+52`;`read events s`] 2 THEN
  ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[] THEN
  CONJ_TAC THENL
   [X_GEN_TAC `j:num` THEN DISCH_TAC THEN
    SUBGOAL_THEN `j < i+1` ASSUME_TAC THENL [ASM_ARITH_TAC;ASM_MESON_TAC[]];
    X_GEN_TAC `j:num` THEN STRIP_TAC THEN ASM_CASES_TAC `j:num = i` THEN
    ASM_REWRITE_TAC[] THEN
    SUBGOAL_THEN `i+1 <= j` ASSUME_TAC THENL [ASM_ARITH_TAC;ASM_MESON_TAC[]]];
  X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
  ARM_SIM_TAC VP2_MEMMOVE_EXEC [1];
  ARM_SIM_TAC VP2_MEMMOVE_EXEC (1--2) THEN ASM_MESON_TAC[LE_0]];;

let VE_MOVE_BACKWARD = prove(ve_move_backward_spec,ve_move_backward_tac);;
ve_check "memmove:backward" ve_move_backward_spec VE_MOVE_BACKWARD;;
