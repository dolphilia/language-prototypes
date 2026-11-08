"""Completion audit of all M3 experiments; feasibility is separate from replay success."""
from datetime import datetime, timezone
import json
from config import ROOT, BUILD, digest
from audit_m1 import validate_inputs
from verify_regions import require_m1


def verification(require_selected=True):
    require_m1()
    from audit_m2 import verification as m2
    m2()
    r=json.loads((ROOT/'reports/m3/verification.json').read_text())
    if r!=json.loads((BUILD/'verification-m3.json').read_text()) or not r['verification_passed']:
        raise RuntimeError('current combined M3 verification missing')
    validate_inputs(r['source_files'])
    if r['prerequisite_audits']!={p:digest(ROOT/'reports'/p/'audit.json') for p in ['m1','m2']}:
        raise RuntimeError('completed M3 prerequisites changed')
    required={'isa','independent','resources','pool'} | ({'selected'} if require_selected else set())
    if not required<=set(r['stages']):raise RuntimeError('M3 selected proof/evaluation still pending')
    paths={'isa':ROOT/'reports/m3/isa/verification.json',
           'resources':ROOT/'reports/m3/resources/verification.json',
           'pool':ROOT/'reports/m3/search/pool-verification.json',
           'selected':ROOT/'reports/m3/search/selected-verification.json'}
    for name,path in paths.items():
        if name not in r['stages']:continue
        p=json.loads(path.read_text())['proof'];validate_inputs(p['inputs'])
        if p['nonce']!=r['stages'][name]['proof_nonce'] or p['checks']!=r['stages'][name]['checks']:
            raise RuntimeError('M3 proof is not from its current combined execution: '+name)
    if require_selected and (r['checked_occurrences']!=46172 or r['distinct_check_names']!=46151):
        raise RuntimeError('M3 proof coverage differs')
    return r


def audit():
    r=verification()
    from audit_isa import audit as isa
    from audit_search import audit as search
    from verify_search import require_resources
    isa();require_resources();search_result=search()
    independent=json.loads((ROOT/'reports/m3/independent-recheck/trial.json').read_text())
    if not independent['investigation_complete'] or independent['independent_recheck_success'] or independent['export_files']:
        raise RuntimeError('independent-check investigation has an unexpected or incomplete result')
    validate_inputs(independent['inputs'])
    if digest(ROOT/'reports/m3/independent-recheck/ret-export.ml')!=independent['script_sha256']:
        raise RuntimeError('independent-check trial input changed')
    if independent['nonce']!=r['stages']['independent']['investigation_nonce']:
        raise RuntimeError('feasibility trial is not from the current combined execution')
    for step in independent['steps']:
        from pathlib import Path
        if Path(step['log']).read_text()!=step['output']:raise RuntimeError('feasibility log changed')
    folder=ROOT/'reports/m3'
    lines=['# M3の完了監査','',
        '**E6a・E6bの調査・E7a・E7bの実装と評価、M3のコマンド統合を完了と判定する。** 独立した証明再検査の機能は未達であり、調査の完了と区別する。',
        '', '| 段階 | 確認した根拠 |','| --- | --- |',
        '| E6a | [有限の命令比較](isa/README.md)。20形式・33エンコーディング、各形式32境界例・256シード例。QEMUと実機の各5,760件、46,080件の閉じた検査。未解決の不一致なし |',
        '| E6b | [実現性調査](independent-recheck/README.md)。2経路を比較し、一つをRETの出力へ試行。固定環境での旧記録版の非互換を再現。出力・正例再生・改変拒否は未達 |',
        '| E7a | [資源の定理](resources/README.md)。基本版・長さ8専用版・M1の任意長と全経路のモデルステップ数、データバイト数、追加・削除の反例。20件 |',
        '| E7b | [有限の探索と確認](search/README.md)。固定5候補、正常4の機能・復帰・保存・アクセス・資源、不正1の具体的な違反。集合の新規51件、選択後の別プロセス21件。固定後は別データ・別順序で各7プロセスの確認 |',
        '| 統合 | [新規実行](verification.json)。46,172回の検査、46,151の異なる検査名。追加公理なし。M1・M2の完了、開始・終了の入力、各段階の新しいnonceを照合 |',
        '', '検査名の種類は数学的に異なる命題の同値類の数ではない。有限の試験、条件付きの定理、測定、調査の未達を分ける。全CPUでのISA同値、秒数の上限、全入力で最速という結果ではない。',
        '', '```sh','make -C prototypes/verified-libc-evolution verify-m3',
        'make -C prototypes/verified-libc-evolution measure-m3',
        'python3 prototypes/verified-libc-evolution/tools/audit_m3.py','```']
    (folder/'audit.md').write_text('\n'.join(lines)+'\n')
    r['phase_complete']=True
    from phase_m3 import save
    save(r)
    names=['verification.json','isa/verification.json','isa/README.md','resources/verification.json',
           'resources/README.md','independent-recheck/trial.json','independent-recheck/README.md',
           'search/audit.json','search/selection.json','search/confirmation.json','audit.md']
    result=dict(complete=True,scope='M3 only',timestamp=datetime.now(timezone.utc).isoformat(),
        verification_nonce=r['nonce'],independent_recheck_success=False,investigation_complete=True,
        selected=search_result['selected'],evidence_sha256={str(folder/n):digest(folder/n) for n in names})
    (folder/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    req=json.loads((ROOT/'reports/requirements.json').read_text())
    for item in req['requirements']:
        if item['id']=='E7b.m3_commands_and_audit':item.update(status='complete',evidence=['reports/m3/audit.md','reports/m3/verification.json','tools/phase_m3.py'])
    (ROOT/'reports/requirements.json').write_text(json.dumps(req,indent=2)+'\n')
    p=ROOT/'reports/progress.md';rows=p.read_text().splitlines()
    for i,row in enumerate(rows):
        if row.startswith('| E7b |'):rows[i]='| E7b | 完了 | [M3監査](m3/audit.md)。固定5候補、新しい正常候補、反例、選択後の再検査と別データの確認、コマンド統合 |'
    p.write_text('\n'.join(rows)+'\n')
    print('M3 audit complete; independent proof replay remains unachieved; overall audit is separate',flush=True)
    return result


if __name__=='__main__':audit()
