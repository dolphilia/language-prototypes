(* Derive ordinary word geometry before entering the M1 copy theorem. *)
loadt (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/proofs/split_geometry.ml");;
let VE_SPLIT_HIGHER = prove
 (`!(x:int64) y.
    (val y <= val x /\ ~(val(word_sub x y) = 0)) <=> val y < val x`,
  REWRITE_TAC[VAL_WORD_SUB_EQ_0;GSYM VAL_EQ] THEN ARITH_TAC);;
let VE_SPLIT_CODE_SUBRANGE = prove
 (`!pc (dst:int64) n. nonoverlapping (word pc,156) (dst,n)
    ==> nonoverlapping (word(pc+80),76) (dst,n)`,
  REPEAT STRIP_TAC THEN NONOVERLAPPING_TAC);;

let ve_split_success_setup exec =
 REWRITE_TAC[ve_split_geometry;C_ARGUMENTS;SOME_FLAGS;fst exec;ADD_CLAUSES] THEN
 REPEAT GEN_TAC THEN STRIP_TAC THEN ASM_REWRITE_TAC[] THEN
 MP_TAC(SPECL [`arena:int64`;`val(capacity:int64)`;`val(split:int64)`;`val(n:int64)`;
              `pc:num`;mk_small_numeral(dest_small_numeral(rhs(concl(fst exec))))] VE_SPLIT_DERIVE) THEN
 ASM_REWRITE_TAC[] THEN STRIP_TAC THEN
 SUBGOAL_THEN `word(val(split:int64)):int64 = split` ASSUME_TAC THENL
  [REWRITE_TAC[WORD_VAL];ALL_TAC] THEN
 RULE_ASSUM_TAC(REWRITE_RULE[WORD_VAL;ve_root_geometry]) THEN
 REPEAT(FIRST_X_ASSUM(CONJUNCTS_THEN STRIP_ASSUME_TAC)) THEN
 SUBGOAL_THEN
  `nonoverlapping (word(pc+80),76) (word_add (arena:int64) split,val(n:int64))`
  ASSUME_TAC THENL
 [MATCH_MP_TAC VE_SPLIT_CODE_SUBRANGE THEN ASM_REWRITE_TAC[];ALL_TAC] THEN
 SUBGOAL_THEN `aligned 8 (word_sub (sp:int64) (word 16))` ASSUME_TAC THENL
  [ALIGNED_WORD_TAC THEN RULE_ASSUM_TAC(REWRITE_RULE[aligned]) THEN
   REWRITE_TAC[aligned] THEN ASM_MESON_TAC[DIVIDES_TRANS;NUMBER_RULE `8 divides 16`];ALL_TAC] THEN
 SUBGOAL_THEN `0 < val(split:int64) /\ val(split:int64) < val(capacity:int64) /\
                val(n:int64) <= val(split:int64) /\ val(n:int64) <= val(capacity:int64)-val(split:int64)`
   STRIP_ASSUME_TAC THENL [ASM_MESON_TAC[ve_split_guard];ALL_TAC] THEN
 SUBGOAL_THEN `val(split:int64) <= val(capacity:int64)` ASSUME_TAC THENL
  [ASM_ARITH_TAC;ALL_TAC] THEN
 SUBGOAL_THEN `val(n:int64) < val(capacity:int64)` ASSUME_TAC THENL
  [ASM_ARITH_TAC;ALL_TAC] THEN
 MP_TAC(SPECL [`word_sub (sp:int64) (word 16)`;`arena:int64`;
               `val(capacity:int64)`;`val(split:int64)`;`val(n:int64)`]
              VE_SPLIT_STACK_SEPARATION) THEN
 ASM_REWRITE_TAC[WORD_VAL] THEN DISCH_TAC THEN
 SUBGOAL_THEN `~(split:int64 = word 0) /\ ~(val(split:int64) = 0) /\
   ~(val(capacity:int64) <= val(split:int64)) /\
   ~(val(split:int64) < val(n:int64)) /\
   val(word_sub (capacity:int64) split) = val capacity - val split` STRIP_ASSUME_TAC THENL
  [ASM_SIMP_TAC[GSYM VAL_EQ;VAL_WORD_0;VAL_WORD_SUB_CASES] THEN ASM_ARITH_TAC;ALL_TAC] THEN
 SUBGOAL_THEN
  `~(val(split:int64) <= val(n:int64) /\ ~(val(word_sub n split) = 0)) /\
   ~(val(word_sub (capacity:int64) split) <= val n /\
      ~(val(word_sub n (word_sub capacity split)) = 0))` STRIP_ASSUME_TAC THENL
  [ASM_REWRITE_TAC[VE_SPLIT_HIGHER] THEN ASM_ARITH_TAC;ALL_TAC] THEN
 SUBGOAL_THEN
  `~(val(capacity:int64)-val(split:int64) <= val(n:int64) /\
      ~(val(word_sub n (word_sub capacity split)) = 0))` ASSUME_TAC THENL
  [MP_TAC(SPECL [`n:int64`;`word_sub (capacity:int64) split`] VE_SPLIT_HIGHER) THEN
   ASM_REWRITE_TAC[] THEN ASM_ARITH_TAC;ALL_TAC] ;;

let ve_split_success_tac mc exec caller callee =
 ve_split_success_setup exec THEN
 ABBREV_TAC `dst:int64 = word_add arena split` THEN
 ENSURES_INIT_TAC "s0" THEN ARM_STEPS_TAC exec (1--14) THEN
 SUBGOAL_THEN `!i. i < val(n:int64) ==>
   read (memory :> bytes8 (word_add (arena:int64) (word i))) s14 = initial i`
   ASSUME_TAC THENL
  [X_GEN_TAC `i:num` THEN DISCH_TAC THEN
   SUBGOAL_THEN `i < val(capacity:int64)` ASSUME_TAC THENL
    [MATCH_MP_TAC LT_TRANS THEN EXISTS_TAC `val(n:int64)` THEN ASM_REWRITE_TAC[];
     ASM_SIMP_TAC[]];ALL_TAC] THEN
 ARM_SUBROUTINE_SIM_TAC (mc,exec,callee,vp2_memcpy_chunk8_mc,VP2_MEMCPY_CHUNK8_CORRECT)
  [`word_add (arena:int64) split`;`arena:int64`;`n:int64`;
   mk_binary "+" (`pc:num`,mk_small_numeral callee);
   vsubst [mk_small_numeral (caller+56),`offset:num`] `word(pc+offset):int64`;
   `initial:num->byte`] 15 THEN
 TRY(ASM_REWRITE_TAC[ADD_CLAUSES] THEN NO_TAC) THEN
 ARM_STEPS_TAC exec (16--19) THEN ENSURES_FINAL_STATE_TAC THEN
 ASM_REWRITE_TAC[WORD_RULE `word_add (word_sub s (word 16)) (word 16):int64 = s`];;
