loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/memory.ml");;

let ve_chunk_bulk_spec =
 `!dst src n pc (input:num->byte).
   n < 2 EXP 64 /\ aligned 8 dst /\ aligned 8 src /\
   nonoverlapping (word pc,76) (dst,n) /\ nonoverlapping (src,n) (dst,n)
   ==> ensures arm
    (\s. aligned_bytes_loaded s (word pc) vp2_memcpy_chunk8_mc /\
         read PC s = word(pc+16) /\
         read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
         read X3 s = word 0 /\
         (!j. j < n ==> read (memory :> bytes8 (word_add src (word j))) s = input j))
    (\s. read PC s = word(pc+44) /\
         read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
         read X3 s = word(8*(n DIV 8)) /\
         (!j. j < n ==> read (memory :> bytes8 (word_add src (word j))) s = input j) /\
         (!j. j < 8*(n DIV 8) ==>
           read (memory :> bytes8 (word_add dst (word j))) s = input j))
    (MAYCHANGE [PC;X3;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
     MAYCHANGE [memory :> bytes(dst,n)])`;;

let ve_chunk_bulk_tac =
 REWRITE_TAC[SOME_FLAGS] THEN REPEAT GEN_TAC THEN STRIP_TAC THEN
 VAL_INT64_TAC `n:num` THEN
 SUBGOAL_THEN `8*(n DIV 8) <= n /\ n < 8*(n DIV 8)+8`
  STRIP_ASSUME_TAC THENL
 [MP_TAC(SPECL [`n:num`;`8`] DIVISION) THEN CONV_TAC NUM_REDUCE_CONV THEN ARITH_TAC;
  ALL_TAC] THEN
 ASM_CASES_TAC `n DIV 8 = 0` THENL
 [SUBGOAL_THEN `n < 8` ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  ASM_REWRITE_TAC[MULT_CLAUSES;LT] THEN ARM_SIM_TAC VP2_MEMCPY_CHUNK8_EXEC (1--3) THEN
  ASM_REWRITE_TAC[WORD_SUB_0;ARITH_RULE `8 <= n <=> ~(n < 8)`];ALL_TAC] THEN
 ENSURES_WHILE_UP_TAC `n DIV 8` `pc+16` `pc+40`
 `\i s. read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
        read X3 s = word(8*i) /\
        (!j. j < n ==> read (memory :> bytes8 (word_add src (word j))) s = input j) /\
        (!j. j < 8*i ==> read (memory :> bytes8 (word_add dst (word j))) s = input j)` THEN
 ASM_REWRITE_TAC[MULT_CLAUSES;LT] THEN REPEAT CONJ_TAC THENL
 [ENSURES_INIT_TAC "s0" THEN ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[];
  X_GEN_TAC `i:num` THEN STRIP_TAC THEN
  SUBGOAL_THEN `8*i+8 <= n /\ 8*i <= n /\ 8 <= n-8*i /\ 8*i < 2 EXP 64`
   STRIP_ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  VAL_INT64_TAC `8*i` THEN
  SUBGOAL_THEN `val(word_sub (word n) (word(8*i)):int64) = n-8*i`
   ASSUME_TAC THENL [ASM_REWRITE_TAC[VAL_WORD_SUB_CASES];ALL_TAC] THEN
  SUBGOAL_THEN `aligned 8 (word_add (src:int64) (word(8*i))) /\
                aligned 8 (word_add (dst:int64) (word(8*i)))`
   STRIP_ASSUME_TAC THENL
   [CONJ_TAC THEN MATCH_MP_TAC ALIGNED_WORD_ADD THEN
    ASM_SIMP_TAC[ALIGNED_WORD;DIMINDEX_64;DIVIDES_RMUL;DIVIDES_REFL] THEN
    CONV_TAC NUM_REDUCE_CONV THEN CONV_TAC DIVIDES_CONV;
    ALL_TAC] THEN
  ENSURES_INIT_TAC "s0" THEN
  ABBREV_TAC `b:int64 = read (memory :> bytes64 (word_add src (word(8*i)))) s0` THEN
  ARM_STEPS_TAC VP2_MEMCPY_CHUNK8_EXEC (1--3) THEN
  ARM_SUBROUTINE_SIM_TAC
   (vp2_memcpy_chunk8_mc,VP2_MEMCPY_CHUNK8_EXEC,28,
    vp2_block_copy8_indexed_mc,VP2_BLOCK_COPY8_INDEXED_CORRECT)
   [`b:int64`;`dst:int64`;`src:int64`;`n:num`;`8*i`;`pc+28`;`read events s`] 4 THEN
  ARM_STEPS_TAC VP2_MEMCPY_CHUNK8_EXEC [5] THEN
  SUBGOAL_THEN
   `!r. r < 8 ==>
      read (memory :> bytes8 (word_add dst (word(8*i+r)))) s5 = input(8*i+r)`
   (LABEL_TAC "block-bytes") THENL
   [MP_TAC(SPECL [`word_add dst (word(8*i)):int64`;
      `word_add src (word(8*i)):int64`;`s5:armstate`;`s5:armstate`] VE_BYTES64_EQ) THEN
    ASM_REWRITE_TAC[] THEN
    REWRITE_TAC[WORD_RULE `word_add (word_add a (word b)) (word c) = word_add a (word(b+c))`] THEN
    DISCH_TAC THEN X_GEN_TAC `r:num` THEN DISCH_TAC THEN
    ASM_MESON_TAC[ARITH_RULE `8*i+8 <= n /\ r < 8 ==> 8*i+r < n`];ALL_TAC] THEN
  ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[GSYM WORD_ADD;ARITH_RULE `8*i+8 = 8*(i+1)`] THEN
  X_GEN_TAC `j:num` THEN DISCH_TAC THEN ASM_CASES_TAC `j < 8*i` THENL
   [ASM_MESON_TAC[];
    SUBGOAL_THEN `j-8*i < 8 /\ 8*i+(j-8*i)=j` STRIP_ASSUME_TAC THENL
     [ASM_ARITH_TAC;ALL_TAC] THEN
    USE_THEN "block-bytes" (fun th ->
      MATCH_ACCEPT_TAC(REWRITE_RULE [ASSUME `8*i+(j-8*i)=j`]
       (MATCH_MP (SPEC `j-8*i` th) (ASSUME `j-8*i < 8`))))];
  X_GEN_TAC `i:num` THEN STRIP_TAC THEN ARM_SIM_TAC VP2_MEMCPY_CHUNK8_EXEC [1];
  SUBGOAL_THEN `8*(n DIV 8) <= n /\ 8*(n DIV 8) < 2 EXP 64`
   STRIP_ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  VAL_INT64_TAC `8*(n DIV 8)` THEN
  SUBGOAL_THEN `val(word_sub (word n) (word(8*(n DIV 8))):int64) = n-8*(n DIV 8)`
   ASSUME_TAC THENL [ASM_REWRITE_TAC[VAL_WORD_SUB_CASES];ALL_TAC] THEN
  SUBGOAL_THEN `~(8 <= n-8*(n DIV 8))` ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  ARM_SIM_TAC VP2_MEMCPY_CHUNK8_EXEC (1--4)];;

let VE_CHUNK_BULK = prove(ve_chunk_bulk_spec,ve_chunk_bulk_tac);;
ve_check "chunk8:bulk" ve_chunk_bulk_spec VE_CHUNK_BULK;;
