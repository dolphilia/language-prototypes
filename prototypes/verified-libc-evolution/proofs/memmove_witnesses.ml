(* A total, non-constant initial RAM image distinguishes overlapping bytes.
   This is a model state, not a claim that these addresses are OS mappings. *)
let ve_move_initial = new_definition
 `ve_move_initial (code:byte list) dst src n =
   armstate_RECORD (word 4096)
    (\r:5 word. if r = word 0 then word dst
       else if r = word 1 then word src
       else if r = word 2 then word n
       else if r = word 30 then word 16384
       else if r = word 31 then word 32768 else word 0)
    (\r:5 word. word 0:int128) (word 0:4 word)
    (\a:int64. if 4096 <= val a /\ val a < 4096 + LENGTH code
              then EL (val a - 4096) code else word(val a MOD 256)) []`;;

let ve_move_witness_tac definition =
 REWRITE_TAC[definition;aligned_bytes_loaded;bytes_loaded;LENGTH] THEN
 CONV_TAC NUM_REDUCE_CONV THEN CONV_TAC(DEPTH_CONV BYTELIST_EXPAND_CONV) THEN
 CONV_TAC(DEPTH_CONV EXPAND_CASES_CONV) THEN
 REWRITE_TAC[ve_move_initial;C_ARGUMENTS;X0;X1;X2;X30;XREG] THEN
 CONV_TAC NUM_REDUCE_CONV THEN
 REWRITE_TAC[BYTES8_ELEMENT;READ_COMPONENT_COMPOSE;armstate_COMPONENTS;READ_ELEMENT;LENGTH] THEN
 CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN CONV_TAC NUM_REDUCE_CONV THEN
 REWRITE_TAC[READ_COMPONENT_COMPOSE;armstate_COMPONENTS;READ_ELEMENT] THEN
 CONV_TAC(DEPTH_CONV EL_CONV) THEN CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN
 CONV_TAC NUM_REDUCE_CONV THEN REWRITE_TAC[] THEN CONV_TAC DIVIDES_CONV;;
