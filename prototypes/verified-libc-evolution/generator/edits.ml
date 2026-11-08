(* Fixed, predeclared edits. This module uses the same untrusted instruction IR. *)
open Generator;;
let families=["offset";"scratch";"frame"];;
let edited family width =
 let offsets=List.init (width/8) (fun j -> if family="offset" && j=1 then 0 else j*8) in
 {name=Printf.sprintf "vp2_edit_%s%d" family width;kind="edit-experiment";
  body=List.concat(List.mapi (fun j off ->
    copy8_at (if family="scratch" && j=0 then 3 else 4) off) offsets) @ [i Ret]};;
let () = List.iter (fun width -> List.iter (fun family ->
 emit Sys.argv.(1) (edited family width)) families) [16;32];;
