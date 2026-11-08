(* Same byte loop as the baseline, checked against the unchanged fill contracts. *)
needs "arm/proofs/base.ml";;
loadt (Sys.getenv "VP_ROOT" ^ "/proofs/specs.ml");;

let vp2_memset_mc = define_assert_from_elf "vp2_memset_mc"
  (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/build/vp2_memset.o")
  [0xd2800003; 0xb40000a2; 0x38236801; 0x91000463;
   0xeb02007f; 0x54ffffa3; 0xd65f03c0];;
let VP2_MEMSET_EXEC = ARM_MK_EXEC_RULE vp2_memset_mc;;

let vp2_memset_core_spec =
 `!dst c n pc.
    nonoverlapping (word pc,28) (dst,val n)
    ==> ensures arm
      (\s. aligned_bytes_loaded s (word pc) vp2_memset_mc /\
           read PC s = word pc /\ C_ARGUMENTS [dst;c;n] s)
      (\s. read PC s = word (pc + 24) /\ read X0 s = dst /\
           (!i. i < val n ==>
             read (memory :> bytes8 (word_add dst (word i))) s = word_zx c))
      (MAYCHANGE [PC;X3] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
       MAYCHANGE [memory :> bytes(dst,val n)])`;;

let vp2_memset_core_tac =
  REWRITE_TAC[C_ARGUMENTS; SOME_FLAGS] THEN
  MAP_EVERY X_GEN_TAC [`dst:int64`; `c:int64`] THEN
  W64_GEN_TAC `n:num` THEN X_GEN_TAC `pc:num` THEN DISCH_TAC THEN
  ASM_CASES_TAC `n = 0` THENL
   [ASM_REWRITE_TAC[LT; VAL_WORD_0] THEN ARM_SIM_TAC VP2_MEMSET_EXEC (1--2);
    ALL_TAC] THEN
  ENSURES_WHILE_UP_TAC `n:num` `pc + 8` `pc + 16`
   `\i s. read X0 s = dst /\ read X1 s = c /\ read X2 s = word n /\
          read X3 s = word i /\
          (!j. j < i ==>
            read (memory :> bytes8 (word_add dst (word j))) s = word_zx c)` THEN
  ASM_REWRITE_TAC[] THEN REPEAT CONJ_TAC THENL
   [ARM_SIM_TAC VP2_MEMSET_EXEC (1--2) THEN REWRITE_TAC[LT];
    X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
    ARM_SIM_TAC VP2_MEMSET_EXEC (1--2) THEN
    REWRITE_TAC[GSYM WORD_ADD] THEN X_GEN_TAC `j:num` THEN
    REWRITE_TAC[ARITH_RULE `j < i + 1 <=> j < i \/ j = i`] THEN
    STRIP_TAC THENL [ASM_MESON_TAC[];
      ASM_REWRITE_TAC[] THEN CONV_TAC WORD_BLAST];
    X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
    ARM_SIM_TAC VP2_MEMSET_EXEC (1--2);
    ARM_SIM_TAC VP2_MEMSET_EXEC (1--2)];;

let VP2_MEMSET_CORE_CORRECT = prove(vp2_memset_core_spec,vp2_memset_core_tac);;

let VP2_MEMSET_CORRECT = prove(vp_fill_contract `vp2_memset_mc`,
  REWRITE_TAC[fst VP2_MEMSET_EXEC] THEN
  ARM_ADD_RETURN_NOSTACK_TAC VP2_MEMSET_EXEC VP2_MEMSET_CORE_CORRECT);;

needs "arm/proofs/base.ml";;

let vp2_memset_access_frame =
 `MAYCHANGE [PC;X3] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
  MAYCHANGE [memory :> bytes(dst,val (n:int64))]`;;

let ve_fill_with_frame spec frame =
  let vs,b = strip_forall spec in
  let a,e = dest_imp b in
  list_mk_forall(vs,mk_imp(a,mk_comb(rator e,frame)));;

let vp2_memset_access_strong =
  ve_fill_with_frame (vp_fill_access_contract `vp2_memset_mc`) vp2_memset_access_frame;;

let ve_fill_open_trace_tac = FIRST_X_ASSUM
  (X_CHOOSE_THEN `trace:uarch_event list` STRIP_ASSUME_TAC o
   check (is_exists o concl));;

let vp2_memset_access_tac =
  REWRITE_TAC[C_ARGUMENTS; SOME_FLAGS; fst VP2_MEMSET_EXEC] THEN
  MAP_EVERY X_GEN_TAC [`dst:int64`; `c:int64`] THEN
  W64_GEN_TAC `n:num` THEN
  MAP_EVERY X_GEN_TAC [`pc:num`; `returnaddress:int64`; `e:uarch_event list`] THEN
  STRIP_TAC THEN ASM_CASES_TAC `n = 0` THENL
   [ASM_REWRITE_TAC[VAL_WORD_0] THEN ARM_SIM_TAC VP2_MEMSET_EXEC (1--3) THEN
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
   [ARM_SIM_TAC VP2_MEMSET_EXEC (1--2) THEN
    EXISTS_TAC `[EventJump(word(pc+4),word(pc+8))]` THEN
    REWRITE_TAC[APPEND;memaccess_inbounds;ALL];
    X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
    ARM_SIM_TAC ~preprocess_tac:ve_fill_open_trace_tac VP2_MEMSET_EXEC (1--2) THEN
    REWRITE_TAC[GSYM WORD_ADD] THEN
    EXISTS_TAC `CONS (EventStore(word_add dst (word i),1)) trace` THEN
    ONCE_REWRITE_TAC[MEMACCESS_INBOUNDS_CONS] THEN
    ASM_REWRITE_TAC[APPEND;memaccess_inbounds;ALL;EX] THEN
    ASM_REWRITE_TAC[VAL_WORD_ADD;CONTAINED_MODULO_LMOD;DIMINDEX_64] THEN
    MATCH_MP_TAC CONTAINED_MODULO_OFFSET_SIMPLE THEN ASM_ARITH_TAC;
    X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
    ARM_SIM_TAC ~preprocess_tac:ve_fill_open_trace_tac VP2_MEMSET_EXEC (1--2) THEN
    EXISTS_TAC `CONS (EventJump(word(pc+20),word(pc+8))) trace` THEN
    RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
    ASM_REWRITE_TAC[APPEND;memaccess_inbounds;ALL];
    ARM_SIM_TAC ~preprocess_tac:ve_fill_open_trace_tac VP2_MEMSET_EXEC (1--3) THEN
    EXISTS_TAC `CONS (EventJump(word(pc+24),returnaddress))
                    (CONS (EventJump(word(pc+20),word(pc+24))) trace)` THEN
    RULE_ASSUM_TAC(REWRITE_RULE[memaccess_inbounds]) THEN
    ASM_REWRITE_TAC[APPEND;memaccess_inbounds;ALL]];;

let VP2_MEMSET_ACCESSES_STRONG =
  prove(vp2_memset_access_strong,vp2_memset_access_tac);;

let VP2_MEMSET_ACCESSES = prove(vp_fill_access_contract `vp2_memset_mc`,
  REPEAT STRIP_TAC THEN MATCH_MP_TAC ENSURES_FRAME_SUBSUMED THEN
  EXISTS_TAC vp2_memset_access_frame THEN CONJ_TAC THENL
   [REWRITE_TAC[subsumed];
    MATCH_MP_TAC VP2_MEMSET_ACCESSES_STRONG THEN ASM_REWRITE_TAC[]]);;


ve_check "fill:core" vp2_memset_core_spec VP2_MEMSET_CORE_CORRECT;;
ve_check "fill:public" (vp_fill_contract `vp2_memset_mc`) VP2_MEMSET_CORRECT;;
ve_check "fill:access-strong" vp2_memset_access_strong VP2_MEMSET_ACCESSES_STRONG;;
ve_check "fill:access" (vp_fill_access_contract `vp2_memset_mc`) VP2_MEMSET_ACCESSES;;
