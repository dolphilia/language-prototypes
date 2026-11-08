(* The public frame cannot hide corruption of an Apple ABI saved register. *)
let ve_public_x19_spec =
 `!dst n s t.
   (MAYCHANGE [PC;X3;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
    MAYCHANGE [memory :> bytes(dst,n)]) s t
   ==> read X19 t = read X19 s`;;
let VE_PUBLIC_X19 = prove(ve_public_x19_spec,
  REWRITE_TAC[SOME_FLAGS;MAYCHANGE;ASSIGNS;seq;assign] THEN REPEAT STRIP_TAC THEN
  REPEAT(FIRST_X_ASSUM(SUBST_ALL_TAC o SYM)) THEN
  CONV_TAC(DEPTH_CONV COMPONENT_READ_OVER_WRITE_CONV) THEN REFL_TAC);;
ve_check "public:preserves_x19" ve_public_x19_spec VE_PUBLIC_X19;;
