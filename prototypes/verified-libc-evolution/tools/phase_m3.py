"""Fresh M3 entry: ISA observations, feasibility, resources, pool, selected body."""
from datetime import datetime, timezone
import json
import secrets
import sys
import time
from config import ROOT, BUILD, digest
from verify_m1 import snapshot
from verify_regions import require_m1
from audit_m1 import validate_inputs


def source_snapshot():
    return snapshot() | {str(p):digest(p) for p in [ROOT/'isa-backend.lock.json',
        ROOT/'reports/m3/candidates.json',ROOT/'reports/m3/search-protocol.md',
        ROOT/'reports/m3/search-measurement-protocol.md']}


def stage(proof):
    return dict(proof_nonce=proof['nonce'],checks=proof['checks'],seconds=proof['elapsed_seconds'])


def save(r):
    proofs=[v for v in r['stages'].values() if 'checks' in v]
    r['checked_occurrences']=sum(len(p['checks']) for p in proofs)
    r['distinct_check_names']=len({c for p in proofs for c in p['checks']})
    text=json.dumps(r,indent=2)+'\n'
    (BUILD/'verification-m3.json').write_text(text)
    (ROOT/'reports/m3/verification.json').write_text(text)


def verify():
    started=time.monotonic();(BUILD/'verification-m3.json').unlink(missing_ok=True)
    require_m1()
    from audit_m2 import verification as m2_verification
    m2_verification()
    m2=json.loads((ROOT/'reports/m2/audit.json').read_text())
    if not m2['complete']:raise RuntimeError('M2 completion is required before the combined M3 entry')
    validate_inputs(m2['evidence_sha256'])
    before=source_snapshot()
    roots={p:digest(ROOT/'reports'/p/'audit.json') for p in ['m1','m2']}
    from verify_isa import verify as isa
    from independent_recheck import investigate
    from verify_resources import verify as resources
    from verify_search import verify as pool
    stages={}
    print('M3 fresh stage: E6a ISA differential checks',flush=True)
    stages['isa']=stage(isa()['proof'])
    print('M3 fresh stage: E6b independent-check feasibility',flush=True)
    feasibility=investigate()
    stages['independent']=dict(investigation_nonce=feasibility['nonce'],seconds=feasibility['seconds'],
                               independent_recheck_success=feasibility['independent_recheck_success'])
    print('M3 fresh stage: E7a resources',flush=True)
    stages['resources']=stage(resources()['proof'])
    print('M3 fresh stage: E7b frozen pool',flush=True)
    stages['pool']=stage(pool()['proof'])
    selection=ROOT/'reports/m3/search/selection.json'
    if selection.exists():
        print('M3 fresh stage: E7b selected body after the fixed choice',flush=True)
        stages['selected']=stage(pool(json.loads(selection.read_text())['selected'])['proof'])
    if source_snapshot()!=before or roots!={p:digest(ROOT/'reports'/p/'audit.json') for p in roots}:
        raise RuntimeError('M3 sources or completed prerequisites changed during verification')
    require_m1();m2_verification()
    r=dict(timestamp=datetime.now(timezone.utc).isoformat(),nonce=secrets.token_hex(24),
        scope='M3 only',verification_passed=True,phase_complete=False,source_files=before,
        prerequisite_audits=roots,stages=stages,seconds=time.monotonic()-started,invoked_as=list(sys.argv))
    save(r)
    print('M3 proof/native/investigation gates passed; evaluate and run audit_m3.py for completion',flush=True)
    return r


def measure():
    from audit_m3 import verification
    r=verification(require_selected=False)
    from measure_search import measure as search
    measured=search()
    r['stages']['selected']=stage(measured['selected_proof_snapshot'])
    r['stages']['selected']['origin']='fresh process after frozen choice in measure-m3'
    save(r)
    from audit_m3 import audit
    return audit()
