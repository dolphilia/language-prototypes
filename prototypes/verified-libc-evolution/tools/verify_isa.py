"""Finite, reproducible single-instruction comparison; never an ISA equivalence proof."""
import collections
import gzip
import json
import platform
import subprocess
import sys
from pathlib import Path
from config import ROOT, BUILD, digest, environment
from prover import run_session
from verify_regions import require_m1

REPORT = ROOT/'reports/m3/isa'
PIN = ROOT/'isa-backend.lock.json'


def observations():
    matrix = json.loads((BUILD/'e6a-qemu-matrix.json').read_text())
    pin = json.loads(PIN.read_text())
    if matrix['binary_sha256'] != pin['sha256'] or digest(pin['binary']) != pin['sha256']:
        raise RuntimeError('independent backend identity differs')
    if matrix['upstream_commit'] != pin['upstream_commit']:
        raise RuntimeError('independent backend source pin differs')
    if matrix['sstep'] != '0x7':
        raise RuntimeError('unexpected QEMU single-step configuration')
    datasets = {b: [json.loads(line) for line in (BUILD/f'e6a-{b}-cases.jsonl').open()]
                for b in ['qemu', 'native']}
    forms = set(matrix['forms'])
    if len(forms) != 20 or sum(map(len, matrix['forms'].values())) != 33:
        raise RuntimeError('M1 instruction coverage changed; review the inventory')
    for backend, rows in datasets.items():
        keys = [(r['form'], r['index']) for r in rows]
        if len(keys) != 5760 or set(keys) != {(f, i) for f in forms for i in range(288)}:
            raise RuntimeError(f'{backend}: coverage or duplicate case')
        for r in rows:
            if hex(r['word']) not in matrix['forms'][r['form']]:
                raise RuntimeError('instruction identity differs')
            if r['kind'] != ('edge' if r['index'] < 32 else 'seeded'):
                raise RuntimeError('edge/seeded classification differs')
            w=r['word']; f=r['form']; rt=w&31
            changed={rt} if f in ['ADD_X_IMM','SUB_X_REG','EOR_X','ORR_X','MOVZ_X'] or f.startswith('LDR') else set()
            if len(r['registers']) != 32 or len(r['after']['registers']) != 32:
                raise RuntimeError('register coverage differs')
            for i, (before, after) in enumerate(zip(r['registers'], r['after']['registers'])):
                if i not in changed and before != after:
                    raise RuntimeError(f'{backend}: preserved register changed')
            if not (f.startswith('CMP_') or f=='TST_X_IMM') and r['nzcv'] != r['after']['nzcv']:
                raise RuntimeError(f'{backend}: preserved flags changed')
            before=bytes.fromhex(r['memory']); after=bytes.fromhex(r['after']['memory'])
            if len(before)!=512 or len(after)!=512:
                raise RuntimeError('memory observation coverage differs')
            off=r['effective_offset']; width=1 if f.startswith('STRB') else 8
            allowed=set(range(off,off+width)) if f.startswith('STR') else set()
            if any(a!=b and i not in allowed for i,(a,b) in enumerate(zip(before,after))):
                raise RuntimeError(f'{backend}: memory outside the write footprint changed')
    for q,n in zip(datasets['qemu'],datasets['native']):
        if (q['form'],q['index'],q['word']) != (n['form'],n['index'],n['word']):
            raise RuntimeError('backend order differs')
        f=q['form']; adapted={18,30,31}
        if f.startswith(('LDR','STR')): adapted.add((q['word']>>5)&31)
        for i in range(32):
            if i not in adapted and (q['registers'][i]!=n['registers'][i] or
                                    q['after']['registers'][i]!=n['after']['registers'][i]):
                raise RuntimeError('rebased backend register mismatch')
        if q['nzcv']!=n['nzcv'] or q['after']['nzcv']!=n['after']['nzcv'] or q['memory']!=n['memory'] or q['after']['memory']!=n['after']['memory']:
            raise RuntimeError('backend flags/memory mismatch')
        mask=(1<<64)-1
        if (q['after']['pc']-q['pc'])&mask != (n['after']['pc']-n['pc'])&mask:
            raise RuntimeError('rebased branch target mismatch')
    return matrix, datasets


def verify():
    require_m1()
    (BUILD/'proof-isa.json').unlink(missing_ok=True)
    for name in ['isa_qemu.py','isa_native.py','isa_proofs.py']:
        subprocess.run([sys.executable,str(ROOT/'tools'/name)],cwd=ROOT,env=environment(),check=True)
    matrix, datasets=observations()
    checks=json.loads((BUILD/'e6a-checks.json').read_text())
    expected=[f'e6a:{b}:{r["form"]}:{r["index"]}:{kind}'
              for b,rows in datasets.items() for r in rows
              for kind in ['universal','initial','numeric','execution']]
    if checks != expected: raise RuntimeError('HOL case coverage differs')
    inputs=[PIN,Path(matrix['binary']),*[ROOT/'tools'/n for n in
            ['verify_isa.py','isa_qemu.py','isa_native.py','isa_proofs.py']],
            *[BUILD/n for n in ['e6a-qemu-cases.jsonl','e6a-native-cases.jsonl',
                'e6a-qemu-matrix.json','e6a-hol-base.ml','e6a-hol-cases.ml',
                'e6a-native.S','e6a-native.c','e6a-native.o','e6a-native']],
            *BUILD.glob('ve_diff_word_*.o'),*[Path(p) for p in matrix['inputs']]]
    body='loadt '+json.dumps(str(BUILD/'e6a-hol-cases.ml'))+';;'
    proof=run_session('isa',body,checks,timeout=10800,inputs=inputs)
    require_m1(); observations()
    REPORT.mkdir(parents=True,exist_ok=True)
    for b in datasets:
        data=(BUILD/f'e6a-{b}-cases.jsonl').read_bytes()
        (REPORT/f'{b}-cases.jsonl.gz').write_bytes(gzip.compress(data,mtime=0))
    result={'phase_complete':True,'scope':'finite M1 instruction observations only',
            'proof':proof,'forms':matrix['forms'],'backend':matrix,
            'cases_per_backend':5760,'edge_per_form':32,'seeded_per_form':256,
            'native_address_adaptation':['ordinary RAM base','SP','X18 reserved by Darwin','LR/PC'],
            'memory_bytes_per_case':512,'unresolved_mismatches':[],
            'cases':{b:digest(REPORT/f'{b}-cases.jsonl.gz') for b in datasets},
            'host':{'system':platform.platform(),'machine':platform.machine()},
            'events_compared':False,
            'model_equivalence_proved':False}
    (REPORT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print('E6a complete: 20 forms, 5760 cases/backend, 46080 closed checks; finite evidence only',flush=True)
    return result


if __name__=='__main__': verify()
