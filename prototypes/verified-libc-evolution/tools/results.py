"""Candidate result and infrastructure status have separate meanings."""
from __future__ import annotations
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Result:
    candidate: str
    contract: str
    status: str
    evidence_kind: str
    reason: str
    evidence: tuple[str, ...] = ()
    code_sha256: str | None = None

    def __post_init__(self):
        if self.status not in {'proved','counterexample','unknown','infrastructure_error'}:
            raise ValueError('invalid result classification')
        permitted={'proved':{'hol_closed_theorem'},
            'counterexample':{'hol_execution','executable_model','native'},
            'unknown':{'unsupported','timeout','unfinished_proof'},
            'infrastructure_error':{'missing_input','malformed_input','driver_error','input_changed'}}
        if self.evidence_kind not in permitted[self.status] or not self.reason:
            raise ValueError('classification has inconsistent evidence')
        if self.status in {'proved','counterexample'} and not self.evidence:
            raise ValueError('proof/violation evidence missing')
        if self.status in {'proved','counterexample'} and (
            self.code_sha256 is None or len(self.code_sha256)!=64 or
            any(c not in '0123456789abcdef' for c in self.code_sha256)):
            raise ValueError('actual code identity missing')

    def as_json(self):
        result=asdict(self)
        result['evidence']=list(self.evidence)
        return result


def admissible(results, required_contracts):
    results=list(results)
    if any(r.status=='infrastructure_error' for r in results):
        raise RuntimeError('verification infrastructure failed')
    if len({(r.candidate,r.code_sha256) for r in results})>1:
        raise ValueError('contracts from different candidates/code cannot be combined')
    by_contract={r.contract:r for r in results}
    if len(by_contract)!=len(results):
        raise ValueError('duplicate contract result')
    return set(by_contract)==set(required_contracts) and all(r.status=='proved' for r in results)


def validate_concrete_input(*,pc,code_size,dst,src,n):
    """No physical mapping claim: numeric part of the existing public contract."""
    limit=1<<64
    if any(type(v) is not int for v in (pc,code_size,dst,src,n)):
        raise ValueError('expected integer model addresses')
    if not(0<=pc<limit and pc%4==0 and 0<dst<limit and 0<src<limit and 0<=n<limit):
        raise ValueError('input is outside the public contract')
    if pc+code_size>limit or dst+n>limit or src+n>limit:
        raise ValueError('input wraps')
    def disjoint(a,k,b,l):
        return k==0 or l==0 or a+k<=b or b+l<=a
    if not disjoint(pc,code_size,dst,n) or not disjoint(src,n,dst,n):
        raise ValueError('input overlaps; not a public-contract counterexample')
    return True
