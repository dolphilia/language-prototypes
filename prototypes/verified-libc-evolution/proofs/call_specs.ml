(* The caller owns only a private 16-byte stack frame. Physical mapping and
   lifetime of this frame and ordinary RAM remain external contracts. *)
let ve_call_geometry = new_definition
 `ve_call_geometry (code:byte list) pc (sp:int64) dst src (n:int64) <=>
    ~(dst = word 0) /\ ~(src = word 0) /\
    val dst + val n <= 2 EXP 64 /\ val src + val n <= 2 EXP 64 /\
    nonoverlapping (src,val n) (dst,val n) /\
    aligned 16 sp /\ 16 <= val sp /\
    nonoverlapping (word pc,LENGTH code) (dst,val n) /\
    nonoverlapping (word pc,LENGTH code) (word_sub sp (word 16),16) /\
    nonoverlapping (word_sub sp (word 16),16) (src,val n) /\
    nonoverlapping (word_sub sp (word 16),16) (dst,val n)`;;

let ve_call_frame =
 `MAYCHANGE [PC;X3;X4;SP;X30] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
  MAYCHANGE [memory :> bytes(dst,val(n:int64));
             memory :> bytes(word_sub sp (word 16),16)]`;;

let ve_call_contract code entry = vsubst [code,`code:byte list`;mk_small_numeral entry,`entry:num`]
 `!dst src n pc sp returnaddress (input:num->byte).
    ve_call_geometry code pc sp dst src n
    ==> ensures arm
      (\s. aligned_bytes_loaded s (word pc) code /\
           read PC s = word(pc+entry) /\ read SP s = sp /\
           read X30 s = returnaddress /\ C_ARGUMENTS [dst;src;n] s /\
           (!i. i < val n ==>
              read (memory :> bytes8 (word_add src (word i))) s = input i))
      (\s. read PC s = returnaddress /\ read X0 s = dst /\
           read SP s = sp /\ read X30 s = returnaddress /\
           (!i. i < val n ==>
              read (memory :> bytes8 (word_add dst (word i))) s = input i))
      (MAYCHANGE [PC;X3;X4;SP;X30] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
       MAYCHANGE [memory :> bytes(dst,val n);
                  memory :> bytes(word_sub sp (word 16),16)])`;;

let ve_call_access_contract code entry = vsubst [code,`code:byte list`;mk_small_numeral entry,`entry:num`]
 `!dst src n pc sp returnaddress e.
    ve_call_geometry code pc sp dst src n
    ==> ensures arm
      (\s. aligned_bytes_loaded s (word pc) code /\
           read PC s = word(pc+entry) /\ read SP s = sp /\
           read X30 s = returnaddress /\ C_ARGUMENTS [dst;src;n] s /\ read events s = e)
      (\s. read PC s = returnaddress /\ read X0 s = dst /\
           read SP s = sp /\ read X30 s = returnaddress /\
           ?trace. read events s = APPEND trace e /\
             memaccess_inbounds trace [src,val n;word_sub sp (word 16),16]
                                     [dst,val n;word_sub sp (word 16),16])
      (MAYCHANGE [PC;X3;X4;SP;X30] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
       MAYCHANGE [memory :> bytes(dst,val n);
                  memory :> bytes(word_sub sp (word 16),16)])`;;
