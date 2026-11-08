needs "arm/proofs/base.ml";;

let vp_memcpy_mc = define_assert_from_elf "vp_memcpy_mc"
  (Sys.getenv "VP_ROOT" ^ "/build/vp_memcpy.o")
  [0xf100205f;0x540000e1;0xaa010003;0xf240087f;
   0x54000081;0xf9400024;0xf9000004;0xd65f03c0;
   0xd2800003;0xb40000c2;0x38636824;0x38236804;
   0x91000463;0xeb02007f;0x54ffff83;0xd65f03c0];;
let VP_MEMCPY_EXEC = ARM_MK_EXEC_RULE vp_memcpy_mc;;

let VP_JOIN_EQ_16 = prove
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

let VP_JOIN_EQ_32 = prove
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

let VP_JOIN_EQ_64 = prove
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

let VP_BYTES64_EQ = prove
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
  REWRITE_TAC[VP_JOIN_EQ_16;VP_JOIN_EQ_32;VP_JOIN_EQ_64] THEN CONV_TAC TAUT);;

let VP_MEMCPY_SCALAR_8_CORRECT =
  GENL [`dst:int64`;`src:int64`;`pc:num`;`returnaddress:int64`;`input:num->byte`]
  (CONV_RULE(DEPTH_CONV WORD_NUM_RED_CONV)
    (SPECL [`dst:int64`;`src:int64`;`word 8:int64`;`pc:num`;
            `returnaddress:int64`;`input:num->byte`] VP_MEMCPY_SCALAR_CORRECT));;

let vp_memcpy_slow_tac step eight =
  let theorem,args = if eight then
    VP_MEMCPY_SCALAR_8_CORRECT,
    [`dst:int64`;`src:int64`;`pc+32`;`returnaddress:int64`;`input:num->byte`]
  else VP_MEMCPY_SCALAR_CORRECT,
    [`dst:int64`;`src:int64`;`read X2 s`;`pc+32`;`returnaddress:int64`;
     `input:num->byte`] in
  ARM_SUBROUTINE_SIM_TAC
    (vp_memcpy_mc,VP_MEMCPY_EXEC,32,vp_memcpy_scalar_mc,theorem) args step THEN
  ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[];;

let vp_memcpy_correct_tac =
  REWRITE_TAC[C_ARGUMENTS; SOME_FLAGS; fst VP_MEMCPY_EXEC] THEN
  REPEAT STRIP_TAC THEN ASM_CASES_TAC `n:int64 = word 8` THENL
   [ALL_TAC;
    SUBGOAL_THEN `~(val(word_sub (n:int64) (word 8)) = 0)` ASSUME_TAC THENL
     [ASM_REWRITE_TAC[VAL_EQ_0;WORD_SUB_EQ_0]; ALL_TAC] THEN
    ENSURES_INIT_TAC "s0" THEN ARM_STEPS_TAC VP_MEMCPY_EXEC (1--2) THEN
    vp_memcpy_slow_tac 3 false] THEN
  UNDISCH_TAC `n:int64 = word 8` THEN DISCH_THEN SUBST_ALL_TAC THEN
  RULE_ASSUM_TAC(CONV_RULE(DEPTH_CONV WORD_NUM_RED_CONV)) THEN
  REWRITE_TAC[VAL_WORD;DIMINDEX_64] THEN CONV_TAC NUM_REDUCE_CONV THEN
  ASM_CASES_TAC `word_and (word_or dst src) (word 7):int64 = word 0` THENL
   [ENSURES_INIT_TAC "s0" THEN
    ABBREV_TAC `b:int64 = read (memory :> bytes64 src) s0` THEN
    ARM_STEPS_TAC VP_MEMCPY_EXEC (1--8) THEN
    ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[] THEN
    MP_TAC(SPECL [`dst:int64`;`src:int64`;`s8:armstate`;`s8:armstate`]
      VP_BYTES64_EQ) THEN ASM_REWRITE_TAC[] THEN ASM_MESON_TAC[];
    SUBGOAL_THEN `~(val(word_and (word_or dst src) (word 7):int64) = 0)`
      ASSUME_TAC THENL [ASM_REWRITE_TAC[VAL_EQ_0]; ALL_TAC] THEN
    ENSURES_INIT_TAC "s0" THEN ARM_STEPS_TAC VP_MEMCPY_EXEC (1--5) THEN
    vp_memcpy_slow_tac 6 true];;

let VP_MEMCPY_CORRECT = prove(vp_copy_contract `vp_memcpy_mc`,vp_memcpy_correct_tac);;

let vp_memcpy_access_strong =
  vp_with_frame (vp_copy_access_contract `vp_memcpy_mc`) vp_memcpy_access_frame;;

