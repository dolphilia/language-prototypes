(* Public contracts are independent of the generator. No additional axioms. *)
needs "arm/proofs/base.ml";;

let vp_copy_contract code = vsubst [code, `code:byte list`]
 `!dst src n pc returnaddress (input:num->byte).
    ~(dst = word 0) /\ ~(src = word 0) /\
    val dst + val n <= 2 EXP 64 /\ val src + val n <= 2 EXP 64 /\
    nonoverlapping (word pc,LENGTH code) (dst,val n) /\
    nonoverlapping (src,val n) (dst,val n)
    ==> ensures arm
      (\s. aligned_bytes_loaded s (word pc) code /\
           read PC s = word pc /\ read X30 s = returnaddress /\
           C_ARGUMENTS [dst;src;n] s /\
           (!i. i < val n ==>
             read (memory :> bytes8 (word_add src (word i))) s = input i))
      (\s. read PC s = returnaddress /\ read X0 s = dst /\
           (!i. i < val n ==>
             read (memory :> bytes8 (word_add dst (word i))) s = input i))
      (MAYCHANGE [PC;X3;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
       MAYCHANGE [memory :> bytes(dst,val n)])`;;

let vp_fill_contract code = vsubst [code, `code:byte list`]
 `!dst c n pc returnaddress.
    ~(dst = word 0) /\ val dst + val n <= 2 EXP 64 /\
    nonoverlapping (word pc,LENGTH code) (dst,val n)
    ==> ensures arm
      (\s. aligned_bytes_loaded s (word pc) code /\
           read PC s = word pc /\ read X30 s = returnaddress /\
           C_ARGUMENTS [dst;c;n] s)
      (\s. read PC s = returnaddress /\ read X0 s = dst /\
           (!i. i < val n ==>
             read (memory :> bytes8 (word_add dst (word i))) s = word_zx c))
      (MAYCHANGE [PC;X3] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
       MAYCHANGE [memory :> bytes(dst,val n)])`;;

let vp_copy_access_contract code = vsubst [code, `code:byte list`]
 `!dst src n pc returnaddress e.
    ~(dst = word 0) /\ ~(src = word 0) /\
    val dst + val n <= 2 EXP 64 /\ val src + val n <= 2 EXP 64 /\
    nonoverlapping (word pc,LENGTH code) (dst,val n) /\
    nonoverlapping (src,val n) (dst,val n)
    ==> ensures arm
      (\s. aligned_bytes_loaded s (word pc) code /\
           read PC s = word pc /\ read X30 s = returnaddress /\
           C_ARGUMENTS [dst;src;n] s /\ read events s = e)
      (\s. read PC s = returnaddress /\
           ?trace. read events s = APPEND trace e /\
             memaccess_inbounds trace [src,val n] [dst,val n])
      (\s s'. true)`;;

let vp_fill_access_contract code = vsubst [code, `code:byte list`]
 `!dst c n pc returnaddress e.
    ~(dst = word 0) /\ val dst + val n <= 2 EXP 64 /\
    nonoverlapping (word pc,LENGTH code) (dst,val n)
    ==> ensures arm
      (\s. aligned_bytes_loaded s (word pc) code /\
           read PC s = word pc /\ read X30 s = returnaddress /\
           C_ARGUMENTS [dst;c;n] s /\ read events s = e)
      (\s. read PC s = returnaddress /\
           ?trace. read events s = APPEND trace e /\
             memaccess_inbounds trace [] [dst,val n])
      (\s s'. true)`;;
