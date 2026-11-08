let ve_construction_rejections = ref ([]:string list);;
let ve_reject_construction name thunk =
 let rejected=try thunk();false with Failure _ -> true in
 if not rejected then failwith("invalid composition accepted: " ^ name);
 ve_construction_rejections := name :: !ve_construction_rejections;;

ve_reject_construction "live-register" (fun () ->
 ignore(Ve_block.create vp2_block_copy8_0_mc (Ve_block.Fixed8(0,`X0`))
   VP2_BLOCK_COPY8_0_CORRECT));;
ve_reject_construction "code-theorem-mismatch" (fun () ->
 ignore(Ve_block.create vp2_block_copy8_8_mc (Ve_block.Fixed8(8,`X4`))
   VP2_BLOCK_COPY8_0_CORRECT));;
ve_reject_construction "wrong-offset" (fun () ->
 ignore(Ve_block.create vp2_block_copy8_0_mc (Ve_block.Fixed8(8,`X4`))
   VP2_BLOCK_COPY8_0_CORRECT));;

let ve_reframe spec frame =
 let vars,body=strip_forall spec in let pre,goal=dest_imp body in
 list_mk_forall(vars,mk_imp(pre,mk_comb(rator goal,frame)));;
let ve_weak_flags_spec=ve_reframe vp2_block_copy8_0_spec
 `MAYCHANGE [PC;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
  MAYCHANGE [memory :> bytes(word_add dst (word 0),8)]`;;
let VE_WEAK_FLAGS = prove(ve_weak_flags_spec,
 REWRITE_TAC[SOME_FLAGS;WORD_ADD_0] THEN REPEAT STRIP_TAC THEN
 ARM_SIM_TAC VP2_BLOCK_COPY8_0_EXEC (1--2) THEN REWRITE_TAC[APPEND]);;
ve_check "composition:weak-flags-fixture" ve_weak_flags_spec VE_WEAK_FLAGS;;
ve_reject_construction "unjustified-flag-preservation" (fun () ->
 ignore(Ve_block.create vp2_block_copy8_0_mc (Ve_block.Fixed8(0,`X4`)) VE_WEAK_FLAGS));;

let ve_insufficient_frame=ve_reframe vp2_copy16_spec
 `MAYCHANGE [PC;X4] ,, MAYCHANGE [events] ,, MAYCHANGE [memory :> bytes(dst,8)]`;;
ve_reject_construction "only-eight-byte-write-permission" (fun () ->
 ignore(prove(ve_insufficient_frame,
   ve_fixedcopy_composed_tac vp2_copy16_mc VP2_COPY16_EXEC
    [(vp2_block_copy8_0_mc,VP2_BLOCK_COPY8_0_CORRECT);
     (vp2_block_copy8_8_mc,VP2_BLOCK_COPY8_8_CORRECT)])));;

let ve_missing_condition =
 let vars,body=strip_forall vp2_block_copy8_0_spec in
 list_mk_forall(vars,snd(dest_imp body));;
ve_reject_construction "dropped-child-preconditions" (fun () ->
 ignore(Ve_block.create vp2_block_copy8_0_mc (Ve_block.Fixed8(0,`X4`))
   (ASSUME ve_missing_condition)));;

if List.rev !ve_construction_rejections <>
 ["live-register";"code-theorem-mismatch";"wrong-offset";
  "unjustified-flag-preservation";"only-eight-byte-write-permission";
  "dropped-child-preconditions"] then failwith "missing construction rejection";;
