(* A concrete nonzero-length instance of the numeric public preconditions.
 * Native tests additionally construct mapped, disjoint data buffers. *)
let vp_contract_witness =
 `~((word 4096:int64) = word 0) /\ ~((word 8192:int64) = word 0) /\
  val(word 4096:int64) + 16 <= 2 EXP 64 /\
  val(word 8192:int64) + 16 <= 2 EXP 64 /\
  nonoverlapping (word 0:int64,64) (word 4096,16) /\
  nonoverlapping (word 8192:int64,16) (word 4096,16)`;;
let VP_CONTRACT_WITNESS = prove(vp_contract_witness,
  CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN CONV_TAC NUM_REDUCE_CONV THEN
  REPEAT CONJ_TAC THEN REWRITE_TAC[NONOVERLAPPING_CLAUSES] THEN
  CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN
  MATCH_MP_TAC NONOVERLAPPING_MODULO_SIMPLE THEN CONV_TAC NUM_REDUCE_CONV);;
