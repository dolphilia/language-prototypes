(* Counted counterpart of GEN_BIGSTEP_TAC / ARM_SUBROUTINE_SIM_TAC.
   The state-update plumbing follows the pinned s2n-bignum helpers
   (Apache-2.0 OR ISC OR MIT-0); the composition rule is proved here. *)
let VE_COUNTED_BIGSTEP = prove
 (`!step (P:S->bool) Q C R s a b.
   P s /\ (!t. Q t /\ C s t ==> eventually_n step b R t)
   ==> ensures_n step P Q C (\t. a)
   ==> eventually_n step (a+b) R s`,
  REPEAT GEN_TAC THEN STRIP_TAC THEN REWRITE_TAC[ensures_n] THEN
  DISCH_THEN(MP_TAC o SPEC `s:S`) THEN ASM_REWRITE_TAC[] THEN DISCH_TAC THEN
  MATCH_MP_TAC EVENTUALLY_N_COMPOSE THEN EXISTS_TAC `\t:S. Q t /\ C (s:S) t` THEN
  ASM_REWRITE_TAC[]);;

let ve_n_bigstep_tac execth sname rest (asl,w) =
 let left,right=dest_imp w in
 let _,la=strip_comb left and _,ra=strip_comb right in
 let child=try rand(concl(BETA_CONV(mk_comb(last la,last ra)))) with Failure why ->
  print_term w; failwith ("counted child: "^why) in
 let remaining=el 1 ra in
 let total=mk_binop `(+):num->num->num` child rest in
 let svar=mk_var(sname,type_of(last ra)) in
 (SUBGOAL_THEN (mk_eq(remaining,total))
   (fun th -> GEN_REWRITE_TAC (RAND_CONV o RATOR_CONV o RATOR_CONV o RAND_CONV) [th]) THENL
  [ASM_ARITH_TAC;ALL_TAC] THEN
  GEN_REWRITE_TAC (LAND_CONV o TOP_DEPTH_CONV) (!simulation_precanon_thms) THEN
  MATCH_MP_TAC VE_COUNTED_BIGSTEP THEN CONJ_TAC THENL
  [BETA_TAC THEN ASM_REWRITE_TAC[];
   BETA_TAC THEN X_GEN_TAC svar THEN
   REPEAT(DISCH_THEN(CONJUNCTS_THEN2 STRIP_ASSUME_TAC MP_TAC)) THEN
   GEN_REWRITE_TAC (LAND_CONV o TOP_DEPTH_CONV) [MAYCHANGE;SEQ_ID] THEN
   GEN_REWRITE_TAC (LAND_CONV o TOP_DEPTH_CONV) [GSYM SEQ_ASSOC] THEN
   GEN_REWRITE_TAC (LAND_CONV o TOP_DEPTH_CONV) [ASSIGNS_SEQ] THEN
   GEN_REWRITE_TAC (LAND_CONV o TOP_DEPTH_CONV) [ASSIGNS_THM] THEN
   REWRITE_TAC[LEFT_IMP_EXISTS_THM] THEN REPEAT GEN_TAC THEN
   NONSELFMODIFYING_STATE_UPDATE_TAC (MATCH_MP aligned_bytes_loaded_update (fst execth)) THEN
   ASSUMPTION_STATE_UPDATE_TAC THEN MAYCHANGE_STATE_UPDATE_TAC THEN
   DISCH_THEN(K ALL_TAC) THEN DISCARD_OLDSTATE_TAC sname]) (asl,w);;

let ve_n_subroutine_tac (mc,exec,offset,submc,theorem) args step rest =
 let subloaded=ALIGNED_BYTES_LOADED_SUBPROGRAM_RULE mc submc offset in
 let length_th=TRANS (AP_TERM `LENGTH:byte list->num` submc)
                     (LENGTH_CONV(mk_comb(`LENGTH:byte list->num`,rhs(concl submc)))) in
 let theorem=REWRITE_RULE[length_th] theorem in
 fun (asl,w) ->
 let oldstate=mk_var("s"^string_of_int(step-1),`:armstate`) in
 let args=map (vsubst [oldstate,`s:armstate`]) args in
 (MP_TAC(TWEAK_PC_OFFSET(SPECL args theorem)) THEN
  ASM_REWRITE_TAC[C_ARGUMENTS;SOME_FLAGS;fst exec;LE_0;SUB_0] THEN
  CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN CONV_TAC NUM_REDUCE_CONV THEN
  ASM_REWRITE_TAC[] THEN REWRITE_TAC[ALLPAIRS;ALL;PAIRWISE;NONOVERLAPPING_CLAUSES] THEN
  TRY(ANTS_TAC THENL
   [CONV_TAC(ONCE_DEPTH_CONV NORMALIZE_RELATIVE_ADDRESS_CONV) THEN
    ALIGNED_WORD_TAC THEN REPEAT CONJ_TAC THEN
    TRY(CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN NO_TAC) THEN
    (NONOVERLAPPING_TAC ORELSE DISJ1_TAC THEN NONOVERLAPPING_TAC ORELSE
     DISJ2_TAC THEN NONOVERLAPPING_TAC);ALL_TAC]) THEN
  CONV_TAC(LAND_CONV(ONCE_DEPTH_CONV NORMALIZE_RELATIVE_ADDRESS_CONV)) THEN
  CONV_TAC(LAND_CONV(ONCE_DEPTH_CONV PC_PLUS_CONV)) THEN ASM_REWRITE_TAC[] THEN
  ve_n_bigstep_tac exec ("s"^string_of_int step) rest THENL
  [FIRST_X_ASSUM(MATCH_ACCEPT_TAC o MATCH_MP subloaded) ORELSE
   (CONJ_TAC THENL [FIRST_X_ASSUM(MATCH_ACCEPT_TAC o MATCH_MP subloaded);ALL_TAC]);
   RULE_ASSUM_TAC(CONV_RULE(TRY_CONV PC_PLUS_CONV))]) (asl,w);;
