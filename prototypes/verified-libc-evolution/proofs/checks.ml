(* Every recorded proof is checked against an independently supplied term. *)
let ve_checks = ref ([]:string list);;
let ve_check name expected theorem =
  if frees expected <> [] || hyp theorem <> [] || not (aconv expected (concl theorem)) then
    failwith ("VE: unexpected or open theorem: " ^ name);
  if mem name !ve_checks then failwith ("VE: duplicate check: " ^ name);
  ve_checks := name :: !ve_checks;;

let ve_timed name thunk =
  let started = Sys.time() in
  let value = thunk() in
  Printf.printf "VE_TIMING %s %.9f\n%!" name (Sys.time() -. started);
  value;;
