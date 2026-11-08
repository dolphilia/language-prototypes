(* Checks shared by the actual prover driver and its failure-path tests. *)
let vp_check_closed expected theorem =
  if hyp theorem <> [] || not (aconv expected (concl theorem))
  then failwith "VP: unexpected or open theorem";;
