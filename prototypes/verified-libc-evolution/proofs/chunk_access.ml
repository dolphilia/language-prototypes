loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/chunk_tail_access.ml");;
loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/chunk_bulk_access.ml");;

let ve_access_reframe spec frame =
 let vars,body=strip_forall spec in let pre,goal=dest_imp body in
 list_mk_forall(vars,mk_imp(pre,mk_comb(rator goal,frame)));;
let ve_chunk_access_frame =
 `MAYCHANGE [PC;X3;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
  MAYCHANGE [memory :> bytes(dst,val(n:int64))]`;;
let ve_chunk_access_strong = ve_access_reframe
 (vp_copy_access_contract `vp2_memcpy_chunk8_mc`) ve_chunk_access_frame;;

let ve_tail_access_call step start =
 ARM_SUBROUTINE_SIM_TAC
  (vp2_memcpy_chunk8_mc,VP2_MEMCPY_CHUNK8_EXEC,0,vp2_memcpy_chunk8_mc,VE_TAIL_ACCESS)
  [`dst:int64`;`src:int64`;`n:num`;start;`pc:num`;`returnaddress:int64`;`read events s`] step THEN
 TRY(ASM_REWRITE_TAC[LT;ADD_CLAUSES] THEN NO_TAC) THEN

 ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[];;

let ve_chunk_access_tac =
 REWRITE_TAC[C_ARGUMENTS;SOME_FLAGS;fst VP2_MEMCPY_CHUNK8_EXEC] THEN
 MAP_EVERY X_GEN_TAC [`dst:int64`;`src:int64`] THEN W64_GEN_TAC `n:num` THEN
 MAP_EVERY X_GEN_TAC [`pc:num`;`returnaddress:int64`;`e:uarch_event list`] THEN STRIP_TAC THEN
 SUBGOAL_THEN `0 <= n` ASSUME_TAC THENL [ARITH_TAC;ALL_TAC] THEN
 SUBGOAL_THEN `8*(n DIV 8) <= n` ASSUME_TAC THENL
 [MP_TAC(SPECL [`n:num`;`8`] DIVISION) THEN CONV_TAC NUM_REDUCE_CONV THEN ARITH_TAC;ALL_TAC] THEN
 ASM_CASES_TAC `word_and (word_or dst src) (word 7):int64 = word 0` THENL
 [SUBGOAL_THEN `aligned 8 (dst:int64) /\ aligned 8 (src:int64)` STRIP_ASSUME_TAC THENL
   [MP_TAC(SPECL [`dst:int64`;`src:int64`] VE_FAST_GUARD) THEN ASM_REWRITE_TAC[];ALL_TAC] THEN
  ENSURES_INIT_TAC "s0" THEN ARM_STEPS_TAC VP2_MEMCPY_CHUNK8_EXEC (1--4) THEN
  ARM_SUBROUTINE_SIM_TAC
   (vp2_memcpy_chunk8_mc,VP2_MEMCPY_CHUNK8_EXEC,0,vp2_memcpy_chunk8_mc,VE_BULK_ACCESS)
   [`dst:int64`;`src:int64`;`n:num`;`pc:num`;`read events s`] 5 THEN
  ve_tail_access_call 6 `8*(n DIV 8)` THEN
  EXISTS_TAC `APPEND tail_trace (APPEND bulk_trace [EventJump(word(pc+12),word(pc+16))])` THEN
  REWRITE_TAC[MEMACCESS_INBOUNDS_APPEND] THEN
  RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
  ASM_REWRITE_TAC[APPEND;GSYM APPEND_ASSOC;memaccess_inbounds;ALL];
  SUBGOAL_THEN `~(val(word_and (word_or dst src) (word 7):int64) = 0)`
   ASSUME_TAC THENL [ASM_REWRITE_TAC[VAL_EQ_0];ALL_TAC] THEN
  ENSURES_INIT_TAC "s0" THEN ARM_STEPS_TAC VP2_MEMCPY_CHUNK8_EXEC (1--4) THEN
  ve_tail_access_call 5 `0` THEN
  EXISTS_TAC `APPEND tail_trace [EventJump(word(pc+12),word(pc+44))]` THEN
  ONCE_REWRITE_TAC[MEMACCESS_INBOUNDS_APPEND] THEN
  RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
  ASM_REWRITE_TAC[APPEND;GSYM APPEND_ASSOC;memaccess_inbounds;ALL]];;

let VP2_MEMCPY_CHUNK8_ACCESSES_STRONG = prove(ve_chunk_access_strong,ve_chunk_access_tac);;
let VP2_MEMCPY_CHUNK8_ACCESSES = prove(vp_copy_access_contract `vp2_memcpy_chunk8_mc`,
 REPEAT STRIP_TAC THEN MATCH_MP_TAC ENSURES_FRAME_SUBSUMED THEN
 EXISTS_TAC ve_chunk_access_frame THEN CONJ_TAC THENL
 [REWRITE_TAC[subsumed];
  MATCH_MP_TAC VP2_MEMCPY_CHUNK8_ACCESSES_STRONG THEN ASM_REWRITE_TAC[]]);;
ve_check "chunk8:access-strong" ve_chunk_access_strong VP2_MEMCPY_CHUNK8_ACCESSES_STRONG;;
ve_check "chunk8:access" (vp_copy_access_contract `vp2_memcpy_chunk8_mc`) VP2_MEMCPY_CHUNK8_ACCESSES;;
