let ve_split_access_success_tac mc exec caller callee =
 ve_split_success_setup exec THEN
 ABBREV_TAC `dst:int64 = word_add arena split` THEN
 ENSURES_INIT_TAC "s0" THEN ARM_STEPS_TAC exec (1--14) THEN
 ARM_SUBROUTINE_SIM_TAC (mc,exec,callee,vp2_memcpy_chunk8_mc,VP2_MEMCPY_CHUNK8_ACCESSES_STRONG)
  [`word_add (arena:int64) split`;`arena:int64`;`n:int64`;
   mk_binary "+" (`pc:num`,mk_small_numeral callee);
   vsubst [mk_small_numeral (caller+56),`offset:num`] `word(pc+offset):int64`;
   `read events s`] 15 THEN
 TRY(ASM_REWRITE_TAC[ADD_CLAUSES] THEN NO_TAC) THEN
 ARM_STEPS_TAC exec (16--19) THEN ENSURES_FINAL_STATE_TAC THEN
 ASM_REWRITE_TAC[WORD_RULE `word_add (word_sub s (word 16)) (word 16):int64 = s`] THEN
 EXISTS_TAC (vsubst [mk_small_numeral callee,`target:num`]
  `APPEND [EventJump(word(pc+68),returnaddress);EventLoad(word_sub sp (word 16),8)]
   (APPEND trace [EventJump(word(pc+52),word(pc+target));EventStore(word_sub sp (word 16),8);
     EventJump(word(pc+28),word(pc+32));EventJump(word(pc+16),word(pc+20));
     EventJump(word(pc+8),word(pc+12));EventJump(word pc,word(pc+4))])`) THEN
 ASM_REWRITE_TAC[APPEND;GSYM APPEND_ASSOC;ADD_CLAUSES] THEN
 SUBGOAL_THEN
  `memaccess_inbounds (trace:uarch_event list)
    [arena,val(capacity:int64);word_sub sp (word 16),16]
    [arena,val(capacity:int64);word_sub sp (word 16),16]` ASSUME_TAC THENL
 [MP_TAC(SPECL [`trace:uarch_event list`;`arena:int64`;`val(capacity:int64)`;
      `val(split:int64)`;`val(n:int64)`;`word_sub (sp:int64) (word 16)`] VE_SPLIT_TRACE_ROOT) THEN
  ASM_REWRITE_TAC[WORD_VAL];ALL_TAC] THEN
 RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
 ASM_REWRITE_TAC[memaccess_inbounds;ALL_APPEND;ALL;EX] THEN
 REPEAT CONJ_TAC THEN DISJ2_TAC THEN MATCH_MP_TAC CONTAINED_MODULO_SIMPLE THEN ARITH_TAC;;

let ve_split_access_failure path =
 let middle = match path with
 | 0 -> `[]:uarch_event list`
 | 1 -> `[EventJump(word(pc+8),word(pc+72));EventJump(word pc,word(pc+4))]`
 | 2 -> `[EventJump(word(pc+16),word(pc+72));EventJump(word(pc+8),word(pc+12));EventJump(word pc,word(pc+4))]`
 | 3 -> `[EventJump(word(pc+28),word(pc+72));EventJump(word(pc+16),word(pc+20));EventJump(word(pc+8),word(pc+12));EventJump(word pc,word(pc+4))]`
 | _ -> failwith "invalid split failure path" in
 let trace = if path=0 then
  `[EventJump(word(pc+76),returnaddress);EventJump(word pc,word(pc+72))]`
 else mk_comb(mk_comb(`CONS:uarch_event->uarch_event list->uarch_event list`,
                `EventJump(word(pc+76),returnaddress)`),middle) in
 EXISTS_TAC trace THEN REWRITE_TAC[APPEND;memaccess_inbounds;ALL];;

let ve_split_access_public_tac exec success =
 REPEAT GEN_TAC THEN DISCH_TAC THEN
 ASM_CASES_TAC `ve_split_guard (val(capacity:int64)) (val(split:int64)) (val(n:int64))` THENL
 [MATCH_MP_TAC success THEN ASM_REWRITE_TAC[];
  ASM_REWRITE_TAC[] THEN ve_split_failure_tac exec ve_split_access_failure];;
