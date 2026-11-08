(* Pure geometry derived from a root and successful checked splitting. *)
let ve_split_guard = new_definition
 `ve_split_guard capacity split length <=>
    0 < split /\ split < capacity /\ length <= split /\ length <= capacity - split`;;
let ve_root_geometry = new_definition
 `ve_root_geometry (arena:int64) capacity pc code_length <=>
    ~(arena = word 0) /\ val arena + capacity <= 2 EXP 64 /\
    nonoverlapping (word pc,code_length) (arena,capacity)`;;

let ve_split_bounds_spec =
 `!capacity split length. ve_split_guard capacity split length
    ==> split <= capacity /\ length <= capacity /\ split + length <= capacity`;;
let VE_SPLIT_BOUNDS = prove(ve_split_bounds_spec,
  REWRITE_TAC[ve_split_guard] THEN ARITH_TAC);;
ve_check "regions:split-bounds" ve_split_bounds_spec VE_SPLIT_BOUNDS;;

let ve_split_derive_spec =
 `!arena capacity split length pc code_length.
    ve_root_geometry arena capacity pc code_length /\ ve_split_guard capacity split length
    ==> length < 2 EXP 64 /\
        ~(word_add arena (word split) = word 0) /\
        val(word_add arena (word split)) + length <= 2 EXP 64 /\
        val arena + length <= 2 EXP 64 /\
        nonoverlapping (word pc,code_length) (word_add arena (word split),length) /\
        nonoverlapping (arena,length) (word_add arena (word split),length)`;;
let VE_SPLIT_DERIVE = prove(ve_split_derive_spec,
  REPEAT GEN_TAC THEN REWRITE_TAC[ve_root_geometry;ve_split_guard] THEN STRIP_TAC THEN
  SUBGOAL_THEN `0 < val(arena:int64)` ASSUME_TAC THENL
   [ASM_REWRITE_TAC[LT_NZ;VAL_EQ_0];ALL_TAC] THEN
  SUBGOAL_THEN `split + length <= capacity /\ split < 2 EXP 64 /\
                length < 2 EXP 64 /\ val(arena:int64)+split < 2 EXP 64`
   STRIP_ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  SUBGOAL_THEN `val(word_add arena (word split):int64) = val arena + split` ASSUME_TAC THENL
   [ASM_SIMP_TAC[VAL_WORD_ADD;VAL_WORD;DIMINDEX_64;MOD_LT];ALL_TAC] THEN
  ASM_REWRITE_TAC[GSYM VAL_EQ;VAL_WORD_0] THEN
  REPEAT CONJ_TAC THENL
   [ASM_ARITH_TAC;ASM_ARITH_TAC;ASM_ARITH_TAC;NONOVERLAPPING_TAC;NONOVERLAPPING_TAC]);;
ve_check "regions:derive-copy-preconditions" ve_split_derive_spec VE_SPLIT_DERIVE;;
