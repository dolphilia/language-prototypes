// Test-only caller checks a requirement stronger than the ordinary ABI.
.text
.p2align 2
.globl _vp2_check_live_x3
_vp2_check_live_x3:
    sub sp, sp, #16
    str x30, [sp]
    mov x16, x0
    mov x0, x1
    mov x1, x2
    mov x2, x3
    mov x3, #291
    blr x16
    cmp x3, #291
    cset w0, ne
    ldr x30, [sp]
    add sp, sp, #16
    ret
.subsections_via_symbols
