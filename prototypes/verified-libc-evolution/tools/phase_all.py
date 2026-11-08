"""The public verify-all command executes every unit through its real Make entry."""
from datetime import datetime, timezone
import json
import secrets
import subprocess
import sys
import time
from config import ROOT, BUILD, digest, environment
from phase_m3 import source_snapshot
from audit_m1 import validate_inputs


def sources():
    return source_snapshot() | {str(p):digest(p) for p in (ROOT/'reports').rglob('*protocol*.md')}


def run(target):
    command=['make',target,'PYTHON='+sys.executable]
    print('ALL entry:',target,flush=True)
    started=time.monotonic()
    subprocess.run(command,cwd=ROOT,env=environment(),check=True)
    return dict(target=target,command=command,seconds=time.monotonic()-started)


def m1_evaluation_current():
    try:
        from audit_m1 import validate_measurements,validate_costs
        validate_measurements(json.loads((ROOT/'reports/m1/measurements.json').read_text()))
        validate_costs(json.loads((ROOT/'reports/m1/proof-costs.json').read_text()))
        return True
    except (OSError,ValueError,RuntimeError):return False


def m3_evaluation_current():
    try:
        from measure_search import validate_trial
        for name in ['exploration','confirmation']:
            r=validate_trial(json.loads((ROOT/f'reports/m3/search/{name}.json').read_text()))
            for candidate in r['candidates']:
                a=candidate['sizes']
                if digest(a['benchmark'])!=a['benchmark_sha256'] or digest(a['size_executable'])!=a['size_sha256']:
                    return False
        return True
    except (OSError,ValueError,RuntimeError):return False


def verify():
    BUILD.mkdir(exist_ok=True)
    (BUILD/'verification-all.json').unlink(missing_ok=True)
    before=sources();started=time.monotonic();commands=[]
    old={}
    for phase in ['m1','m2','m3']:
        path=ROOT/'reports'/phase/'verification.json'
        if path.exists():
            r=json.loads(path.read_text());old[phase]=r['proof']['nonce'] if phase=='m1' else r['nonce']
    commands.append(run('verify-m1'))
    if not m1_evaluation_current():commands.append(run('measure-m1'))
    else:commands.append(run('audit-m1'))
    from verify_regions import require_m1
    require_m1()
    commands.append(run('verify-m2'))
    # This also supports a verification-only M2 invocation: completion still
    # needs all evaluations and the integrated audit, with no empty success.
    commands.append(run('audit-m2'))
    commands.append(run('verify-m3'))
    if not m3_evaluation_current():commands.append(run('measure-m3'))
    else:commands.append(run('audit-m3'))
    if sources()!=before:raise RuntimeError('full-plan sources changed during verify-all')
    validate_inputs(before)
    fresh={}
    for phase in ['m1','m2','m3']:
        r=json.loads((ROOT/'reports'/phase/'verification.json').read_text())
        if not r['phase_complete']:raise RuntimeError('required unit is incomplete: '+phase)
        fresh[phase]=r['proof']['nonce'] if phase=='m1' else r['nonce']
        if old.get(phase)==fresh[phase]:raise RuntimeError('a previous unit success was reused: '+phase)
    r=dict(scope='full E0-E7 plan',verification_passed=True,complete=False,
        nonce=secrets.token_hex(24),timestamp=datetime.now(timezone.utc).isoformat(),
        source_files=before,previous_unit_nonces=old,fresh_unit_nonces=fresh,
        commands=commands,seconds=time.monotonic()-started,
        audits={p:digest(ROOT/'reports'/p/'audit.json') for p in ['m1','m2','m3']})
    text=json.dumps(r,indent=2)+'\n'
    (BUILD/'verification-all.json').write_text(text)
    (ROOT/'reports/verification-all.json').write_text(text)
    from audit_all import audit
    return audit()
