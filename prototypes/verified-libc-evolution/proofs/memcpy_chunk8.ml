(* Public contract unchanged from the preserved prototype. *)
loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/chunk_tail.ml");;
loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/chunk_bulk.ml");;

let ve_chunk_tail_call step start =
 ARM_SUBROUTINE_SIM_TAC
  (vp2_memcpy_chunk8_mc,VP2_MEMCPY_CHUNK8_EXEC,0,vp2_memcpy_chunk8_mc,VE_CHUNK_TAIL)
  [`dst:int64`;`src:int64`;`n:num`;start;`pc:num`;`returnaddress:int64`;`input:num->byte`] step THEN
 TRY(ASM_REWRITE_TAC[LT;ADD_CLAUSES] THEN NO_TAC) THEN
 ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[];;

let ve_chunk_public_tac =
 REWRITE_TAC[C_ARGUMENTS;SOME_FLAGS;fst VP2_MEMCPY_CHUNK8_EXEC] THEN
 MAP_EVERY X_GEN_TAC [`dst:int64`;`src:int64`] THEN W64_GEN_TAC `n:num` THEN
 MAP_EVERY X_GEN_TAC [`pc:num`;`returnaddress:int64`;`input:num->byte`] THEN
 STRIP_TAC THEN
 SUBGOAL_THEN `0 <= n` ASSUME_TAC THENL [ARITH_TAC;ALL_TAC] THEN
 SUBGOAL_THEN `8*(n DIV 8) <= n` ASSUME_TAC THENL
 [MP_TAC(SPECL [`n:num`;`8`] DIVISION) THEN CONV_TAC NUM_REDUCE_CONV THEN ARITH_TAC;ALL_TAC] THEN
 ASM_CASES_TAC `word_and (word_or dst src) (word 7):int64 = word 0` THENL
 [SUBGOAL_THEN `aligned 8 (dst:int64) /\ aligned 8 (src:int64)` STRIP_ASSUME_TAC THENL
   [MP_TAC(SPECL [`dst:int64`;`src:int64`] VE_FAST_GUARD) THEN ASM_REWRITE_TAC[];ALL_TAC] THEN
  ENSURES_INIT_TAC "s0" THEN ARM_STEPS_TAC VP2_MEMCPY_CHUNK8_EXEC (1--4) THEN
  ARM_SUBROUTINE_SIM_TAC
   (vp2_memcpy_chunk8_mc,VP2_MEMCPY_CHUNK8_EXEC,0,vp2_memcpy_chunk8_mc,VE_CHUNK_BULK)
   [`dst:int64`;`src:int64`;`n:num`;`pc:num`;`input:num->byte`] 5 THEN
  ve_chunk_tail_call 6 `8*(n DIV 8)`;
  SUBGOAL_THEN `~(val(word_and (word_or dst src) (word 7):int64) = 0)`
   ASSUME_TAC THENL [ASM_REWRITE_TAC[VAL_EQ_0];ALL_TAC] THEN
  ENSURES_INIT_TAC "s0" THEN ARM_STEPS_TAC VP2_MEMCPY_CHUNK8_EXEC (1--4) THEN
  ve_chunk_tail_call 5 `0`];;

let VP2_MEMCPY_CHUNK8_CORRECT = prove(vp_copy_contract `vp2_memcpy_chunk8_mc`,ve_chunk_public_tac);;
ve_check "chunk8:public" (vp_copy_contract `vp2_memcpy_chunk8_mc`) VP2_MEMCPY_CHUNK8_CORRECT;;
