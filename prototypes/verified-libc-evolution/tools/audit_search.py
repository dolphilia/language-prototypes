"""Audit the pool, immutable selection, fresh recheck, and independent raw timings."""
import collections
import json
from config import ROOT, BUILD, digest
from build import MachO, check_span
from audit_m1 import validate_inputs
from verify_regions import require_m1
from verify_search import require_pool, require_resources, REPORT, FROZEN
from measure_search import validate_trial, scores, method_inputs


def audit():
    require_m1();require_resources();pool=require_pool()
    selection=json.loads((REPORT/'selection.json').read_text())
    exploration=validate_trial(json.loads((REPORT/'exploration.json').read_text()))
    confirmation=validate_trial(json.loads((REPORT/'confirmation.json').read_text()))
    selected=json.loads((REPORT/'selected-verification.json').read_text())
    name=selection['selected'];values,eligible,chosen=scores(exploration)
    if chosen!=name or selection['scores']!=values or selection['eligible_within_5_percent']!=eligible:
        raise RuntimeError('selection rule no longer agrees with exploration')
    if selection['frozen_sha256']!=digest(FROZEN):raise RuntimeError('selection pool identity differs')
    if selection['exploration_sha256']!=digest(REPORT/'exploration.json') or selection['method_inputs']!=method_inputs():
        raise RuntimeError('frozen selection inputs changed')
    if {r['name'] for r in exploration['candidates']}!=set(pool['proved']) or len(exploration['candidates'])!=4:
        raise RuntimeError('exploration did not cover precisely the proved candidates')
    if confirmation!=json.loads((BUILD/'measurement-search.json').read_text()):
        raise RuntimeError('current confirmation gate differs')
    if [r['name'] for r in confirmation['candidates']]!=[name] or confirmation['seed']==exploration['seed']:
        raise RuntimeError('confirmation inputs are not separate')
    if confirmation['selection_sha256']!=digest(REPORT/'selection.json'):
        raise RuntimeError('confirmation was not for this frozen selection')
    if not selected['verification_passed'] or selected['proved']!=[name] or len(selected['proof']['checks'])!=21:
        raise RuntimeError('selected body has not passed all fresh checks')
    if selected['proof']!=json.loads((BUILD/'proof-search-selected.json').read_text()):
        raise RuntimeError('current selected proof receipt differs')
    validate_inputs(selected['proof']['inputs'])
    validate_inputs(confirmation['selected_proof_snapshot']['inputs'])
    records=json.loads(FROZEN.read_text())['candidates']
    if len(records)!=5 or set(pool['proved'])|{'ve_opt_u2_bad'}!={r['name'] for r in records}:
        raise RuntimeError('candidate classification coverage differs')
    for r in records:
        if digest(BUILD/(r['name']+'.o'))!=r['object_sha256']:
            raise RuntimeError('candidate object changed')
    for tag,record in [('pool',pool),('selected',selected)]:
        for r in record['native']['positive']:
            target=BUILD/(r['name']+'-'+tag+'-native')
            if digest(target)!=r['executable_sha256']:raise RuntimeError('native executable changed')
            check_span(target,r['name'],MachO(BUILD/(r['name']+'.o')).function(r['name']),object_only=False)
        for r in record['native']['negative']:
            target=BUILD/(r['name']+'-'+tag+'-negative')
            if digest(target)!=r['executable_sha256']:raise RuntimeError('negative native executable changed')
            check_span(target,r['name'],MachO(BUILD/(r['name']+'.o')).function(r['name']),object_only=False)
        if [(r['name'],r['returncode']) for r in record['native']['negative']][0]!=('ve_opt_u2_mov',7):
            raise RuntimeError('normal guard control missing')
        if record['native']['negative'][1]['returncode'] not in [-10,-11]:
            raise RuntimeError('guard counterexample missing')
    for trial in [exploration,confirmation]:
        for r in trial['candidates']:
            sizes=r['sizes'];body=MachO(BUILD/(r['name']+'.o')).function(r['name'])
            if sizes['combined_body_bytes']!=len(body)+28 or len(body)+28>256:
                raise RuntimeError('body capacity gate failed')
            check_span(sizes['benchmark'],r['name'],body,object_only=False)
            if digest(sizes['benchmark'])!=sizes['benchmark_sha256'] or digest(sizes['size_executable'])!=sizes['size_sha256']:
                raise RuntimeError('measured executable changed')
    archived=sorted((REPORT/'confirmations').glob('*.json'))
    if not any(p.stem==confirmation['nonce'] for p in archived):raise RuntimeError('confirmation archive missing')
    cases=confirmation['candidates'][0]['cases'];sizes=confirmation['candidates'][0]['sizes']
    counts={v:dict(collections.Counter(c['candidate_vs'][v] for c in cases)) for v in ['scalar','original','libc']}
    folder=REPORT
    lines=['# 有限の候補探索と、固定後の確認','',
        '**E7bの実装・証明・評価を完了した。M3の統合監査は別に行う。**',
        '',f'固定した5候補から`{name}`を選択した。本体{sizes["copy_body_bytes"]}バイト、埋め込み28バイトと合計{sizes["combined_body_bytes"]}バイト。専用スタック・ヒープ・証明用の実行処理は0である。',
        '', '[候補と選択規則](../search-protocol.md) · [測定方法](../search-measurement-protocol.md) · [選択の固定記録](selection.json)',
        '', '| 候補 | 判定 | 本体バイト | 探索のスコア |','| --- | --- | ---: | ---: |']
    for r in records:
        score=f'{values[r["name"]]["score"]:.6f}' if r['name'] in values else '—'
        lines.append(f'| `{r["name"]}` | '+('反例あり' if r['name'].endswith('_bad') else '証明済み')+f' | {r["bytes"]} | {score} |')
    lines += ['', '正しさの未解決候補は0。スコアは整列済み64・256・4096バイトでの「候補の中央値÷基本スカラー版の中央値」の平均である。最小から5%以内では小さい本体を優先し、同じ大きさなら小さいスコアを選ぶ。',
        '',f'候補集合は新規{len(pool["proof"]["checks"])}件の検査、固定した選択後は別プロセスの{len(selected["proof"]["checks"])}件を通した。機能、有限復帰、保存、途中のアクセス、資源を同じ公開契約で確認し、追加公理はない。各候補を組み込んだ実機ハーネスは1,109,765件の検査を通る。この数には共通の基本版・埋め込み等の検査も含む。',
        '', '不正候補はn=8で残量を8バイトしか検査せず、2回目の8バイトロードがsrc+8から始まる。11ステップの範囲外アクセスを、正しい公開事前条件の初期状態と有限実行で証明した。同じ実機入力では正常版が通り、不正版だけがガードページへ到達した。証明失敗を反例にはしていない。',
        '', '整列済みの元のM1は`7(n DIV 8)+5(n MOD 8)+10`、2ワード版は`10(n DIV 16)+5(n MOD 16)+10`ステップ。未整列はともに`5n+7`、読み書きは各nバイトである。命令数の減少が実時間の改善へ比例するとは限らない。',
        '', '## 固定後の測定','',
        f'確認用の試行は合計{len(archived)}回を保存している。以下は現在の確認用測定であり、過去の各試行は`confirmations/`へ残す。探索と確認ではデータ・実行順序のシードを変えた。確認結果から選び直していない。以下は整列済みのns/呼び出しの中央値。速度判定の「不明」と、正しさの未解決候補は別である。',
        '', '| n | 基本版 | 元のM1 | 選択した候補 | libc | 元のM1比 |',
        '| ---: | ---: | ---: | ---: | ---: | --- |']
    for n in [0,1,8,16,64,256,4096,1048576]:
        c=next(c for c in cases if (c['n'],c['sa'],c['da'])==(n,0,0))
        lines.append('| '+str(n)+' | '+' | '.join(f'{c["ns_per_call"][v]["median"]:.3f}' for v in ['scalar','original','candidate','libc'])+' | '+c['candidate_vs']['original']+' |')
    lines += ['',f'全105ケースで、元のM1比は{counts["original"]}、基本版比は{counts["scalar"]}、libc比は{counts["libc"]}だった。短い長さと未整列の退行も全ケースに含めて報告する。',
        '', '探索用の最小値や一つの平均から、全長・全整列・全CPUで最速とは主張しない。2ワード反復の端数はバイト処理なので、8バイト等の短い入力で元の版より不利になる経路がある。今回は固定した候補集合を拡大しない。',
        '', '## 容量と検証の費用','',
        f'容量用の同じbasename `size` の実行ファイルは{sizes["executable_bytes"]:,}バイト、対象コピーのオブジェクトは{sizes["copy_object_bytes"]}バイト。本体の予算と、配置・メタデータ・Cの起動処理は別に数える。',
        '',f'探索用の測定は{exploration["elapsed_seconds"]:.1f}秒、確認用は{confirmation["elapsed_seconds"]:.1f}秒。候補集合の新規証明は{exploration["proof_snapshot"]["elapsed_seconds"]:.1f}秒、選択後の新規証明は{confirmation["selected_proof_seconds"]:.1f}秒で、モデルのロードを含む。人間の思考・作業時間は測っていない。',
        '', '[探索の生データ](exploration.json) · [確認の生データ](confirmation.json) · [全候補の証明入力](pool-verification.json) · [選択後の再検査](selected-verification.json)',
        '', '## 再利用できた点と追加の負担','',
        '親は反復と端数の定理を呼び、端数はM1のバイト部品を再利用する。新しい2ワード反復の内部は9命令を直接検査する証明を用意した。全最適化を既存のマクロだけで自動証明できたという結果ではない。二つのワード値の名前付け、二つ目の位置の数値境界、ゴールと文脈のワード式の正規化が必要だった。これは証明支援を改善できる作業であり、原理的にソフトウェアで扱えない限界とは区別する。',
        '', 'E6aの有限の差分検査を新しい全エンコーディングまで拡大したとは扱わない。新しい分岐変位と即値16はHOLの実物の命令列と実機の関数全体で確認した。M2の呼び出し元は元のM1コピーへ結合したままであり、選択した候補へ差し替える場合はリンク後の証明をやり直す。',
        '', '通常RAMの所有・寿命・有効性、ISAとCPUの対応、OSローダー、論理・実行環境、測定ハーネスは残る前提である。独立した証明再検査の機能はE6bで未達のままである。',
        '', '```sh','python3 prototypes/verified-libc-evolution/tools/verify_search.py',
        'python3 prototypes/verified-libc-evolution/tools/measure_search.py',
        'python3 prototypes/verified-libc-evolution/tools/audit_search.py','```']
    (folder/'README.md').write_text('\n'.join(lines)+'\n')
    result=dict(complete=True,scope='E7b implementation/evaluation only; M3 integration excluded',
        selected=name,counts=counts,selection_sha256=digest(folder/'selection.json'),
        evidence_sha256={str(folder/n):digest(folder/n) for n in ['pool-verification.json','selected-verification.json',
              'exploration.json','selection.json','confirmation.json','README.md']})
    (folder/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    req=json.loads((ROOT/'reports/requirements.json').read_text())
    for item in req['requirements']:
        if item['id'].startswith('E7b.') and item['id']!='E7b.m3_commands_and_audit':
            item.update(status='complete',evidence=['reports/m3/search/README.md','reports/m3/search/audit.json'])
    (ROOT/'reports/requirements.json').write_text(json.dumps(req,indent=2)+'\n')
    print('E7b implementation/evaluation audit complete; M3 integration remains separate',flush=True)
    return result


if __name__=='__main__':audit()
