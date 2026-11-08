(* Total model state with disjoint code, destination, source and return target.
   Physical mappings/permissions remain the public external RAM contract. *)
let ve_initial = new_definition
 `ve_initial (code:byte list) n =
   armstate_RECORD (word 4096)
    (\r:5 word. if r = word 0 then word 8192
       else if r = word 1 then word 12288
       else if r = word 2 then word n
       else if r = word 19 then word 19
       else if r = word 30 then word 16384
       else if r = word 31 then word 32768 else word 0)
    (\r:5 word. word 0:int128) (word 0:4 word)
    (\a:int64. if 4096 <= val a /\ val a < 4096 + LENGTH code
              then EL (val a - 4096) code
              else if 12288 <= val a /\ val a < 12352 then word 85
              else if 8192 <= val a /\ val a < 8256 then word 170
              else word 0) []`;;

let ve_pre code n pc = vsubst [code,`code:byte list`;n,`n:num`;pc,`pc:num`]
 `\s. aligned_bytes_loaded s (word pc) code /\
       read PC s = word pc /\ read X30 s = word 16384 /\
       C_ARGUMENTS [word 8192;word 12288;word n] s /\
       read X19 s = word 19 /\ read events s = [] /\
       (!i. i < n ==>
        read (memory :> bytes8 (word_add (word 12288) (word i))) s = word 85)`;;

let ve_initial_pre code n = ve_pre code n `4096`;;

let ve_reduce_state_tac =
  REWRITE_TAC[ve_initial;C_ARGUMENTS;X0;X1;X2;X3;X19;X30;XREG] THEN
  CONV_TAC NUM_REDUCE_CONV THEN
  REWRITE_TAC[BYTES8_ELEMENT;READ_COMPONENT_COMPOSE;armstate_COMPONENTS;
              READ_ELEMENT;LENGTH] THEN
  CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN
  CONV_TAC NUM_REDUCE_CONV THEN REWRITE_TAC[];;

let ve_witness_tac definition =
  REWRITE_TAC[definition;aligned_bytes_loaded;bytes_loaded;LENGTH] THEN
  CONV_TAC NUM_REDUCE_CONV THEN
  CONV_TAC(DEPTH_CONV BYTELIST_EXPAND_CONV) THEN
  CONV_TAC(DEPTH_CONV EXPAND_CASES_CONV) THEN
  ve_reduce_state_tac THEN
  CONV_TAC(DEPTH_CONV EL_CONV) THEN
  CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN
  CONV_TAC NUM_REDUCE_CONV THEN CONV_TAC DIVIDES_CONV;;

(* Reduce each bounded existential before combining outer conjunctions; global
   distributivity would unnecessarily expand all combinations of witnesses. *)
let ve_range_cases = [ARITH_RULE `j < 0 <=> F`;
    ARITH_RULE `j < 1 <=> j = 0`;
    ARITH_RULE `j < 4 <=> j = 0 \/ j = 1 \/ j = 2 \/ j = 3`;
    ARITH_RULE `j < 8 <=> j = 0 \/ j = 1 \/ j = 2 \/ j = 3 \/
                           j = 4 \/ j = 5 \/ j = 6 \/ j = 7`];;
let ve_range_exists_conv tm =
 if not(is_exists tm) then failwith "not a bounded existential" else
 let th=(REWRITE_CONV(ve_range_cases @
    [RIGHT_OR_DISTRIB;EXISTS_OR_THM;UNWIND_THM2;CONG])
    THENC NUM_REDUCE_CONV) tm in
 if aconv (lhs(concl th)) (rhs(concl th)) then failwith "unchanged" else th;;

let ve_bad_access_tac =
  REWRITE_TAC[memaccess_inbounds;ALL;EX] THEN
  CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN
  REWRITE_TAC[contained_modulo] THEN
  CONV_TAC(DEPTH_CONV EXPAND_CASES_CONV) THEN
  CONV_TAC(DEPTH_CONV ve_range_exists_conv) THEN CONV_TAC NUM_REDUCE_CONV;;

let ve_numeric_pre code n = vsubst [code,`code:byte list`;n,`n:num`]
 `~((word 8192:int64) = word 0) /\ ~((word 12288:int64) = word 0) /\
  val(word 8192:int64) + val(word n:int64) <= 2 EXP 64 /\
  val(word 12288:int64) + val(word n:int64) <= 2 EXP 64 /\
  nonoverlapping (word 4096:int64,LENGTH(code:byte list)) (word 8192,val(word n:int64)) /\
  nonoverlapping (word 12288:int64,val(word n:int64)) (word 8192,val(word n:int64))`;;

let ve_numeric_tac definitions =
  REWRITE_TAC (definitions @ [LENGTH;NONOVERLAPPING_CLAUSES]) THEN
  CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN
  CONV_TAC NUM_REDUCE_CONV THEN
  REPEAT CONJ_TAC THEN
  MATCH_MP_TAC NONOVERLAPPING_MODULO_SIMPLE THEN CONV_TAC NUM_REDUCE_CONV;;

(* Explicitly instantiate a proved finite execution at a proved loaded state.
   No failed proof tactic is used as a counterexample. *)
let ve_execution prefix side witness =
  let all_states = REWRITE_RULE[ensures_n] (MP (SPEC `4096` prefix) side) in
  REWRITE_RULE[] (MP (SPEC ((rand o concl) witness) all_states) (BETA_RULE witness));;
