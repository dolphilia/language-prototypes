let ve_chunk_zero_spec =
 `!dst src pc returnaddress e.
   ensures arm
    (\s. aligned_bytes_loaded s (word pc) vp2_memcpy_chunk8_mc /\
         read PC s = word pc /\ read X30 s = returnaddress /\
         C_ARGUMENTS [dst;src;word 0] s /\ read events s = e)
    (\s. read PC s = returnaddress /\ read X0 s = dst /\
         read events s = APPEND
          (if word_and (word_or dst src) (word 7):int64 = word 0 then
            [EventJump(word(pc+72),returnaddress);EventJump(word(pc+48),word(pc+72));
             EventJump(word(pc+24),word(pc+44));EventJump(word(pc+12),word(pc+16))]
           else
            [EventJump(word(pc+72),returnaddress);EventJump(word(pc+48),word(pc+72));
             EventJump(word(pc+12),word(pc+44))]) e)
    (MAYCHANGE [PC;X3;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events])`;;
let VE_CHUNK_ZERO = prove(ve_chunk_zero_spec,
 REWRITE_TAC[C_ARGUMENTS;SOME_FLAGS] THEN REPEAT GEN_TAC THEN
 ASM_CASES_TAC `word_and (word_or dst src) (word 7):int64 = word 0` THENL
 [ASM_REWRITE_TAC[] THEN ARM_SIM_TAC VP2_MEMCPY_CHUNK8_EXEC (1--10) THEN REWRITE_TAC[APPEND];
  SUBGOAL_THEN `~(val(word_and (word_or dst src) (word 7):int64) = 0)`
   ASSUME_TAC THENL [ASM_REWRITE_TAC[VAL_EQ_0];ALL_TAC] THEN
  ASM_REWRITE_TAC[] THEN ARM_SIM_TAC VP2_MEMCPY_CHUNK8_EXEC (1--7) THEN REWRITE_TAC[APPEND]]);;
ve_check "chunk8:zero-no-data" ve_chunk_zero_spec VE_CHUNK_ZERO;;
