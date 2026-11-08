let ve_move_zero_spec =
 `!dst src pc returnaddress e.
   ensures arm
    (\s. aligned_bytes_loaded s (word pc) vp2_memmove_mc /\
         read PC s = word pc /\ read X30 s = returnaddress /\
         C_ARGUMENTS [dst;src;word 0] s /\ read events s = e)
    (\s. read PC s = returnaddress /\ read X0 s = dst /\
         read events s = APPEND
          [EventJump(word(pc+64),returnaddress);EventJump(word pc,word(pc+64))] e)
    (MAYCHANGE [PC] ,, MAYCHANGE [events])`;;
let VE_MOVE_ZERO = prove(ve_move_zero_spec,
  REWRITE_TAC[C_ARGUMENTS] THEN REPEAT GEN_TAC THEN
  ARM_SIM_TAC VP2_MEMMOVE_EXEC (1--2) THEN REWRITE_TAC[APPEND]);;
ve_check "memmove:zero-no-data" ve_move_zero_spec VE_MOVE_ZERO;;

let ve_move_same_spec =
 `!buffer n pc returnaddress e.
   ~(n:int64 = word 0)
   ==> ensures arm
    (\s. aligned_bytes_loaded s (word pc) vp2_memmove_mc /\
         read PC s = word pc /\ read X30 s = returnaddress /\
         C_ARGUMENTS [buffer;buffer;n] s /\ read events s = e)
    (\s. read PC s = returnaddress /\ read X0 s = buffer /\
         read events s = APPEND
          [EventJump(word(pc+64),returnaddress);EventJump(word(pc+8),word(pc+64));
           EventJump(word pc,word(pc+4))] e)
    (MAYCHANGE [PC] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events])`;;
let VE_MOVE_SAME = prove(ve_move_same_spec,
  REWRITE_TAC[C_ARGUMENTS;SOME_FLAGS] THEN REPEAT STRIP_TAC THEN
  SUBGOAL_THEN `~(val(n:int64) = 0)` ASSUME_TAC THENL
   [ASM_REWRITE_TAC[VAL_EQ_0];ALL_TAC] THEN
  ARM_SIM_TAC VP2_MEMMOVE_EXEC (1--4) THEN REWRITE_TAC[APPEND]);;
ve_check "memmove:same-no-data" ve_move_same_spec VE_MOVE_SAME;;
