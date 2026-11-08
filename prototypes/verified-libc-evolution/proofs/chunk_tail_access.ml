let ve_open_trace name = FIRST_X_ASSUM
 (X_CHOOSE_THEN (mk_var(name,`:uarch_event list`)) STRIP_ASSUME_TAC o
  check (is_exists o concl));;

let ve_tail_access_spec =
 `!dst src n a pc returnaddress e.
   a <= n /\ n < 2 EXP 64 /\ nonoverlapping (word pc,76) (dst,n) /\
   nonoverlapping (src,n) (dst,n)
   ==> ensures arm
    (\s. aligned_bytes_loaded s (word pc) vp2_memcpy_chunk8_mc /\
         read PC s = word(pc+44) /\ read X30 s = returnaddress /\
         read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
         read X3 s = word a /\ read events s = e)
    (\s. read PC s = returnaddress /\
         ?tail_trace. read events s = APPEND tail_trace e /\
          memaccess_inbounds tail_trace [src,n] [dst,n])
    (MAYCHANGE [PC;X3;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
     MAYCHANGE [memory :> bytes(dst,n)])`;;

let ve_tail_access_tac =
 REWRITE_TAC[SOME_FLAGS] THEN REPEAT GEN_TAC THEN STRIP_TAC THEN
 VAL_INT64_TAC `n:num` THEN
 SUBGOAL_THEN `a < 2 EXP 64` ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
 VAL_INT64_TAC `a:num` THEN
 ASM_CASES_TAC `a:num = n` THENL
 [ASM_REWRITE_TAC[] THEN ARM_SIM_TAC VP2_MEMCPY_CHUNK8_EXEC (1--3) THEN
  EXISTS_TAC `[EventJump(word(pc+72),returnaddress);EventJump(word(pc+48),word(pc+72))]` THEN
  REWRITE_TAC[APPEND;memaccess_inbounds;ALL];ALL_TAC] THEN
 SUBGOAL_THEN `a < n /\ ~(n <= a)` STRIP_ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
 ENSURES_WHILE_AUP_TAC `a:num` `n:num` `pc+52` `pc+64`
 `\i s. read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
        read X30 s = returnaddress /\ read X3 s = word i /\
        (?trace. read events s = APPEND trace e /\ memaccess_inbounds trace [src,n] [dst,n])` THEN
 ASM_REWRITE_TAC[] THEN REPEAT CONJ_TAC THENL
 [ARM_SIM_TAC VP2_MEMCPY_CHUNK8_EXEC (1--2) THEN
  EXISTS_TAC `[EventJump(word(pc+48),word(pc+52))]` THEN
  REWRITE_TAC[APPEND;memaccess_inbounds;ALL];
  X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
  SUBGOAL_THEN `i+1 <= n` ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  ENSURES_INIT_TAC "s0" THEN ve_open_trace "trace" THEN
  ARM_SUBROUTINE_SIM_TAC
   (vp2_memcpy_chunk8_mc,VP2_MEMCPY_CHUNK8_EXEC,52,vp2_block_copybyte_indexed_mc,
    REWRITE_RULE[VE_ALIGNED1] VP2_BLOCK_COPYBYTE_INDEXED_CORRECT)
   [`read (memory :> bytes8 (word_add src (word i))) s`;
    `dst:int64`;`src:int64`;`n:num`;`i:num`;`pc+52`;`read events s`] 1 THEN
  ARM_STEPS_TAC VP2_MEMCPY_CHUNK8_EXEC [2] THEN
  ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[GSYM WORD_ADD] THEN
  EXISTS_TAC `APPEND [EventStore(word_add dst (word i),1);
                      EventLoad(word_add src (word i),1)] trace` THEN
  ONCE_REWRITE_TAC[MEMACCESS_INBOUNDS_APPEND] THEN
  RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
  ASM_REWRITE_TAC[APPEND;memaccess_inbounds;ALL;EX] THEN
  ASM_REWRITE_TAC[VAL_WORD_ADD;CONTAINED_MODULO_LMOD;DIMINDEX_64] THEN
  CONJ_TAC THEN MATCH_MP_TAC CONTAINED_MODULO_OFFSET_SIMPLE THEN ASM_ARITH_TAC;
  X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
  ARM_SIM_TAC ~preprocess_tac:(ve_open_trace "trace") VP2_MEMCPY_CHUNK8_EXEC (1--2) THEN
  EXISTS_TAC `CONS(EventJump(word(pc+68),word(pc+52))) trace` THEN
  RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
  ASM_REWRITE_TAC[APPEND;memaccess_inbounds;ALL];
  ARM_SIM_TAC ~preprocess_tac:(ve_open_trace "trace") VP2_MEMCPY_CHUNK8_EXEC (1--3) THEN
  EXISTS_TAC `CONS(EventJump(word(pc+72),returnaddress))
            (CONS(EventJump(word(pc+68),word(pc+72))) trace)` THEN
  RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
  ASM_REWRITE_TAC[APPEND;memaccess_inbounds;ALL]];;

let VE_TAIL_ACCESS = prove(ve_tail_access_spec,ve_tail_access_tac);;
ve_check "chunk8:tail-access" ve_tail_access_spec VE_TAIL_ACCESS;;
