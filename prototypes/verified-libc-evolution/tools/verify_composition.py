"""Fresh check of the implemented subset of E1/E2; not a phase-completion gate."""
import json
from config import ROOT,BUILD
from blocks import prepare as blocks
from composition import prepare as composition
from prover import run_session


def verify():
    b,bc=blocks();p,pc=composition()
    sources=[b,p,ROOT/'proofs/composition_negatives.ml',ROOT/'proofs/public_frame.ml',
             ROOT/'proofs/chunk_tail.ml']
    checks=bc+pc+['composition:weak-flags-fixture','public:preserves_x19','chunk8:tail']
    inputs=[*sources,ROOT/'proofs/blocks.ml',ROOT/'proofs/composition.ml',
        *BUILD.glob('vp2_block_*.o'),*BUILD.glob('vp2_copy*.o'),BUILD/'vp2_memcpy_chunk8.o']
    body='\n'.join('loadt '+json.dumps(str(p))+';;' for p in sources)
    return run_session('composition',body,checks,inputs=inputs)


if __name__=='__main__': verify()
