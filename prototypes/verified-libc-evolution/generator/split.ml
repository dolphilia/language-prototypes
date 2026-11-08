(* Check all bounds before subtracting capacity or forming a subregion. *)
open Generator;;
open Calls;;
let split = [
 Emit(Normal(IfZero(2,"invalid")));
 Emit(Normal(Compare(2,1)));Emit(Normal(Cond(2,"invalid")));
 Emit(Normal(Compare(3,2)));Emit(Higher "invalid");
 Emit(Normal(Sub(4,1,2)));
 Emit(Normal(Compare(3,4)));Emit(Higher "invalid");
 Emit StackSubtract16;Emit SaveLink;
 Emit(MoveRegister(1,0));Emit(AddRegister(0,0,2));Emit(MoveRegister(2,3));
 Emit CallCopy;Emit RestoreLink;Emit StackAdd16;
 Emit(Constant(0,0));Emit(Normal Ret);
 Mark "invalid";Emit(Constant(0,1));Emit(Normal Ret)];;
let () = if Array.length Sys.argv<>2 then failwith "usage: generate_split directory"
 else emit_call Sys.argv.(1) "vp2_copy_split" split;;
