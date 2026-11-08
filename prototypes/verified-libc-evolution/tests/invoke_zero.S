// Test-only tail trampoline: construct the concrete mutation witness's X3=0.
.text
.p2align 2
.globl _vp2_invoke_x3_zero
_vp2_invoke_x3_zero:
    mov x16, x0
    mov x0, x1
    mov x1, x2
    mov x2, x3
    mov x3, #0
    br x16
.subsections_via_symbols
