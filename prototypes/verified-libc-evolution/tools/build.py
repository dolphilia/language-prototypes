"""Generate fixed instruction blocks, assemble, and compare actual spans."""
import json
import struct
import subprocess
import sys
from config import ROOT, BASE, BUILD, environment, opam_command, digest

sys.path.insert(0, str(BASE / 'tools'))
from macho import MachO

M1_NAMES=tuple([f'vp2_block_copy8_{offset}' for offset in [0,8,16,24]]+[
    'vp2_block_copy8_indexed','vp2_block_copybyte_indexed','vp2_equivalent_copy',
    'vp2_memcpy_chunk8','vp2_memset','vp2_copy16','vp2_copy32','vp2_copy16_x3','vp2_block_copy8_x3'])


def run(args):
    subprocess.run(list(map(str, args)), cwd=ROOT, env=environment(), check=True)


def words(path):
    lines=path.read_text().splitlines()
    if not lines or any(len(w)!=8 or any(c not in '0123456789abcdef' for c in w) for w in lines):
        raise ValueError(f'invalid literal: {path}')
    return b''.join(struct.pack('<I',int(w,16)) for w in lines)


def check_span(path,name,expected,*,object_only=True):
    actual=MachO(path).function(name,object_only=object_only)
    if actual!=expected:
        raise RuntimeError(f'{name}: actual bytes differ from expected proof target')
    return actual


def prepare():
    BUILD.mkdir(exist_ok=True)
    run(opam_command(['ocamlc','-c','-o',BUILD/'generator.cmo',ROOT/'generator/main.ml']))
    run(opam_command(['ocamlc','-o',BUILD/'generate',BUILD/'generator.cmo']))
    run([BUILD/'generate',BUILD])
    records=[]
    for name in sorted(M1_NAMES):
        literal=BUILD/(name+'.words')
        assembly=literal.with_suffix('.S')
        target=literal.with_suffix('.o')
        run(['xcrun','clang','-arch','arm64','-c',assembly,'-o',target])
        actual=check_span(target,name,words(literal))
        records.append(dict(name=name,bytes=len(actual),sha256=digest(target)))
    for name,n in [('vp2_copy16',16),('vp2_copy32',32)]:
        # A separate, literal assembly reference: no generator/IR constructor.
        target=BUILD/(name+'_direct.o')
        run(['xcrun','clang','-arch','arm64','-c',ROOT/'tests'/f'{name}_direct.S','-o',target])
        reference=MachO(target).function(name+'_direct',object_only=True)
        if reference!=words(BUILD/(name+'.words')):
            raise RuntimeError(f'{name}: direct and composed bodies differ')
    (BUILD/'artifacts.json').write_text(json.dumps(records,indent=2)+'\n')
    return records


def mutations():
    result=[]
    definitions=[('return','vp_memcpy_scalar',0,0xd2800000,0,3),
        ('callee','vp_memcpy_scalar',0,0xd2800013,0,3),
        ('termination','vp_memcpy_scalar',24,0x17fffffc,1,8),
        ('overread','vp_memcpy_scalar',8,0x39400424,1,3),
        ('overwrite','vp_memcpy_scalar',12,0x39000404,1,4),
        ('short_fast','vp_memcpy',0,0xf100105f,4,6),
        ('self_branch','vp_memcpy_scalar',28,0x14000000,0,2)]
    for name,function,offset,word,n,steps in definitions:
        source=MachO(BASE/'build'/f'{function}.o')
        sym=source.symbol('_'+function)
        sec=source.sections[sym.section-1]
        changed=bytearray(source.data)
        struct.pack_into('<I',changed,sec.offset+sym.address-sec.address+offset,word)
        path=BUILD/f've_mut_{name}.o'
        path.write_bytes(changed)
        code=MachO(path).function(function,object_only=True)
        if code[offset:offset+4]!=struct.pack('<I',word):
            raise RuntimeError('mutation missing in actual span')
        result.append(dict(name=name,function=function,n=n,steps=steps,
            words=list(struct.unpack('<'+'I'*(len(code)//4),code)),object=str(path)))
    (BUILD/'mutations.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    prepare()
    mutations()
