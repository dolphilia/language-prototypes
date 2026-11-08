(* RET-free instruction blocks. Public specifications do not come from the IR. *)
let ve_copy8_block_spec code offset scratch =
 vsubst [code,`code:byte list`;mk_small_numeral offset,`k:num`;
         scratch,`scratch:(armstate,int64)component`]
 `!dst src (b:int64) pc e.
   nonoverlapping (word pc,8) (word_add dst (word k),8) /\
   aligned 8 (word_add dst (word k)) /\ aligned 8 (word_add src (word k))
   ==> ensures arm
    (\s. aligned_bytes_loaded s (word pc) code /\ read PC s = word pc /\
         read X0 s = dst /\ read X1 s = src /\
         read (memory :> bytes64 (word_add src (word k))) s = b /\ read events s = e)
    (\s. read PC s = word(pc+8) /\
         read (memory :> bytes64 (word_add dst (word k))) s = b /\
         read events s = APPEND [EventStore(word_add dst (word k),8);
                                EventLoad(word_add src (word k),8)] e)
    (MAYCHANGE [PC;scratch] ,, MAYCHANGE [events] ,,
     MAYCHANGE [memory :> bytes(word_add dst (word k),8)])`;;

let ve_indexed_block_spec code width =
 let cell = if width=8 then `bytes64` else `bytes8` in
 let value_type = if width=8 then `:int64` else `:byte` in
 let b=mk_var("b",value_type) in
 let dst=mk_var("dst",`:int64`) and src=mk_var("src",`:int64`)
 and i=mk_var("i",`:num`) and s=mk_var("s",`:armstate`) in
 let address a = list_mk_comb(`word_add:int64->int64->int64`,[a;mk_comb(`word:num->int64`,i)]) in
 let read_cell a = list_mk_icomb "read" [list_mk_icomb ":>" [`memory`;mk_comb(cell,address a)];s] in
 let data_pre=mk_eq(read_cell src,b) and data_post=mk_eq(read_cell dst,b) in
 let template=vsubst [code,`code:byte list`;mk_small_numeral width,`w:num`]
 `!dst src n i pc e.
   i + w <= n /\ n < 2 EXP 64 /\
   nonoverlapping (word pc,8) (dst,n) /\
   aligned w (word_add src (word i)) /\ aligned w (word_add dst (word i))
   ==> ensures arm
    (\s. aligned_bytes_loaded s (word pc) code /\ read PC s = word pc /\
         read X0 s = dst /\ read X1 s = src /\ read X3 s = word i /\
         data_pre dst src i s /\ read events s = e)
    (\s. read PC s = word(pc+8) /\ data_post dst i s /\
         read events s = APPEND [EventStore(word_add dst (word i),w);
                                EventLoad(word_add src (word i),w)] e)
    (MAYCHANGE [PC;X4] ,, MAYCHANGE [events] ,,
     MAYCHANGE [memory :> bytes(word_add dst (word i),w)])` in
 mk_forall(b, ((DEPTH_CONV BETA_CONV) o vsubst
   [list_mk_abs([dst;src;i;s],data_pre),`data_pre:int64->int64->num->armstate->bool`;
    list_mk_abs([dst;i;s],data_post),`data_post:int64->num->armstate->bool`]) template
   |> concl |> rhs);;

(* Construction checks the actual code and a separately supplied specification.
   The record is only a convenience; the HOL theorem remains the authority. *)
module Ve_block : sig
 type kind = Fixed8 of int * term | Indexed of int
 type t
 val create : thm -> kind -> thm -> t
 val code : t -> thm
 val theorem : t -> thm
end = struct
 type kind = Fixed8 of int * term | Indexed of int
 type t = {code:thm; theorem:thm; expected:term; kind:kind}
 let create code kind theorem =
  let code_name=lhs(concl code) in
  let expected=match kind with
   | Fixed8(offset,scratch) ->
     if not(mem offset [0;8;16;24]) || not(mem scratch [`X3`;`X4`])
     then failwith "unsupported offset or live-register collision";
     ve_copy8_block_spec code_name offset scratch
   | Indexed width ->
     if not(mem width [1;8]) then failwith "unsupported indexed block width";
     ve_indexed_block_spec code_name width in
  if hyp code <> [] || hyp theorem <> [] ||
     not(aconv expected (concl theorem)) then failwith "block contract mismatch";
  {code;theorem;expected;kind}
 let code b=b.code
 let theorem b=b.theorem
end;;
