(* Unverified byte ingestion only. The executable is never rewritten into an
   object file. Offsets are cross-checked by the Python Mach-O/LLVM gates. *)
let ve_define_linked_span name path offset length expected =
 let bytes = load_file path in
 let u32 i =
  if i < 0 || i + 4 > Bytes.length bytes then failwith "linked header truncated";
  let b j = Int64.of_int(Char.code(Bytes.get bytes (i+j))) in
  Int64.logor (b 0) (Int64.logor (Int64.shift_left (b 1) 8)
    (Int64.logor (Int64.shift_left (b 2) 16) (Int64.shift_left (b 3) 24))) in
 if u32 0 <> 0xfeedfacfL || u32 4 <> 0x0100000cL ||
    Int64.logand (u32 8) 0xffffffL <> 0L || u32 12 <> 2L then
   failwith "linked span requires thin ordinary arm64 MH_EXECUTE";
 if offset < 32 || offset mod 4 <> 0 || length <= 0 || length mod 4 <> 0 ||
    offset > Bytes.length bytes - length then failwith "linked span out of bounds";
 define_assert_word_list name (term_of_bytes(Bytes.sub bytes offset length)) expected;;
