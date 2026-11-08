// Test-only frame: lend bytes 16..31 while checking both adjacent boundaries.
.text
.p2align 2
.globl _vp2_check_call_stack_copy
.globl _vp2_check_call_stack_split
_vp2_check_call_stack_copy:
_vp2_check_call_stack_split:
    sub sp, sp, #80
    stp x19, x20, [sp, #48]
    str x30, [sp, #64]
    mov x19, sp
    mov x9, #0x1927
    str x9, [sp, #0]
    mov x9, #0x3645
    str x9, [sp, #8]
    mov x9, #0x5179
    str x9, [sp, #32]
    mov x9, #0x83a1
    str x9, [sp, #40]
    mov x16, x0
    mov x0, x1
    mov x1, x2
    mov x2, x3
    mov x3, x4
    add sp, sp, #32
    blr x16
    sub x9, sp, #32
    cmp x9, x19
    mov sp, x19
    b.ne 9f
    ldr x9, [sp, #0]
    mov x10, #0x1927
    cmp x9, x10
    b.ne 9f
    ldr x9, [sp, #8]
    mov x10, #0x3645
    cmp x9, x10
    b.ne 9f
    ldr x9, [sp, #32]
    mov x10, #0x5179
    cmp x9, x10
    b.ne 9f
    ldr x9, [sp, #40]
    mov x10, #0x83a1
    cmp x9, x10
    b.ne 9f
    mov x0, #0
    b 10f
9:  mov x0, #1
10: ldr x30, [sp, #64]
    ldp x19, x20, [sp, #48]
    add sp, sp, #80
    ret
.subsections_via_symbols
