needs "arm/proofs/base.ml";;

let vp_probe_ret_mc = define_assert_from_elf "vp_probe_ret_mc"
  (Sys.getenv "VP_ROOT" ^ "/build/probe_ret.o") [0xd65f03c0];;
let VP_PROBE_RET_EXEC = ARM_MK_EXEC_RULE vp_probe_ret_mc;;

let vp_probe_ret_spec =
 `!pc returnaddress.
    ensures arm
      (\s. aligned_bytes_loaded s (word pc) vp_probe_ret_mc /\
           read PC s = word pc /\ read X30 s = returnaddress)
      (\s. read PC s = returnaddress)
      (MAYCHANGE [PC] ,, MAYCHANGE [events])`;;

let VP_PROBE_RET_CORRECT = prove(vp_probe_ret_spec,
  REPEAT GEN_TAC THEN ARM_SIM_TAC VP_PROBE_RET_EXEC [1]);;
