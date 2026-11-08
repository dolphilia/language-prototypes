(* Reused logical byte/word and alignment lemmas from the preserved prototype. *)
let VE_JOIN_EQ_16 = prove
 (`!(a:byte) (b:byte) (c:byte) (d:byte).
     (word_join a b:int16 = word_join c d) <=> a=c /\ b=d`,
  REPEAT GEN_TAC THEN EQ_TAC THENL
   [DISCH_THEN(fun th ->
      MP_TAC(AP_TERM `\w:int16. word_subword w (8,8):byte` th) THEN
      MP_TAC(AP_TERM `\w:int16. word_subword w (0,8):byte` th)) THEN
    SIMP_TAC[WORD_SUBWORD_JOIN_LOWER;WORD_SUBWORD_JOIN_UPPER;
      DIMINDEX_8;DIMINDEX_16;ARITH;WORD_SUBWORD_TRIVIAL;SUB_REFL] THEN
    MESON_TAC[];
    STRIP_TAC THEN ASM_REWRITE_TAC[]]);;

let VE_JOIN_EQ_32 = prove
 (`!(a:int16) (b:int16) (c:int16) (d:int16).
     (word_join a b:int32 = word_join c d) <=> a=c /\ b=d`,
  REPEAT GEN_TAC THEN EQ_TAC THENL
   [DISCH_THEN(fun th ->
      MP_TAC(AP_TERM `\w:int32. word_subword w (16,16):int16` th) THEN
      MP_TAC(AP_TERM `\w:int32. word_subword w (0,16):int16` th)) THEN
    SIMP_TAC[WORD_SUBWORD_JOIN_LOWER;WORD_SUBWORD_JOIN_UPPER;
      DIMINDEX_16;DIMINDEX_32;ARITH;WORD_SUBWORD_TRIVIAL;SUB_REFL] THEN
    MESON_TAC[];
    STRIP_TAC THEN ASM_REWRITE_TAC[]]);;

let VE_JOIN_EQ_64 = prove
 (`!(a:int32) (b:int32) (c:int32) (d:int32).
     (word_join a b:int64 = word_join c d) <=> a=c /\ b=d`,
  REPEAT GEN_TAC THEN EQ_TAC THENL
   [DISCH_THEN(fun th ->
      MP_TAC(AP_TERM `\w:int64. word_subword w (32,32):int32` th) THEN
      MP_TAC(AP_TERM `\w:int64. word_subword w (0,32):int32` th)) THEN
    SIMP_TAC[WORD_SUBWORD_JOIN_LOWER;WORD_SUBWORD_JOIN_UPPER;
      DIMINDEX_32;DIMINDEX_64;ARITH;WORD_SUBWORD_TRIVIAL;SUB_REFL] THEN
    MESON_TAC[];
    STRIP_TAC THEN ASM_REWRITE_TAC[]]);;

let VE_BYTES64_EQ = prove
 (`!a b (s:armstate) t.
     read (memory :> bytes64 a) s = read (memory :> bytes64 b) t <=>
     (!i. i < 8 ==>
       read (memory :> bytes8 (word_add a (word i))) s =
       read (memory :> bytes8 (word_add b (word i))) t)`,
  REPEAT GEN_TAC THEN REWRITE_TAC[READ_MEMORY_BYTESIZED_SPLIT] THEN
  CONV_TAC(RAND_CONV EXPAND_CASES_CONV) THEN
  REWRITE_TAC[WORD_RULE `word_add (word_add a (word i)) (word j) =
                         word_add a (word(i+j))`; WORD_ADD_0] THEN
  CONV_TAC NUM_REDUCE_CONV THEN
  REWRITE_TAC[VE_JOIN_EQ_16;VE_JOIN_EQ_32;VE_JOIN_EQ_64] THEN CONV_TAC TAUT);;


(* Explicit guard and zero-data-access facts, separate from input testing. *)
let VE_MASK_OR_ZERO = WORD_BITWISE_RULE
 `word_and (word_or (a:int64) b) (word 7) = word 0 <=>
  word_and a (word 7) = word 0 /\ word_and b (word 7) = word 0`;;
let VE_ALIGNED_MASK = prove
 (`!a:int64. aligned 8 a <=> word_and a (word 7) = word 0`,
  GEN_TAC THEN REWRITE_TAC[aligned;DIVIDES_MOD;DIMINDEX_64;GSYM VAL_EQ;
    VAL_WORD_0;ARITH_RULE `7 = 2 EXP 3 - 1`;VAL_WORD_AND_MASK_WORD] THEN
  CONV_TAC NUM_REDUCE_CONV);;
let ve_fast_guard_spec =
 `!(a:int64) b. word_and (word_or a b) (word 7) = word 0 <=>
               aligned 8 a /\ aligned 8 b`;;
let VE_FAST_GUARD = prove(ve_fast_guard_spec,
  REWRITE_TAC[VE_ALIGNED_MASK;VE_MASK_OR_ZERO]);;

