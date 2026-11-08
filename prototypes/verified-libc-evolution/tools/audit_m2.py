"""M2 completion requires the current integrated run and every stage audit."""
from datetime import datetime,timezone
import json
from config import ROOT,BUILD,digest
from audit_m1 import validate_inputs
from verify_regions import require_m1,REGION_CHECKS


def verification():
    require_m1()
    path=ROOT/'reports/m2/verification.json';r=json.loads(path.read_text())
    gate=json.loads((BUILD/'verification-m2.json').read_text())
    if r!=gate or not r['verification_passed'] or set(r['stages'])!={'regions','memmove','calls','split'}:
        raise RuntimeError('current integrated M2 verification receipt missing')
    validate_inputs(r['source_files'])
    if digest(ROOT/'reports/m1/audit.json')!=r['m1_audit_sha256']:
        raise RuntimeError('M1 prerequisite changed after integrated M2 verification')
    from audit_memmove import verification as move
    from audit_calls import verification as calls
    from audit_split import verification as split
    regions=json.loads((ROOT/'reports/m2/regions.json').read_text())
    if not regions['complete'] or regions['region_theorems']!=len(REGION_CHECKS):
        raise RuntimeError('E3a evidence missing')
    validate_inputs(regions['proof']['inputs'])
    stages={'regions':regions,'memmove':move(),'calls':calls(),'split':split()}
    for name,s in stages.items():
        if s['proof']['nonce']!=r['stages'][name]['proof_nonce'] or s['proof']['checks']!=r['stages'][name]['checks']:
            raise RuntimeError('stage proof is not from the current integrated M2 run: '+name)
    if r['checked_occurrences']!=179 or r['distinct_check_names']!=118:
        raise RuntimeError('integrated M2 proof coverage differs')
    return r


def audit():
    r=verification()
    from audit_memmove import audit as move
    from audit_calls import audit as calls
    from audit_split import audit as split
    for action in [move,calls,split]:action()
    folder=ROOT/'reports/m2'
    for name in ['memmove','calls','split']:
        a=json.loads((folder/(name+'-audit.json')).read_text())
        if not a['complete']:raise RuntimeError('M2 stage evaluation incomplete: '+name)
        validate_inputs(a['evidence_sha256'])
    r['phase_complete']=True
    (folder/'verification.json').write_text(json.dumps(r,indent=2)+'\n')
    (BUILD/'verification-m2.json').write_text(json.dumps(r,indent=2)+'\n')
    lines=['# M2の完了監査','',
        'M2（E3a・E4・E5・E3b）の実装・証明・実物・評価・コマンド統合を完了と判定する。M3と全体の完了はこの判定へ含めない。','',
        '| 条件 | 根拠 |','| --- | --- |',
        '| 現在のソースでの統合入口 | [新規実行](verification.json)。4個の新規証明プロセス、合計179回の検査、118の異なる検査名。M1の前提と開始・終了の全入力を照合 |',
        '| 領域と権限 | [E3a](regions.md)。借用・権限・寿命・返却、コピーの入口条件。通常RAMと台帳の根は外部契約 |',
        '| 重複コピー | [E4](memmove-audit.md)。42定理、35,709件、8誤実装、303ケース各7回 |',
        '| 直接呼び出しとリンク | [E5](calls-audit.md)。2配置・33定理、各10,944件、改変23・取り込み9・誤実装3例、42ケース各7回 |',
        '| 検査付きの呼び出し元 | [E3b](split-audit.md)。64定理、184,572件、5誤実装、正常42・不正6ケース各7回。実際の分岐から入口条件を導く |',
        '| 容量・実行資源 | コピー76・埋め込み28・memmove68・単純呼び出し24・検査付き80で本体合計276バイト。葉関数は専用枠なし、呼び出し元の最大専用枠16バイト、ヒープと証明用の実行処理なし |',
        '', '179は重複するM1の部品等を各新規プロセスで検査した回数の合計である。118は検査名の種類であり、数学的に異なる命題の同値類を数えたものではない。',
        '', '定理・反例・実物との照合・有限の実機試験・測定・外部への信頼を区別する。速度の優位や一般のOS・アロケータ・リンカ・借用検査器の検証を主張しない。',
        '', '[呼び出しの前提](calls-assumptions.json) · [検査付きの前提](split-assumptions.json) · [領域の根](regions.json)',
        '', '```sh','make -C prototypes/verified-libc-evolution verify-m2',
        'make -C prototypes/verified-libc-evolution measure-m2','```']
    (folder/'audit.md').write_text('\n'.join(lines)+'\n')
    names=['verification.json','regions.json','regions-proof.json','memmove-audit.json','calls-audit.json',
        'split-audit.json','calls-assumptions.json','split-assumptions.json','audit.md']
    result=dict(scope='M2 only',complete=True,timestamp=datetime.now(timezone.utc).isoformat(),
        verification_nonce=r['nonce'],evidence_sha256={str(folder/n):digest(folder/n) for n in names})
    (folder/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    requirements=json.loads((ROOT/'reports/requirements.json').read_text())
    for item in requirements['requirements']:
        if item['id']=='E3b.m2_commands_and_audit':
            item.update(status='complete',evidence=['reports/m2/audit.md','reports/m2/verification.json','tools/entry.py','tools/phase_m2.py'])
    (ROOT/'reports/requirements.json').write_text(json.dumps(requirements,indent=2)+'\n')
    progress=ROOT/'reports/progress.md';rows=progress.read_text().splitlines()
    for i,row in enumerate(rows):
        if row.startswith('| E3b |'):
            rows[i]='| E3b | 完了 | [M2監査](m2/audit.md)。64定理、184,572件、5誤実装、48ケース各7回、統合入口を再検査 |'
    marker='\nM2は[統合監査](m2/audit.md)を完了した。M3と全体は未完了。\n'
    text='\n'.join(rows)+'\n'
    if marker.strip() not in text:text+=marker
    progress.write_text(text)
    print('M2 audit complete; M3 and the overall plan remain incomplete',flush=True)
    return result


if __name__=='__main__':audit()
