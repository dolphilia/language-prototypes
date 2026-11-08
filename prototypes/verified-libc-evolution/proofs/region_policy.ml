(* Global properties of a reachable ledger, beyond particular examples. *)
let VE_PAIRWISE_MEM_SYMMETRIC = prove
 (`!R:A->A->bool.
    (!a b. R a b ==> R b a)
    ==> !loans a b. PAIRWISE R loans /\ MEM a loans /\ MEM b loans /\ ~(a=b)
                   ==> R a b`,
  GEN_TAC THEN DISCH_TAC THEN LIST_INDUCT_TAC THEN
  ASM_REWRITE_TAC[PAIRWISE;MEM;GSYM ALL_MEM] THEN ASM_MESON_TAC[]);;
let VE_LEASE_PAIRWISE_MEM = MATCH_MP
 (BETA_RULE(ISPEC `\a b. ~(ve_lid a = ve_lid b) /\ ve_compatible a b` VE_PAIRWISE_MEM_SYMMETRIC))
 (prove(`!a b. (~(ve_lid a = ve_lid b) /\ ve_compatible a b)
             ==> ~(ve_lid b = ve_lid a) /\ ve_compatible b a`,
    MESON_TAC[VE_COMPATIBLE_SYM]));;

let ve_exclusive_spec =
 `!owner epoch serial capacity alive loans a b.
    ve_write_authorized (VEContext owner epoch serial capacity alive loans) a /\
    ve_authorized (VEContext owner epoch serial capacity alive loans) b /\ ~(a=b)
    ==> ve_separate a b`;;
let VE_EXCLUSIVE = prove(ve_exclusive_spec,
  REPEAT GEN_TAC THEN REWRITE_TAC[ve_write_authorized;ve_authorized;ve_valid] THEN
  STRIP_TAC THEN
  MP_TAC(SPECL [`loans:ve_lease list`;`a:ve_lease`;`b:ve_lease`] VE_LEASE_PAIRWISE_MEM) THEN
  ASM_REWRITE_TAC[ve_compatible] THEN ASM_MESON_TAC[]);;
ve_check "regions:exclusive-separation" ve_exclusive_spec VE_EXCLUSIVE;;

let ve_authorized_bounds_spec =
 `!owner epoch serial capacity alive loans token.
    ve_authorized (VEContext owner epoch serial capacity alive loans) token
    ==> ve_fits owner epoch serial capacity token /\
        ve_loffset token + ve_llength token <= capacity`;;
let VE_AUTHORIZED_BOUNDS = prove(ve_authorized_bounds_spec,
  REWRITE_TAC[ve_authorized;ve_valid] THEN MESON_TAC[ve_fits]);;
ve_check "regions:authorized-bounds" ve_authorized_bounds_spec VE_AUTHORIZED_BOUNDS;;
