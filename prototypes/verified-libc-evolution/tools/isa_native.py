from pathlib import Path
import json,struct,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'build'
sys.path.insert(0,str(ROOT/'tools'))
from config import environment
from build import MachO
matrix=json.load(open(B/'e6a-qemu-matrix.json'))
forms={int(w,16):name for name,ws in matrix['forms'].items() for w in ws}
encodings=sorted(forms);offsets=list(range(-64,0,4))+list(range(4,68,4))
lines=['.text','.p2align 2','.globl _ve_native_read_x18','_ve_native_read_x18:','mov x0, x18','ret']
for index,w in enumerate(encodings):
    form=forms[w]
    if form=='B':delta=(w&0x3ffffff);delta=(delta-(1<<26) if delta&(1<<25) else delta)*4
    elif form.startswith('B_COND_') or form=='CBZ_X':
        delta=(w>>5)&0x7ffff;delta=(delta-(1<<19) if delta&(1<<18) else delta)*4
    else:delta=None
    if delta is not None and delta not in offsets:raise RuntimeError('unsafe native branch target')
    stem=f've_native_step_{index}';src=f've_native_src_{index}'
    lines+=['.p2align 2',f'.globl _{stem}',f'_{stem}:','sub sp, sp, #96']
    for r in range(19,31,2):lines.append(f'stp x{r}, x{r+1}, [sp, #{(r-19)*8}]')
    lines+=['mov x9, sp','str x9, [x2, #288]','msr nzcv, x1','mov sp, x2','mov x16, x0']
    for r in range(0,16,2):lines.append(f'ldp x{r}, x{r+1}, [x16, #{r*8}]')
    lines.append('ldr x17, [x16, #136]')
    for r in range(19,31):lines.append(f'ldr x{r}, [x16, #{r*8}]')
    lines+=['ldr x16, [x16, #128]',f'b _{src}']
    for off in range(-64,68,4):
        if off==0:
            lines += [f'.globl _{src}',f'.private_extern _{src}',f'_{src}:',f'.long {hex(w)}',
                      f'.globl _{src}_end',f'.private_extern _{src}_end',f'_{src}_end:']
        else:
            key=('m'+str(-off)) if off<0 else ('p'+str(off))
            lines += [f'Llanding_{index}_{key}:',f'b Lcapture_{index}_{key}']
    for off in offsets:
        key=('m'+str(-off)) if off<0 else ('p'+str(off))
        lines.append(f'Lcapture_{index}_{key}:')
        for r in range(0,30,2):lines.append(f'stp x{r}, x{r+1}, [sp, #{r*8}]')
        lines+=['str x30, [sp, #240]','mov x9, sp','str x9, [sp, #248]',
                f'adr x9, Llanding_{index}_{key}','str x9, [sp, #256]',
                'mrs x9, nzcv','lsr x9, x9, #28','str x9, [sp, #264]',
                'ldr x9, [sp, #288]','mov sp, x9']
        for r in range(19,31,2):lines.append(f'ldp x{r}, x{r+1}, [sp, #{(r-19)*8}]')
        lines+=['add sp, sp, #96','ret']
# Keep the entire harness __text as one atom: numeric branch immediates
# require the landing pads to stay at their original relative positions.
(B/'e6a-native.S').write_text('\n'.join(lines)+'\n')
externs=[];table=[]
for i,w in enumerate(encodings):
    externs += [f'extern void ve_native_step_{i}(uint64_t*,uint64_t,uint64_t*);',f'extern unsigned char ve_native_src_{i}[];']
    f=forms[w];kind=0;rn=rm=imm=0
    if f.startswith(('LDR','STR')):
        rn=(w>>5)&31
        if rn==31:raise RuntimeError('SP memory form excluded')
        if f.endswith('_REG'):
            kind=1;rm=(w>>16)&31
            if rm==31:raise RuntimeError('ZR index excluded')
        else:kind=2;imm=((w>>10)&4095)*8
    width=1 if f.startswith(('LDRB','STRB')) else 8 if kind else 0
    table.append(f'{{ve_native_step_{i},ve_native_src_{i},{kind},{rn},{rm},{imm},{width}}}')
