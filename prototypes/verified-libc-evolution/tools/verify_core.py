"""Fresh proof of all implemented M1 contracts and model witnesses.

This is proof evidence, not completion of performance/edit-cost evaluations.
"""
import argparse
import json
from config import ROOT,BASE,BUILD
from counterexamples import prepare as counterexamples
from blocks import prepare as blocks
from composition import prepare as composition
from chunk_mutations import prepare as mutations
from prover import run_session


def verify(stem='m1-core'):
    e0,e0checks=counterexamples();b,bchecks=blocks();p,pchecks=composition()
    m,mchecks=mutations()
    names=['nontermination.ml','validrewrite.ml']
    sources=[e0,*[ROOT/'proofs'/n for n in names],b,p,
        *[ROOT/'proofs'/n for n in ['composition_negatives.ml','public_frame.ml',
            'memcpy_chunk8.ml','chunk_access.ml','memset.ml','zero.ml']],m,
        ROOT/'proofs/model_boundaries.ml']
    checks=e0checks+['self_branch:stable','self_branch:nonreachability','equivalent:public']
    checks+=bchecks+pchecks+['composition:weak-flags-fixture','public:preserves_x19',
        'chunk8:tail','chunk8:bulk','chunk8:public','chunk8:tail-access','chunk8:bulk-access',
        'chunk8:access-strong','chunk8:access','fill:core','fill:public',
        'fill:access-strong','fill:access','chunk8:zero-no-data']
    checks+=mchecks+['chunk8:numeric-high-end','chunk8:numeric-large',
                    'chunk8:wrap-outside-contract','chunk8:aligned-guard']
    indirect=['blocks.ml','composition.ml','witnesses.ml','memory.ml','chunk_tail.ml',
              'chunk_bulk.ml','chunk_tail_access.ml','chunk_bulk_access.ml']
    inputs=[*sources,*[ROOT/'proofs'/n for n in indirect],BASE/'proofs/specs.ml',
        ROOT/'tools/verify_core.py',ROOT/'generator/main.ml',
        *BUILD.glob('vp2_*.o'),*BUILD.glob('ve_mut_*.o'),*BUILD.glob('chunk_mut_*.o')]
    body='\n'.join('ve_timed '+json.dumps('module:'+p.name)+
        ' (fun () -> loadt '+json.dumps(str(p))+');;' for p in sources)
    return run_session(stem,body,checks,inputs=inputs)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--stem',default='m1-core')
    verify(parser.parse_args().stem)
