"""E4 proof/runtime gates. Completion still requires the performance audit."""
import json
from pathlib import Path
from config import ROOT,BUILD,digest
from blocks import prepare as blocks
from prover import run_session
from verify_regions import require_m1
from native_m2 import memmove as native
from move_mutations import prepare as mutations
from native_move_mutations import verify as native_mutations
from m2_artifacts import leaf
from results import Result,admissible


def verify():
    require_m1();observed=native()
    block_file,block_checks=blocks();mutation_file,mutation_checks=mutations()
    negative=native_mutations()
    names=['memmove_specs.ml','memmove_bounds.ml','memmove_forward.ml','memmove_backward.ml',
           'memmove.ml','memmove_zero.ml','memmove_access_loops.ml','memmove_access.ml']
    sources=[block_file,*[ROOT/'proofs'/n for n in names],mutation_file]
    checks=block_checks+['memmove:forward-unread-range','memmove:backward-unread-range',
        'memmove:forward','memmove:backward','memmove:public','memmove:zero-no-data','memmove:same-no-data',
        'memmove:forward-access','memmove:backward-access','memmove:access-strong','memmove:access']+mutation_checks
    manifest=json.loads((BUILD/'move-mutations.json').read_text())
    inputs=[*sources,ROOT/'proofs/blocks.ml',ROOT/'proofs/witnesses.ml',ROOT/'proofs/memmove_witnesses.ml',
        Path(__file__).resolve(),ROOT/'tools/blocks.py',ROOT/'tools/build_m2.py',ROOT/'tools/move_mutations.py',
        ROOT/'tools/native_m2.py',ROOT/'tools/native_move_mutations.py',ROOT/'tools/m2_artifacts.py',
        ROOT/'generator/main.ml',ROOT/'generator/m2.ml',
        BUILD/'vp2_memmove.o',*[BUILD/(n+'.o') for n in block_checks],*[Path(r['object']) for r in manifest]]
    body='\n'.join('ve_timed '+json.dumps('module:'+p.name)+
        ' (fun () -> loadt '+json.dumps(str(p))+');;' for p in sources)
    proof=run_session('memmove',body,checks,inputs=inputs)
    artifacts=leaf('vp2_memmove',['test_memmove'])
    if any(r['body_bytes']>256 for r in artifacts):raise RuntimeError('E4 body budget exceeded')
    selected=[Result('vp2_memmove',contract,'proved','hol_closed_theorem',label,
        ('reports/m2/memmove-proof.json',label),digest(BUILD/'vp2_memmove.o'))
        for contract,label in [('ve_move_contract','memmove:public'),('ve_move_access_contract','memmove:access')]]
    if not admissible(selected,['ve_move_contract','ve_move_access_contract']):raise RuntimeError('memmove not admissible')
    candidates=[dict(candidate='vp2_memmove',admissible=True,contracts=[r.as_json() for r in selected])]
    for r in manifest:
        label='move-mut:'+r['name']+':execution'
        if label not in proof['checks'] or proof['inputs'].get(r['object'])!=digest(r['object']):
            raise RuntimeError('mutation proof/code binding missing')
        result=Result('move-mut:'+r['name'],'memmove.'+r['kind'],'counterexample','hol_execution',
            'valid initial state with a finite first-return data violation or out-of-bounds access; not a failed tactic or a general Hoare negation',
            ('reports/m2/memmove-proof.json',label),digest(r['object']))
        candidates.append(dict(candidate=result.candidate,admissible=False,contracts=[result.as_json()]))
    require_m1()
    report=dict(scope='E4 verification, performance audit pending',verification_passed=True,phase_complete=False,
        proof=proof,native=observed,native_mutations=negative,artifacts=artifacts,
        body_bytes=68,private_stack_bytes=0,private_heap_bytes=0,ghost_runtime_bytes=0,
        candidates=candidates,
        remaining=['performance and size report from the predeclared M2 method','E4/M2 completion audit'],
        limits=['ordinary sequential RAM and external validity/lifetime/exclusive update contract',
            'same initial source snapshot, not whole-source preservation during overlap',
            'finite model/native negative observations are distinguished from a general Hoare-contract negation'])
    folder=ROOT/'reports/m2';folder.mkdir(exist_ok=True)
    (folder/'memmove-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    (folder/'memmove-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('E4 proof/runtime gates passed; performance audit and M2 remain incomplete',flush=True)
    return report


if __name__=='__main__': verify()
