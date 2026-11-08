(* The overlap contract is independent of the generator and permits equal
   pointers. Only the copy contract's source/destination nonoverlap is removed. *)
let ve_move_contract code = vsubst [code,`code:byte list`]
 `!dst src n pc returnaddress (input:num->byte).
    ~(dst = word 0) /\ ~(src = word 0) /\
    val dst + val n <= 2 EXP 64 /\ val src + val n <= 2 EXP 64 /\
    nonoverlapping (word pc,LENGTH code) (dst,val n)
    ==> ensures arm
      (\s. aligned_bytes_loaded s (word pc) code /\
           read PC s = word pc /\ read X30 s = returnaddress /\
           C_ARGUMENTS [dst;src;n] s /\
           (!i. i < val n ==>
             read (memory :> bytes8 (word_add src (word i))) s = input i))
      (\s. read PC s = returnaddress /\ read X0 s = dst /\
           (!i. i < val n ==>
             read (memory :> bytes8 (word_add dst (word i))) s = input i))
      (MAYCHANGE [PC;X3;X4] ,, MAYCHANGE SOME_FLAGS ,, MAYCHANGE [events] ,,
       MAYCHANGE [memory :> bytes(dst,val n)])`;;

let ve_move_access_contract code = vsubst [code,`code:byte list`]
 `!dst src n pc returnaddress e.
    ~(dst = word 0) /\ ~(src = word 0) /\
    val dst + val n <= 2 EXP 64 /\ val src + val n <= 2 EXP 64 /\
    nonoverlapping (word pc,LENGTH code) (dst,val n)
    ==> ensures arm
      (\s. aligned_bytes_loaded s (word pc) code /\
           read PC s = word pc /\ read X30 s = returnaddress /\
           C_ARGUMENTS [dst;src;n] s /\ read events s = e)
      (\s. read PC s = returnaddress /\
           ?trace. read events s = APPEND trace e /\
             memaccess_inbounds trace [src,val n] [dst,val n])
      (\s:armstate t:armstate. T)`;;

let vp2_memmove_mc = define_assert_from_elf "vp2_memmove_mc"
 (Sys.getenv "VP_EVOLUTION_ROOT" ^ "/build/vp2_memmove.o")
 [0xb4000202;0xeb01001f;0x540001c0;0x54000108;0xd2800003;
  0x38636824;0x38236804;0x91000463;0xeb02007f;0x54ffff83;
  0xd65f03c0;0xaa0203e3;0xd1000463;0x38636824;0x38236804;0xb5ffffa3;0xd65f03c0];;
let VP2_MEMMOVE_EXEC = ARM_MK_EXEC_RULE vp2_memmove_mc;;
let VE_MOVE_ALIGNED1 = prove(`!a:int64. aligned 1 a`,REWRITE_TAC[aligned;DIVIDES_1]);;
