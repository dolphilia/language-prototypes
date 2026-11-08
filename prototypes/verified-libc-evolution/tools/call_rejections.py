"""Concrete malformed-artifact refusals; these are not HOL counterexamples."""
import json
import struct
from config import ROOT,BUILD,digest
from build import MachO,words,run
from call_artifacts import call_object,linked,branch_displacement,CallArtifactError


def verify(report):
    name='vp2_call_copy';source=BUILD/(name+'.o');template=words(BUILD/(name+'.template.words'))
    parsed=MachO(source);section=parsed.sections[0]
    reloc=parsed.unpack('<I',section.header_offset+56)[0]
    address,info=parsed.unpack('<iI',reloc)
    rows=[];folder=BUILD/'call-refusals';folder.mkdir(exist_ok=True)
    def refused(label,action,path=None):
        try:action()
        except (CallArtifactError,ValueError) as error:
            rows.append(dict(name=label,classification='unsupported_or_mismatched_artifact',
                diagnostic=str(error),path=str(path) if path else None,
                sha256=digest(path) if path else None))
        else:raise RuntimeError('unsafe call artifact accepted: '+label)
    edits=[('relocation-kind',reloc+4,info^(1<<28)),
           ('non-pc-relative',reloc+4,info^(1<<24)),
           ('wrong-width',reloc+4,info^(1<<25)),
           ('non-external',reloc+4,info^(1<<27)),
           ('wrong-symbol-index',reloc+4,(info&~0xffffff)|0),
           ('missing-symbol-index',reloc+4,(info&~0xffffff)|0xffffff),
           ('negative-position',reloc,0xfffffffc),
           ('unaligned-position',reloc,1),
           ('position-outside-body',reloc,len(template)),
           ('extra-addend-relocation',section.header_offset+60,2),
           ('missing-relocation',section.header_offset+60,0),
           ('in-place-addend',section.offset+address,0x94000001)]
    for label,offset,value in edits:
        data=bytearray(source.read_bytes());struct.pack_into('<I',data,offset,value)
        path=folder/(label+'.o');path.write_bytes(data)
        refused(label,lambda p=path:call_object(p,name,template),path)
    for layout in report['layouts']:
        executable=bytearray(open(layout['path'],'rb').read())
        p=MachO(layout['path']);callee=p.symbol('_vp2_memcpy_chunk8');s=p.sections[callee.section-1]
        callee_file=s.offset+callee.address-s.address
        for label,offset,value in [
            ('same-name-changed-callee',callee_file,0xd2800023),
            ('wrong-target-or-stub',layout['bundle_file_offset']+layout['caller_offset']+8,0x94000000)]:
            data=bytearray(executable);struct.pack_into('<I',data,offset,value)
            path=folder/(label+'-'+layout['label']);path.write_bytes(data)
            refused(label+'-'+layout['label'],lambda p=path,l=layout:
                linked(p,name,report['object'],template,l['label']),path)
    # Real link results containing an intermediate stub or a dyld-resolved
    # libc import, even though a same-named proved callee is also in the file.
    stub=folder/'stub.S'
    stub.write_text('.text\n.p2align 2\n.globl _vp2_copy_stub\n_vp2_copy_stub:\nb _vp2_memcpy_chunk8\n')
    run(['xcrun','clang','-arch','arm64','-c',stub,'-o',stub.with_suffix('.o')])
    for label,target in [('intermediate-stub','_vp2_copy_stub'),('dynamic-libc','_memcpy')]:
        source_text=(BUILD/'vp2_call_copy.S').read_text().replace('bl _vp2_memcpy_chunk8','bl '+target)
        asm=folder/(label+'.S');asm.write_text(source_text);obj=asm.with_suffix('.o')
        run(['xcrun','clang','-arch','arm64','-c',asm,'-o',obj])
        refused(label+'-object',lambda p=obj:call_object(p,name,template),obj)
        target_exe=folder/(label+'-linked')
        run(['xcrun','clang','-arch','arm64',obj,BUILD/'vp2_memcpy_chunk8.o',
            *([stub.with_suffix('.o')] if label=='intermediate-stub' else []),
            BUILD/'calls_test.o',BUILD/'abi_calls.o',BUILD/'call_stack.o','-o',target_exe])
        refused(label+'-linked',lambda p=target_exe:
            linked(p,name,report['object'],template,label),target_exe)
    for label,place,target in [('positive-range-overflow',0,1<<27),
                               ('negative-range-overflow',(1<<27)+4,0),('unaligned-target',0,2)]:
        refused(label,lambda p=place,t=target:branch_displacement(p,t))
    if branch_displacement(0,(1<<27)-4)!=(1<<27)-4 or branch_displacement(1<<27,0)!=-(1<<27):
        raise RuntimeError('valid branch range endpoints rejected')
    result=dict(scope='artifact/parser refusals, not semantic counterexamples',results=rows,
        supported_range_endpoints=[-(1<<27),(1<<27)-4],
        inputs={str(p):digest(p) for p in [source,ROOT/'tools/call_artifacts.py',
            ROOT/'tools/call_rejections.py',*[l['path'] for l in report['layouts']]]})
    (BUILD/'call-rejections.json').write_text(json.dumps(result,indent=2)+'\n')
    print('call artifact refusals:',len(rows),flush=True)
    return result


if __name__=='__main__':verify(json.loads((BUILD/'calls-layouts.json').read_text()))
