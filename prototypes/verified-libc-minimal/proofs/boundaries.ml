(* Explicit guard and zero-data-access facts, separate from input testing. *)
let VP_MASK_OR_ZERO = WORD_BITWISE_RULE
 `word_and (word_or (a:int64) b) (word 7) = word 0 <=>
  word_and a (word 7) = word 0 /\ word_and b (word 7) = word 0`;;
let VP_ALIGNED_MASK = prove
 (`!a:int64. aligned 8 a <=> word_and a (word 7) = word 0`,
  GEN_TAC THEN REWRITE_TAC[aligned;DIVIDES_MOD;DIMINDEX_64;GSYM VAL_EQ;
    VAL_WORD_0;ARITH_RULE `7 = 2 EXP 3 - 1`;VAL_WORD_AND_MASK_WORD] THEN
  CONV_TAC NUM_REDUCE_CONV);;
let vp_fast_guard_spec =
 `!(a:int64) b. word_and (word_or a b) (word 7) = word 0 <=>
               aligned 8 a /\ aligned 8 b`;;
let VP_FAST_GUARD = prove(vp_fast_guard_spec,
  REWRITE_TAC[VP_ALIGNED_MASK;VP_MASK_OR_ZERO]);;

let vp_memcpy_zero_spec =
 `!dst src pc returnaddress e.
    ensures arm
      (\s. aligned_bytes_loaded s (word pc) vp_memcpy_mc /\
           read PC s = word pc /\ read X30 s = returnaddress /\
           C_ARGUMENTS [dst;src;word 0] s /\ read events s = e)
      (\s. read PC s = returnaddress /\ read X0 s = dst /\
           read events s = APPEND
             [EventJump(word(pc+60),returnaddress);
              EventJump(word(pc+36),word(pc+60));
              EventJump(word(pc+4),word(pc+32))] e)
      (MAYCHANGE [PC;X3] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events])`;;
let VP_MEMCPY_ZERO = prove(vp_memcpy_zero_spec,
  REWRITE_TAC[C_ARGUMENTS;SOME_FLAGS] THEN REPEAT GEN_TAC THEN
  ARM_SIM_TAC VP_MEMCPY_EXEC (1--5) THEN REWRITE_TAC[APPEND]);;
let vp_memset_zero_spec =
 `!dst c pc returnaddress e.
    ensures arm
      (\s. aligned_bytes_loaded s (word pc) vp_memset_mc /\
           read PC s = word pc /\ read X30 s = returnaddress /\
           C_ARGUMENTS [dst;c;word 0] s /\ read events s = e)
      (\s. read PC s = returnaddress /\ read X0 s = dst /\
           read events s = APPEND
             [EventJump(word(pc+24),returnaddress);
              EventJump(word(pc+4),word(pc+24))] e)
      (MAYCHANGE [PC;X3] ,, MAYCHANGE [events])`;;
let VP_MEMSET_ZERO = prove(vp_memset_zero_spec,
  REWRITE_TAC[C_ARGUMENTS] THEN REPEAT GEN_TAC THEN
  ARM_SIM_TAC VP_MEMSET_EXEC (1--3) THEN REWRITE_TAC[APPEND]);;
let vp_memcpy_scalar_zero_spec =
 `!dst src pc returnaddress e.
    ensures arm
      (\s. aligned_bytes_loaded s (word pc) vp_memcpy_scalar_mc /\
           read PC s = word pc /\ read X30 s = returnaddress /\
           C_ARGUMENTS [dst;src;word 0] s /\ read events s = e)
      (\s. read PC s = returnaddress /\ read X0 s = dst /\
           read events s = APPEND
             [EventJump(word(pc+28),returnaddress);
              EventJump(word(pc+4),word(pc+28))] e)
      (MAYCHANGE [PC;X3] ,, MAYCHANGE [events])`;;
let VP_MEMCPY_SCALAR_ZERO = prove(vp_memcpy_scalar_zero_spec,
  REWRITE_TAC[C_ARGUMENTS] THEN REPEAT GEN_TAC THEN
  ARM_SIM_TAC VP_MEMCPY_SCALAR_EXEC (1--3) THEN REWRITE_TAC[APPEND]);;
