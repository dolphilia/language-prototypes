"""Partial E4 functional/termination/frame evidence; access and mutants pending."""
import json
from pathlib import Path
from config import ROOT,BUILD
from blocks import prepare as blocks
from prover import run_session
from verify_regions import require_m1
from native_m2 import memmove as native


def verify():
    require_m1();observed=native()
    block_file,block_checks=blocks()
    names=['memmove_specs.ml','memmove_bounds.ml','memmove_forward.ml','memmove_backward.ml',
           'memmove.ml','memmove_zero.ml']
    sources=[block_file,*[ROOT/'proofs'/n for n in names]]
    checks=block_checks+['memmove:forward-unread-range','memmove:backward-unread-range',
        'memmove:forward','memmove:backward','memmove:public','memmove:zero-no-data','memmove:same-no-data']
    inputs=[*sources,ROOT/'proofs/blocks.ml',Path(__file__).resolve(),ROOT/'tools/blocks.py',
        ROOT/'tools/build_m2.py',ROOT/'generator/main.ml',ROOT/'generator/m2.ml',
        BUILD/'vp2_memmove.o',*[BUILD/(n+'.o') for n in block_checks]]
    body='\n'.join('ve_timed '+json.dumps('module:'+p.name)+
        ' (fun () -> loadt '+json.dumps(str(p))+');;' for p in sources)
    proof=run_session('memmove-core',body,checks,inputs=inputs)
    require_m1()
    report=dict(scope='E4 partial core',complete=False,proof=proof,native=observed,
        functional_frame_termination_proved=True,
        pending=['arbitrary-length access theorem','model/native mutation witnesses',
                 'performance evaluation','E4/M2 completion audit'])
    folder=ROOT/'reports/m2';folder.mkdir(exist_ok=True)
    (folder/'memmove-core.json').write_text(json.dumps(report,indent=2)+'\n')
    print('E4 core proved; E4/M2 remain incomplete',flush=True)
    return report


if __name__=='__main__': verify()
