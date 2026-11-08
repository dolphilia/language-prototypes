(* Ordinary unsigned-address order, with full-range no-wrap conditions. *)
let VE_MOVE_ORDER_NONOVERLAP = prove
 (`!(a:int64) b m n.
    val a + m <= val b /\ val b + n <= 2 EXP 64
    ==> nonoverlapping (a,m) (b,n)`,
  REPEAT STRIP_TAC THEN REWRITE_TAC[nonoverlapping;DIMINDEX_64] THEN
  MATCH_MP_TAC NONOVERLAPPING_MODULO_SIMPLE THEN DISJ1_TAC THEN ASM_ARITH_TAC);;
let VE_MOVE_ADDRESS = prove
 (`!(a:int64) n i. val a+n <= 2 EXP 64 /\ i<n
    ==> val(word_add a (word i)) = val a+i`,
  REPEAT GEN_TAC THEN STRIP_TAC THEN
  SUBGOAL_THEN `i < 2 EXP 64 /\ val(a:int64)+i < 2 EXP 64` STRIP_ASSUME_TAC THENL
   [ASM_ARITH_TAC;ASM_SIMP_TAC[VAL_WORD_ADD;VAL_WORD;DIMINDEX_64;MOD_LT]]);;

let ve_move_forward_range_spec =
 `!(dst:int64) src n i.
    val dst < val src /\ val dst+n <= 2 EXP 64 /\ val src+n <= 2 EXP 64 /\ i<n
    ==> nonoverlapping (word_add src (word i),n-i) (word_add dst (word i),1)`;;
let VE_MOVE_FORWARD_RANGE = prove(ve_move_forward_range_spec,
  REPEAT GEN_TAC THEN STRIP_TAC THEN
  SUBGOAL_THEN `val(word_add (dst:int64) (word i)) = val dst+i /\
                val(word_add (src:int64) (word i)) = val src+i` STRIP_ASSUME_TAC THENL
   [CONJ_TAC THEN MATCH_MP_TAC VE_MOVE_ADDRESS THEN ASM_MESON_TAC[];ALL_TAC] THEN
  ONCE_REWRITE_TAC[NONOVERLAPPING_SYM] THEN MATCH_MP_TAC VE_MOVE_ORDER_NONOVERLAP THEN
  ASM_REWRITE_TAC[] THEN ASM_ARITH_TAC);;
ve_check "memmove:forward-unread-range" ve_move_forward_range_spec VE_MOVE_FORWARD_RANGE;;

let ve_move_backward_range_spec =
 `!(dst:int64) src n i.
    val src < val dst /\ val dst+n <= 2 EXP 64 /\ val src+n <= 2 EXP 64 /\ i<n
    ==> nonoverlapping (src,i+1) (word_add dst (word i),1)`;;
let VE_MOVE_BACKWARD_RANGE = prove(ve_move_backward_range_spec,
  REPEAT GEN_TAC THEN STRIP_TAC THEN
  SUBGOAL_THEN `val(word_add (dst:int64) (word i)) = val dst+i` ASSUME_TAC THENL
   [MATCH_MP_TAC VE_MOVE_ADDRESS THEN ASM_MESON_TAC[];ALL_TAC] THEN
  MATCH_MP_TAC VE_MOVE_ORDER_NONOVERLAP THEN ASM_REWRITE_TAC[] THEN ASM_ARITH_TAC);;
ve_check "memmove:backward-unread-range" ve_move_backward_range_spec VE_MOVE_BACKWARD_RANGE;;
