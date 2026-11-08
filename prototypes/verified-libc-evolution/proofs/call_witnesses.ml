(* An explicit total state. No claim of OS mapping at these model addresses. *)
let ve_call_initial = new_definition
 `ve_call_initial (code:byte list) entry =
   armstate_RECORD (word(4096+entry))
    (\r:5 word. if r = word 0 then word 8192
       else if r = word 1 then word 12288
       else if r = word 2 then word 0
       else if r = word 19 then word 19
       else if r = word 30 then word 16384
       else if r = word 31 then word 32768 else word 0)
    (\r:5 word. word 0:int128) (word 0:4 word)
    (\a:int64. if 4096 <= val a /\ val a < 4096 + LENGTH code
              then EL (val a - 4096) code else word 0) []`;;

let ve_call_pre code entry pc =
 vsubst [code,`code:byte list`;mk_small_numeral entry,`entry:num`;pc,`pc:num`]
 `\s. aligned_bytes_loaded s (word pc) code /\
       read PC s = word(pc+entry) /\ read X30 s = word 16384 /\
       read SP s = word 32768 /\ C_ARGUMENTS [word 8192;word 12288;word 0] s /\
       read X19 s = word 19 /\ read events s = []`;;

let ve_call_witness_tac definition =
 REWRITE_TAC[definition;aligned_bytes_loaded;bytes_loaded;LENGTH] THEN
 CONV_TAC NUM_REDUCE_CONV THEN CONV_TAC(DEPTH_CONV BYTELIST_EXPAND_CONV) THEN
 CONV_TAC(DEPTH_CONV EXPAND_CASES_CONV) THEN
 REWRITE_TAC[ve_call_initial;C_ARGUMENTS;X0;X1;X2;X19;X30;SP;XREG] THEN
 CONV_TAC NUM_REDUCE_CONV THEN
 REWRITE_TAC[BYTES8_ELEMENT;READ_COMPONENT_COMPOSE;armstate_COMPONENTS;READ_ELEMENT;LENGTH] THEN
 CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN CONV_TAC NUM_REDUCE_CONV THEN
 REWRITE_TAC[READ_COMPONENT_COMPOSE;armstate_COMPONENTS;READ_ELEMENT] THEN
 CONV_TAC(DEPTH_CONV EL_CONV) THEN CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN
 CONV_TAC NUM_REDUCE_CONV THEN REWRITE_TAC[] THEN CONV_TAC DIVIDES_CONV;;

let ve_call_numeric_tac definition =
 REWRITE_TAC[ve_call_geometry;definition;LENGTH;NONOVERLAPPING_CLAUSES;aligned] THEN
 CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN CONV_TAC NUM_REDUCE_CONV THEN
 CONV_TAC(DEPTH_CONV DIVIDES_CONV) THEN REWRITE_TAC[] THEN REPEAT CONJ_TAC THEN
 MATCH_MP_TAC NONOVERLAPPING_MODULO_SIMPLE THEN CONV_TAC NUM_REDUCE_CONV;;

let ve_call_finish_numeric =
 REWRITE_TAC[DE_MORGAN_THM;NOT_EXISTS_THM;TAUT `~a \/ b <=> a ==> b`] THEN
 CONV_TAC(DEPTH_CONV EXPAND_CASES_CONV) THEN
 CONV_TAC NUM_REDUCE_CONV;;
