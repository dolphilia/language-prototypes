(* A state-indexed ghost ledger. The physical RAM/unique root authority is an
   external contract; transitions, rather than record fields alone, grant
   usable permissions. No new axioms, parser, or concurrent borrow checker. *)
needs "arm/proofs/base.ml";;

let ve_lease_INDUCT,ve_lease_RECURSION = define_type
 "ve_lease = VELease num num num num num bool";;
let ve_lid = new_recursive_definition ve_lease_RECURSION
 `ve_lid (VELease id owner epoch offset length writable) = id`;;
let ve_lowner = new_recursive_definition ve_lease_RECURSION
 `ve_lowner (VELease id owner epoch offset length writable) = owner`;;
let ve_lepoch = new_recursive_definition ve_lease_RECURSION
 `ve_lepoch (VELease id owner epoch offset length writable) = epoch`;;
let ve_loffset = new_recursive_definition ve_lease_RECURSION
 `ve_loffset (VELease id owner epoch offset length writable) = offset`;;
let ve_llength = new_recursive_definition ve_lease_RECURSION
 `ve_llength (VELease id owner epoch offset length writable) = length`;;
let ve_lwrite = new_recursive_definition ve_lease_RECURSION
 `ve_lwrite (VELease id owner epoch offset length writable) = writable`;;

let ve_context_INDUCT,ve_context_RECURSION = define_type
 "ve_context = VEContext num num num num bool (ve_lease list)";;

let ve_separate = new_definition
 `ve_separate a b <=> ve_llength a = 0 \/ ve_llength b = 0 \/
    ve_loffset a + ve_llength a <= ve_loffset b \/
    ve_loffset b + ve_llength b <= ve_loffset a`;;
let ve_compatible = new_definition
 `ve_compatible a b <=> (~ve_lwrite a /\ ~ve_lwrite b) \/ ve_separate a b`;;
let ve_fits = new_definition
 `ve_fits owner epoch serial capacity token <=>
    ve_lowner token = owner /\ ve_lepoch token = epoch /\
    ve_lid token < serial /\ ve_loffset token + ve_llength token <= capacity`;;
let ve_valid = new_recursive_definition ve_context_RECURSION
 `ve_valid (VEContext owner epoch serial capacity alive loans) <=>
    (!token. MEM token loans ==> ve_fits owner epoch serial capacity token) /\
    PAIRWISE (\a b. ~(ve_lid a = ve_lid b) /\ ve_compatible a b) loans /\
    (~alive ==> loans = [])`;;
let ve_owner_ready = new_recursive_definition ve_context_RECURSION
 `ve_owner_ready (VEContext owner epoch serial capacity alive loans) <=>
    ve_valid (VEContext owner epoch serial capacity alive loans) /\ alive /\ loans = []`;;
let ve_authorized = new_recursive_definition ve_context_RECURSION
 `ve_authorized (VEContext owner epoch serial capacity alive loans) token <=>
    ve_valid (VEContext owner epoch serial capacity alive loans) /\ alive /\
    MEM token loans /\ ve_lowner token = owner /\ ve_lepoch token = epoch`;;
let ve_write_authorized = new_definition
 `ve_write_authorized context token <=> ve_authorized context token /\ ve_lwrite token`;;

let ve_borrow = new_recursive_definition ve_context_RECURSION
 `ve_borrow (VEContext owner epoch serial capacity alive loans)
             offset length writable token next <=>
    ve_valid (VEContext owner epoch serial capacity alive loans) /\ alive /\
    offset + length <= capacity /\
    (!old. MEM old loans ==> ve_compatible token old) /\
    token = VELease serial owner epoch offset length writable /\
    next = VEContext owner epoch (SUC serial) capacity T (CONS token loans)`;;
let ve_end_borrow = new_recursive_definition ve_context_RECURSION
 `ve_end_borrow (VEContext owner epoch serial capacity alive loans) token next <=>
    ve_valid (VEContext owner epoch serial capacity alive loans) /\ alive /\
    MEM token loans /\
    next = VEContext owner epoch serial capacity T
       (FILTER (\old. ~(ve_lid old = ve_lid token)) loans)`;;
let ve_invalidate = new_recursive_definition ve_context_RECURSION
 `ve_invalidate (VEContext owner epoch serial capacity alive loans) next <=>
    ve_owner_ready (VEContext owner epoch serial capacity alive loans) /\
    next = VEContext owner (SUC epoch) serial capacity F []`;;

