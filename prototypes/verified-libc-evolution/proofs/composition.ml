(* Parent data operations are discharged using child theorems. Only control
   instructions (including the final RET) may be simulated in the parent. *)
let ve_sequence pc predicate = ENSURES_SEQUENCE_TAC pc predicate;;
let ve_branch guard positive negative = ASM_CASES_TAC guard THENL [positive;negative];;
let ve_loop_up bound start finish invariant =
  ENSURES_WHILE_UP_TAC bound start finish invariant;;

let ve_fixedcopy_spec ?(scratch=[`X4`]) code width =
 let dst=`dst:int64` and src=`src:int64` and pc=`pc:num`
 and ra=`returnaddress:int64` and e=`e:uarch_event list` in
 let address a k = list_mk_comb(`word_add:int64->int64->int64`,[a;mk_comb(`word:num->int64`,mk_small_numeral k)]) in
 let event name a = list_mk_icomb name [mk_pair(a,`8`)] in
 let jump=mk_comb(`EventJump:int64#int64->uarch_event`,
      mk_pair(mk_comb(`word:num->int64`,mk_binop `(+):num->num->num` pc (mk_small_numeral width)),ra)) in
 let trace=jump::flat(List.init (width/8) (fun j ->
   let k=width-8-j*8 in [event "EventStore" (address dst k);event "EventLoad" (address src k)])) in
 let template=vsubst[code,`code:byte list`;mk_small_numeral width,`width:num`;
      mk_list(`PC`::scratch,`:(armstate,int64)component`),`clobbers:((armstate,int64)component)list`;
      mk_small_numeral(width/8),`count:num`;list_mk_abs([dst;src;pc;ra],mk_list(trace,`:uarch_event`)),
      `trace:int64->int64->num->int64->uarch_event list`]
 `!dst src pc returnaddress (payload:num->int64) e.
   nonoverlapping (word pc,LENGTH code) (dst,width) /\
   nonoverlapping (src,width) (dst,width) /\ aligned 8 dst /\ aligned 8 src
   ==> ensures arm
    (\s. aligned_bytes_loaded s (word pc) code /\ read PC s = word pc /\
         read X30 s = returnaddress /\ read X0 s = dst /\ read X1 s = src /\
         (!j. j < count ==>
           read (memory :> bytes64 (word_add src (word (8*j)))) s = payload j) /\
         read events s = e)
    (\s. read PC s = returnaddress /\ read X0 s = dst /\
         (!j. j < count ==>
           read (memory :> bytes64 (word_add dst (word (8*j)))) s = payload j) /\
         read events s = APPEND (trace dst src pc returnaddress) e)
    (MAYCHANGE (clobbers:((armstate,int64)component)list) ,, MAYCHANGE [events] ,,
     MAYCHANGE [memory :> bytes(dst,width)])` in
 (rhs o concl o DEPTH_CONV BETA_CONV) template;;

let ve_fixedcopy_composed_tac code execution children =
 REWRITE_TAC[fst execution] THEN
 CONV_TAC(DEPTH_CONV EXPAND_CASES_CONV) THEN
 CONV_TAC NUM_REDUCE_CONV THEN REWRITE_TAC[WORD_ADD_0] THEN REPEAT STRIP_TAC THEN
 ENSURES_INIT_TAC "s0" THEN
 EVERY (List.mapi (fun j (child_code,child_theorem) ->
   ARM_SUBROUTINE_SIM_TAC
    (code,execution,j*8,child_code,REWRITE_RULE[WORD_ADD_0;ADD_CLAUSES] child_theorem)
    [`dst:int64`;`src:int64`;mk_comb(`payload:num->int64`,mk_small_numeral j);
     (if j=0 then `pc:num` else
       mk_binop `(+):num->num->num` `pc:num` (mk_small_numeral(j*8)));`read events s`]
    (j+1)) children) THEN
 ARM_STEPS_TAC execution [List.length children+1] THEN
 ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[APPEND;WORD_ADD_0];;
