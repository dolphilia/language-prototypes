(* Fixed AArch64 instruction IR. The encoder and pretty-printer are untrusted:
   assembler output is compared, then the actual code is proved in HOL. *)
type addr = Imm of int * int | Index of int * int;;
type instruction =
  | Zero of int | XorZero of int
  | Load8 of int * addr | Store8 of int * addr
  | Load64 of int * addr | Store64 of int * addr
  | Add of int * int * int | Sub of int * int * int
  | Compare of int * int | CompareImm of int * int
  | Or of int * int * int | Test7 of int
  | Branch of string | Cond of int * string | IfZero of int * string | Ret;;
type item = Label of string | Ins of instruction;;
type block = { name:string; kind:string; body:item list };;

let reg r = if r < 0 || r > 30 then failwith "unsupported register" else r;;
let bits r n = (reg r) lsl n;;
let imm12 n = if n < 0 || n > 4095 then failwith "immediate out of range" else n lsl 10;;
let mem load wide r address =
  let r=reg r in match address with
  | Imm (base,off) ->
    let scale=if wide then 8 else 1 in
    if off mod scale <> 0 then failwith "unscaled offset";
    (if wide then (if load then 0xf9400000 else 0xf9000000)
     else (if load then 0x39400000 else 0x39000000)) lor
    imm12 (off/scale) lor bits base 5 lor r
  | Index (base,index) ->
    (if wide then (if load then 0xf8606800 else 0xf8206800)
     else (if load then 0x38606800 else 0x38206800)) lor
    bits index 16 lor bits base 5 lor r;;

let positions body =
  let pc=ref 0 in List.fold_left (fun acc -> function
    | Label l -> if List.mem_assoc l acc then failwith "duplicate label" else (l,!pc)::acc
    | Ins _ -> pc := !pc+4; acc) [] body;;
let displacement labels pc label width =
  let d=(List.assoc label labels - pc)/4 in
  if d < -(1 lsl (width-1)) || d >= 1 lsl (width-1) then failwith "branch out of range";
  d land ((1 lsl width)-1);;
let encode labels pc = function
  | Zero r -> 0xd2800000 lor reg r
  | XorZero r -> 0xca000000 lor bits r 16 lor bits r 5 lor reg r
  | Load8 (r,a) -> mem true false r a | Store8(r,a) -> mem false false r a
  | Load64(r,a) -> mem true true r a | Store64(r,a) -> mem false true r a
  | Add(d,n,k) -> 0x91000000 lor imm12 k lor bits n 5 lor reg d
  | Sub(d,n,m) -> 0xcb000000 lor bits m 16 lor bits n 5 lor reg d
  | Compare(n,m) -> 0xeb00001f lor bits m 16 lor bits n 5
  | CompareImm(n,k) -> 0xf100001f lor imm12 k lor bits n 5
  | Or(d,n,m) -> 0xaa000000 lor bits m 16 lor bits n 5 lor reg d
  | Test7 n -> 0xf240081f lor bits n 5
  | Branch l -> 0x14000000 lor displacement labels pc l 26
  | Cond(c,l) -> if c<0 || c>14 then failwith "condition" else
      0x54000000 lor ((displacement labels pc l 19) lsl 5) lor c
  | IfZero(r,l) -> 0xb4000000 lor ((displacement labels pc l 19) lsl 5) lor reg r
  | Ret -> 0xd65f03c0;;

let address = function
  | Imm(b,0) -> Printf.sprintf "[x%d]" b
  | Imm(b,k) -> Printf.sprintf "[x%d, #%d]" b k
  | Index(b,i) -> Printf.sprintf "[x%d, x%d]" b i;;
let asm = function
  | Zero r -> Printf.sprintf "mov x%d, #0" r
  | XorZero r -> Printf.sprintf "eor x%d, x%d, x%d" r r r
  | Load8(r,a) -> Printf.sprintf "ldrb w%d, %s" r (address a)
  | Store8(r,a) -> Printf.sprintf "strb w%d, %s" r (address a)
  | Load64(r,a) -> Printf.sprintf "ldr x%d, %s" r (address a)
  | Store64(r,a) -> Printf.sprintf "str x%d, %s" r (address a)
  | Add(d,n,k) -> Printf.sprintf "add x%d, x%d, #%d" d n k
  | Sub(d,n,m) -> Printf.sprintf "sub x%d, x%d, x%d" d n m
  | Compare(n,m) -> Printf.sprintf "cmp x%d, x%d" n m
  | CompareImm(n,k) -> Printf.sprintf "cmp x%d, #%d" n k
  | Or(d,n,m) -> Printf.sprintf "orr x%d, x%d, x%d" d n m
  | Test7 n -> Printf.sprintf "tst x%d, #7" n
  | Branch l -> "b L"^l
  | Cond(c,l) -> "b."^(List.assoc c [0,"eq";1,"ne";2,"hs";3,"lo"])^" L"^l
  | IfZero(r,l) -> Printf.sprintf "cbz x%d, L%s" r l
  | Ret -> "ret";;

