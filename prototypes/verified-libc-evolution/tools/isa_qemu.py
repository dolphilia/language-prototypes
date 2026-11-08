from pathlib import Path
import subprocess,os,select,time,json,hashlib,struct,random
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build'
QEMU=Path('/opt/homebrew/Cellar/qemu/10.1.0/bin/qemu-system-aarch64')
EXPECTED='b27ed0e029cfbd452be5a440139d8ff84d473353c8694521888d609ef8a244ce'
COMMIT='f8b2f64e2336a28bf0d50b6ef8a7d8c013e9bcf3'
PC=0x40000040;MEM=0x40010000;LIMIT=(1<<64)-1

def classify(w):
    if w==0xd65f03c0:return 'RET'
    if w&0xfc000000==0x14000000:return 'B'
    if w&0xff000010==0x54000000:return 'B_COND_'+{1:'NE',2:'HS',3:'LO'}[w&15]
    if w&0xff000000==0xb4000000:return 'CBZ_X'
    if w&0xff800000==0xd2800000:return 'MOVZ_X'
    for mask,value,name in [(0xffe0fc00,0xca000000,'EOR_X'),
          (0xffc00000,0xf9400000,'LDR_X_IMM'),(0xffc00000,0xf9000000,'STR_X_IMM'),
          (0xffe0fc00,0xf8606800,'LDR_X_REG'),(0xffe0fc00,0xf8206800,'STR_X_REG'),
          (0xffe0fc00,0x38606800,'LDRB_W_REG'),(0xffe0fc00,0x38206800,'STRB_W_REG'),
          (0xffc00000,0x91000000,'ADD_X_IMM'),(0xffe0fc00,0xcb000000,'SUB_X_REG'),
          (0xffe0fc1f,0xeb00001f,'CMP_X_REG'),(0xffc0001f,0xf100001f,'CMP_X_IMM'),
          (0xffe0fc00,0xaa000000,'ORR_X'),(0xfffffc1f,0xf240081f,'TST_X_IMM')]:
        if w&mask==value:return name
    raise ValueError(f'unclassified positive instruction {w:08x}')