let VP_MEMCPY_SCALAR_8_ACCESSES_STRONG =
  GENL [`dst:int64`;`src:int64`;`pc:num`;`returnaddress:int64`;`e:uarch_event list`]
  (CONV_RULE(DEPTH_CONV WORD_NUM_RED_CONV)
    (SPECL [`dst:int64`;`src:int64`;`word 8:int64`;`pc:num`;
            `returnaddress:int64`;`e:uarch_event list`]
       VP_MEMCPY_SCALAR_ACCESSES_STRONG));;

let vp_memcpy_slow_access_tac step eight prefix =
  let theorem,args = if eight then VP_MEMCPY_SCALAR_8_ACCESSES_STRONG,
    [`dst:int64`;`src:int64`;`pc+32`;`returnaddress:int64`;`read events s`]
  else VP_MEMCPY_SCALAR_ACCESSES_STRONG,
    [`dst:int64`;`src:int64`;`read X2 s`;`pc+32`;`returnaddress:int64`;
     `read events s`] in
  ARM_SUBROUTINE_SIM_TAC
    (vp_memcpy_mc,VP_MEMCPY_EXEC,32,vp_memcpy_scalar_mc,theorem) args step THEN
  TRY vp_open_trace_tac THEN
  ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[] THEN
  EXISTS_TAC (mk_comb(mk_comb(`APPEND:uarch_event list->uarch_event list->uarch_event list`,
                              `trace:uarch_event list`),prefix)) THEN
  ONCE_REWRITE_TAC[MEMACCESS_INBOUNDS_APPEND] THEN
  ASM_REWRITE_TAC[APPEND;GSYM APPEND_ASSOC;memaccess_inbounds;ALL];;

let vp_memcpy_access_tac =
  REWRITE_TAC[C_ARGUMENTS;SOME_FLAGS;fst VP_MEMCPY_EXEC] THEN
  REPEAT STRIP_TAC THEN ASM_CASES_TAC `n:int64 = word 8` THENL
   [ALL_TAC;
    SUBGOAL_THEN `~(val(word_sub (n:int64) (word 8)) = 0)` ASSUME_TAC THENL
     [ASM_REWRITE_TAC[VAL_EQ_0;WORD_SUB_EQ_0];ALL_TAC] THEN
    ENSURES_INIT_TAC "s0" THEN ARM_STEPS_TAC VP_MEMCPY_EXEC (1--2) THEN
    vp_memcpy_slow_access_tac 3 false `[EventJump(word(pc+4),word(pc+32))]`] THEN
  UNDISCH_TAC `n:int64 = word 8` THEN DISCH_THEN SUBST_ALL_TAC THEN
  RULE_ASSUM_TAC(CONV_RULE(DEPTH_CONV WORD_NUM_RED_CONV)) THEN
  REWRITE_TAC[VAL_WORD;DIMINDEX_64] THEN CONV_TAC NUM_REDUCE_CONV THEN
  ASM_CASES_TAC `word_and (word_or dst src) (word 7):int64 = word 0` THENL
   [ENSURES_INIT_TAC "s0" THEN ARM_STEPS_TAC VP_MEMCPY_EXEC (1--8) THEN
    ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[] THEN
    EXISTS_TAC `[EventJump(word(pc+28),returnaddress);EventStore(dst,8);
      EventLoad(src,8);EventJump(word(pc+16),word(pc+20));
      EventJump(word(pc+4),word(pc+8))]` THEN
    REWRITE_TAC[APPEND;memaccess_inbounds;ALL;EX;CONTAINED_MODULO_REFL] THEN
    CONV_TAC NUM_REDUCE_CONV;
    SUBGOAL_THEN `~(val(word_and (word_or dst src) (word 7):int64) = 0)`
      ASSUME_TAC THENL [ASM_REWRITE_TAC[VAL_EQ_0];ALL_TAC] THEN
    ENSURES_INIT_TAC "s0" THEN ARM_STEPS_TAC VP_MEMCPY_EXEC (1--5) THEN
    vp_memcpy_slow_access_tac 6 true
      `[EventJump(word(pc+16),word(pc+32));EventJump(word(pc+4),word(pc+8))]`];;

let VP_MEMCPY_ACCESSES_STRONG = prove(vp_memcpy_access_strong,vp_memcpy_access_tac);;
let VP_MEMCPY_ACCESSES = prove(vp_copy_access_contract `vp_memcpy_mc`,
  REPEAT STRIP_TAC THEN MATCH_MP_TAC ENSURES_FRAME_SUBSUMED THEN
  EXISTS_TAC vp_memcpy_access_frame THEN CONJ_TAC THENL
   [REWRITE_TAC[subsumed];
    MATCH_MP_TAC VP_MEMCPY_ACCESSES_STRONG THEN ASM_REWRITE_TAC[]]);;
