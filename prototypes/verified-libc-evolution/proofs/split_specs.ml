(* Arbitrary size_t values are accepted; the guard is deliberately absent
   from the public precondition. Root ownership and stack validity are roots. *)
let ve_split_geometry = new_definition
 `ve_split_geometry (code:byte list) pc (sp:int64) arena (capacity:int64) <=>
    ve_root_geometry arena (val capacity) pc (LENGTH code) /\
    aligned 16 sp /\ 16 <= val sp /\
    nonoverlapping (word pc,LENGTH code) (word_sub sp (word 16),16) /\
    nonoverlapping (word_sub sp (word 16),16) (arena,val capacity)`;;

let ve_split_call_contract code entry =
 vsubst [code,`code:byte list`;mk_small_numeral entry,`entry:num`]
 `!arena capacity split n pc sp returnaddress (initial:num->byte).
    ve_split_geometry code pc sp arena capacity
    ==> ensures arm
     (\s. aligned_bytes_loaded s (word pc) code /\
          read PC s = word(pc+entry) /\ read SP s = sp /\ read X30 s = returnaddress /\
          C_ARGUMENTS [arena;capacity;split;n] s /\
          (!i. i < val capacity ==>
            read (memory :> bytes8 (word_add arena (word i))) s = initial i))
     (\s. read PC s = returnaddress /\ read SP s = sp /\ read X30 s = returnaddress /\
          read X0 s = word(if ve_split_guard (val capacity) (val split) (val n) then 0 else 1) /\
          (if ve_split_guard (val capacity) (val split) (val n)
           then !i. i < val n ==>
             read (memory :> bytes8 (word_add (word_add arena split) (word i))) s = initial i
           else !i. i < val capacity ==>
             read (memory :> bytes8 (word_add arena (word i))) s = initial i))
     (MAYCHANGE [PC;X0;X1;X2;X3;X4;SP;X30] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
      MAYCHANGE [memory :> bytes(word_add arena split,
             if ve_split_guard (val capacity) (val split) (val n) then val n else 0);
                 memory :> bytes(word_sub sp (word 16),16)])`;;

let ve_split_access_contract code entry =
 vsubst [code,`code:byte list`;mk_small_numeral entry,`entry:num`]
 `!arena capacity split n pc sp returnaddress e.
    ve_split_geometry code pc sp arena capacity
    ==> ensures arm
     (\s. aligned_bytes_loaded s (word pc) code /\
          read PC s = word(pc+entry) /\ read SP s = sp /\ read X30 s = returnaddress /\
          C_ARGUMENTS [arena;capacity;split;n] s /\ read events s = e)
     (\s. read PC s = returnaddress /\ read SP s = sp /\ read X30 s = returnaddress /\
          read X0 s = word(if ve_split_guard (val capacity) (val split) (val n) then 0 else 1) /\
          ?trace. read events s = APPEND trace e /\
           (if ve_split_guard (val capacity) (val split) (val n)
            then memaccess_inbounds trace [arena,val capacity;word_sub sp (word 16),16]
                                          [arena,val capacity;word_sub sp (word 16),16]
            else memaccess_inbounds trace [] []))
     (MAYCHANGE [PC;X0;X1;X2;X3;X4;SP;X30] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
      MAYCHANGE [memory :> bytes(word_add arena split,
             if ve_split_guard (val capacity) (val split) (val n) then val n else 0);
                 memory :> bytes(word_sub sp (word 16),16)])`;;

let ve_split_require_guard spec =
 let vars,body=strip_forall spec in let pre,goal=dest_imp body in
 list_mk_forall(vars,mk_imp(mk_conj(pre,
   `ve_split_guard (val(capacity:int64)) (val(split:int64)) (val(n:int64))`),goal));;
