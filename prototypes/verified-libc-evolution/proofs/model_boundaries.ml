(* Satisfiable numeric instances at the address-space boundary. The public
   arbitrary-size theorems, rather than finite native tests, cover execution.
   No claim that these enormous regions can be mapped by the physical OS. *)
let ve_high_end_pre = subst
 [`word 18446744073709551608:int64`,`word 8192:int64`]
 (ve_numeric_pre `vp2_memcpy_chunk8_mc` `8`);;
let VE_HIGH_END_PRE = prove(ve_high_end_pre,ve_numeric_tac [vp2_memcpy_chunk8_mc]);;
ve_check "chunk8:numeric-high-end" ve_high_end_pre VE_HIGH_END_PRE;;

let ve_large_pre = subst
 [`word 9223372036854775808:int64`,`word 8192:int64`;
  `word 1:int64`,`word 12288:int64`]
 (ve_numeric_pre `vp2_memcpy_chunk8_mc` `9223372036854771712`);;
let VE_LARGE_PRE = prove(ve_large_pre,ve_numeric_tac [vp2_memcpy_chunk8_mc]);;
ve_check "chunk8:numeric-large" ve_large_pre VE_LARGE_PRE;;

let ve_wrap_rejected_spec =
 `~(val(word 18446744073709551612:int64)+val(word 8:int64) <= 2 EXP 64)`;;
let VE_WRAP_REJECTED = prove(ve_wrap_rejected_spec,
 CONV_TAC(DEPTH_CONV WORD_NUM_RED_CONV) THEN CONV_TAC NUM_REDUCE_CONV);;
ve_check "chunk8:wrap-outside-contract" ve_wrap_rejected_spec VE_WRAP_REJECTED;;
ve_check "chunk8:aligned-guard" ve_fast_guard_spec VE_FAST_GUARD;;
