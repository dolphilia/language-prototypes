let ve_chunk_count unroll =
 let block=mk_small_numeral(8*unroll) and iteration=mk_small_numeral(3*unroll+4) in
 vsubst [block,`block:num`;iteration,`iteration:num`]
 `if word_and (word_or (dst:int64) src) (word 7) = word 0
  then iteration*(val(n:int64) DIV block)+5*(val n MOD block)+10
  else 5*val n+7`;;

let ve_chunk_resource_tac mc exec unroll bulk tail =
 let block=mk_small_numeral(8*unroll) and iteration=mk_small_numeral(3*unroll+4) in
 let offset=mk_small_numeral(44+12*(unroll-1)) in
 let sub tm=vsubst[block,`block:num`;iteration,`iteration:num`;offset,`tail:num`] tm in
 let index=sub `block*(n DIV block)` in
 let tail_call step start =
  ve_n_subroutine_tac (mc,exec,0,mc,tail)
   [`dst:int64`;`src:int64`;`n:num`;start;`pc:num`;`returnaddress:int64`;`read events s`] step `0` THEN
  TRY(ASM_REWRITE_TAC[ADD_CLAUSES] THEN NO_TAC) THEN
  ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC ve_count_rewrites THEN ASM_ARITH_TAC in
 REWRITE_TAC[SOME_FLAGS;fst exec] THEN
 MAP_EVERY X_GEN_TAC [`dst:int64`;`src:int64`] THEN W64_GEN_TAC `n:num` THEN
 MAP_EVERY X_GEN_TAC [`pc:num`;`returnaddress:int64`;`e:uarch_event list`] THEN STRIP_TAC THEN
 SUBGOAL_THEN (sub `block*(n DIV block) <= n /\
   n = block*(n DIV block)+(n MOD block) /\ n MOD block < block`)
  STRIP_ASSUME_TAC THENL
 [MP_TAC(SPECL [`n:num`;block] DIVISION) THEN CONV_TAC NUM_REDUCE_CONV THEN ARITH_TAC;ALL_TAC] THEN
 ASM_CASES_TAC `word_and (word_or dst src) (word 7):int64 = word 0` THEN ASM_REWRITE_TAC[] THENL
 [SUBGOAL_THEN `aligned 8 (dst:int64) /\ aligned 8 (src:int64)` STRIP_ASSUME_TAC THENL
  [MP_TAC(SPECL [`dst:int64`;`src:int64`] VE_FAST_GUARD) THEN ASM_REWRITE_TAC[];ALL_TAC] THEN
  ENSURES_N_SEQUENCE_TAC `pc+16`
   `\s. read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
     read X30 s = returnaddress /\ read X3 s = word 0 /\
     read events s = CONS(EventJump(word(pc+12),word(pc+16))) e`
   `4` (sub `iteration*(n DIV block)+5*(n MOD block)+6`) THEN
  REPEAT CONJ_TAC THENL
  [ARM_SIM_TAC exec (1--4);
   ENSURES_INIT_TAC "s0" THEN
   ve_n_subroutine_tac (mc,exec,0,mc,bulk)
    [`dst:int64`;`src:int64`;`n:num`;`pc:num`;`read events s`] 1
    (sub `5*(n MOD block)+3`) THEN
   TRY(ASM_REWRITE_TAC[ADD_CLAUSES] THEN NO_TAC) THEN tail_call 2 index;
   ARITH_TAC];
  SUBGOAL_THEN `~(val(word_and (word_or dst src) (word 7):int64) = 0)` ASSUME_TAC THENL
  [ASM_REWRITE_TAC[VAL_EQ_0];ALL_TAC] THEN
  ENSURES_N_SEQUENCE_TAC (sub `pc+tail`)
   (sub `\s. read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
     read X30 s = returnaddress /\ read X3 s = word 0 /\
     read events s = CONS(EventJump(word(pc+12),word(pc+tail))) e`)
   `4` `5*n+3` THEN REPEAT CONJ_TAC THENL
  [ARM_SIM_TAC exec (1--4);
   ENSURES_INIT_TAC "s0" THEN tail_call 1 `0`;
   ARITH_TAC]];;
