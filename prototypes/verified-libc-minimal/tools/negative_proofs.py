"""Mutate real objects AND the imported literal, then require proof failure.

These checks reuse the positive proof tactics against the original contracts.
Byte equality alone therefore cannot make a mutant pass.
"""
from pathlib import Path
import json
import struct
from check_artifacts import ROOT
from macho import MachO
from run_proof import run_session


def mutate(name, function, offset, replacement):
    source=MachO(ROOT/'build'/f'{function}.o')
    symbol=source.symbol('_'+function)
    section=source.sections[symbol.section-1]
    start=section.offset+symbol.address-section.address
    changed=bytearray(source.data)
    old=struct.unpack_from('<I',changed,start+offset)[0]
    struct.pack_into('<I',changed,start+offset,replacement)
    target=ROOT/'build'/f'mut_{name}.o'
    target.write_bytes(changed)
    # The mutation must actually be present in the same span the importer sees.
    assert MachO(target).function(function,object_only=True)[offset:offset+4] == struct.pack('<I',replacement)
    return old,target


def prepare():
    base=(ROOT/'proofs/memcpy.ml').read_text().split('let VP_MEMCPY_SCALAR_CORE_CORRECT')[0]
    access=(ROOT/'proofs/accesses.ml').read_text()
    access=access[access.index('let vp_memcpy_scalar_access_strong'):access.index('let VP_MEMCPY_SCALAR_ACCESSES_STRONG')]
    sections=['''let vp_rejected = ref [];;
let vp_expect_rejection name thunk =
  let failure = try thunk(); None with Failure message -> Some message in
  match failure with
  | None -> failwith ("VP: mutated implementation accepted: " ^ name)
  | Some message -> vp_rejected := name :: !vp_rejected;
      print_endline ("VP_REJECT " ^ name ^ ": " ^ message);;
''']
    names=[]
    for name,offset,replacement,mode in [
        ('return',0,0xd2800000,'functional'),
        ('callee',0,0xd2800013,'functional'),
        ('termination',24,0x17fffffc,'functional'),
        # Access src+1 / dst+1 even for a one-byte call: exactly one past end.
        ('overread',8,0x39400424,'access'),
        ('overwrite',12,0x39000404,'access')]:
        old,path=mutate(name,'vp_memcpy_scalar',offset,replacement)
        lower=f'vp_mutation_{name}'; upper=f'VP_MUTATION_{name.upper()}'
        chunk=base.replace('vp_memcpy_scalar',lower).replace('VP_MEMCPY_SCALAR',upper)
        chunk=chunk.replace(f'{lower}.o',path.name)
        chunk=chunk.replace(f'0x{old:08x}',f'0x{replacement:08x}',1)
        sections.append(chunk)
        if mode=='functional':
            spec,tactic=lower+'_core_spec',lower+'_core_tac'
        else:
            chunk=access.replace('vp_memcpy_scalar',lower).replace('VP_MEMCPY_SCALAR',upper)
            sections.append(chunk)
            spec,tactic=lower+'_access_strong',lower+'_access_tac'
        sections.append(f'vp_expect_rejection "{name}" (fun () -> ignore(prove({spec},{tactic})));;')
        names.append(name)
    old,path=mutate('short_fast','vp_memcpy',0,0xf100105f)
    chunk=(ROOT/'proofs/optimized.ml').read_text().split('let VP_MEMCPY_CORRECT =')[0]
    chunk=chunk.replace('vp_memcpy_mc','vp_mut_fast_mc').replace('VP_MEMCPY_EXEC','VP_MUT_FAST_EXEC')
    chunk=chunk.replace('/build/vp_memcpy.o','/build/'+path.name)
    chunk=chunk.replace(f'0x{old:08x}','0xf100105f',1)
    chunk=chunk.replace('vp_memcpy_correct_tac','vp_mut_fast_correct_tac')
    sections.append(chunk)
    sections.append('vp_expect_rejection "short_fast" (fun () -> ignore(prove(vp_copy_contract `vp_mut_fast_mc`,vp_mut_fast_correct_tac)));;')
    names.append('short_fast')
    expected='['+';'.join(json.dumps(n) for n in names)+']'
    sections.append(f'if List.rev !vp_rejected <> {expected} then failwith "VP: incomplete semantic negatives";;')
    path=ROOT/'build/negative-proofs.ml'
    path.write_text('\n'.join(sections)+'\n')
    return path,names


def run_negatives():
    path,names=prepare()
    body='\n'.join(f'loadt {json.dumps(str(ROOT/"proofs"/p))};;'
        for p in ['macros.ml','memset.ml','memcpy.ml','accesses.ml','optimized.ml'])
    body+=f'\nloadt {json.dumps(str(path))};;'
    return run_session('semantic-negatives',body,['rejected:'+n for n in names])


if __name__=='__main__': run_negatives()
