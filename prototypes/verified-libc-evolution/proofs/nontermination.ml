(* PC/code invariant, rather than a timeout or literal state cycle: events
   grow at every branch, so the entire state need not repeat. *)
let ve_one_step_invariant_spec =
 `!R (I:S->bool).
    ensures_n R I I (\s t. T) (\s. 1)
    ==> !s t. I s /\ R s t ==> I t`;;
let VE_ONE_STEP_INVARIANT = prove(ve_one_step_invariant_spec,
  REWRITE_TAC[ensures_n;eventually_n;STEPS_ONE] THEN MESON_TAC[]);;

let ve_steps_invariant_spec =
 `!R (I:S->bool).
    (!s t. I s /\ R s t ==> I t)
    ==> !n s t. steps R n s t ==> I s ==> I t`;;
let VE_STEPS_INVARIANT = prove(ve_steps_invariant_spec,
  REPEAT GEN_TAC THEN DISCH_TAC THEN MATCH_MP_TAC steps_INDUCT THEN
  REPEAT STRIP_TAC THEN ASM_MESON_TAC[]);;

let ve_self_stable_spec =
 `!pc. ensures_n arm
   (\s. aligned_bytes_loaded s (word pc) ve_mut_self_branch_mc /\
        read PC s = word(pc+28))
   (\s. aligned_bytes_loaded s (word pc) ve_mut_self_branch_mc /\
        read PC s = word(pc+28))
   (\s t. T) (\s. 1)`;;
let VE_SELF_STABLE = prove(ve_self_stable_spec,
  GEN_TAC THEN ARM_SIM_TAC VE_MUT_SELF_BRANCH_EXEC [1]);;

let ve_self_nonreach_spec =
 `!pc s n t.
    aligned_bytes_loaded s (word pc) ve_mut_self_branch_mc /\
    read PC s = word(pc+28) /\
    ~(word(pc+28):int64 = word 16384) /\ steps arm n s t
    ==> ~(read PC t = word 16384)`;;
let VE_SELF_NONREACH = prove(ve_self_nonreach_spec,
  REPEAT GEN_TAC THEN STRIP_TAC THEN
  MP_TAC(MATCH_MP VE_STEPS_INVARIANT
    (MATCH_MP VE_ONE_STEP_INVARIANT (SPEC `pc:num` VE_SELF_STABLE))) THEN
  DISCH_THEN(MP_TAC o SPECL [`n:num`;`s:armstate`;`t:armstate`]) THEN
  ASM_REWRITE_TAC[] THEN ASM_MESON_TAC[]);;

ve_check "self_branch:stable" ve_self_stable_spec VE_SELF_STABLE;;
ve_check "self_branch:nonreachability" ve_self_nonreach_spec VE_SELF_NONREACH;;
