needs "arm/proofs/base.ml";;

let vp_memset_access_frame =
 `MAYCHANGE [PC;X3] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
  MAYCHANGE [memory :> bytes(dst,val (n:int64))]`;;

let vp_with_frame spec frame =
  let vs,b = strip_forall spec in
  let a,e = dest_imp b in
  list_mk_forall(vs,mk_imp(a,mk_comb(rator e,frame)));;

let vp_memset_access_strong =
  vp_with_frame (vp_fill_access_contract `vp_memset_mc`) vp_memset_access_frame;;

let vp_open_trace_tac = FIRST_X_ASSUM
  (X_CHOOSE_THEN `trace:uarch_event list` STRIP_ASSUME_TAC o
   check (is_exists o concl));;

let vp_memset_access_tac =
  REWRITE_TAC[C_ARGUMENTS; SOME_FLAGS; fst VP_MEMSET_EXEC] THEN
  MAP_EVERY X_GEN_TAC [`dst:int64`; `c:int64`] THEN
  W64_GEN_TAC `n:num` THEN
  MAP_EVERY X_GEN_TAC [`pc:num`; `returnaddress:int64`; `e:uarch_event list`] THEN
  STRIP_TAC THEN ASM_CASES_TAC `n = 0` THENL
   [ASM_REWRITE_TAC[VAL_WORD_0] THEN ARM_SIM_TAC VP_MEMSET_EXEC (1--3) THEN
    EXISTS_TAC `[EventJump(word(pc+24),returnaddress);
                 EventJump(word(pc+4),word(pc+24))]` THEN
    REWRITE_TAC[APPEND;memaccess_inbounds;ALL];
    ALL_TAC] THEN
  ENSURES_WHILE_UP_TAC `n:num` `pc + 8` `pc + 16`
   `\i s. read X0 s = dst /\ read X1 s = c /\ read X2 s = word n /\
          read X30 s = returnaddress /\ read X3 s = word i /\
          (?trace. read events s = APPEND trace e /\
            memaccess_inbounds trace [] [dst,n])` THEN
  ASM_REWRITE_TAC[] THEN REPEAT CONJ_TAC THENL
   [ARM_SIM_TAC VP_MEMSET_EXEC (1--2) THEN
    EXISTS_TAC `[EventJump(word(pc+4),word(pc+8))]` THEN
    REWRITE_TAC[APPEND;memaccess_inbounds;ALL];
    X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
    ARM_SIM_TAC ~preprocess_tac:vp_open_trace_tac VP_MEMSET_EXEC (1--2) THEN
    REWRITE_TAC[GSYM WORD_ADD] THEN
    EXISTS_TAC `CONS (EventStore(word_add dst (word i),1)) trace` THEN
    ONCE_REWRITE_TAC[MEMACCESS_INBOUNDS_CONS] THEN
    ASM_REWRITE_TAC[APPEND;memaccess_inbounds;ALL;EX] THEN
    ASM_REWRITE_TAC[VAL_WORD_ADD;CONTAINED_MODULO_LMOD;DIMINDEX_64] THEN
    MATCH_MP_TAC CONTAINED_MODULO_OFFSET_SIMPLE THEN ASM_ARITH_TAC;
    X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
    ARM_SIM_TAC ~preprocess_tac:vp_open_trace_tac VP_MEMSET_EXEC (1--2) THEN
    EXISTS_TAC `CONS (EventJump(word(pc+20),word(pc+8))) trace` THEN
    RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
    ASM_REWRITE_TAC[APPEND;memaccess_inbounds;ALL];
    ARM_SIM_TAC ~preprocess_tac:vp_open_trace_tac VP_MEMSET_EXEC (1--3) THEN
    EXISTS_TAC `CONS (EventJump(word(pc+24),returnaddress))
                    (CONS (EventJump(word(pc+20),word(pc+24))) trace)` THEN
    RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
    ASM_REWRITE_TAC[APPEND;memaccess_inbounds;ALL]];;

let VP_MEMSET_ACCESSES_STRONG =
  prove(vp_memset_access_strong,vp_memset_access_tac);;

let VP_MEMSET_ACCESSES = prove(vp_fill_access_contract `vp_memset_mc`,
  REPEAT STRIP_TAC THEN MATCH_MP_TAC ENSURES_FRAME_SUBSUMED THEN
  EXISTS_TAC vp_memset_access_frame THEN CONJ_TAC THENL
   [REWRITE_TAC[subsumed];
    MATCH_MP_TAC VP_MEMSET_ACCESSES_STRONG THEN ASM_REWRITE_TAC[]]);;

