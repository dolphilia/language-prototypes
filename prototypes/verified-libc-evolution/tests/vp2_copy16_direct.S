.text
.p2align 2
.globl _vp2_copy16_direct
_vp2_copy16_direct:
    ldr x4, [x1]
    str x4, [x0]
    ldr x4, [x1, #8]
    str x4, [x0, #8]
    ret
.globl _vp2_copy16_direct_end
.private_extern _vp2_copy16_direct_end
_vp2_copy16_direct_end:
.subsections_via_symbols
