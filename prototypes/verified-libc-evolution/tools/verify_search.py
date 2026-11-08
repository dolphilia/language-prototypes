"""Kernel/native gates for the finite pool and for the frozen selected body."""
import json
import secrets
from config import ROOT, BUILD, digest
from audit_m1 import validate_inputs
from verify_regions import require_m1
from search_proofs import prepare, SOURCES
from search_build import native
from prover import run_session

REPORT=ROOT/'reports/m3/search'
FROZEN=ROOT/'reports/m3/candidates.json'


def require_resources():
    r=json.loads((ROOT/'reports/m3/resources/verification.json').read_text())
    if not r['complete'] or len(r['proof']['checks'])!=20:
        raise RuntimeError('current E7a resource theorems required')
    if r['proof']!=json.loads((BUILD/'proof-resources.json').read_text()):
        raise RuntimeError('resource receipt differs')
    validate_inputs(r['proof']['inputs'])
    return r


def require_pool():
    r=json.loads((REPORT/'pool-verification.json').read_text())
    if not r['verification_passed'] or r['unknown'] or len(r['proved'])!=4:
        raise RuntimeError('complete finite-pool verification required')
    if r['proof']!=json.loads((BUILD/'proof-search-pool.json').read_text()):
        raise RuntimeError('pool receipt differs')
    validate_inputs(r['proof']['inputs'])
    if r['frozen_sha256']!=digest(FROZEN):raise RuntimeError('frozen pool changed')
    return r


def verify(selected=None):
    require_m1();resources=require_resources()
    pool=None;selection=None
    if selected:
        pool=require_pool();selection=json.loads((REPORT/'selection.json').read_text())
        if selection['selected']!=selected or selected not in pool['proved']:
            raise RuntimeError('selected candidate does not match the frozen selection')
        if selection['frozen_sha256']!=digest(FROZEN):raise RuntimeError('selection pool changed')
    stem='search-selected' if selected else 'search-pool'
    (BUILD/('proof-'+stem+'.json')).unlink(missing_ok=True)
    path,checks,generated=prepare(selected)
    tested=native([selected] if selected else None,tag='selected' if selected else 'pool')
    expected_count=21 if selected else 51
    if len(checks)!=expected_count:raise RuntimeError('candidate certificate coverage differs')
    sources=[ROOT/'tools'/n for n in ['verify_search.py','search_build.py','search_proofs.py',
                                      'search_witnesses.py','blocks.py']]
    sources += [ROOT/'generator/candidates.py',FROZEN,ROOT/'reports/m3/search-protocol.md']
    sources += [ROOT/'proofs'/n for n in [*SOURCES,'blocks.ml','memory.ml','witnesses.ml',
                   'costs.ml','resource_tail.ml','resource_bulk.ml','resource_composition.ml','resource_chunk.ml']]
    if selected:sources.append(REPORT/'selection.json')
    records=json.loads(FROZEN.read_text())['candidates']
    code=[BUILD/(r['name']+'.o') for r in records]
    inputs=[path,*generated,*sources,*code,*BUILD.glob('vp2_block_*.o')]
    proof=run_session(stem,'loadt '+json.dumps(str(path))+';;',checks,inputs=inputs)
    require_m1();require_resources()
    proved=[selected] if selected else [r['name'] for r in records if not r['name'].endswith('_bad')]
    result={'verification_passed':True,'phase_complete':False,
            'scope':'selected body only' if selected else 'frozen finite pool only',
            'nonce':secrets.token_hex(24),'proof':proof,'native':tested,
            'frozen_sha256':digest(FROZEN),'proved':proved,'unknown':[],
            'counterexamples':[{'name':'ve_opt_u2_bad','n':8,'steps':11,
                'violation':'second 8-byte load starts at src+8, outside the public 8-byte input',
                'evidence':['HOL initial state','HOL numeric preconditions','HOL finite trace','native guarded execution with a normal control']}],
            'private_stack_bytes':0,'heap_bytes':0,'runtime_proof_bytes':0,
            'resource_prerequisite_nonce':resources['proof']['nonce'],
            'body_bytes':{r['name']:r['bytes'] for r in records if r['name'] in proved},
            'new_encoding_limit':'E6a checks M1 forms/encodings; E7 adds branch displacements and CMP immediate 16 within those forms, checked here by HOL and native whole-function tests, not a new independent per-instruction matrix'}
    if selected:
        result['selection_sha256']=digest(REPORT/'selection.json')
        result['pool_verification_nonce']=pool['nonce']
    REPORT.mkdir(exist_ok=True)
    (REPORT/('selected-verification.json' if selected else 'pool-verification.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(f'{stem}: all functional/frame/access/resource/native gates passed; selection/evaluation audit remains separate',flush=True)
    return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--selected')
    verify(parser.parse_args().selected)
