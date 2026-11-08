needs "arm/proofs/base.ml";;
loadt (Sys.getenv "VP_ROOT" ^ "/proofs/specs.ml");;

let vp2_memcpy_chunk8_mc = define_assert_from_elf "vp2_memcpy_chunk8_mc"
 (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/build/vp2_memcpy_chunk8.o")
 [0xd2800003;0xaa010004;0xf240089f;0x54000101;
  0xcb030044;0xf100209f;0x540000a3;0xf8636824;0xf8236804;
  0x91002063;0x17fffffa;0xeb02007f;0x540000c2;
  0x38636824;0x38236804;0x91000463;0xeb02007f;0x54ffff83;0xd65f03c0];;
let VP2_MEMCPY_CHUNK8_EXEC = ARM_MK_EXEC_RULE vp2_memcpy_chunk8_mc;;
let VE_ALIGNED1 = prove(`!x:int64. aligned 1 x`,REWRITE_TAC[aligned;DIVIDES_1]);;

(* General starting index: both the unaligned path (a=0) and the aligned
   remainder (a=8*(n DIV 8)) use this theorem. *)
let ve_chunk_tail_spec =
 `!dst src n a pc returnaddress (input:num->byte).
   a <= n /\ n < 2 EXP 64 /\
   nonoverlapping (word pc,76) (dst,n) /\
   nonoverlapping (src,n) (dst,n)
   ==> ensures arm
    (\s. aligned_bytes_loaded s (word pc) vp2_memcpy_chunk8_mc /\
         read PC s = word(pc+44) /\ read X30 s = returnaddress /\
         read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
         read X3 s = word a /\
         (!j. j < n ==> read (memory :> bytes8 (word_add src (word j))) s = input j) /\
         (!j. j < a ==> read (memory :> bytes8 (word_add dst (word j))) s = input j))
    (\s. read PC s = returnaddress /\ read X0 s = dst /\
         (!j. j < n ==> read (memory :> bytes8 (word_add dst (word j))) s = input j))
    (MAYCHANGE [PC;X3;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
     MAYCHANGE [memory :> bytes(dst,n)])`;;

let ve_chunk_tail_tac =
 REWRITE_TAC[SOME_FLAGS] THEN REPEAT GEN_TAC THEN STRIP_TAC THEN
 VAL_INT64_TAC `n:num` THEN
 ASM_CASES_TAC `a:num = n` THENL
 [ASM_REWRITE_TAC[] THEN ARM_SIM_TAC VP2_MEMCPY_CHUNK8_EXEC (1--3);ALL_TAC] THEN
 SUBGOAL_THEN `a < n /\ ~(n <= a)` STRIP_ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
 ENSURES_WHILE_AUP_TAC `a:num` `n:num` `pc+52` `pc+64`
 `\i s. read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
        read X30 s = returnaddress /\ read X3 s = word i /\
        (!j. j < n ==> read (memory :> bytes8 (word_add src (word j))) s = input j) /\
        (!j. j < i ==> read (memory :> bytes8 (word_add dst (word j))) s = input j)` THEN
 ASM_REWRITE_TAC[] THEN REPEAT CONJ_TAC THENL
 [SUBGOAL_THEN `a < 2 EXP 64` ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  VAL_INT64_TAC `a:num` THEN ARM_SIM_TAC VP2_MEMCPY_CHUNK8_EXEC (1--2);
  X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
  SUBGOAL_THEN `i+1 <= n` ASSUME_TAC THENL [ASM_ARITH_TAC;ALL_TAC] THEN
  ENSURES_INIT_TAC "s0" THEN
  SUBGOAL_THEN `read (memory :> bytes8 (word_add src (word i))) s0 = input i`
   ASSUME_TAC THENL [ASM_MESON_TAC[];ALL_TAC] THEN
  ARM_SUBROUTINE_SIM_TAC
   (vp2_memcpy_chunk8_mc,VP2_MEMCPY_CHUNK8_EXEC,52,
    vp2_block_copybyte_indexed_mc,REWRITE_RULE[VE_ALIGNED1] VP2_BLOCK_COPYBYTE_INDEXED_CORRECT)
   [`input(i:num):byte`;`dst:int64`;`src:int64`;`n:num`;`i:num`;
    `pc+52`;`read events s`] 1 THEN
  ARM_STEPS_TAC VP2_MEMCPY_CHUNK8_EXEC [2] THEN
  ENSURES_FINAL_STATE_TAC THEN ASM_REWRITE_TAC[] THEN
  REWRITE_TAC[GSYM WORD_ADD] THEN X_GEN_TAC `j:num` THEN
  REWRITE_TAC[ARITH_RULE `j < i+1 <=> j < i \/ j=i`] THEN
  STRIP_TAC THENL [ASM_MESON_TAC[];ASM_REWRITE_TAC[]];
  X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
  ARM_SIM_TAC VP2_MEMCPY_CHUNK8_EXEC (1--2);
  ARM_SIM_TAC VP2_MEMCPY_CHUNK8_EXEC (1--3)];;

let VE_CHUNK_TAIL = prove(ve_chunk_tail_spec,ve_chunk_tail_tac);;
ve_check "chunk8:tail" ve_chunk_tail_spec VE_CHUNK_TAIL;;
