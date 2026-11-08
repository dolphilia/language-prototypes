(* Explicit containment avoids depending on address-canonicalization heuristics
   for a variable word offset. Every lemma is proved in the existing kernel. *)
let VE_SPLIT_REGION_CONTAINED = prove
 (`!(arena:int64) capacity split n.
   val arena + capacity <= 2 EXP 64 /\ split < capacity /\ n <= capacity-split
   ==> contained (word_add arena (word split),n) (arena,capacity)`,
 REPEAT GEN_TAC THEN STRIP_TAC THEN
 SUBGOAL_THEN `val(arena:int64)+split < 2 EXP 64 /\ split < 2 EXP 64 /\
               split+n <= capacity` STRIP_ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
 SUBGOAL_THEN `val(word_add (arena:int64) (word split)) = val arena+split` ASSUME_TAC THENL
  [ASM_SIMP_TAC[VAL_WORD_ADD;VAL_WORD;DIMINDEX_64;MOD_LT];ALL_TAC] THEN
 ASM_REWRITE_TAC[contained;DIMINDEX_64] THEN
 MATCH_MP_TAC CONTAINED_MODULO_SIMPLE THEN ASM_ARITH_TAC);;

let VE_SPLIT_STACK_SEPARATION = prove
 (`!(stack:int64) arena capacity split n.
   nonoverlapping (stack,16) (arena,capacity) /\
   val arena+capacity <= 2 EXP 64 /\ split < capacity /\ n <= capacity-split
   ==> nonoverlapping (stack,16) (word_add arena (word split),n)`,
 REPEAT GEN_TAC THEN STRIP_TAC THEN
 MATCH_MP_TAC(ISPECL [`stack:int64`;`16`;`arena:int64`;`capacity:num`;
                    `stack:int64`;`16`;`word_add (arena:int64) (word split)`;`n:num`]
                   NONOVERLAPPING_SUBREGIONS) THEN
 ASM_REWRITE_TAC[] THEN CONJ_TAC THENL
 [REWRITE_TAC[contained;CONTAINED_MODULO_REFL;LE_REFL];
  MATCH_MP_TAC VE_SPLIT_REGION_CONTAINED THEN ASM_REWRITE_TAC[]]);;
