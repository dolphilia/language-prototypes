(* Closed rejection theorems, rather than unprovable permissions as evidence. *)
let ve_overlap_write_spec =
 `!owner epoch token next.
    ~ve_borrow (VEContext owner epoch 1 32 T [VELease 0 owner epoch 8 8 T])
          12 8 T token next`;;
let VE_OVERLAP_WRITE_REJECTED = prove(ve_overlap_write_spec,
  REPEAT GEN_TAC THEN REWRITE_TAC[ve_borrow] THEN STRIP_TAC THEN
  SUBGOAL_THEN `ve_compatible token (VELease 0 owner epoch 8 8 T)` MP_TAC THENL
   [ASM_MESON_TAC[MEM];
    ASM_REWRITE_TAC([ve_compatible;ve_separate] @ ve_region_fields) THEN
    CONV_TAC NUM_REDUCE_CONV]);;
ve_check "regions:overlap-write-rejected" ve_overlap_write_spec VE_OVERLAP_WRITE_REJECTED;;

let ve_shared_overlap_spec =
 `!owner epoch.
    ve_borrow (VEContext owner epoch 1 32 T [VELease 0 owner epoch 8 8 F])
       12 8 F (VELease 1 owner epoch 12 8 F)
       (VEContext owner epoch 2 32 T [VELease 1 owner epoch 12 8 F;VELease 0 owner epoch 8 8 F])`;;
let VE_SHARED_OVERLAP = prove(ve_shared_overlap_spec,
  SIMP_TAC([ve_borrow;ve_valid;ve_fits;ve_compatible;ve_separate;PAIRWISE;ALL;MEM;
             FORALL_UNWIND_THM2] @ ve_region_fields) THEN ARITH_TAC);;
ve_check "regions:shared-overlap-allowed" ve_shared_overlap_spec VE_SHARED_OVERLAP;;

let ve_capacity_reject_spec =
 `(!owner epoch token next.
     ~ve_borrow (VEContext owner epoch 0 16 T []) 8 9 T token next) /\
  ~ve_split_guard 16 17 0 /\ ~ve_split_guard 16 8 9 /\
  ~ve_split_guard 16 0 0 /\ ~ve_split_guard 16 16 0`;;
let VE_CAPACITY_REJECT = prove(ve_capacity_reject_spec,
  REWRITE_TAC[ve_borrow;ve_split_guard] THEN ARITH_TAC);;
ve_check "regions:capacity-rejected" ve_capacity_reject_spec VE_CAPACITY_REJECT;;

let ve_subtraction_guard_spec =
 `16 - 17 = 0 /\ 0 <= 16 - 17 /\ ~ve_split_guard 16 17 0 /\
  ~(val(word_add (word 18446744073709551608) (word 16):int64) =
       val(word 18446744073709551608:int64) + 16)`;;
let VE_SUBTRACTION_GUARD = prove(ve_subtraction_guard_spec,
  REWRITE_TAC[ve_split_guard] THEN CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN
  CONV_TAC NUM_REDUCE_CONV);;
ve_check "regions:unguarded-subtraction-and-address-rejected" ve_subtraction_guard_spec VE_SUBTRACTION_GUARD;;
