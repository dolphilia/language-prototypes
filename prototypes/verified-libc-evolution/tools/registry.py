"""Bind candidate decisions to actual object identity and checked contracts."""
import json
from config import ROOT,BUILD,digest
from results import Result,admissible


def build_registry(proof):
    checked=set(proof['checks']);entries=[]
    def proved(candidate,contract,label,obj):
        if label not in checked or proof['inputs'].get(str(obj))!=digest(obj):
            raise RuntimeError('proof/code binding missing for '+candidate)
        return Result(candidate,contract,'proved','hol_closed_theorem',label,
            ('reports/m1/core-proof.json',label),digest(obj))
    for candidate,contracts in [
        ('vp2_memcpy_chunk8',[('vp_copy_contract','chunk8:public'),('vp_copy_access_contract','chunk8:access')]),
        ('vp2_memset',[('vp_fill_contract','fill:public'),('vp_fill_access_contract','fill:access')])]:
        rows=[proved(candidate,contract,label,BUILD/(candidate+'.o')) for contract,label in contracts]
        if not admissible(rows,[c for c,l in contracts]): raise RuntimeError('selected kernel inadmissible')
        entries.append(dict(candidate=candidate,distribution_candidate=True,admissible=True,
                            contracts=[r.as_json() for r in rows]))
    equiv=proved('vp2_equivalent_copy','vp_copy_contract','equivalent:public',BUILD/'vp2_equivalent_copy.o')
    missing=Result('vp2_equivalent_copy','vp_copy_access_contract','unknown','unfinished_proof',
        'separate access theorem deliberately not supplied for this research-only candidate',
        (),digest(BUILD/'vp2_equivalent_copy.o'))
    entries.append(dict(candidate='vp2_equivalent_copy',distribution_candidate=False,
        admissible=admissible([equiv,missing],['vp_copy_contract','vp_copy_access_contract']),
        contracts=[equiv.as_json(),missing.as_json()]))
    for r in json.loads((BUILD/'chunk-mutations.json').read_text()):
        label='chunk-mut:'+r['name']+':execution'
        if label not in checked: raise RuntimeError('mutation execution missing')
        result=Result('chunk-mut:'+r['name'],'copy.'+r['property'],'counterexample','hol_execution',
            'valid initial state and finite violating execution; not a failed tactic',
            ('reports/m1/core-proof.json',label),digest(r['object']))
        entries.append(dict(candidate='chunk-mut:'+r['name'],distribution_candidate=False,
                            admissible=False,contracts=[result.as_json()]))
    return {'proof_nonce':proof['nonce'],'candidates':entries,
        'infrastructure_tests':'expected driver failures are separate from candidate unknowns; see verification tests/logs'}
