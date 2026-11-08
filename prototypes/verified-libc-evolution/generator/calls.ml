(* Untrusted call/stack IR. The only external target is the proved M1 copy. *)
open Generator;;
type call_instruction = Normal of instruction | MoveRegister of int * int
 | AddRegister of int * int * int | Constant of int * int
 | Higher of string | StackSubtract16 | StackAdd16 | SaveLink | RestoreLink | CallCopy;;
type call_item = Mark of string | Emit of call_instruction;;

let call_copy = [Emit StackSubtract16;Emit SaveLink;Emit CallCopy;
                 Emit RestoreLink;Emit StackAdd16;Emit(Normal Ret)];;

let emit_call directory name body =
 let position=ref 0 in
 let labels=List.fold_left(fun acc -> function
   | Mark label -> if List.mem_assoc label acc then failwith "duplicate call label" else (label,!position)::acc
   | Emit _ -> position:= !position+4;acc) [] body in
 let encoding pc = function
  | Normal op -> encode labels pc op
  | MoveRegister(d,n) -> 0xaa0003e0 lor bits n 16 lor reg d
  | AddRegister(d,n,m) -> 0x8b000000 lor bits m 16 lor bits n 5 lor reg d
  | Constant(d,k) -> if k<0 || k>65535 then failwith "MOVZ immediate" else 0xd2800000 lor (k lsl 5) lor reg d
  | Higher label -> 0x54000008 lor (displacement labels pc label 19 lsl 5)
  | StackSubtract16 -> 0xd10043ff | StackAdd16 -> 0x910043ff
  | SaveLink -> 0xf90003fe | RestoreLink -> 0xf94003fe
  | CallCopy -> 0x94000000 in
 let assembly = function
  | Normal op -> asm op
  | MoveRegister(d,n) -> Printf.sprintf "mov x%d, x%d" d n
  | AddRegister(d,n,m) -> Printf.sprintf "add x%d, x%d, x%d" d n m
  | Constant(d,k) -> Printf.sprintf "mov x%d, #%d" d k
  | Higher label -> "b.hi L"^label
  | StackSubtract16 -> "sub sp, sp, #16" | StackAdd16 -> "add sp, sp, #16"
  | SaveLink -> "str x30, [sp]" | RestoreLink -> "ldr x30, [sp]"
  | CallCopy -> "bl _vp2_memcpy_chunk8" in
 let source=open_out(Filename.concat directory (name^".S"))
 and words=open_out(Filename.concat directory (name^".template.words")) in
 Printf.fprintf source ".text\n.p2align 2\n.globl _%s\n_%s:\n" name name;
 position:=0;
 List.iter(function
  | Mark label -> Printf.fprintf source "L%s:\n" label
  | Emit op -> Printf.fprintf source "    %s\n" (assembly op);
      Printf.fprintf words "%08x\n" (encoding !position op);position:= !position+4) body;
 Printf.fprintf source ".globl _%s_end\n.private_extern _%s_end\n_%s_end:\n.subsections_via_symbols\n" name name name;
 close_out source;close_out words;;
let () = if Array.length Sys.argv<>2 then failwith "usage: generate_calls directory"
 else emit_call Sys.argv.(1) "vp2_call_copy" call_copy;;
