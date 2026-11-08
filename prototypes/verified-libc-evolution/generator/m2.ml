(* M2 extends the untrusted IR only with forms needed for the new kernels. *)
open Generator;;
type operation = G of instruction | Move of int * int | SubImmediate of int * int * int
               | Nonzero of int * string | Higher of string;;
type entry = L of string | O of operation;;
let op x = O(G x);;
let move = [op(IfZero(2,"end"));op(Compare(0,1));op(Cond(0,"end"));O(Higher "backward");
 op(Zero 3);L "forward";op(Load8(4,Index(1,3)));op(Store8(4,Index(0,3)));
 op(Add(3,3,1));op(Compare(3,2));op(Cond(3,"forward"));op Ret;
 L "backward";O(Move(3,2));L "backloop";O(SubImmediate(3,3,1));
 op(Load8(4,Index(1,3)));op(Store8(4,Index(0,3)));O(Nonzero(3,"backloop"));
 L "end";op Ret];;

let emit_m2 directory name body =
 let pc=ref 0 in
 let labels=List.fold_left(fun acc -> function
   | L label -> if List.mem_assoc label acc then failwith "duplicate label" else (label,!pc)::acc
   | O _ -> pc:= !pc+4;acc) [] body in
 let encode_at pc = function
  | G instruction -> encode labels pc instruction
  | Move(d,n) -> 0xaa0003e0 lor bits n 16 lor reg d
  | SubImmediate(d,n,k) -> 0xd1000000 lor imm12 k lor bits n 5 lor reg d
  | Nonzero(r,label) -> 0xb5000000 lor (displacement labels pc label 19 lsl 5) lor reg r
  | Higher label -> 0x54000008 lor (displacement labels pc label 19 lsl 5) in
 let print = function
  | G instruction -> asm instruction
  | Move(d,n) -> Printf.sprintf "mov x%d, x%d" d n
  | SubImmediate(d,n,k) -> Printf.sprintf "sub x%d, x%d, #%d" d n k
  | Nonzero(r,label) -> Printf.sprintf "cbnz x%d, L%s" r label
  | Higher label -> "b.hi L"^label in
 let source=open_out(Filename.concat directory (name^".S"))
 and words=open_out(Filename.concat directory (name^".words")) in
 Printf.fprintf source ".text\n.p2align 2\n.globl _%s\n_%s:\n" name name;
 pc:=0;
 List.iter(function
   | L label -> Printf.fprintf source "L%s:\n" label
   | O instruction -> Printf.fprintf source "    %s\n" (print instruction);
       Printf.fprintf words "%08x\n" (encode_at !pc instruction);pc:= !pc+4) body;
 Printf.fprintf source ".globl _%s_end\n.private_extern _%s_end\n_%s_end:\n.subsections_via_symbols\n" name name name;
 close_out source;close_out words;;
let () = if Array.length Sys.argv<>2 then failwith "usage: generate_m2 directory"
 else emit_m2 Sys.argv.(1) "vp2_memmove" move;;