class Backend:
    def __init__(self):
        if hashlib.sha256(QEMU.read_bytes()).hexdigest()!=EXPECTED:raise RuntimeError('QEMU identity changed')
        self.command=[str(QEMU),'-machine','virt','-cpu','cortex-a72','-accel','tcg','-m','128M',
            '-display','none','-serial','none','-monitor','none','-nic','none','-nodefaults','-S','-gdb','stdio']
        self.p=subprocess.Popen(self.command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
        self.buf=bytearray()
        self.features=self.rsp('qSupported:xmlRegisters=aarch64')
        self.xml=self.rsp('qXfer:features:read:aarch64-core.xml:0,fff')
        self.original=bytes.fromhex(self.rsp('g'))
        if len(self.original)!=268:raise RuntimeError('unexpected GPR packet layout')
        self.cpsr=int.from_bytes(self.original[-4:],'little')
        self.sstep=self.rsp('qqemu.sstep')
    def byte(self):
        if not self.buf:
            if not select.select([self.p.stdout],[],[],5)[0]:raise TimeoutError('QEMU RSP timeout')
            data=os.read(self.p.stdout.fileno(),65536)
            if not data:raise RuntimeError('QEMU ended')
            self.buf.extend(data)
        b=self.buf[0];del self.buf[0];return b
    def rsp(self,message):
        data=message.encode();self.p.stdin.write(b'$'+data+b'#'+f'{sum(data)&255:02x}'.encode())
        while self.byte()!=36:pass
        raw=bytearray()
        while True:
            b=self.byte()
            if b==35:break
            raw.append(b)
        check=int(bytes([self.byte(),self.byte()]),16)
        if sum(raw)&255!=check:raise RuntimeError('RSP checksum mismatch')
        self.p.stdin.write(b'+')
        out=bytearray();i=0
        while i<len(raw):
            b=raw[i];i+=1
            if b==125:b=raw[i]^32;i+=1
            elif b==42:
                count=raw[i]-29;i+=1;out+=bytes([out[-1]])*count;continue
            out.append(b)
        return out.decode()
    def memory(self,a,data):
        if self.rsp(f'M{a:x},{len(data):x}:'+data.hex())!='OK':raise RuntimeError('write memory')
    def execute(self,w,regs,flags,data):
        self.memory(PC,struct.pack('<I',w));self.memory(MEM,data)
        packet=b''.join(r.to_bytes(8,'little') for r in regs)+PC.to_bytes(8,'little')+((self.cpsr&0x0fffffff)|(flags<<28)).to_bytes(4,'little')
        if self.rsp('G'+packet.hex())!='OK':raise RuntimeError('write GPR packet')
        stop=self.rsp('s')
        if not stop.startswith('T05'):raise RuntimeError('instruction did not single step: '+stop)
        raw=bytes.fromhex(self.rsp('g'))
        if len(raw)!=268:raise RuntimeError('output register layout changed')
        after=[int.from_bytes(raw[i*8:(i+1)*8],'little') for i in range(32)]
        return dict(registers=after,pc=int.from_bytes(raw[256:264],'little'),nzcv=(int.from_bytes(raw[264:],'little')>>28)&15,
            memory=self.rsp(f'm{MEM:x},{len(data):x}'),stop=stop)
    def close(self):
        self.p.terminate()
        try:self.p.wait(timeout=5)
        except subprocess.TimeoutExpired:self.p.kill();self.p.wait()

names=['vp2_block_copy8_0','vp2_block_copy8_8','vp2_block_copy8_16','vp2_block_copy8_24',
       'vp2_block_copy8_x3','vp2_block_copy8_indexed','vp2_block_copybyte_indexed',
       'vp2_equivalent_copy','vp2_memcpy_chunk8','vp2_memset','vp2_copy16','vp2_copy32','vp2_copy16_x3']
forms={};inputs={}
for name in names:
    p=BUILD/(name+'.words');inputs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    for line in p.read_text().splitlines():
        w=int(line,16);form=classify(w)
        forms.setdefault(form,set()).add(w)
forms={k:sorted(v) for k,v in sorted(forms.items())}
edges=[0,1,2,3,4,7,8,15,16,31,32,63,64,127,128,255,256,511,1023,
       (1<<31)-1,1<<31,(1<<32)-1,1<<32,(1<<32)+1,(1<<63)-2,(1<<63)-1,1<<63,(1<<63)+1,LIMIT-7,LIMIT-2,LIMIT-1,LIMIT]
rng=random.Random(0x19273645);backend=Backend();started=time.monotonic();counts={}
try:
    with (BUILD/'e6a-qemu-cases.jsonl').open('w') as out:
        for form,encodings in forms.items():
            for index in range(288):
                regs=[rng.getrandbits(64) for _ in range(32)]
                if index<32:
                    for r in range(5):regs[r]=edges[(index+r*7)%32]
                regs[31]=0x40020000;regs[30]=PC+32+4*(index%8)
                flags=index%16 if index<32 else rng.randrange(16)
                data=rng.randbytes(512)
                w=encodings[index%len(encodings)]
                byte_access=form.startswith(('LDRB','STRB'))
                raw_offset=edges[index]%512 if index<32 else (index%512 if byte_access else 8*(index%64))
                effective=MEM+(raw_offset if byte_access else (raw_offset//8)*8)
                if form.startswith(('LDR','STR')):
                    rn=(w>>5)&31
                    if form.endswith('_REG'):
                        rm=(w>>16)&31;regs[rn]=(effective-regs[rm])&LIMIT
                    else:
                        width=8 if '_X_' in form else 1
                        offset=((w>>10)&4095)*width;regs[rn]=(effective-offset)&LIMIT
                result=backend.execute(w,regs,flags,data)
                case=dict(form=form,index=index,kind='edge' if index<32 else 'seeded',word=w,
                    pc=PC,memory_base=MEM,effective_offset=effective-MEM if form.startswith(('LDR','STR')) else None,registers=regs,nzcv=flags,memory=data.hex(),after=result)
                out.write(json.dumps(case,separators=(',',':'))+'\n')
            counts[form]=288;print('QEMU only:',form,288,flush=True)
    report=dict(status='backend observations only; HOL and native differential checks pending',seed='0x19273645',
        command=backend.command,upstream_commit=COMMIT,binary=str(QEMU),binary_sha256=EXPECTED,
        feature_xml=backend.xml,sstep=backend.sstep,forms={k:[hex(w) for w in v] for k,v in forms.items()},
        counts=counts,seconds=time.monotonic()-started,inputs=inputs,
        cases_sha256=hashlib.sha256((BUILD/'e6a-qemu-cases.jsonl').read_bytes()).hexdigest())
    (BUILD/'e6a-qemu-matrix.json').write_text(json.dumps(report,indent=2)+'\n')
finally:backend.close()
