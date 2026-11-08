"""E3b actual runtime checks, region protocol and finite violation witnesses."""
from datetime import datetime,timezone
import json
from pathlib import Path
from config import ROOT,BASE,BUILD,digest
from build_split import prepare as build,prerequisites
from split_mutations import prepare as mutations
from split_proof import prepare as declarations
from split_witnesses import prepare as witnesses
from blocks import prepare as blocks
from verify_regions import REGION_CHECKS
from audit_m1 import validate_inputs
from prover import run_session
from results import Result,admissible

REGION_SOURCES=['regions.ml','region_bounds.ml','region_split.ml','region_policy.ml','region_negatives.ml','region_calls.ml']
SPLIT_SOURCES=['split_specs.ml','split_success.ml','split_geometry.ml','split_public.ml',
               'split_trace.ml','split_access.ml','split_protocol.ml','split_witnesses.ml']


def verify():
    (BUILD/'proof-split.json').unlink(missing_ok=True)
    prior_calls,prior_regions=prerequisites()
    stable=[Path(__file__).resolve(),ROOT/'generator/split.ml',ROOT/'generator/calls.ml',ROOT/'generator/main.ml',
        *[ROOT/'proofs'/n for n in REGION_SOURCES+SPLIT_SOURCES],
        *[ROOT/'tools'/n for n in ['build_split.py','split_mutations.py','split_proof.py','split_witnesses.py',
            'call_artifacts.py','build.py','blocks.py']],ROOT/'tests/split.c',ROOT/'tests/split_negative.c',
        ROOT/'tests/split_abi.S',ROOT/'tests/call_stack.S',ROOT/'include/vp2_split.h',
        ROOT/'include/vp2_evolution.h',ROOT/'include/vp2_memory.h',BASE/'tools/macho.py']
    initial_inputs={str(p):digest(p) for p in stable}
    layout=build();negative=mutations();block_file,block_checks=blocks()
    call_file,call_checks=declarations(layout);witness_file,witness_checks=witnesses(layout,negative)
    sources=[block_file,ROOT/'proofs/memcpy_chunk8.ml',ROOT/'proofs/chunk_access.ml',
        *[ROOT/'proofs'/n for n in REGION_SOURCES],call_file,witness_file]
    checks=block_checks+['chunk8:tail','chunk8:bulk','chunk8:public','chunk8:tail-access',
        'chunk8:bulk-access','chunk8:access-strong','chunk8:access']+[
        'regions:'+n for n in REGION_CHECKS]+call_checks+witness_checks
    helpers=['memory.ml','blocks.ml','chunk_tail.ml','chunk_bulk.ml','chunk_tail_access.ml',
        'chunk_bulk_access.ml','linked_span.ml','witnesses.ml','call_witnesses.ml']
    paths=[*stable,*sources,*[ROOT/'proofs'/n for n in helpers],BASE/'proofs/specs.ml',
        BUILD/'vp2_copy_split.o',BUILD/'vp2_memcpy_chunk8.o',*[BUILD/(n+'.o') for n in block_checks],
        layout['layout']['path'],negative['control']['path'],
        *[r['object'] for r in negative['results']],*[r['layout']['path'] for r in negative['results']]]
    body='\n'.join('ve_timed '+json.dumps('module:'+p.name)+
        ' (fun () -> loadt '+json.dumps(str(p))+');;' for p in sources)
    proof=run_session('split',body,checks,inputs=paths)
    validate_inputs(initial_inputs);prerequisites()
    specs=[('ve_split_call_contract','split:public'),('ve_split_access_contract','split:access'),
           ('ve_split_protocol_contract','split:machine-protocol')]
    selected=[Result('vp2_copy_split',contract,'proved','hol_closed_theorem',label,
        ('reports/m2/split-proof.json',label),layout['layout']['sha256']) for contract,label in specs]
    if not admissible(selected,[s[0] for s in specs]):raise RuntimeError('checked caller is not admissible')
    candidates=[dict(candidate='vp2_copy_split',admissible=True,contracts=[r.as_json() for r in selected])]
    for r in negative['results']:
        label='split-mut:'+r['name']+':execution'
        if label not in proof['checks']:raise RuntimeError('checked caller mutation proof missing')
        result=Result('split-mut:'+r['name'],'checked-split.'+r['kind'],'counterexample','hol_execution',
            'valid root/stack initial state; finite wrong return/data or out-of-root access, not a failed tactic',
            ('reports/m2/split-proof.json',label),r['layout']['sha256'])
        candidates.append(dict(candidate=result.candidate,admissible=False,contracts=[result.as_json()]))
    result=dict(timestamp=datetime.now(timezone.utc).isoformat(),scope='E3b verification; evaluation/audit pending',
        verification_passed=True,phase_complete=False,proof=proof,layouts=layout,mutations=negative,
        source_files=initial_inputs,candidates=candidates,caller_body_bytes=80,callee_body_bytes=76,
        private_stack_bytes=16,private_heap_bytes=0,ghost_runtime_bytes=0,
        prerequisites=dict(e5_proof_nonce=prior_calls['proof']['nonce'],e3a_proof_nonce=prior_regions['proof']['nonce']),
        conditions_supplied_by=dict(external='valid live exclusive owned ordinary RAM plus separate valid private stack and mapped code',
            runtime='0 < split < L, n <= split, n <= L-split before subtraction/subregion construction/copy',
            derived='nonnull/nowrap/subregion bounds/nonoverlap, child ABI and return address, permission transitions for the same checked sizes'),
        limits=['one sequential ghost ledger is a protocol, not linear HOL resources or a general borrow checker',
            'ownership-to-RAM correspondence, physical mapping/lifetime/exclusivity and OS maintenance remain external',
            'restricted actual post-link code verification, not general relocation/linker or OS verification',
            'finite violations and native observations are not general Hoare-theorem negations'])
    folder=ROOT/'reports/m2'
    (folder/'split-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    (folder/'split-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('E3b proof/native gates passed; evaluation and M2/M3 audit remain incomplete',flush=True)
    return result


if __name__=='__main__':verify()
