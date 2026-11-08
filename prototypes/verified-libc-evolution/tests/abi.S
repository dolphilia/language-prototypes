// Test harness only: the verified functions themselves never touch the stack.
.text
.p2align 2
.globl _vp2_check_copy_abi
.globl _vp2_check_fill_abi
_vp2_check_copy_abi:
_vp2_check_fill_abi:
    sub sp, sp, #176
    stp x19, x20, [sp, #0]
    stp x21, x22, [sp, #16]
    stp x23, x24, [sp, #32]
    stp x25, x26, [sp, #48]
    stp x27, x28, [sp, #64]
    stp x29, x30, [sp, #80]
    stp d8, d9, [sp, #96]
    stp d10, d11, [sp, #112]
    stp d12, d13, [sp, #128]
    stp d14, d15, [sp, #144]
    mov x9, sp
    str x9, [sp, #160]
    mov x16, x0
    mov x0, x1
    mov x1, x2
    mov x2, x3
    mov x19, #19
    mov x20, #20
    mov x21, #21
    mov x22, #22
    mov x23, #23
    mov x24, #24
    mov x25, #25
    mov x26, #26
    mov x27, #27
    mov x28, #28
    mov x29, #29
    mov x9, #123
    fmov d8, x9
    fmov d9, x9
    fmov d10, x9
    fmov d11, x9
    fmov d12, x9
    fmov d13, x9
    fmov d14, x9
    fmov d15, x9
    blr x16
    mov x0, #1
    mov x9, sp
    ldr x10, [sp, #160]
    cmp x9, x10
    b.ne 9f
    cmp x19, #19
    b.ne 9f
    cmp x20, #20
    b.ne 9f
    cmp x21, #21
    b.ne 9f
    cmp x22, #22
    b.ne 9f
    cmp x23, #23
    b.ne 9f
    cmp x24, #24
    b.ne 9f
    cmp x25, #25
    b.ne 9f
    cmp x26, #26
    b.ne 9f
    cmp x27, #27
    b.ne 9f
    cmp x28, #28
    b.ne 9f
    cmp x29, #29
    b.ne 9f
    fmov x9, d8
    cmp x9, #123
    b.ne 9f
    fmov x9, d9
    cmp x9, #123
    b.ne 9f
    fmov x9, d10
    cmp x9, #123
    b.ne 9f
    fmov x9, d11
    cmp x9, #123
    b.ne 9f
    fmov x9, d12
    cmp x9, #123
    b.ne 9f
    fmov x9, d13
    cmp x9, #123
    b.ne 9f
    fmov x9, d14
    cmp x9, #123
    b.ne 9f
    fmov x9, d15
    cmp x9, #123
    b.ne 9f
    mov x0, #0
9:  ldp d8, d9, [sp, #96]
    ldp d10, d11, [sp, #112]
    ldp d12, d13, [sp, #128]
    ldp d14, d15, [sp, #144]
    ldp x19, x20, [sp, #0]
    ldp x21, x22, [sp, #16]
    ldp x23, x24, [sp, #32]
    ldp x25, x26, [sp, #48]
    ldp x27, x28, [sp, #64]
    ldp x29, x30, [sp, #80]
    add sp, sp, #176
    ret
.subsections_via_symbols
