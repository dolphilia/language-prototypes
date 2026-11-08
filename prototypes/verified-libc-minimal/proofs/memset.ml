needs "arm/proofs/base.ml";;
loadt (Sys.getenv "VP_ROOT" ^ "/proofs/specs.ml");;

let vp_memset_mc = define_assert_from_elf "vp_memset_mc"
  (Sys.getenv "VP_ROOT" ^ "/build/vp_memset.o")
  [0xd2800003; 0xb40000a2; 0x38236801; 0x91000463;
   0xeb02007f; 0x54ffffa3; 0xd65f03c0];;
let VP_MEMSET_EXEC = ARM_MK_EXEC_RULE vp_memset_mc;;

let vp_memset_core_spec =
 `!dst c n pc.
    nonoverlapping (word pc,28) (dst,val n)
    ==> ensures arm
      (\s. aligned_bytes_loaded s (word pc) vp_memset_mc /\
           read PC s = word pc /\ C_ARGUMENTS [dst;c;n] s)
      (\s. read PC s = word (pc + 24) /\ read X0 s = dst /\
           (!i. i < val n ==>
             read (memory :> bytes8 (word_add dst (word i))) s = word_zx c))
      (MAYCHANGE [PC;X3] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
       MAYCHANGE [memory :> bytes(dst,val n)])`;;

let vp_memset_core_tac =
  REWRITE_TAC[C_ARGUMENTS; SOME_FLAGS] THEN
  MAP_EVERY X_GEN_TAC [`dst:int64`; `c:int64`] THEN
  W64_GEN_TAC `n:num` THEN X_GEN_TAC `pc:num` THEN DISCH_TAC THEN
  ASM_CASES_TAC `n = 0` THENL
   [ASM_REWRITE_TAC[LT; VAL_WORD_0] THEN ARM_SIM_TAC VP_MEMSET_EXEC (1--2);
    ALL_TAC] THEN
  ENSURES_WHILE_UP_TAC `n:num` `pc + 8` `pc + 16`
   `\i s. read X0 s = dst /\ read X1 s = c /\ read X2 s = word n /\
          read X3 s = word i /\
          (!j. j < i ==>
            read (memory :> bytes8 (word_add dst (word j))) s = word_zx c)` THEN
  ASM_REWRITE_TAC[] THEN REPEAT CONJ_TAC THENL
   [ARM_SIM_TAC VP_MEMSET_EXEC (1--2) THEN REWRITE_TAC[LT];
    X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
    ARM_SIM_TAC VP_MEMSET_EXEC (1--2) THEN
    REWRITE_TAC[GSYM WORD_ADD] THEN X_GEN_TAC `j:num` THEN
    REWRITE_TAC[ARITH_RULE `j < i + 1 <=> j < i \/ j = i`] THEN
    STRIP_TAC THENL [ASM_MESON_TAC[];
      ASM_REWRITE_TAC[] THEN CONV_TAC WORD_BLAST];
    X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
    ARM_SIM_TAC VP_MEMSET_EXEC (1--2);
    ARM_SIM_TAC VP_MEMSET_EXEC (1--2)];;

let VP_MEMSET_CORE_CORRECT = prove(vp_memset_core_spec,vp_memset_core_tac);;

let VP_MEMSET_CORRECT = prove(vp_fill_contract `vp_memset_mc`,
  REWRITE_TAC[fst VP_MEMSET_EXEC] THEN
  ARM_ADD_RETURN_NOSTACK_TAC VP_MEMSET_EXEC VP_MEMSET_CORE_CORRECT);;
