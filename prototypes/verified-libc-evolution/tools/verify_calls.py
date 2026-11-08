"""E5 fresh-kernel verification of two actual linked code bundles."""
import json
from pathlib import Path
from config import ROOT,BASE,BUILD,digest
from verify_regions import require_m1
from build_calls import prepare as build
from blocks import prepare as blocks
from calls_proof import declarations
from call_mutations import prepare as mutations
from call_rejections import verify as rejections
from call_witnesses import prepare as witnesses
from call_ingest_checks import prepare as ingest
from prover import run_session


def verify():
    (BUILD/'proof-calls.json').unlink(missing_ok=True)
    require_m1();layout=build();negative=mutations();refused=rejections(layout)
    block_file,block_checks=blocks();call_file,call_checks=declarations(layout)
    witness_file,witness_checks=witnesses(layout,negative)
    ingest_file,ingest_names,ingest_paths=ingest(layout)
    sources=[block_file,ROOT/'proofs/memcpy_chunk8.ml',ROOT/'proofs/chunk_access.ml',
             call_file,witness_file,ingest_file]
    checks=block_checks+['chunk8:tail','chunk8:bulk','chunk8:public','chunk8:tail-access',
        'chunk8:bulk-access','chunk8:access-strong','chunk8:access']+call_checks+witness_checks
    names=['blocks.ml','memory.ml','chunk_tail.ml','chunk_bulk.ml','chunk_tail_access.ml','chunk_bulk_access.ml',
        'linked_span.ml','call_specs.ml','calls.ml','witnesses.ml','call_witnesses.ml']
    helpers=['build_calls.py','call_artifacts.py','call_rejections.py','call_mutations.py',
        'calls_proof.py','call_witnesses.py','call_ingest_checks.py','verify_calls.py','blocks.py']
    paths=[*sources,*[ROOT/'proofs'/n for n in names],*[ROOT/'tools'/n for n in helpers],
        ROOT/'generator/main.ml',ROOT/'generator/calls.ml',BASE/'proofs/specs.ml',
        ROOT/'tests/calls.c',ROOT/'tests/call_negative.c',ROOT/'tests/call_stack.S',ROOT/'tests/abi.S',
        ROOT/'include/vp2_calls.h',ROOT/'include/vp2_memory.h',ROOT/'include/vp2_evolution.h',
        BUILD/'vp2_call_copy.o',BUILD/'vp2_memcpy_chunk8.o',
        *[BUILD/(n+'.o') for n in block_checks],*[l['path'] for l in layout['layouts']],
        negative['control']['path'],*[r['path'] for r in negative['results']],*[r['object'] for r in negative['results']],
        *[r['path'] for r in refused['results'] if r['path']],*ingest_paths]
    body='\n'.join('ve_timed '+json.dumps('module:'+p.name)+' (fun () -> loadt '+json.dumps(str(p))+');;' for p in sources)
    proof=run_session('calls',body,checks,inputs=paths)
    require_m1()
    result=dict(scope='E5 verification; measurement/completion audit pending',verification_passed=True,
        phase_complete=False,proof=proof,layouts=layout,mutations=negative,artifact_refusals=refused,
        linked_ingest_refusals=ingest_names,caller_body_bytes=24,callee_body_bytes=76,
        private_stack_bytes=16,private_heap_bytes=0,ghost_runtime_bytes=0,
        additional_trust=['unverified restricted Mach-O extractor and linked-span byte ingestion',
            'LLVM symbol comparison is an independent observation, not a verified parser',
            'OS maps the exact verified code with a common slide preserving relative offsets',
            'ordinary valid RAM/stack mappings and lifetime/exclusivity supplied by caller'],
        exclusions=['general linker verification','dynamic or indirect callee resolution',
            'a general Hoare-theorem negation inferred from a failed tactic'])
    folder=ROOT/'reports/m2'
    (folder/'calls-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    (folder/'calls-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('E5 proof/native gates passed; evaluation and E3b/M2 remain incomplete',flush=True)
    return result


if __name__=='__main__':verify()
