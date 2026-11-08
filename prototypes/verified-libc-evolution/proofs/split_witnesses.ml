(* Loaded concrete states satisfy the original root/stack contract, even for
   inputs whose dynamic guard is false. No guard is added to that contract. *)
let ve_split_initial = new_definition
 `ve_split_initial (code:byte list) split n =
   armstate_RECORD (word 4096)
    (\r:5 word. if r = word 0 then word 8192
       else if r = word 1 then word 16
       else if r = word 2 then word split
       else if r = word 3 then word n
       else if r = word 19 then word 19
       else if r = word 30 then word 16384
       else if r = word 31 then word 32768 else word 0)
    (\r:5 word. word 0:int128) (word 0:4 word)
    (\a:int64. if 4096 <= val a /\ val a < 4096+LENGTH code
              then EL (val a-4096) code else word(val a MOD 256)) []`;;

let ve_split_witness_pre code split n pc =
 vsubst [code,`code:byte list`;mk_small_numeral split,`split:num`;
          mk_small_numeral n,`n:num`;pc,`pc:num`]
 `\s. aligned_bytes_loaded s (word pc) code /\
       read PC s = word pc /\ read SP s = word 32768 /\ read X30 s = word 16384 /\
       C_ARGUMENTS [word 8192;word 16;word split;word n] s /\ read events s = [] /\
       read (memory :> bytes8 (word 8192)) s = word 0 /\
       read (memory :> bytes8 (word 8200)) s = word 8 /\
       (!i. i < 16 ==> read (memory :> bytes8 (word_add (word 8192) (word i))) s = word i)`;;

let ve_split_witness_tac definition =
 REWRITE_TAC[definition;aligned_bytes_loaded;bytes_loaded;LENGTH] THEN
 CONV_TAC NUM_REDUCE_CONV THEN CONV_TAC(DEPTH_CONV BYTELIST_EXPAND_CONV) THEN
 CONV_TAC(DEPTH_CONV EXPAND_CASES_CONV) THEN
 REWRITE_TAC[ve_split_initial;C_ARGUMENTS;X0;X1;X2;X3;X30;SP;XREG] THEN
 CONV_TAC NUM_REDUCE_CONV THEN
 REWRITE_TAC[BYTES8_ELEMENT;READ_COMPONENT_COMPOSE;armstate_COMPONENTS;READ_ELEMENT;LENGTH] THEN
 CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN CONV_TAC NUM_REDUCE_CONV THEN
 REWRITE_TAC[READ_COMPONENT_COMPOSE;armstate_COMPONENTS;READ_ELEMENT] THEN
 CONV_TAC(DEPTH_CONV EL_CONV) THEN CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN
 CONV_TAC NUM_REDUCE_CONV THEN REWRITE_TAC[] THEN CONV_TAC DIVIDES_CONV;;

let ve_split_numeric_tac definition =
 REWRITE_TAC[ve_split_geometry;ve_root_geometry;definition;LENGTH;NONOVERLAPPING_CLAUSES;aligned] THEN
 CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN CONV_TAC NUM_REDUCE_CONV THEN
 CONV_TAC(DEPTH_CONV DIVIDES_CONV) THEN REWRITE_TAC[] THEN REPEAT CONJ_TAC THEN
 MATCH_MP_TAC NONOVERLAPPING_MODULO_SIMPLE THEN CONV_TAC NUM_REDUCE_CONV;;

let ve_split_expand_exists_conv =
 let dual = prove
  (`!k (P:num->bool). (?j. j < k /\ P j) <=> ~(!j. j < k ==> ~P j)`,
   REWRITE_TAC[NOT_FORALL_THM;NOT_IMP]) in
 GEN_REWRITE_CONV I [dual] THENC RAND_CONV EXPAND_CASES_CONV THENC NUM_REDUCE_CONV;;
let ve_split_finish_numeric =
 CONV_TAC(DEPTH_CONV ve_split_expand_exists_conv) THEN CONV_TAC NUM_REDUCE_CONV;;
