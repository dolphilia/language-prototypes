"""Fresh end-to-end M2 verification and its separate measurement entry."""
from datetime import datetime,timezone
import json
import secrets
import sys
import time
from config import ROOT,BUILD,digest
from verify_m1 import snapshot
from audit_m1 import validate_inputs
from verify_regions import require_m1


def finish_evaluation(name):
    """Refresh stale measurements only after their current proof has exited."""
    path=ROOT/'reports/m2'/(name+'-measurements.json')
    stale=False
    try:
        measured=json.loads(path.read_text())
        validate_inputs(measured['method_inputs'])
        validate_inputs(measured['proof_snapshot']['inputs'])
    except (OSError,ValueError,KeyError,RuntimeError):stale=True
    if stale:
        import importlib
        print('M2 refresh evaluation:',name,flush=True)
        importlib.import_module('measure_'+name).measure()
    import importlib
    return importlib.import_module('audit_'+name).audit()


def verify():
    started=time.monotonic();gate=BUILD/'verification-m2.json';gate.unlink(missing_ok=True)
    require_m1();before=snapshot();m1_digest=digest(ROOT/'reports/m1/audit.json')
    from verify_regions import verify as regions
    from verify_memmove import verify as memmove
    from verify_calls import verify as calls
    from verify_split import verify as split
    stages={}
    for name,action in [('regions',regions),('memmove',memmove),('calls',calls),('split',split)]:
        print('M2 fresh stage:',name,flush=True)
        result=action()
        stages[name]=dict(proof_nonce=result['proof']['nonce'],checks=result['proof']['checks'],
                          proof_seconds=result['proof']['elapsed_seconds'])
        if name in ['memmove','calls','split']:
            # In particular E3b starts only after E5's proof and evaluation.
            # No proof process is active while an evaluation is refreshed.
            finish_evaluation(name)
    after=snapshot()
    if before!=after or digest(ROOT/'reports/m1/audit.json')!=m1_digest:
        raise RuntimeError('M2 source or M1 prerequisite changed during verification')
    validate_inputs(before);require_m1()
    result=dict(timestamp=datetime.now(timezone.utc).isoformat(),nonce=secrets.token_hex(24),
        scope='M2 only',verification_passed=True,phase_complete=False,
        invoked_as=list(sys.argv),source_files=before,m1_audit_sha256=m1_digest,stages=stages,
        seconds=time.monotonic()-started,
        checked_occurrences=sum(len(s['checks']) for s in stages.values()),
        distinct_check_names=len({n for s in stages.values() for n in s['checks']}))
    gate.write_text(json.dumps(result,indent=2)+'\n')
    (ROOT/'reports/m2/verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print('M2 proof/native gates passed; use audit_m2.py for current saved evaluations or measure-m2 to rerun them',flush=True)
    return json.loads(gate.read_text())


def measure():
    from audit_m2 import verification
    verification()
    from measure_memmove import measure as memmove
    from measure_calls import measure as calls
    from measure_split import measure as split
    for action in [memmove,calls,split]:action()
    from audit_m2 import audit
    return audit()
