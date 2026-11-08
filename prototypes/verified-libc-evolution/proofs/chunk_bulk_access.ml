let ve_bulk_access_spec =
 `!dst src n pc e.
   n < 2 EXP 64 /\ aligned 8 dst /\ aligned 8 src /\
   nonoverlapping (word pc,76) (dst,n) /\ nonoverlapping (src,n) (dst,n)
   ==> ensures arm
    (\s. aligned_bytes_loaded s (word pc) vp2_memcpy_chunk8_mc /\
         read PC s = word(pc+16) /\
         read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
         read X3 s = word 0 /\ read events s = e)
    (\s. read PC s = word(pc+44) /\
         read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
         read X3 s = word(8*(n DIV 8)) /\
         ?bulk_trace. read events s = APPEND bulk_trace e /\ memaccess_inbounds bulk_trace [src,n] [dst,n])
    (MAYCHANGE [PC;X3;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
     MAYCHANGE [memory :> bytes(dst,n)])`;;

let ve_bulk_access_tac =
 REWRITE_TAC[SOME_FLAGS] THEN REPEAT GEN_TAC THEN STRIP_TAC THEN
 VAL_INT64_TAC `n:num` THEN
 SUBGOAL_THEN `8*(n DIV 8) <= n /\ n < 8*(n DIV 8)+8`
  STRIP_ASSUME_TAC THENL
 [MP_TAC(SPECL [`n:num`;`8`] DIVISION) THEN CONV_TAC NUM_REDUCE_CONV THEN ARITH_TAC;ALL_TAC] THEN
 ASM_CASES_TAC `n DIV 8 = 0` THENL
 [SUBGOAL_THEN `n < 8` ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  ASM_REWRITE_TAC[MULT_CLAUSES] THEN ARM_SIM_TAC VP2_MEMCPY_CHUNK8_EXEC (1--3) THEN
  ASM_REWRITE_TAC[WORD_SUB_0;ARITH_RULE `8 <= n <=> ~(n < 8)`] THEN
  EXISTS_TAC `[EventJump(word(pc+24),word(pc+44))]` THEN
  REWRITE_TAC[APPEND;memaccess_inbounds;ALL];ALL_TAC] THEN
 ENSURES_WHILE_UP_TAC `n DIV 8` `pc+16` `pc+40`
 `\i s. read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
        read X3 s = word(8*i) /\
        (?trace. read events s = APPEND trace e /\ memaccess_inbounds trace [src,n] [dst,n])` THEN
 ASM_REWRITE_TAC[MULT_CLAUSES] THEN REPEAT CONJ_TAC THENL
 [ENSURES_INIT_TAC "s0" THEN ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[] THEN
  EXISTS_TAC `[]:uarch_event list` THEN REWRITE_TAC[APPEND;memaccess_inbounds;ALL];
  X_GEN_TAC `i:num` THEN STRIP_TAC THEN
  SUBGOAL_THEN `8*i+8 <= n /\ 8*i <= n /\ 8 <= n-8*i /\ 8*i < 2 EXP 64`
   STRIP_ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN VAL_INT64_TAC `8*i` THEN
  SUBGOAL_THEN `val(word_sub (word n) (word(8*i)):int64) = n-8*i`
   ASSUME_TAC THENL [ASM_REWRITE_TAC[VAL_WORD_SUB_CASES];ALL_TAC] THEN
  SUBGOAL_THEN `aligned 8 (word_add (src:int64) (word(8*i))) /\
                aligned 8 (word_add (dst:int64) (word(8*i)))`
   STRIP_ASSUME_TAC THENL
   [CONJ_TAC THEN MATCH_MP_TAC ALIGNED_WORD_ADD THEN
    ASM_SIMP_TAC[ALIGNED_WORD;DIMINDEX_64;DIVIDES_RMUL;DIVIDES_REFL] THEN
    CONV_TAC NUM_REDUCE_CONV THEN CONV_TAC DIVIDES_CONV;ALL_TAC] THEN
  ENSURES_INIT_TAC "s0" THEN ve_open_trace "trace" THEN
  ARM_STEPS_TAC VP2_MEMCPY_CHUNK8_EXEC (1--3) THEN
  ARM_SUBROUTINE_SIM_TAC
   (vp2_memcpy_chunk8_mc,VP2_MEMCPY_CHUNK8_EXEC,28,vp2_block_copy8_indexed_mc,
    VP2_BLOCK_COPY8_INDEXED_CORRECT)
   [`read (memory :> bytes64 (word_add src (word(8*i)))) s`;
    `dst:int64`;`src:int64`;`n:num`;`8*i`;`pc+28`;`read events s`] 4 THEN
  ARM_STEPS_TAC VP2_MEMCPY_CHUNK8_EXEC [5] THEN
  ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[GSYM WORD_ADD;ARITH_RULE `8*i+8=8*(i+1)`] THEN
  EXISTS_TAC `APPEND [EventStore(word_add dst (word(8*i)),8);
    EventLoad(word_add src (word(8*i)),8);EventJump(word(pc+24),word(pc+28))] trace` THEN
  ONCE_REWRITE_TAC[MEMACCESS_INBOUNDS_APPEND] THEN
  RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
  ASM_REWRITE_TAC[APPEND;memaccess_inbounds;ALL;EX] THEN
  ASM_REWRITE_TAC[VAL_WORD_ADD;CONTAINED_MODULO_LMOD;DIMINDEX_64] THEN
  CONJ_TAC THEN MATCH_MP_TAC CONTAINED_MODULO_OFFSET_SIMPLE THEN ASM_ARITH_TAC;
  X_GEN_TAC `i:num` THEN STRIP_TAC THEN
  ARM_SIM_TAC ~preprocess_tac:(ve_open_trace "trace") VP2_MEMCPY_CHUNK8_EXEC [1] THEN
  EXISTS_TAC `CONS(EventJump(word(pc+40),word(pc+16))) trace` THEN
  RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
  ASM_REWRITE_TAC[APPEND;memaccess_inbounds;ALL];
  SUBGOAL_THEN `8*(n DIV 8) < 2 EXP 64` ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  VAL_INT64_TAC `8*(n DIV 8)` THEN
  SUBGOAL_THEN `val(word_sub (word n) (word(8*(n DIV 8))):int64) = n-8*(n DIV 8)`
   ASSUME_TAC THENL [ASM_REWRITE_TAC[VAL_WORD_SUB_CASES];ALL_TAC] THEN
  SUBGOAL_THEN `~(8 <= n-8*(n DIV 8))` ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  ARM_SIM_TAC ~preprocess_tac:(ve_open_trace "trace") VP2_MEMCPY_CHUNK8_EXEC (1--4) THEN
  EXISTS_TAC `CONS(EventJump(word(pc+24),word(pc+44)))
            (CONS(EventJump(word(pc+40),word(pc+16))) trace)` THEN
  RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
  ASM_REWRITE_TAC[APPEND;memaccess_inbounds;ALL]];;

let VE_BULK_ACCESS = prove(ve_bulk_access_spec,ve_bulk_access_tac);;
ve_check "chunk8:bulk-access" ve_bulk_access_spec VE_BULK_ACCESS;;
