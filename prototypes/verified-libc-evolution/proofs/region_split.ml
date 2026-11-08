(* Splitting consumes the whole-owner permission while the two loans exist. *)
let VE_SPLIT_DISJ_IMP = TAUT `(p \/ q ==> r) <=> (p ==> r) /\ (q ==> r)`;;
let ve_split_borrows_spec =
 `!owner epoch capacity split length.
    ve_split_guard capacity split length
    ==> ve_borrow (VEContext owner epoch 0 capacity T []) 0 length F
          (VELease 0 owner epoch 0 length F)
          (VEContext owner epoch 1 capacity T [VELease 0 owner epoch 0 length F]) /\
        ve_borrow (VEContext owner epoch 1 capacity T [VELease 0 owner epoch 0 length F])
          split length T (VELease 1 owner epoch split length T)
          (VEContext owner epoch 2 capacity T
             [VELease 1 owner epoch split length T;VELease 0 owner epoch 0 length F])`;;
let VE_SPLIT_BORROWS = prove(ve_split_borrows_spec,
  REPEAT GEN_TAC THEN DISCH_TAC THEN
  MP_TAC(SPECL [`capacity:num`;`split:num`;`length:num`] VE_SPLIT_BOUNDS) THEN
  ASM_REWRITE_TAC[] THEN STRIP_TAC THEN
  UNDISCH_TAC `ve_split_guard capacity split length` THEN
  REWRITE_TAC[ve_split_guard] THEN STRIP_TAC THEN
  ASM_SIMP_TAC([ve_borrow;ve_valid;ve_fits;ve_compatible;ve_separate;MEM;PAIRWISE;ALL;
                FORALL_UNWIND_THM2;VE_SPLIT_DISJ_IMP;FORALL_AND_THM] @ ve_region_fields) THEN
  CONV_TAC NUM_REDUCE_CONV THEN ASM_REWRITE_TAC[] THEN ASM_ARITH_TAC);;
ve_check "regions:split-borrows" ve_split_borrows_spec VE_SPLIT_BORROWS;;

let ve_split_permissions_spec =
 `!owner epoch capacity split length.
    ve_split_guard capacity split length
    ==> let context = VEContext owner epoch 2 capacity T
           [VELease 1 owner epoch split length T;VELease 0 owner epoch 0 length F] in
        ve_valid context /\
        ve_authorized context (VELease 0 owner epoch 0 length F) /\
        ve_write_authorized context (VELease 1 owner epoch split length T) /\
        ~ve_owner_ready context`;;
let VE_SPLIT_PERMISSIONS = prove(ve_split_permissions_spec,
  REPEAT GEN_TAC THEN DISCH_TAC THEN
  MP_TAC(SPECL [`capacity:num`;`split:num`;`length:num`] VE_SPLIT_BOUNDS) THEN
  ASM_REWRITE_TAC[LET_DEF;LET_END_DEF] THEN STRIP_TAC THEN
  UNDISCH_TAC `ve_split_guard capacity split length` THEN
  REWRITE_TAC[ve_split_guard] THEN STRIP_TAC THEN
  ASM_SIMP_TAC([ve_valid;ve_authorized;ve_write_authorized;ve_owner_ready;ve_fits;
    ve_compatible;ve_separate;MEM;PAIRWISE;ALL;FORALL_UNWIND_THM2;VE_SPLIT_DISJ_IMP;FORALL_AND_THM;NOT_CONS_NIL]
    @ ve_region_fields) THEN CONV_TAC NUM_REDUCE_CONV THEN ASM_REWRITE_TAC[] THEN ASM_ARITH_TAC);;
ve_check "regions:split-permissions" ve_split_permissions_spec VE_SPLIT_PERMISSIONS;;