let i x = Ins x;;
let copy8_at scratch offset =
 if not(List.mem scratch [3;4]) then failwith "scratch collides with live argument/return register";
 [i(Load64(scratch,Imm(1,offset)));i(Store64(scratch,Imm(0,offset)))];;
let copy8_indexed = [i(Load64(4,Index(1,3)));i(Store64(4,Index(0,3)))];;
let copybyte_indexed = [i(Load8(4,Index(1,3)));i(Store8(4,Index(0,3)))];;
let scalar zero = [i zero;i(IfZero(2,"end"));Label "loop"] @ copybyte_indexed @
 [i(Add(3,3,1));i(Compare(3,2));i(Cond(3,"loop"));Label "end";i Ret];;
let chunk8 = [i(Zero 3);i(Or(4,0,1));i(Test7 4);i(Cond(1,"byte"));
 Label "bulk";i(Sub(4,2,3));i(CompareImm(4,8));i(Cond(3,"byte"))] @
 copy8_indexed @ [i(Add(3,3,8));i(Branch "bulk");Label "byte";
 i(Compare(3,2));i(Cond(2,"end"));Label "tail"] @ copybyte_indexed @
 [i(Add(3,3,1));i(Compare(3,2));i(Cond(3,"tail"));Label "end";i Ret];;
let fill = [i(Zero 3);i(IfZero(2,"end"));Label "loop";i(Store8(1,Index(0,3)));
 i(Add(3,3,1));i(Compare(3,2));i(Cond(3,"loop"));Label "end";i Ret];;
let fixed name offsets = {name;kind="fixed-copy";
  body=List.concat_map (copy8_at 4) offsets @ [i Ret]};;
let blocks =
 (List.map (fun off -> {name=Printf.sprintf "vp2_block_copy8_%d" off;kind="block";
                       body=copy8_at 4 off}) [0;8;16;24]) @
 [{name="vp2_block_copy8_indexed";kind="block";body=copy8_indexed};
  {name="vp2_block_copybyte_indexed";kind="block";body=copybyte_indexed};
  {name="vp2_equivalent_copy";kind="copy";body=scalar(XorZero 3)};
  {name="vp2_memcpy_chunk8";kind="copy";body=chunk8};
  {name="vp2_memset";kind="fill";body=fill};
  fixed "vp2_copy16" [0;8];fixed "vp2_copy32" [0;8;16;24];
  {name="vp2_copy16_x3";kind="fixed-copy";
   body=copy8_at 3 0 @ copy8_at 4 8 @ [i Ret]};
  {name="vp2_block_copy8_x3";kind="block";body=copy8_at 3 0}];;

let emit directory b =
  let labels=positions b.body in
  let out=open_out(Filename.concat directory (b.name^".S")) in
  let words=open_out(Filename.concat directory (b.name^".words")) in
  Printf.fprintf out ".text\n.p2align 2\n.globl _%s\n_%s:\n" b.name b.name;
  let pc=ref 0 in List.iter (function
    | Label l -> Printf.fprintf out "L%s:\n" l
    | Ins op -> Printf.fprintf out "    %s\n" (asm op);
                Printf.fprintf words "%08x\n" (encode labels !pc op); pc:= !pc+4) b.body;
  Printf.fprintf out ".globl _%s_end\n.private_extern _%s_end\n_%s_end:\n.subsections_via_symbols\n"
    b.name b.name b.name;
  close_out out;close_out words;;
let () = if Array.length Sys.argv = 3 && Sys.argv.(1)="--check-scratch" then
    ignore(copy8_at (int_of_string Sys.argv.(2)) 0)
  else if Array.length Sys.argv <> 2 then failwith "usage: generate directory"
  else List.iter (emit Sys.argv.(1)) blocks;;