c=r'''
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern uint64_t ve_native_read_x18(void);
EXTERNS
struct variant {void (*fn)(uint64_t*,uint64_t,uint64_t*);unsigned char *pc;int kind,rn,rm,imm,width;};
static const struct variant variants[]={TABLE};
struct request {uint32_t variant,index;uint64_t flags,offset,registers[32];unsigned char memory[512];};
_Static_assert(sizeof(struct request)==792,"protocol layout");
static void registers(uint64_t *r) {putchar('[');for(int i=0;i<32;++i)printf("%s%llu",i?",":"",(unsigned long long)r[i]);putchar(']');}
static void hex(const unsigned char *p) {putchar('"');for(int i=0;i<512;++i)printf("%02x",p[i]);putchar('"');}
int main(void) {
  struct request r;unsigned char *data;
  if(posix_memalign((void**)&data,64,512))return 2;
  for(;;) {
    size_t got=fread(&r,1,sizeof(r),stdin);if(!got && feof(stdin))break;if(got!=sizeof(r))return 2;
    if(r.variant>=sizeof(variants)/sizeof(*variants) || r.flags>15)return 2;
    const struct variant *v=&variants[r.variant];
    _Alignas(64) uint64_t out[40]={0};
    memcpy(data,r.memory,512);
    r.registers[18]=ve_native_read_x18();r.registers[31]=(uint64_t)(uintptr_t)out;
    r.registers[30]=(uint64_t)(uintptr_t)v->pc+32+4*(r.index%8);
    if(v->kind && (r.offset>512-(unsigned)v->width || (v->width==8 && r.offset%8)))return 2;
    uint64_t effective=(uint64_t)(uintptr_t)data+r.offset;
    if(v->kind==1)r.registers[v->rn]=effective-r.registers[v->rm];
    else if(v->kind==2)r.registers[v->rn]=effective-v->imm;
    v->fn(r.registers,r.flags<<28,out);
    printf("{\"index\":%u,\"variant\":%u,\"pc\":%llu,\"memory_base\":%llu,\"nzcv\":%llu,\"registers\":",r.index,r.variant,(unsigned long long)(uintptr_t)v->pc,(unsigned long long)(uintptr_t)data,(unsigned long long)r.flags);
    registers(r.registers);printf(",\"memory\":");hex(r.memory);
    printf(",\"after\":{\"pc\":%llu,\"nzcv\":%llu,\"registers\":",(unsigned long long)out[32],(unsigned long long)out[33]);registers(out);
    printf(",\"memory\":");hex(data);puts("}}");
  }
  free(data);return ferror(stdin)?2:0;
}
'''.replace('EXTERNS','\n'.join(externs)).replace('TABLE',','.join(table))
(B/'e6a-native.c').write_text(c)
for args in [['xcrun','clang','-arch','arm64','-c',B/'e6a-native.S','-o',B/'e6a-native.o'],
             ['xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror',B/'e6a-native.c',B/'e6a-native.o','-o',B/'e6a-native']]:
    subprocess.run(list(map(str,args)),cwd=ROOT,env=environment(),check=True)
p=MachO(B/'e6a-native')
for i,w in enumerate(encodings):
    s=p.symbol(f'_ve_native_src_{i}');e=p.symbol(f'_ve_native_src_{i}_end');section=p.sections[s.section-1]
    if e.address-s.address!=4 or p.span(section.offset+s.address-section.address,4)!=struct.pack('<I',w):raise RuntimeError('actual native instruction differs')
cases=[json.loads(l) for l in (B/'e6a-qemu-cases.jsonl').open()]
payload=b''.join(struct.pack('<IIQQ32Q512s',encodings.index(c['word']),c['index'],c['nzcv'],c.get('effective_offset') or 0,*c['registers'],bytes.fromhex(c['memory'])) for c in cases)
result=subprocess.run([str(B/'e6a-native')],cwd=ROOT,env=environment(),input=payload,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
if result.returncode:raise RuntimeError('native harness failed: '+str(result.returncode)+' '+result.stderr.decode())
rows=[json.loads(l) for l in result.stdout.splitlines()]
if len(rows)!=len(cases):raise RuntimeError('native output coverage differs')
with (B/'e6a-native-cases.jsonl').open('w') as out:
    for c,r in zip(cases,rows):
        if r['index']!=c['index'] or encodings[r['variant']]!=c['word']:raise RuntimeError('native case order differs')
        r.update(form=c['form'],kind=c['kind'],word=c['word'],effective_offset=c.get('effective_offset'))
        out.write(json.dumps(r,separators=(',',':'))+'\n')
print('native single-instruction observations:',len(rows),'cases;',len(encodings),'encodings; HOL comparison pending',flush=True)
print('first observation PC/GPR3:',rows[0]['pc'],rows[0]['registers'][3],rows[0]['after']['registers'][3],flush=True)
