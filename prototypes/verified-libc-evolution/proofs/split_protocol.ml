(* These are ghost transitions on the same checked sizes used by the machine.
   They do not manufacture physical RAM or make HOL facts linear resources. *)
let ve_split_protocol = new_definition
 `ve_split_protocol owner epoch capacity split n <=>
    ve_borrow (VEContext owner epoch 0 capacity T []) 0 n F
      (VELease 0 owner epoch 0 n F)
      (VEContext owner epoch 1 capacity T [VELease 0 owner epoch 0 n F]) /\
    ve_borrow (VEContext owner epoch 1 capacity T [VELease 0 owner epoch 0 n F]) split n T
      (VELease 1 owner epoch split n T)
      (VEContext owner epoch 2 capacity T [VELease 1 owner epoch split n T;VELease 0 owner epoch 0 n F]) /\
    ve_valid (VEContext owner epoch 2 capacity T [VELease 1 owner epoch split n T;VELease 0 owner epoch 0 n F]) /\
    ve_authorized (VEContext owner epoch 2 capacity T [VELease 1 owner epoch split n T;VELease 0 owner epoch 0 n F])
      (VELease 0 owner epoch 0 n F) /\
    ve_write_authorized (VEContext owner epoch 2 capacity T [VELease 1 owner epoch split n T;VELease 0 owner epoch 0 n F])
      (VELease 1 owner epoch split n T) /\
    ~ve_owner_ready (VEContext owner epoch 2 capacity T [VELease 1 owner epoch split n T;VELease 0 owner epoch 0 n F]) /\
    ve_end_borrow (VEContext owner epoch 2 capacity T [VELease 1 owner epoch split n T;VELease 0 owner epoch 0 n F])
      (VELease 1 owner epoch split n T) (VEContext owner epoch 2 capacity T [VELease 0 owner epoch 0 n F]) /\
    ve_end_borrow (VEContext owner epoch 2 capacity T [VELease 0 owner epoch 0 n F])
      (VELease 0 owner epoch 0 n F) (VEContext owner epoch 2 capacity T []) /\
    ve_owner_ready (VEContext owner epoch 2 capacity T [])`;;

let ve_split_protocol_spec =
 `!owner epoch capacity split n. ve_split_guard capacity split n
    ==> ve_split_protocol owner epoch capacity split n`;;
let VE_SPLIT_PROTOCOL = prove(ve_split_protocol_spec,
 REPEAT GEN_TAC THEN DISCH_TAC THEN
 MP_TAC(SPECL [`owner:num`;`epoch:num`;`capacity:num`;`split:num`;`n:num`] VE_SPLIT_BORROWS) THEN
 MP_TAC(SPECL [`owner:num`;`epoch:num`;`capacity:num`;`split:num`;`n:num`] VE_SPLIT_PERMISSIONS) THEN
 MP_TAC(SPECL [`owner:num`;`epoch:num`;`capacity:num`;`split:num`;`n:num`] VE_SPLIT_RETURN) THEN
 ASM_REWRITE_TAC[ve_split_protocol;LET_DEF;LET_END_DEF] THEN MESON_TAC[]);;
ve_check "split:region-protocol" ve_split_protocol_spec VE_SPLIT_PROTOCOL;;

let VE_SPLIT_STATUS_ZERO = prove
 (`!guard. (word(if guard then 0 else 1):int64 = word 0) <=> guard`,
  GEN_TAC THEN BOOL_CASES_TAC `guard:bool` THEN REWRITE_TAC[] THEN
  CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN REWRITE_TAC[]);;

let ve_split_protocol_contract code entry =
 let vars,body=strip_forall(ve_split_call_contract code entry) in
 let pre,goal=dest_imp body in let fn,args=strip_comb goal in
 let post=el 2 args and s=`s:armstate` in
 let protocol = `read X0 s = word 0 ==>
   ve_split_protocol owner epoch (val(capacity:int64)) (val(split:int64)) (val(n:int64))` in
 let enriched=mk_abs(s,mk_conj(mk_comb(post,s),protocol)) in
 list_mk_forall(`owner:num`::`epoch:num`::vars,
   mk_imp(pre,list_mk_comb(fn,[el 0 args;el 1 args;enriched;el 3 args])));;

let ve_split_protocol_tac correct base =
 let _,body=strip_forall base in let _,goal=dest_imp body in
 let _,args=strip_comb goal in let post=el 2 args in
 REPEAT GEN_TAC THEN DISCH_TAC THEN ENSURES_POSTCONDITION_TAC post THEN CONJ_TAC THENL
 [X_GEN_TAC `s:armstate` THEN BETA_TAC THEN DISCH_TAC THEN CONJ_TAC THENL
  [ASM_REWRITE_TAC[];
   DISCH_TAC THEN MATCH_MP_TAC VE_SPLIT_PROTOCOL THEN
   ASM_MESON_TAC[VE_SPLIT_STATUS_ZERO]];
  MATCH_MP_TAC correct THEN ASM_REWRITE_TAC[]];;
