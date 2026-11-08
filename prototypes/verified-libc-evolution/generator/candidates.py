"""Untrusted finite template generator. No search beyond the five fixed entries."""
from pathlib import Path

CANDIDATES = [
    ('ve_opt_u1_mov', 1, 'mov x3, #0', 8, 'original'),
    ('ve_opt_u1_eor', 1, 'eor x3, x3, x3', 8, 'new'),
    ('ve_opt_u2_mov', 2, 'mov x3, #0', 16, 'new'),
    ('ve_opt_u2_eor', 2, 'eor x3, x3, x3', 16, 'new'),
    ('ve_opt_u2_bad', 2, 'mov x3, #0', 8, 'deliberately invalid threshold'),
]


def source(name, unroll, init, threshold):
    body = [init, 'orr x4, x0, x1', 'tst x4, #7', 'b.ne Lbyte',
            'Lbulk:', 'sub x4, x2, x3', f'cmp x4, #{threshold}', 'b.lo Lbyte']
    for _ in range(unroll):
        body += ['ldr x4, [x1, x3]', 'str x4, [x0, x3]', 'add x3, x3, #8']
    body += ['b Lbulk', 'Lbyte:', 'cmp x3, x2', 'b.hs Lend', 'Ltail:',
             'ldrb w4, [x1, x3]', 'strb w4, [x0, x3]', 'add x3, x3, #1',
             'cmp x3, x2', 'b.lo Ltail', 'Lend:', 'ret']
    return '\n'.join(['.text','.p2align 2',f'.globl _{name}',f'_{name}:',*body,
                      f'.globl _{name}_end',f'.private_extern _{name}_end',
                      f'_{name}_end:','.subsections_via_symbols',''])


def generate(directory):
    for name,unroll,init,threshold,_ in CANDIDATES:
        (Path(directory)/(name+'.S')).write_text(source(name,unroll,init,threshold))
