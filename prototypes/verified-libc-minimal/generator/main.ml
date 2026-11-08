(* Small fixed-register block generator; no parser or instruction allocator.
   The assembler is untrusted: the resulting bytes are checked in HOL Light. *)
type block = { name : string; instructions : string list; words : int list };;

let copy_byte = {
  name = "vp_macro_copybyte";
  instructions = ["ldrb w4, [x1]"; "strb w4, [x0]"; "ret"];
  words = [0x39400024; 0x39000004; 0xd65f03c0]
};;

let fill_byte = {
  name = "vp_macro_fillbyte";
  instructions = ["strb w1, [x0]"; "ret"];
  words = [0x39000001; 0xd65f03c0]
};;

let copy8 = {
  name = "vp_macro_copy8";
  instructions = ["ldr x4, [x1]"; "str x4, [x0]"; "ret"];
  words = [0xf9400024; 0xf9000004; 0xd65f03c0]
};;

(* The indexed forms are the same fixed-register operations used in the loops.
 * HOL checks these fragments separately and checks their enclosing functions. *)
let copy_byte_indexed = {
  name = "vp_macro_copybyte_indexed";
  instructions = ["ldrb w4, [x1, x3]"; "strb w4, [x0, x3]"; "ret"];
  words = [0x38636824; 0x38236804; 0xd65f03c0]
};;
let fill_byte_indexed = {
  name = "vp_macro_fillbyte_indexed";
  instructions = ["strb w1, [x0, x3]"; "ret"];
  words = [0x38236801; 0xd65f03c0]
};;
let body b = List.rev (List.tl (List.rev b.instructions));;

let memcpy_scalar = {
  name = "vp_memcpy_scalar";
  instructions = ["mov x3, #0"; "cbz x2, 2f"; "1:"] @
    body copy_byte_indexed @ ["add x3, x3, #1"; "cmp x3, x2";
    "b.lo 1b"; "2: ret"];
  words = [0xd2800003; 0xb40000c2; 0x38636824; 0x38236804;
    0x91000463; 0xeb02007f; 0x54ffff83; 0xd65f03c0]
};;

let memset_scalar = {
  name = "vp_memset";
  instructions = ["mov x3, #0"; "cbz x2, 2f"; "1:"] @
    body fill_byte_indexed @ ["add x3, x3, #1"; "cmp x3, x2"; "b.lo 1b"; "2: ret"];
  words = [0xd2800003; 0xb40000a2; 0x38236801; 0x91000463;
    0xeb02007f; 0x54ffffa3; 0xd65f03c0]
};;

let memcpy_public = {
  name = "vp_memcpy";
  instructions = ["cmp x2, #8"; "b.ne 3f"; "orr x3, x0, x1";
    "tst x3, #7"; "b.ne 3f"] @ copy8.instructions @ ["3:"] @
    memcpy_scalar.instructions;
  words = [0xf100205f;0x540000e1;0xaa010003;0xf240087f;
    0x54000081;0xf9400024;0xf9000004;0xd65f03c0] @ memcpy_scalar.words
};;

let emit directory b =
  let out = open_out (Filename.concat directory (b.name ^ ".S")) in
  Printf.fprintf out ".text\n.p2align 2\n.globl _%s\n_%s:\n" b.name b.name;
  List.iter (fun line -> Printf.fprintf out "    %s\n" line) b.instructions;
  Printf.fprintf out ".globl _%s_end\n.private_extern _%s_end\n_%s_end:\n.subsections_via_symbols\n"
    b.name b.name b.name;
  close_out out;
  let out = open_out (Filename.concat directory (b.name ^ ".words")) in
  List.iter (fun word -> Printf.fprintf out "%08x\n" word) b.words;
  close_out out;;

let () =
  if Array.length Sys.argv = 3 && Sys.argv.(2) = "baseline-public" then
    emit Sys.argv.(1) {memcpy_scalar with name="vp_memcpy"}
  else if Array.length Sys.argv <> 2 then failwith "usage: generate output-directory [baseline-public]"
  else List.iter (emit Sys.argv.(1))
    [copy_byte; fill_byte; copy8; copy_byte_indexed; fill_byte_indexed;
     memcpy_scalar; memset_scalar; memcpy_public];;
