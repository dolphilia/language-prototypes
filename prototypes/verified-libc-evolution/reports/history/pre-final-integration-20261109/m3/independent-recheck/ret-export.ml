load_path := "/Users/dolphilia/github/language-prototypes/prototypes/verified-libc-minimal/.deps/s2n-bignum" :: !load_path;;
loadt "/Users/dolphilia/github/language-prototypes/prototypes/verified-libc-minimal/proofs/probe_ret.ml";;
ignore(save_thm "VE_RET_EXPORTED" VP_PROBE_RET_CORRECT);;
export_saved_proofs (Some "ve_ret");;
exit 0;;
