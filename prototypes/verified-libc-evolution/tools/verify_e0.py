"""Fresh acceptance for the E0 HOL evidence, independent of the dev session."""
import json
from config import ROOT, BASE, BUILD
from counterexamples import prepare
from prover import run_session


def verify():
    path,checks=prepare()
    sources=[path,*[ROOT/'proofs'/p for p in ['witnesses.ml','nontermination.ml','validrewrite.ml']],
             BASE/'proofs/specs.ml',BUILD/'vp2_equivalent_copy.o',*BUILD.glob('ve_mut_*.o')]
    body='\n'.join('loadt '+json.dumps(str(p))+';;' for p in sources[:4])
    checks += ['self_branch:stable','self_branch:nonreachability','equivalent:public']
    return run_session('e0',body,checks,inputs=sources)


if __name__=='__main__': verify()
