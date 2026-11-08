needs "arm/proofs/base.ml";;

let vp_macro_copybyte_mc = define_assert_from_elf "vp_macro_copybyte_mc"
  (Sys.getenv "VP_ROOT" ^ "/build/vp_macro_copybyte.o")
  [0x39400024; 0x39000004; 0xd65f03c0];;
let VP_COPYBYTE_EXEC = ARM_MK_EXEC_RULE vp_macro_copybyte_mc;;

let VP_COPYBYTE_CORRECT = prove
 (`!dst src b pc e.
     nonoverlapping (word pc,12) (dst,1)
     ==> ensures arm
       (\s. aligned_bytes_loaded s (word pc) vp_macro_copybyte_mc /\
            read PC s = word pc /\ read X0 s = dst /\ read X1 s = src /\
            read (memory :> bytes8 src) s = b /\ read events s = e)
       (\s. read PC s = word (pc + 8) /\ read (memory :> bytes8 dst) s = b /\
            read events s = APPEND [EventStore(dst,1);EventLoad(src,1)] e)
       (MAYCHANGE [PC;X4] ,, MAYCHANGE [events] ,,
        MAYCHANGE [memory :> bytes(dst,1)])`,
  REPEAT STRIP_TAC THEN ARM_SIM_TAC VP_COPYBYTE_EXEC (1--2) THEN
  REWRITE_TAC[APPEND] THEN CONV_TAC WORD_BLAST);;

let vp_macro_fillbyte_mc = define_assert_from_elf "vp_macro_fillbyte_mc"
  (Sys.getenv "VP_ROOT" ^ "/build/vp_macro_fillbyte.o")
  [0x39000001; 0xd65f03c0];;
let VP_FILLBYTE_EXEC = ARM_MK_EXEC_RULE vp_macro_fillbyte_mc;;

let VP_FILLBYTE_CORRECT = prove
 (`!dst c pc e.
     nonoverlapping (word pc,8) (dst,1)
     ==> ensures arm
       (\s. aligned_bytes_loaded s (word pc) vp_macro_fillbyte_mc /\
            read PC s = word pc /\ read X0 s = dst /\ read X1 s = c /\
            read events s = e)
       (\s. read PC s = word (pc + 4) /\
            read (memory :> bytes8 dst) s = word_zx c /\
            read events s = APPEND [EventStore(dst,1)] e)
       (MAYCHANGE [PC] ,, MAYCHANGE [events] ,,
        MAYCHANGE [memory :> bytes(dst,1)])`,
  REPEAT STRIP_TAC THEN ARM_SIM_TAC VP_FILLBYTE_EXEC [1] THEN
  REWRITE_TAC[APPEND] THEN CONV_TAC WORD_BLAST);;

let vp_macro_copy8_mc = define_assert_from_elf "vp_macro_copy8_mc"
  (Sys.getenv "VP_ROOT" ^ "/build/vp_macro_copy8.o")
  [0xf9400024; 0xf9000004; 0xd65f03c0];;
let VP_COPY8_EXEC = ARM_MK_EXEC_RULE vp_macro_copy8_mc;;

let VP_COPY8_CORRECT = prove
 (`!dst src b pc e.
     nonoverlapping (word pc,12) (dst,8) /\ aligned 8 dst /\ aligned 8 src
     ==> ensures arm
       (\s. aligned_bytes_loaded s (word pc) vp_macro_copy8_mc /\
            read PC s = word pc /\ read X0 s = dst /\ read X1 s = src /\
            read (memory :> bytes64 src) s = b /\ read events s = e)
       (\s. read PC s = word (pc + 8) /\ read (memory :> bytes64 dst) s = b /\
            read events s = APPEND [EventStore(dst,8);EventLoad(src,8)] e)
       (MAYCHANGE [PC;X4] ,, MAYCHANGE [events] ,,
        MAYCHANGE [memory :> bytes(dst,8)])`,
  REPEAT STRIP_TAC THEN ARM_SIM_TAC VP_COPY8_EXEC (1--2) THEN REWRITE_TAC[APPEND]);;

