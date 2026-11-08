"""Bind finite model/native evidence to the current, actually used M1 bodies."""
import gzip
import hashlib
import json
from pathlib import Path
from config import ROOT, BUILD, digest
from build import MachO, words
from audit_m1 import validate_inputs
from verify_regions import require_m1
from verify_isa import observations, REPORT


def audit():
    require_m1()
    result=json.loads((REPORT/'verification.json').read_text())
    if not result['phase_complete'] or result['model_equivalence_proved'] or result['events_compared']:
        raise RuntimeError('ISA experiment scope differs')
    proof=result['proof']
    if proof!=json.loads((BUILD/'proof-isa.json').read_text()):
        raise RuntimeError('current ISA receipt differs')
    validate_inputs(proof['inputs'])
    matrix,datasets=observations()
    expected=[f'e6a:{backend}:{r["form"]}:{r["index"]}:{kind}'
              for backend,rows in datasets.items() for r in rows
              for kind in ['universal','initial','numeric','execution']]
    if proof['checks']!=expected or len(expected)!=46080 or result['unresolved_mismatches']:
        raise RuntimeError('ISA coverage or mismatch result differs')
    for path,sha in matrix['inputs'].items():
        p=Path(path)
        if digest(p)!=sha or MachO(p.with_suffix('.o')).function(p.stem)!=words(p):
            raise RuntimeError('inventory does not describe an actual M1 body: '+path)
    for backend in datasets:
        path=REPORT/f'{backend}-cases.jsonl.gz'
        if digest(path)!=result['cases'][backend]:raise RuntimeError('saved cases changed')
        data=gzip.decompress(path.read_bytes())
        if hashlib.sha256(data).hexdigest()!=proof['inputs'][str(BUILD/f'e6a-{backend}-cases.jsonl')]:
            raise RuntimeError('saved observations differ from the proved inputs')
    requirements=json.loads((ROOT/'reports/requirements.json').read_text())
    for item in requirements['requirements']:
        if item['id'].startswith('E6a.'):
            item.update(status='complete',evidence=['reports/m3/isa/verification.json',
                        'reports/m3/isa/README.md','isa-backend.lock.json','tools/audit_isa.py'])
    (ROOT/'reports/requirements.json').write_text(json.dumps(requirements,indent=2)+'\n')
    path=REPORT/'README.md';rows=path.read_text().splitlines()
    for i,row in enumerate(rows):
        if row.startswith('状態:'):
            rows[i]=f'状態: **完了**。新規HOLプロセスで46,080件の閉じた検査を{proof["elapsed_seconds"]:.1f}秒で受理し、追加公理なしを確認した。[入力・対象・結果](verification.json)と、圧縮した[QEMUの観測](qemu-cases.jsonl.gz)・[実機の観測](native-cases.jsonl.gz)を保存している。未解決の不一致は0件である。'
    path.write_text('\n'.join(rows)+'\n')
    path=ROOT/'reports/progress.md';rows=path.read_text().splitlines()
    for i,row in enumerate(rows):
        if row.startswith('| E6a |'):
            rows[i]='| E6a | 完了 | [命令の差分検査](m3/isa/README.md)。20形式・33エンコーディング、各バックエンド5,760例、46,080件の閉じた検査。有限の根拠でありモデル全体の同値ではない |'
    path.write_text('\n'.join(rows)+'\n')
    print('E6a audit complete; finite observations only; E7b/M3 integration remain incomplete',flush=True)
    return result


if __name__=='__main__':audit()