let vp_memcpy_access_frame =
 `MAYCHANGE [PC;X3;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
  MAYCHANGE [memory :> bytes(dst,val (n:int64))]`;;

let vp_memcpy_scalar_access_strong =
  vp_with_frame (vp_copy_access_contract `vp_memcpy_scalar_mc`)
    vp_memcpy_access_frame;;

let vp_memcpy_scalar_access_tac =
  REWRITE_TAC[C_ARGUMENTS; SOME_FLAGS; fst VP_MEMCPY_SCALAR_EXEC] THEN
  MAP_EVERY X_GEN_TAC [`dst:int64`; `src:int64`] THEN
  W64_GEN_TAC `n:num` THEN
  MAP_EVERY X_GEN_TAC [`pc:num`; `returnaddress:int64`; `e:uarch_event list`] THEN
  STRIP_TAC THEN ASM_CASES_TAC `n = 0` THENL
   [ASM_REWRITE_TAC[VAL_WORD_0] THEN ARM_SIM_TAC VP_MEMCPY_SCALAR_EXEC (1--3) THEN
    EXISTS_TAC `[EventJump(word(pc+28),returnaddress);
                 EventJump(word(pc+4),word(pc+28))]` THEN
    REWRITE_TAC[APPEND;memaccess_inbounds;ALL];
    ALL_TAC] THEN
  ENSURES_WHILE_UP_TAC `n:num` `pc + 8` `pc + 20`
   `\i s. read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
          read X30 s = returnaddress /\ read X3 s = word i /\
          (?trace. read events s = APPEND trace e /\
            memaccess_inbounds trace [src,n] [dst,n])` THEN
  ASM_REWRITE_TAC[] THEN REPEAT CONJ_TAC THENL
   [ARM_SIM_TAC VP_MEMCPY_SCALAR_EXEC (1--2) THEN
    EXISTS_TAC `[EventJump(word(pc+4),word(pc+8))]` THEN
    REWRITE_TAC[APPEND;memaccess_inbounds;ALL];
    X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
    ARM_SIM_TAC ~preprocess_tac:vp_open_trace_tac VP_MEMCPY_SCALAR_EXEC (1--3) THEN
    REWRITE_TAC[GSYM WORD_ADD] THEN
    EXISTS_TAC `CONS (EventStore(word_add dst (word i),1))
                  (CONS (EventLoad(word_add src (word i),1)) trace)` THEN
    RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
    ASM_REWRITE_TAC[APPEND;memaccess_inbounds;ALL;EX] THEN
    ASM_REWRITE_TAC[VAL_WORD_ADD;CONTAINED_MODULO_LMOD;DIMINDEX_64] THEN
    CONJ_TAC THEN MATCH_MP_TAC CONTAINED_MODULO_OFFSET_SIMPLE THEN ASM_ARITH_TAC;
    X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
    ARM_SIM_TAC ~preprocess_tac:vp_open_trace_tac VP_MEMCPY_SCALAR_EXEC (1--2) THEN
    EXISTS_TAC `CONS (EventJump(word(pc+24),word(pc+8))) trace` THEN
    RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
    ASM_REWRITE_TAC[APPEND;memaccess_inbounds;ALL];
    ARM_SIM_TAC ~preprocess_tac:vp_open_trace_tac VP_MEMCPY_SCALAR_EXEC (1--3) THEN
    EXISTS_TAC `CONS (EventJump(word(pc+28),returnaddress))
                    (CONS (EventJump(word(pc+24),word(pc+28))) trace)` THEN
    RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
    ASM_REWRITE_TAC[APPEND;memaccess_inbounds;ALL]];;

let VP_MEMCPY_SCALAR_ACCESSES_STRONG =
  prove(vp_memcpy_scalar_access_strong,vp_memcpy_scalar_access_tac);;

let VP_MEMCPY_SCALAR_ACCESSES = prove(vp_copy_access_contract `vp_memcpy_scalar_mc`,
  REPEAT STRIP_TAC THEN MATCH_MP_TAC ENSURES_FRAME_SUBSUMED THEN
  EXISTS_TAC vp_memcpy_access_frame THEN CONJ_TAC THENL
   [REWRITE_TAC[subsumed];
    MATCH_MP_TAC VP_MEMCPY_SCALAR_ACCESSES_STRONG THEN ASM_REWRITE_TAC[]]);;
