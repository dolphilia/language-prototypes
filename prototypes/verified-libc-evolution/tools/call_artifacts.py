"""One external BRANCH26 relocation, followed by exact post-link code checks.

This extractor is explicitly unverified. It retains the old strict leaf
reader unchanged and admits only one documented call relocation here.
"""
import struct
import re
import subprocess
from config import ROOT,BUILD,digest,environment
from build import MachO,words,check_span


class CallArtifactError(ValueError):
    pass


def raw_symbols(parsed):
    cursor=32;table=None
    for _ in range(parsed.unpack('<I',16)[0]):
        kind,size=parsed.unpack('<II',cursor)
        if kind==2:table=parsed.unpack('<IIIIII',cursor)[2:]
        cursor+=size
    if table is None:raise CallArtifactError('symbol table missing')
    symoff,count,stroff,strsize=table;strings=parsed.span(stroff,strsize);rows=[]
    for i in range(count):
        index,kind,section,desc,value=parsed.unpack('<IBBHQ',symoff+16*i)
        if kind&0xe0:raise CallArtifactError('debug symbols outside the supported call object')
        end=strings.find(b'\0',index)
        if end<0:raise CallArtifactError('unterminated symbol')
        rows.append(dict(name=strings[index:end].decode('ascii'),kind=kind,section=section,desc=desc,value=value))
    return rows


def call_object(path,name,template,callee='vp2_memcpy_chunk8'):
    p=MachO(path)
    if p.kind!=1:raise CallArtifactError('expected call object')
    start=p.symbol('_'+name);end=p.symbol('_'+name+'_end')
    if start.section!=end.section:raise CallArtifactError('call boundaries differ')
    s=p.sections[start.section-1]
    vmaddr,vmsize,fileoff,filesize,protection=s.segment_mapping
    delta=s.address-vmaddr
    if (s.name,s.segment)!=('__text','__TEXT') or not s.flags&0x80000400 or not protection&4 or \
       delta<0 or delta+s.size>vmsize or s.offset!=fileoff+delta or delta+s.size>filesize:
        raise CallArtifactError('call object executable mapping invalid')
    if start.address!=s.address or end.address-start.address!=s.size or s.size!=len(template) or s.size%4:
        raise CallArtifactError('call object must contain exactly one aligned function')
    if any(other.size for other in p.sections if other!=s):raise CallArtifactError('additional call-object data')
    body=p.span(s.offset,s.size)
    if body!=template:raise CallArtifactError('call object differs from its unrelocated template')
    symbols=raw_symbols(p)
    public=[r for r in symbols if r['name']!='ltmp0']
    temporary=[r for r in symbols if r['name']=='ltmp0']
    if (temporary not in ([],[dict(name='ltmp0',kind=14,section=start.section,desc=0,value=start.address)]) or
        {r['name'] for r in public}!={'_'+name,'_'+name+'_end','_'+callee} or len(public)!=3):
        raise CallArtifactError('unexpected object symbols')
    reloff,count=p.unpack('<II',s.header_offset+56)
    if count!=1 or s.relocations!=1:raise CallArtifactError('exactly one call relocation is supported; no ADDEND')
    address,info=p.unpack('<iI',reloff)
    index=info&0xffffff;pcrel=(info>>24)&1;length=(info>>25)&3;external=(info>>27)&1;kind=info>>28
    if (kind,pcrel,length,external)!=(2,1,2,1) or index>=len(symbols):
        raise CallArtifactError('only external PC-relative 4-byte ARM64_RELOC_BRANCH26 is supported')
    target=symbols[index]
    if target!={'name':'_'+callee,'kind':1,'section':0,'desc':0,'value':0}:
        raise CallArtifactError('relocation does not name the one undefined approved callee')
    if address<0 or address%4 or address+4>len(body):raise CallArtifactError('invalid call relocation position')
    opcode=struct.unpack_from('<I',body,address)[0]
    calls=[i for i in range(0,len(body),4) if struct.unpack_from('<I',body,i)[0]&0xfc000000==0x94000000]
    if calls!=[address] or opcode!=0x94000000:raise CallArtifactError('single BL with zero in-place addend required')
    return dict(path=str(path),sha256=digest(path),name=name,body_bytes=len(body),call_offset=address,
                relocation=dict(type=kind,pcrel=pcrel,length=length,external=external,target=target['name'],addend=0))


