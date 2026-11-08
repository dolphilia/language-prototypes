(* Resource specifications are independent of the instruction generator.
   Counts concern model steps and data bytes, not wall-clock cycles. *)
let ve_event_read = new_recursive_definition uarch_event_RECURSION
 `(ve_event_read (EventLoad load_pair) = SND load_pair) /\
  (ve_event_read (EventStore store_pair) = 0) /\
  (ve_event_read (EventJump jump_pair) = 0) /\
  (ve_event_read (EventX86PEXT pext_tuple) = 0) /\
  (ve_event_read (EventX86POPCNT popcnt_pair) = 0)`;;
let ve_event_write = new_recursive_definition uarch_event_RECURSION
 `(ve_event_write (EventLoad load_pair) = 0) /\
  (ve_event_write (EventStore store_pair) = SND store_pair) /\
  (ve_event_write (EventJump jump_pair) = 0) /\
  (ve_event_write (EventX86PEXT pext_tuple) = 0) /\
  (ve_event_write (EventX86POPCNT popcnt_pair) = 0)`;;
let ve_read_bytes = new_recursive_definition list_RECURSION
 `(ve_read_bytes [] = 0) /\
  (ve_read_bytes (CONS (h:uarch_event) t) = ve_event_read h + ve_read_bytes t)`;;
let ve_write_bytes = new_recursive_definition list_RECURSION
 `(ve_write_bytes [] = 0) /\
  (ve_write_bytes (CONS (h:uarch_event) t) = ve_event_write h + ve_write_bytes t)`;;
let VE_BYTE_COUNTS_APPEND = prove
 (`!(a:uarch_event list) b.
   ve_read_bytes(APPEND a b) = ve_read_bytes a + ve_read_bytes b /\
   ve_write_bytes(APPEND a b) = ve_write_bytes a + ve_write_bytes b`,
  LIST_INDUCT_TAC THEN ASM_REWRITE_TAC[APPEND;ve_read_bytes;ve_write_bytes;ADD_CLAUSES;ADD_ASSOC]);;
let ve_count_rewrites = [ve_read_bytes;ve_write_bytes;ve_event_read;ve_event_write;SND;ADD_CLAUSES;ADD_ASSOC];;

let ve_resource_contract code count fill =
 let template =
 `!dst src n pc returnaddress e.
   ~(dst = word 0) /\ ~(src = word 0) /\
   val dst + val n <= 2 EXP 64 /\ val src + val n <= 2 EXP 64 /\
   nonoverlapping (word pc,LENGTH code) (dst,val n) /\
   nonoverlapping (src,val n) (dst,val n)
   ==> ensures_n arm
    (\s. aligned_bytes_loaded s (word pc) code /\ read PC s = word pc /\
         read X30 s = returnaddress /\ read X0 s = dst /\ read X1 s = src /\ read X2 s = n /\
         read events s = e)
    (\s. read PC s = returnaddress /\ read X0 s = dst /\
         ve_read_bytes(read events s) = ve_read_bytes e + reads /\
         ve_write_bytes(read events s) = ve_write_bytes e + val n)
    (MAYCHANGE [PC;X3;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
     MAYCHANGE [memory :> bytes(dst,val n)]) (\s:armstate. cost)` in
 let vars,body=strip_forall template in
 let term=list_mk_forall(vars,vsubst [code,`code:byte list`;count,`cost:num`;
   (if fill then `0` else `val(n:int64)`),`reads:num`] body) in
 if not fill then term else
 let vs,body=strip_forall term in
 let _,goal=dest_imp body in
 list_mk_forall(vs,mk_imp(vsubst [code,`code:byte list`]
  `~((dst:int64) = word 0) /\ val dst + val(n:int64) <= 2 EXP 64 /\
    nonoverlapping (word pc:int64,LENGTH(code:byte list)) (dst,val(n:int64))`,goal));;

let ve_open_cost_trace = FIRST_X_ASSUM
 (X_CHOOSE_THEN `trace:uarch_event list` STRIP_ASSUME_TAC o check (is_exists o concl));;

let ve_scalar_cost_tac exec fill =
 REWRITE_TAC[SOME_FLAGS;fst exec] THEN
 MAP_EVERY X_GEN_TAC [`dst:int64`;`src:int64`] THEN W64_GEN_TAC `n:num` THEN
 MAP_EVERY X_GEN_TAC [`pc:num`;`returnaddress:int64`;`e:uarch_event list`] THEN STRIP_TAC THEN
 ASM_CASES_TAC `n = 0` THENL
 [ASM_REWRITE_TAC[] THEN CONV_TAC NUM_REDUCE_CONV THEN ARM_SIM_TAC exec (1--3) THEN
  ASM_REWRITE_TAC ve_count_rewrites;
  ALL_TAC] THEN
 ENSURES_N_WHILE_UP_TAC `n:num` `pc+8` (if fill then `pc+16` else `pc+20`)
 (if fill then
  `\i s. read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
    read X30 s = returnaddress /\ read X3 s = word i /\
    (?trace. read events s = trace /\ ve_read_bytes trace = ve_read_bytes e /\ ve_write_bytes trace = ve_write_bytes e+i)`
  else
  `\i s. read X0 s = dst /\ read X1 s = src /\ read X2 s = word n /\
    read X30 s = returnaddress /\ read X3 s = word i /\
    (?trace. read events s = trace /\ ve_read_bytes trace = ve_read_bytes e+i /\ ve_write_bytes trace = ve_write_bytes e+i)`)
 (if fill then `\i:num. 2` else `\i:num. 3`) `2` `2` `3` THEN
 ASM_REWRITE_TAC[] THEN REPEAT CONJ_TAC THENL
 [ARM_SIM_TAC exec (1--2) THEN TRY(EXISTS_TAC `read events s2`) THEN ASM_REWRITE_TAC ve_count_rewrites;
  X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
  ARM_SIM_TAC ~preprocess_tac:ve_open_cost_trace exec (1--(if fill then 2 else 3)) THEN REWRITE_TAC[GSYM WORD_ADD] THEN
  TRY(EXISTS_TAC (if fill then `read events s2` else `read events s3`)) THEN
  ASM_REWRITE_TAC ve_count_rewrites THEN ARITH_TAC;
  X_GEN_TAC `i:num` THEN STRIP_TAC THEN VAL_INT64_TAC `i:num` THEN
  ARM_SIM_TAC ~preprocess_tac:ve_open_cost_trace exec (1--2) THEN TRY(EXISTS_TAC `read events s2`) THEN ASM_REWRITE_TAC ve_count_rewrites;
  ARM_SIM_TAC ~preprocess_tac:ve_open_cost_trace exec (1--3) THEN ASM_REWRITE_TAC ve_count_rewrites;
  ASM_SIMP_TAC[NSUM_CONST_NUMSEG;ARITH_RULE `~(n=0) ==> (n-1)+1=n`] THEN ASM_ARITH_TAC];;