(* A proved block carries the actual code definition and its derived theorem.
   Fixed register choices are intentional in this first prototype. *)
type vp_proved_block = { code : thm; correctness : thm };;
let vp_copy_byte = {code=vp_macro_copybyte_mc; correctness=VP_COPYBYTE_CORRECT};;
let vp_fill_byte = {code=vp_macro_fillbyte_mc; correctness=VP_FILLBYTE_CORRECT};;
let vp_copy8 = {code=vp_macro_copy8_mc; correctness=VP_COPY8_CORRECT};;

let vp_macro_copybyte_indexed_mc = define_assert_from_elf "vp_macro_copybyte_indexed_mc"
  (Sys.getenv "VP_ROOT" ^ "/build/vp_macro_copybyte_indexed.o")
  [0x38636824;0x38236804;0xd65f03c0];;
let VP_COPYBYTE_INDEXED_EXEC = ARM_MK_EXEC_RULE vp_macro_copybyte_indexed_mc;;
let VP_COPYBYTE_INDEXED_CORRECT = prove
 (`!dst src n i b pc e.
     i < n /\ n < 2 EXP 64 /\ nonoverlapping (word pc,12) (dst,n)
     ==> ensures arm
       (\s. aligned_bytes_loaded s (word pc) vp_macro_copybyte_indexed_mc /\
            read PC s = word pc /\ read X0 s = dst /\ read X1 s = src /\
            read X3 s = word i /\ read (memory :> bytes8 (word_add src (word i))) s = b /\
            read events s = e)
       (\s. read PC s = word(pc+8) /\
            read (memory :> bytes8 (word_add dst (word i))) s = b /\
            read events s = APPEND
              [EventStore(word_add dst (word i),1);EventLoad(word_add src (word i),1)] e)
       (MAYCHANGE [PC;X4] ,, MAYCHANGE [events] ,,
        MAYCHANGE [memory :> bytes(word_add dst (word i),1)])`,
  REPEAT STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN ARM_SIM_TAC VP_COPYBYTE_INDEXED_EXEC (1--2) THEN
  REWRITE_TAC[APPEND] THEN CONV_TAC WORD_BLAST);;

let vp_macro_fillbyte_indexed_mc = define_assert_from_elf "vp_macro_fillbyte_indexed_mc"
  (Sys.getenv "VP_ROOT" ^ "/build/vp_macro_fillbyte_indexed.o")
  [0x38236801;0xd65f03c0];;
let VP_FILLBYTE_INDEXED_EXEC = ARM_MK_EXEC_RULE vp_macro_fillbyte_indexed_mc;;
let VP_FILLBYTE_INDEXED_CORRECT = prove
 (`!dst c n i pc e.
     i < n /\ n < 2 EXP 64 /\ nonoverlapping (word pc,8) (dst,n)
     ==> ensures arm
       (\s. aligned_bytes_loaded s (word pc) vp_macro_fillbyte_indexed_mc /\
            read PC s = word pc /\ read X0 s = dst /\ read X1 s = c /\
            read X3 s = word i /\ read events s = e)
       (\s. read PC s = word(pc+4) /\
            read (memory :> bytes8 (word_add dst (word i))) s = word_zx c /\
            read events s = APPEND [EventStore(word_add dst (word i),1)] e)
       (MAYCHANGE [PC] ,, MAYCHANGE [events] ,,
        MAYCHANGE [memory :> bytes(word_add dst (word i),1)])`,
  REPEAT STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN ARM_SIM_TAC VP_FILLBYTE_INDEXED_EXEC [1] THEN
  REWRITE_TAC[APPEND] THEN CONV_TAC WORD_BLAST);;
let vp_copy_byte_indexed =
 {code=vp_macro_copybyte_indexed_mc;correctness=VP_COPYBYTE_INDEXED_CORRECT};;
let vp_fill_byte_indexed =
 {code=vp_macro_fillbyte_indexed_mc;correctness=VP_FILLBYTE_INDEXED_CORRECT};;