let ve_split_return_spec =
 `!owner epoch capacity split length.
    ve_split_guard capacity split length
    ==> ve_end_borrow (VEContext owner epoch 2 capacity T
           [VELease 1 owner epoch split length T;VELease 0 owner epoch 0 length F])
          (VELease 1 owner epoch split length T)
          (VEContext owner epoch 2 capacity T [VELease 0 owner epoch 0 length F]) /\
        ve_end_borrow (VEContext owner epoch 2 capacity T [VELease 0 owner epoch 0 length F])
          (VELease 0 owner epoch 0 length F) (VEContext owner epoch 2 capacity T []) /\
        ve_owner_ready (VEContext owner epoch 2 capacity T [])`;;
let VE_SPLIT_RETURN = prove(ve_split_return_spec,
  REPEAT GEN_TAC THEN DISCH_TAC THEN
  MP_TAC(SPECL [`capacity:num`;`split:num`;`length:num`] VE_SPLIT_BOUNDS) THEN
  ASM_REWRITE_TAC[] THEN STRIP_TAC THEN
  UNDISCH_TAC `ve_split_guard capacity split length` THEN
  REWRITE_TAC[ve_split_guard] THEN STRIP_TAC THEN
  ASM_SIMP_TAC([ve_end_borrow;ve_owner_ready;ve_valid;ve_fits;ve_compatible;ve_separate;
     FILTER;MEM;PAIRWISE;ALL;FORALL_UNWIND_THM2;VE_SPLIT_DISJ_IMP;FORALL_AND_THM] @ ve_region_fields) THEN
  CONV_TAC NUM_REDUCE_CONV THEN ASM_REWRITE_TAC[] THEN ASM_ARITH_TAC);;
ve_check "regions:split-returned" ve_split_return_spec VE_SPLIT_RETURN;;

(* The abstract checked operation uses a snapshot; the actual BL/check paths
   are deliberately deferred to E5/E3b. *)
let ve_split_image = new_definition
 `ve_split_image (before:num->byte) split length =
    \i. if split <= i /\ i < split+length then before(i-split) else before i`;;
let ve_checked_split = new_definition
 `ve_checked_split (before:num->byte) capacity split length status after <=>
    if ve_split_guard capacity split length
    then status = 0 /\ after = ve_split_image before split length
    else status = 1 /\ after = before`;;
let ve_split_success_spec =
 `!before capacity split length status after.
    ve_split_guard capacity split length /\
    ve_checked_split before capacity split length status after
    ==> status = 0 /\
        (!i. i < length ==> after(split+i) = before i) /\
        (!i. ~(split <= i /\ i < split+length) ==> after i = before i) /\
        (!i. i < length ==> after i = before i)`;;
let VE_SPLIT_SUCCESS = prove(ve_split_success_spec,
  REPEAT GEN_TAC THEN DISCH_THEN(CONJUNCTS_THEN2 ASSUME_TAC MP_TAC) THEN
  ASM_REWRITE_TAC[ve_checked_split] THEN
  DISCH_THEN(CONJUNCTS_THEN2 ASSUME_TAC SUBST_ALL_TAC) THEN
  UNDISCH_TAC `ve_split_guard capacity split length` THEN
  REWRITE_TAC[ve_split_guard] THEN STRIP_TAC THEN
  ASM_REWRITE_TAC[] THEN REPEAT CONJ_TAC THEN REPEAT STRIP_TAC THEN
  REWRITE_TAC[ve_split_image] THEN
  ASM_SIMP_TAC[ARITH_RULE `i < n ==> k <= k+i /\ k+i < k+n`;ADD_SUB2] THEN
  ASM_CASES_TAC `split <= i /\ i < split+length` THEN
  ASM_REWRITE_TAC[] THEN ASM_ARITH_TAC);;
ve_check "regions:checked-success" ve_split_success_spec VE_SPLIT_SUCCESS;;

let ve_split_failure_spec =
 `!before capacity split length status after.
    ~ve_split_guard capacity split length /\
    ve_checked_split before capacity split length status after
    ==> status = 1 /\ after = before`;;
let VE_SPLIT_FAILURE = prove(ve_split_failure_spec,
  REWRITE_TAC[ve_checked_split] THEN MESON_TAC[]);;
ve_check "regions:checked-failure" ve_split_failure_spec VE_SPLIT_FAILURE;;