let ve_region_fields = [ve_lid;ve_lowner;ve_lepoch;ve_loffset;ve_llength;ve_lwrite];;

let VE_COMPATIBLE_SYM = prove
 (`!a b. ve_compatible a b <=> ve_compatible b a`,
  REWRITE_TAC[ve_compatible;ve_separate] THEN MESON_TAC[]);;
let VE_FITS_NEXT = prove
 (`!owner epoch serial capacity token.
    ve_fits owner epoch serial capacity token
    ==> ve_fits owner epoch (SUC serial) capacity token`,
  REWRITE_TAC[ve_fits] THEN REPEAT STRIP_TAC THEN ASM_REWRITE_TAC[] THEN ASM_ARITH_TAC);;
let ve_root_ledger_spec =
 `!owner epoch capacity. ve_valid (VEContext owner epoch 0 capacity T []) /\
    ve_owner_ready (VEContext owner epoch 0 capacity T [])`;;
let VE_ROOT_LEDGER = prove(ve_root_ledger_spec,
  REWRITE_TAC[ve_valid;ve_owner_ready;MEM;PAIRWISE]);;
ve_check "regions:root-ledger" ve_root_ledger_spec VE_ROOT_LEDGER;;

let ve_borrow_valid_spec =
 `!owner epoch serial capacity alive loans offset length writable token next.
    ve_borrow (VEContext owner epoch serial capacity alive loans)
       offset length writable token next ==> ve_valid next`;;
let VE_BORROW_VALID = prove(ve_borrow_valid_spec,
  REPEAT GEN_TAC THEN REWRITE_TAC[ve_borrow;ve_valid] THEN STRIP_TAC THEN
  ASM_REWRITE_TAC[ve_valid;PAIRWISE;GSYM ALL_MEM] THEN
  CONJ_TAC THENL
  [REWRITE_TAC[MEM] THEN X_GEN_TAC `item:ve_lease` THEN STRIP_TAC THENL
    [ASM_REWRITE_TAC(ve_fits::ve_region_fields) THEN ARITH_TAC;
     ASM_MESON_TAC[VE_FITS_NEXT]];
   X_GEN_TAC `item:ve_lease` THEN DISCH_TAC THEN
   CONJ_TAC THENL
    [SUBGOAL_THEN `ve_fits owner epoch serial capacity (item:ve_lease)` MP_TAC THENL
      [ASM_MESON_TAC[];REWRITE_TAC(ve_fits::ve_region_fields) THEN ARITH_TAC];
     ASM_MESON_TAC[]]]);;
ve_check "regions:borrow-valid" ve_borrow_valid_spec VE_BORROW_VALID;;

let VE_PAIRWISE_FILTER = prove
 (`!R:A->A->bool P l. PAIRWISE R l ==> PAIRWISE R (FILTER P l)`,
  GEN_TAC THEN GEN_TAC THEN LIST_INDUCT_TAC THEN REWRITE_TAC[FILTER;PAIRWISE] THEN
  COND_CASES_TAC THEN ASM_REWRITE_TAC[PAIRWISE;GSYM ALL_MEM;MEM_FILTER] THEN
  ASM_MESON_TAC[]);;

let ve_end_valid_spec =
 `!owner epoch serial capacity alive loans token next.
    ve_end_borrow (VEContext owner epoch serial capacity alive loans) token next
    ==> ve_valid next /\ ~ve_authorized next token`;;
let VE_END_VALID = prove(ve_end_valid_spec,
  REPEAT GEN_TAC THEN REWRITE_TAC[ve_end_borrow] THEN STRIP_TAC THEN
  ASM_REWRITE_TAC[ve_valid;ve_authorized;MEM_FILTER] THEN
  ASM_MESON_TAC[ve_valid;VE_PAIRWISE_FILTER]);;
ve_check "regions:end-valid" ve_end_valid_spec VE_END_VALID;;

let ve_invalidate_valid_spec =
 `!owner epoch serial capacity alive loans next.
    ve_invalidate (VEContext owner epoch serial capacity alive loans) next
    ==> ve_valid next /\ (!token. ~ve_authorized next token)`;;
let VE_INVALIDATE_VALID = prove(ve_invalidate_valid_spec,
  REPEAT GEN_TAC THEN REWRITE_TAC[ve_invalidate] THEN STRIP_TAC THEN
  ASM_REWRITE_TAC[ve_valid;ve_authorized;PAIRWISE;MEM]);;
