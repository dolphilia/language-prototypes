(* Abstract calls: the M1 theorem is reused after deriving its antecedent.
   No BL instruction, stack, or runtime guard path is claimed here. *)
let ve_region_copy_spec =
 `!arena capacity split length pc returnaddress (input:num->byte).
    ve_root_geometry arena capacity pc (LENGTH vp2_memcpy_chunk8_mc) /\
    ve_split_guard capacity split length
    ==> ensures arm
     (\s. aligned_bytes_loaded s (word pc) vp2_memcpy_chunk8_mc /\
          read PC s = word pc /\ read X30 s = returnaddress /\
          C_ARGUMENTS [word_add arena (word split);arena;word length] s /\
          (!i. i < length ==> read (memory :> bytes8 (word_add arena (word i))) s = input i))
     (\s. read PC s = returnaddress /\ read X0 s = word_add arena (word split) /\
          (!i. i < length ==>
           read (memory :> bytes8 (word_add (word_add arena (word split)) (word i))) s = input i))
     (MAYCHANGE [PC;X3;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
      MAYCHANGE [memory :> bytes(word_add arena (word split),length)])`;;
let VE_REGION_COPY = prove(ve_region_copy_spec,
  REPEAT GEN_TAC THEN STRIP_TAC THEN
  MP_TAC(SPECL [`arena:int64`;`capacity:num`;`split:num`;`length:num`;`pc:num`;
                `LENGTH vp2_memcpy_chunk8_mc`] VE_SPLIT_DERIVE) THEN
  ASM_REWRITE_TAC[] THEN STRIP_TAC THEN
  SUBGOAL_THEN `val(word length:int64) = length` ASSUME_TAC THENL
   [ASM_SIMP_TAC[VAL_WORD;DIMINDEX_64;MOD_LT];ALL_TAC] THEN
  MP_TAC(SPECL [`word_add arena (word split):int64`;`arena:int64`;`word length:int64`;
                `pc:num`;`returnaddress:int64`;`input:num->byte`] VP2_MEMCPY_CHUNK8_CORRECT) THEN
  ASM_REWRITE_TAC[] THEN DISCH_THEN MATCH_MP_TAC THEN
  ASM_MESON_TAC[ve_root_geometry]);;
ve_check "regions:abstract-copy" ve_region_copy_spec VE_REGION_COPY;;

let ve_region_copy_access_spec =
 `!arena capacity split length pc returnaddress e.
    ve_root_geometry arena capacity pc (LENGTH vp2_memcpy_chunk8_mc) /\
    ve_split_guard capacity split length
    ==> ensures arm
     (\s. aligned_bytes_loaded s (word pc) vp2_memcpy_chunk8_mc /\
          read PC s = word pc /\ read X30 s = returnaddress /\
          C_ARGUMENTS [word_add arena (word split);arena;word length] s /\ read events s = e)
     (\s. read PC s = returnaddress /\
          ?trace. read events s = APPEND trace e /\
            memaccess_inbounds trace [arena,length] [word_add arena (word split),length])
     (\s:armstate t:armstate. T)`;;
let VE_REGION_COPY_ACCESS = prove(ve_region_copy_access_spec,
  REPEAT GEN_TAC THEN STRIP_TAC THEN
  MP_TAC(SPECL [`arena:int64`;`capacity:num`;`split:num`;`length:num`;`pc:num`;
                `LENGTH vp2_memcpy_chunk8_mc`] VE_SPLIT_DERIVE) THEN
  ASM_REWRITE_TAC[] THEN STRIP_TAC THEN
  SUBGOAL_THEN `val(word length:int64) = length` ASSUME_TAC THENL
   [ASM_SIMP_TAC[VAL_WORD;DIMINDEX_64;MOD_LT];ALL_TAC] THEN
  MP_TAC(SPECL [`word_add arena (word split):int64`;`arena:int64`;`word length:int64`;
                `pc:num`;`returnaddress:int64`;`e:uarch_event list`] VP2_MEMCPY_CHUNK8_ACCESSES) THEN
  ASM_REWRITE_TAC[] THEN DISCH_THEN MATCH_MP_TAC THEN
  ASM_MESON_TAC[ve_root_geometry]);;
ve_check "regions:abstract-access" ve_region_copy_access_spec VE_REGION_COPY_ACCESS;;

(* One closed statement connects the same capacity/split/length to all ghost
   transitions and the machine-code contract. The external root binds owner
   to arena; a classical HOL theorem is not itself a linear ownership token. *)
let ve_region_protocol_spec =
 let vars,body=strip_forall ve_region_copy_spec in
 let pre,call=dest_imp body in
 let post spec = snd(dest_imp(snd(strip_forall spec))) in
 list_mk_forall([`owner:num`;`epoch:num`] @ vars,
   mk_imp(pre,list_mk_conj[post ve_split_borrows_spec;post ve_split_permissions_spec;
                         post ve_split_return_spec;call]));;
let VE_REGION_PROTOCOL = prove(ve_region_protocol_spec,
  REPEAT GEN_TAC THEN STRIP_TAC THEN CONJ_TAC THENL
  [MATCH_MP_TAC VE_SPLIT_BORROWS THEN ASM_REWRITE_TAC[];
   CONJ_TAC THENL
   [MATCH_MP_TAC VE_SPLIT_PERMISSIONS THEN ASM_REWRITE_TAC[];
    CONJ_TAC THENL
    [MATCH_MP_TAC VE_SPLIT_RETURN THEN ASM_REWRITE_TAC[];
     MATCH_MP_TAC(SPECL [`arena:int64`;`capacity:num`;`split:num`;`length:num`;
       `pc:num`;`returnaddress:int64`;`input:num->byte`] VE_REGION_COPY) THEN
     ASM_REWRITE_TAC[]]]]);;
ve_check "regions:abstract-protocol" ve_region_protocol_spec VE_REGION_PROTOCOL;;
