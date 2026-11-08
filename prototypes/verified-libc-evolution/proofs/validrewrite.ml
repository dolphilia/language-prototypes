(* Adapted from the preserved scalar proof; the first instruction is EOR,
   not MOV. The unchanged independent public contract is checked below. *)
needs "arm/proofs/base.ml";;
loadt (Sys.getenv "VP_ROOT" ^ "/proofs/specs.ml");;

let ve_equivalent_mc = define_assert_from_elf "ve_equivalent_mc"
  (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/build/vp2_equivalent_copy.o")
  [0xca030063; 0xb40000c2; 0x38636824; 0x38236804;
   0x91000463; 0xeb02007f; 0x54ffff83; 0xd65f03c0];;
let VE_EQUIVALENT_EXEC = ARM_MK_EXEC_RULE ve_equivalent_mc;;

let ve_equivalent_core_spec =
 `!dst src n pc (input:num->byte).
    nonoverlapping (word pc,32) (dst,val n) /\
    nonoverlapping (src,val n) (dst,val n)
    ==> ensures arm
      (\s. aligned_bytes_loaded s (word pc) ve_equivalent_mc /\
           read PC s = word pc /\ C_ARGUMENTS [dst;src;n] s /\
           (!i. i < val n ==>
             read (memory :> bytes8 (word_add src (word i))) s = input i))
      (\s. read PC s = word (pc + 28) /\ read X0 s = dst /\
           (!i. i < val n ==>
             read (memory :> bytes8 (word_add dst (word i))) s = input i))
      (MAYCHANGE [PC;X3;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
       MAYCHANGE [memory :> bytes(dst,val n)])`;;

let ve_equivalent_core_tac =
  REWRITE_TAC[C_ARGUMENTS; SOME_FLAGS] THEN
  MAP_EVERY X_GEN_TAC [`dst:int64`; `src:int64`] THEN
  W64_GEN_TAC `n:num` THEN MAP_EVERY X_GEN_TAC [`pc:num`; `input:num->byte`] THEN
  STRIP_TAC THEN
  ASM_CASES_TAC `n = 0` THENL
   [ASM_REWRITE_TAC[LT; VAL_WORD_0] THEN ARM_SIM_TAC VE_EQUIVALENT_EXEC (1--2);
    ALL_TAC] THEN
  ENSURES_WHILE_UP_TAC `n:num` `pc + 8` `pc + 20`
   `\i s. read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
          read X3 s = word i /\
          (!j. j < n ==>
            read (memory :> bytes8 (word_add src (word j))) s = input j) /\
          (!j. j < i ==>
            read (memory :> bytes8 (word_add dst (word j))) s = input j)` THEN
  ASM_REWRITE_TAC[] THEN REPEAT CONJ_TAC THENL
   [ARM_SIM_TAC VE_EQUIVALENT_EXEC (1--2) THEN REWRITE_TAC[LT];
    X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
    ARM_SIM_TAC ~preprocess_tac:(SUBGOAL_THEN
      `read (memory :> bytes8 (word_add src (word i))) s0 = input i`
      ASSUME_TAC THENL [ASM_MESON_TAC[]; ALL_TAC])
      VE_EQUIVALENT_EXEC (1--3) THEN
    REWRITE_TAC[GSYM WORD_ADD] THEN X_GEN_TAC `j:num` THEN
    REWRITE_TAC[ARITH_RULE `j < i + 1 <=> j < i \/ j = i`] THEN
    STRIP_TAC THENL [ASM_MESON_TAC[];
      ASM_REWRITE_TAC[] THEN CONV_TAC WORD_BLAST];
    X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
    ARM_SIM_TAC VE_EQUIVALENT_EXEC (1--2);
    ARM_SIM_TAC VE_EQUIVALENT_EXEC (1--2)];;

let VE_EQUIVALENT_CORE_CORRECT =
  prove(ve_equivalent_core_spec,ve_equivalent_core_tac);;

let VE_EQUIVALENT_CORRECT = prove(vp_copy_contract `ve_equivalent_mc`,
  GEN_REWRITE_TAC (funpow 4 BINDER_CONV) [SWAP_FORALL_THM] THEN
  REWRITE_TAC[fst VE_EQUIVALENT_EXEC] THEN
  ARM_ADD_RETURN_NOSTACK_TAC VE_EQUIVALENT_EXEC VE_EQUIVALENT_CORE_CORRECT);;

ve_check "equivalent:public" (vp_copy_contract `ve_equivalent_mc`) VE_EQUIVALENT_CORRECT;;
