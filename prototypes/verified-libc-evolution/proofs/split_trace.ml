(* The child's precise source/destination accesses are contained in the root. *)
let ve_split_trace_root_spec =
 `!(trace:uarch_event list) (arena:int64) capacity split n stack.
    val arena + capacity <= 2 EXP 64 /\ split < capacity /\
    n <= split /\ n <= capacity-split /\
    memaccess_inbounds trace [arena,n] [word_add arena (word split),n]
    ==> memaccess_inbounds trace [arena,capacity;stack,16] [arena,capacity;stack,16]`;;
let VE_SPLIT_TRACE_ROOT = prove(ve_split_trace_root_spec,
 REPEAT GEN_TAC THEN STRIP_TAC THEN
 SUBGOAL_THEN `val(arena:int64)+split < 2 EXP 64 /\ split < 2 EXP 64 /\
                split+n <= capacity /\ n <= capacity` STRIP_ASSUME_TAC THENL
  [ASM_ARITH_TAC;ALL_TAC] THEN
 SUBGOAL_THEN `val(word_add (arena:int64) (word split)) = val arena + split` ASSUME_TAC THENL
  [ASM_SIMP_TAC[VAL_WORD_ADD;VAL_WORD;DIMINDEX_64;MOD_LT];ALL_TAC] THEN
 SUBGOAL_THEN `contained (arena:int64,n) (arena,capacity) /\
  contained (word_add arena (word split),n) (arena,capacity)` STRIP_ASSUME_TAC THENL
 [REWRITE_TAC[contained;DIMINDEX_64] THEN ASM_REWRITE_TAC[] THEN
  CONJ_TAC THEN MATCH_MP_TAC CONTAINED_MODULO_SIMPLE THEN ASM_ARITH_TAC;ALL_TAC] THEN
 MP_TAC(ISPECL [`trace:uarch_event list`;`[arena:int64,n:num]`;
   `[arena:int64,capacity:num;stack,16]`;`[word_add (arena:int64) (word split),n:num]`;
   `[arena:int64,capacity:num;stack,16]`] MEMACCESS_INBOUNDS_CONTAINED) THEN
 ASM_REWRITE_TAC[ALL;EX]);;
ve_check "split:trace-root" ve_split_trace_root_spec VE_SPLIT_TRACE_ROOT;;
