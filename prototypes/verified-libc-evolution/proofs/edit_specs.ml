(* Same copy contract; the scratch edit deliberately permits X3 as well.
   The frame edit restores the stricter X3-preservation requirement. *)
let ve_edit_composed_tac code execution children =
 REWRITE_TAC[fst execution] THEN CONV_TAC(DEPTH_CONV EXPAND_CASES_CONV) THEN
 CONV_TAC NUM_REDUCE_CONV THEN REWRITE_TAC[WORD_ADD_0] THEN REPEAT STRIP_TAC THEN
 ENSURES_INIT_TAC "s0" THEN
 EVERY(List.mapi (fun j (slot,child_code,child_theorem) ->
  ARM_SUBROUTINE_SIM_TAC
   (code,execution,j*8,child_code,REWRITE_RULE[WORD_ADD_0;ADD_CLAUSES] child_theorem)
   [`dst:int64`;`src:int64`;mk_comb(`payload:num->int64`,mk_small_numeral slot);
    (if j=0 then `pc:num` else mk_binop `(+):num->num->num` `pc:num` (mk_small_numeral(j*8)));
    `read events s`] (j+1)) children) THEN
 ARM_STEPS_TAC execution [List.length children+1] THEN
 ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[APPEND;WORD_ADD_0];;

let ve_edit_rejections=ref ([]:string list);;
let ve_edit_reject name thunk =
 let started=Sys.time() in
 let reason=try ignore(thunk());None with Failure message -> Some message in
 (match reason with None -> failwith("invalid edit accepted: "^name)
 | Some message ->
   Printf.printf "VE_EDIT_REJECT %s %.9f %S\n%!" name (Sys.time()-.started) message;
   ve_edit_rejections:=name::!ve_edit_rejections);;