def branch_displacement(place,target):
    delta=target-place
    if delta%4 or not(-(1<<27)<=delta<(1<<27)):raise CallArtifactError('direct BL target outside signed 26-bit range')
    return delta


def linked(path,name,object_record,template,label,callee='vp2_memcpy_chunk8'):
    p=MachO(path)
    if p.kind!=2:raise CallArtifactError('expected executable link result')
    caller=p.function(name);expected=bytearray(template)
    off=object_record['call_offset'];instruction=struct.unpack_from('<I',caller,off)[0]
    if instruction&0xfc000000!=0x94000000:raise CallArtifactError('linked call is not BL')
    caller_symbol=p.symbol('_'+name);callee_symbol=p.symbol('_'+callee)
    immediate=instruction&0x3ffffff
    if immediate&(1<<25):immediate-=1<<26
    place=caller_symbol.address+off;target=place+4*immediate
    displacement=branch_displacement(place,callee_symbol.address)
    if target!=callee_symbol.address:raise CallArtifactError('BL resolves to a stub or wrong target')
    struct.pack_into('<I',expected,off,instruction)
    if caller!=expected:raise CallArtifactError('non-BL caller bytes changed at link time')
    callee_body=words(BUILD/(callee+'.words'))
    try:check_span(path,callee,callee_body,object_only=False)
    except RuntimeError as error:raise CallArtifactError(str(error)) from error
    if caller_symbol.section!=callee_symbol.section:raise CallArtifactError('caller/callee must share __text')
    listing=subprocess.check_output(['xcrun','llvm-objdump','--macho','--syms',str(path)],
        cwd=ROOT,env=environment(),text=True)
    for function in [name,callee]:
        for suffix in ['', '_end']:
            symbol='_'+function+suffix
            rows=re.findall(r'^([0-9a-f]+)\s+.*?\s'+re.escape(symbol)+r'$',listing,re.M)
            if len(rows)!=1 or int(rows[0],16)!=p.symbol(symbol).address:
                raise CallArtifactError('LLVM and linked symbol positions disagree: '+symbol)
    section=p.sections[caller_symbol.section-1]
    base=min(caller_symbol.address,callee_symbol.address)
    finish=max(p.symbol('_'+name+'_end').address,p.symbol('_'+callee+'_end').address)
    file_offset=section.offset+base-section.address
    bundle=p.span(file_offset,finish-base)
    caller_offset=caller_symbol.address-base;callee_offset=callee_symbol.address-base
    occupied=set(range(caller_offset,caller_offset+len(caller)))|set(range(callee_offset,callee_offset+len(callee_body)))
    if len(occupied)!=len(caller)+len(callee_body):raise CallArtifactError('caller/callee spans overlap')
    for i in range(0,len(bundle),4):
        if i not in occupied and bundle[i:i+4]!=struct.pack('<I',0xd503201f):
            raise CallArtifactError('only NOP padding between caller and callee is supported')
    return dict(label=label,path=str(path),sha256=digest(path),preferred_base=base,
        caller_offset=caller_offset,callee_offset=callee_offset,bundle_file_offset=file_offset,
        bundle_bytes=len(bundle),bundle_words=list(struct.unpack('<'+'I'*(len(bundle)//4),bundle)),
        caller_bytes=len(caller),callee_bytes=len(callee_body),padding_bytes=len(bundle)-len(caller)-len(callee_body),
        call_offset=off,displacement=displacement,target=target,
        note='common runtime load base is quantified by the proof; preferred_base is artifact metadata only')
