"""Fresh kernel evidence for E3a, including re-proved M1 call contracts."""
from datetime import datetime,timezone
import json
from pathlib import Path
from config import ROOT,BASE,BUILD,digest
from audit_m1 import validate_inputs,validate_costs,validate_measurements
from blocks import prepare as blocks
from prover import run_session

REGION_CHECKS=[
    'root-ledger','borrow-valid','end-valid','invalidate-valid','borrow-rights',
    'owner-returned','expired-generation','active-invalidation-rejected',
    'transition-valid','trace-valid','split-bounds','derive-copy-preconditions',
    'split-borrows','split-permissions','split-returned','checked-success','checked-failure',
    'exclusive-separation','authorized-bounds','overlap-write-rejected','shared-overlap-allowed',
    'capacity-rejected','unguarded-subtraction-and-address-rejected','abstract-copy','abstract-access',
    'abstract-protocol']


def require_m1():
    report=json.loads((ROOT/'reports/m1/audit.json').read_text())
    if report['scope']!='M1 only' or not report['complete']:
        raise RuntimeError('M1 completion audit required before E3a')
    validate_inputs(report['evidence_sha256'])
    verified=json.loads((ROOT/'reports/m1/verification.json').read_text())
    if not verified['verification_passed'] or not verified['phase_complete']:
        raise RuntimeError('M1 verification/evaluation incomplete')
    validate_inputs(verified['source_files']);validate_inputs(verified['proof']['inputs'])
    validate_costs(json.loads((ROOT/'reports/m1/proof-costs.json').read_text()))
    validate_measurements(json.loads((ROOT/'reports/m1/measurements.json').read_text()))
    return report


def verify():
    prerequisite=require_m1()
    block_file,block_checks=blocks()
    m1_sources=['memcpy_chunk8.ml','chunk_access.ml']
    region_sources=['regions.ml','region_bounds.ml','region_split.ml','region_policy.ml',
                    'region_negatives.ml','region_calls.ml']
    sources=[block_file,*[ROOT/'proofs'/n for n in m1_sources+region_sources]]
    checks=block_checks+['chunk8:tail','chunk8:bulk','chunk8:public','chunk8:tail-access',
        'chunk8:bulk-access','chunk8:access-strong','chunk8:access']
    checks+=['regions:'+n for n in REGION_CHECKS]
    indirect=['blocks.ml','chunk_tail.ml','chunk_bulk.ml','memory.ml',
              'chunk_tail_access.ml','chunk_bulk_access.ml']
    code=['vp2_memcpy_chunk8',*[name for name in block_checks]]
    inputs=[*sources,*[ROOT/'proofs'/n for n in indirect],BASE/'proofs/specs.ml',
            Path(__file__).resolve(),ROOT/'tools/blocks.py',
            *[BUILD/(name+'.o') for name in code]]
    body='\n'.join('ve_timed '+json.dumps('module:'+p.name)+
        ' (fun () -> loadt '+json.dumps(str(p))+');;' for p in sources)
    proof=run_session('regions',body,checks,inputs=inputs)
    require_m1()
    report=dict(timestamp=datetime.now(timezone.utc).isoformat(),scope='E3a only',
        complete=True,m1_prerequisite_snapshot=prerequisite,proof=proof,
        region_theorems=len(REGION_CHECKS),
        abstract_call_boundary='entry registers already contain checked and derived arguments; BL and runtime branch paths remain E5/E3b',
        ghost_runtime_bytes=0,
        external_roots=['ordinary mapped RAM and lifetime throughout the call',
            'one exclusive root authority binds the owner identifier to arena and capacity',
            'one current ledger flows through the sequential transition trace; classical HOL facts are not linear resources',
            'the physical-memory/ghost-ledger correspondence and OS maintenance of validity',
            'the existing ISA-model, HOL-kernel, execution and artifact-loader trust boundaries'],
        exclusions=['general borrow checker','concurrency','allocator or OS verification','actual caller BL/check instructions'])
    folder=ROOT/'reports/m2';folder.mkdir(exist_ok=True)
    (folder/'regions-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    (folder/'regions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('E3a evidence complete; actual caller paths and M2 remain incomplete',flush=True)
    return report


if __name__=='__main__': verify()
