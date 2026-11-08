(* Actual BL, private stack save/restore, and the embedded M1 theorem. *)
let ve_call_tac mc exec caller callee =
 REWRITE_TAC[ve_call_geometry;C_ARGUMENTS;SOME_FLAGS;fst exec;ADD_CLAUSES] THEN
 REPEAT GEN_TAC THEN STRIP_TAC THEN
 SUBGOAL_THEN `aligned 8 (word_sub (sp:int64) (word 16))` ASSUME_TAC THENL
  [ALIGNED_WORD_TAC THEN RULE_ASSUM_TAC(REWRITE_RULE[aligned]) THEN
   REWRITE_TAC[aligned] THEN ASM_MESON_TAC[DIVIDES_TRANS;NUMBER_RULE `8 divides 16`];ALL_TAC] THEN
 ENSURES_INIT_TAC "s0" THEN ARM_STEPS_TAC exec (1--3) THEN
 ARM_SUBROUTINE_SIM_TAC (mc,exec,callee,vp2_memcpy_chunk8_mc,VP2_MEMCPY_CHUNK8_CORRECT)
  [`dst:int64`;`src:int64`;`n:int64`;
   mk_binary "+" (`pc:num`,mk_small_numeral callee);
   vsubst [mk_small_numeral (caller+12),`offset:num`] `word(pc+offset):int64`;
   `input:num->byte`] 4 THEN
 TRY(ASM_REWRITE_TAC[ADD_CLAUSES] THEN NO_TAC) THEN
 ARM_STEPS_TAC exec (5--7) THEN ENSURES_FINAL_STATE_TAC THEN
 ASM_REWRITE_TAC[WORD_RULE `word_add (word_sub s (word 16)) (word 16):int64 = s`];;

let ve_call_access_tac mc exec caller callee =
 REWRITE_TAC[ve_call_geometry;C_ARGUMENTS;SOME_FLAGS;fst exec;ADD_CLAUSES] THEN
 REPEAT GEN_TAC THEN STRIP_TAC THEN
 SUBGOAL_THEN `aligned 8 (word_sub (sp:int64) (word 16))` ASSUME_TAC THENL
  [ALIGNED_WORD_TAC THEN RULE_ASSUM_TAC(REWRITE_RULE[aligned]) THEN
   REWRITE_TAC[aligned] THEN ASM_MESON_TAC[DIVIDES_TRANS;NUMBER_RULE `8 divides 16`];ALL_TAC] THEN
 ENSURES_INIT_TAC "s0" THEN ARM_STEPS_TAC exec (1--3) THEN
 ARM_SUBROUTINE_SIM_TAC (mc,exec,callee,vp2_memcpy_chunk8_mc,VP2_MEMCPY_CHUNK8_ACCESSES_STRONG)
  [`dst:int64`;`src:int64`;`n:int64`;
   mk_binary "+" (`pc:num`,mk_small_numeral callee);
   vsubst [mk_small_numeral (caller+12),`offset:num`] `word(pc+offset):int64`;
   `read events s`] 4 THEN
 TRY(ASM_REWRITE_TAC[ADD_CLAUSES] THEN NO_TAC) THEN
 ARM_STEPS_TAC exec (5--7) THEN ENSURES_FINAL_STATE_TAC THEN
 ASM_REWRITE_TAC[WORD_RULE `word_add (word_sub s (word 16)) (word 16):int64 = s`] THEN
 EXISTS_TAC (vsubst [mk_small_numeral (caller+20),`last:num`;
                      mk_small_numeral (caller+8),`branch:num`;
                      mk_small_numeral callee,`target:num`]
  `APPEND [EventJump(word(pc+last),returnaddress);EventLoad(word_sub sp (word 16),8)]
    (APPEND trace [EventJump(word(pc+branch),word(pc+target));EventStore(word_sub sp (word 16),8)])`) THEN
 ASM_REWRITE_TAC[APPEND;GSYM APPEND_ASSOC;ADD_CLAUSES] THEN
 SUBGOAL_THEN
  `memaccess_inbounds (trace:uarch_event list)
     [src,val(n:int64);word_sub sp (word 16),16]
     [dst,val(n:int64);word_sub sp (word 16),16]` ASSUME_TAC THENL
 [MP_TAC(ISPECL [`trace:uarch_event list`;`[src:int64,val(n:int64)]`;
    `[src:int64,val(n:int64);word_sub sp (word 16),16]`;`[dst:int64,val(n:int64)]`;
    `[dst:int64,val(n:int64);word_sub sp (word 16),16]`] MEMACCESS_INBOUNDS_MEM) THEN
  ASM_REWRITE_TAC[ALL;MEM];ALL_TAC] THEN
 RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
 ASM_REWRITE_TAC[memaccess_inbounds;ALL_APPEND;ALL;EX] THEN
 REPEAT CONJ_TAC THEN DISJ2_TAC THEN MATCH_MP_TAC CONTAINED_MODULO_SIMPLE THEN ARITH_TAC;;