ve_check "regions:invalidate-valid" ve_invalidate_valid_spec VE_INVALIDATE_VALID;;

let ve_borrow_rights_spec =
 `!owner epoch serial capacity alive loans offset length writable token next.
    ve_borrow (VEContext owner epoch serial capacity alive loans)
       offset length writable token next
    ==> ve_authorized next token /\
        (writable ==> ve_write_authorized next token) /\ ~ve_owner_ready next`;;
let VE_BORROW_RIGHTS = prove(ve_borrow_rights_spec,
  REPEAT GEN_TAC THEN DISCH_TAC THEN
  SUBGOAL_THEN `ve_valid next` ASSUME_TAC THENL
   [ASM_MESON_TAC[VE_BORROW_VALID];ALL_TAC] THEN
  UNDISCH_TAC `ve_borrow (VEContext owner epoch serial capacity alive loans)
       offset length writable token next` THEN
  REWRITE_TAC[ve_borrow] THEN STRIP_TAC THEN
  ASM_REWRITE_TAC([ve_authorized;ve_write_authorized;ve_owner_ready;MEM;NOT_CONS_NIL]
                 @ ve_region_fields) THEN ASM_MESON_TAC[]);;
ve_check "regions:borrow-rights" ve_borrow_rights_spec VE_BORROW_RIGHTS;;

let ve_single_return_spec =
 `!owner epoch serial capacity token.
    ve_valid (VEContext owner epoch serial capacity T [token])
    ==> ve_end_borrow (VEContext owner epoch serial capacity T [token]) token
          (VEContext owner epoch serial capacity T []) /\
        ve_owner_ready (VEContext owner epoch serial capacity T [])`;;
let VE_SINGLE_RETURN = prove(ve_single_return_spec,
  REPEAT STRIP_TAC THEN
  ASM_REWRITE_TAC[ve_end_borrow;ve_owner_ready;ve_valid;MEM;FILTER;PAIRWISE]);;
ve_check "regions:owner-returned" ve_single_return_spec VE_SINGLE_RETURN;;

let ve_expired_generation_spec =
 `!owner epoch serial capacity alive loans id offset length writable.
    ~ve_authorized (VEContext owner (SUC epoch) serial capacity alive loans)
          (VELease id owner epoch offset length writable)`;;
let VE_EXPIRED_GENERATION = prove(ve_expired_generation_spec,
  REWRITE_TAC[ve_authorized;ve_lepoch] THEN ARITH_TAC);;
ve_check "regions:expired-generation" ve_expired_generation_spec VE_EXPIRED_GENERATION;;

let ve_active_invalidation_spec =
 `!owner epoch serial capacity loans token next.
    MEM token loans
    ==> ~ve_invalidate (VEContext owner epoch serial capacity T loans) next`;;
let VE_ACTIVE_INVALIDATION = prove(ve_active_invalidation_spec,
  REWRITE_TAC[ve_invalidate;ve_owner_ready] THEN MESON_TAC[MEM]);;
ve_check "regions:active-invalidation-rejected" ve_active_invalidation_spec VE_ACTIVE_INVALIDATION;;

let ve_region_step = new_definition
 `ve_region_step context next <=>
    (?offset length writable token. ve_borrow context offset length writable token next) \/
    (?token. ve_end_borrow context token next) \/ ve_invalidate context next`;;
let ve_region_step_valid_spec =
 `!context next. ve_region_step context next ==> ve_valid next`;;
let VE_REGION_STEP_VALID = prove(ve_region_step_valid_spec,
  MATCH_MP_TAC ve_context_INDUCT THEN REPEAT GEN_TAC THEN
  REWRITE_TAC[ve_region_step] THEN
  MESON_TAC[VE_BORROW_VALID;VE_END_VALID;VE_INVALIDATE_VALID]);;
ve_check "regions:transition-valid" ve_region_step_valid_spec VE_REGION_STEP_VALID;;

let ve_region_trace_spec =
 `!n context next. steps ve_region_step n context next
    ==> ve_valid context ==> ve_valid next`;;
let VE_REGION_TRACE_VALID = prove(ve_region_trace_spec,
  MATCH_MP_TAC steps_INDUCT THEN REPEAT STRIP_TAC THEN
  ASM_MESON_TAC[VE_REGION_STEP_VALID]);;
ve_check "regions:trace-valid" ve_region_trace_spec VE_REGION_TRACE_VALID;;
