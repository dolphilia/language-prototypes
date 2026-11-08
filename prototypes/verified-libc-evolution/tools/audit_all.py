"""Full-plan audit. No unit is inferred complete from a later narrative alone."""
from datetime import datetime, timezone
import json
from config import ROOT, BUILD, digest
from audit_m1 import validate_inputs
from verify_regions import require_m1


def audit():
    r=json.loads((ROOT/'reports/verification-all.json').read_text())
    if r!=json.loads((BUILD/'verification-all.json').read_text()) or not r['verification_passed'] or r['scope']!='full E0-E7 plan':
        raise RuntimeError('the real full-plan verification entry has not completed')
    validate_inputs(r['source_files'])
    targets={x['target'] for x in r['commands']}
    if not {'verify-m1','verify-m2','verify-m3'}<=targets:
        raise RuntimeError('all public verification entries must have run')
    require_m1()
    from audit_m2 import verification as m2
    from audit_m3 import verification as m3
    m2();m3()
    for phase in ['m1','m2','m3']:
        a=json.loads((ROOT/'reports'/phase/'audit.json').read_text())
        if not a['complete'] or digest(ROOT/'reports'/phase/'audit.json')!=r['audits'][phase]:
            raise RuntimeError('completed unit audit changed after the full run: '+phase)
        validate_inputs(a['evidence_sha256'])
        v=json.loads((ROOT/'reports'/phase/'verification.json').read_text())
        nonce=v['proof']['nonce'] if phase=='m1' else v['nonce']
        if nonce!=r['fresh_unit_nonces'][phase] or nonce==r['previous_unit_nonces'].get(phase):
            raise RuntimeError('a previous success was reused: '+phase)
    req_path=ROOT/'reports/requirements.json';req=json.loads(req_path.read_text())
    scope=json.loads((ROOT/'tools/requirements-scope.json').read_text())['ids']
    if len(scope)!=82 or [x['id'] for x in req['requirements']]!=scope:
        raise RuntimeError('the full plan requirement scope changed')
    pending=[x['id'] for x in req['requirements'] if not x['id'].startswith('ALL.') and x['status']!='complete']
    if pending:raise RuntimeError('required experiments remain incomplete: '+str(pending))
    readme=(ROOT/'README.md').read_text()
    for entry in ['verify-m1','verify-m2','verify-m3','verify-all','measure-m1','measure-m2','measure-m3','QEMU','未達']:
        if entry not in readme:raise RuntimeError('setup/limits/entry documentation incomplete: '+entry)
    independent=json.loads((ROOT/'reports/m3/independent-recheck/trial.json').read_text())
    if not independent['investigation_complete'] or independent['independent_recheck_success']:
        raise RuntimeError('independent-recheck outcome must retain the actual investigated limit')
    selected=json.loads((ROOT/'reports/m3/search/selection.json').read_text())['selected']
    confirmation=json.loads((ROOT/'reports/m3/search/confirmation.json').read_text())
    sizes=confirmation['candidates'][0]['sizes']
    trust=['# 保証の供給元と、残る信頼','',
        '本書は、論理上の条件をどこから導いたか、実物との対応、有限の検査、外部への信頼を分ける。整数やハッシュを持つだけで、RAMの所有や正しさが生まれるわけではない。',
        '', '| 段階 | ソフトウェア内で導出・確認したこと | 残る条件・信頼 |',
        '| --- | --- | --- |',
        '| B0・E0 | 固定した環境、閉じた期待命題、実際のバイト。証明済み・具体的な反例・未解決・基盤異常を区別 | 仕様の意図への適合、基礎論理、実行環境 |',
        '| E1 | RETなしの部品の定理とバイト一致、親の合成、直接版との一致 | 期待する仕様・モデル、カーネルと実行器 |',
        '| E2 | 実行時の整列ガードからワード処理の条件を導き、任意長の機能・復帰・保存・アクセスを証明 | 通常RAMの実在・有効性・寿命、非重複の所有領域、コードのロード |',
        '| E3a | 領域、分割、借用、返却、失効の逐次的な遷移と、コピーの入口条件 | 一つの根の権限と現行台帳の供給、台帳と物理メモリの対応。HOLの事実自体は線形資源ではない |',
        '| E3b | 実際の比較分岐から部分領域の境界・非重複・減算の条件を導く。失敗経路はデータアクセスなし | 根の所有領域と16バイトの専用スタックが呼び出し中有効であること |',
        '| E4 | 移動方向と開始時のスナップショットの不変条件で、コピーの非重複条件を取り除く | 入出力の通常RAM、コード等との分離。競合やMMIOの契約は対象外 |',
        '| E5 | 2配置のBLの実際の分岐先、子の全バイト、LR/SP復元、枠外の保存 | Mach-O抽出・LLVM・IOの対応、OSローダー。汎用リンカの正しさの定理ではない |',
        '| E6a | 独立したQEMUと実機の有限の入力・出力をHOLで照合 | 全入力・全CPUのISA同値は未証明。QEMUの配布バイナリと上流ソースの対応も未証明 |',
        '| E6b | 旧記録系のビルド・起動・RET出力の最小試行と、非互換の再現 | 独立した証明再検査機能は未達。現在はHOLカーネル・ランタイムを信頼する |',
        '| E7a | 実際の命令に対する任意長のステップ数とデータ量 | 実時間はCPU、キャッシュ、OS等に依存し、モデルの式だけでは保証しない |',
        '| E7b | 有限5候補を検査し、証明済みの候補を固定。選択後に再検査・別データの測定 | 有限の性能観測と測定器。全長・全機種・全候補での最適性ではない |',
        '', '## 取り除いた信頼と、残る根','',
        'ライブラリの正しさをコンパイラや生成器の正しさだけに委ねず、実際の対象バイトから独立した公開契約を証明した。生成器と証明を探す補助は不正な候補を出してよいが、期待命題・空の仮定・許可した基礎公理の検査を通らなければ受理しない。Cの試験器・測定器のコンパイル等は別の検査境界として残る。',
        '', 'ISAと物理CPU、RAMのマッピング・権限・寿命、実行中の外部更新の不在、OSによるコードのロードは外部条件である。さらに形式化したい部分と、最後に採用する根を区別する。今回の根にはHOLの基礎公理（INFINITY・SELECT・ETA）とカーネル・実行環境が含まれ、実装を正しいとする新しい公理は追加していない。',
        '', '領域の供給と現在の台帳を言語の型・実行系で強制すること、抽出器を形式化すること、証明の依存関係を細かくして再検査を減らすことは、ソフトウェアで進められる。一方、それらも最後は仕様・論理・IO・ハードウェア等の採用した根を持つ。根の存在を、未実装の検査を省く理由にはしない。',
        '', '## 軽くなった負担と増えた負担','',
        '呼び出し元は検査付きAPIで整数の範囲を繰り返し証明せずに扱え、memmoveでは入力と出力の非重複を要求されなくなった。部品と反復の定理の再利用、実物の照合、有限探索で、生成器の提案をそのまま信頼せずに試せる。',
        '', 'その代わり、モデル・仕様・公開契約・物理の根の対応、証明用の不変条件、ABIとリンク、反例の初期状態、証明・測定入力の追跡が増える。2ワード版では値の名前付け、アドレス境界、文脈も含む正規化が必要だった。現在の段階全体のソーススナップショットと共有ヘルパーのハッシュは保守的で、無関係な変更でも再検査や再測定を要する場合がある。人の手作業時間の一般的な軽減は測っていない。',
        '', '本体の速度・容量を評価することと、証明・導入・探索の費用を評価することを分ける。小さな本体は証明環境や全実験データが小さいという意味ではない。']
    (ROOT/'reports/trust-boundaries.md').write_text('\n'.join(trust)+'\n')
    lines=['# 発展計画全体の完了監査','',
        '**M1・M2・M3と全体の必須条件を完了した。** 独立した証明再検査機能は未達であり、E6bは実現性調査としての完了である。',
        '', '| 単位 | 完了の根拠 |','| --- | --- |',
        '| M1: E0・E1・E2 | [監査](m1/audit.md)。79件、部品の合成、同じ任意長の契約、実物・境界・ABI・反例、104バイト、測定と3回の修正実験 |',
        '| M2: E3・E4・E5 | [監査](m2/audit.md)。領域と権限、memmove、2配置の直接呼び出し、検査付きの実物。4新規プロセス、179回の検査 |',
        '| M3: E6・E7 | [監査](m3/audit.md)。全対象形式の有限比較、独立再検査の調査、資源定理、5候補の探索、固定後の再検査と別測定 |',
        '| 全体 | [実際のverify-all実行](verification-all.json)。各Make入口を実行し、以前と異なる単位nonce、全ソース、完了監査を照合 |',
        '| 信頼と費用 | [供給元と残る根](trust-boundaries.md)。論理の導出、アルゴリズム、実物の検査、有限の観測、未達を区別 |',
        '',f'選択した候補は`{selected}`、コピー{sizes["copy_body_bytes"]}バイトと埋め込み28バイトで合計{sizes["combined_body_bytes"]}バイト。[探索と確認](m3/search/README.md)には短い長さ・未整列の退行とlibc比較も残した。全入力で最速という結論ではない。',
        '', '[要件82件と証拠](requirements.json) · [導入と入口](../README.md)',
        '', '調査の完了は、独立したカーネルによる正例再生や改変拒否の実装成功ではない。現在の固定環境では旧記録版が非互換であり、HOLで受理した同じ証明を独立に再検査できていない。',
        '', '```sh','make -C prototypes/verified-libc-evolution verify-all','```']
    (ROOT/'reports/audit.md').write_text('\n'.join(lines)+'\n')
    for item in req['requirements']:
        if item['id'].startswith('ALL.'):
            item.update(status='complete',evidence=['reports/verification-all.json','reports/audit.md',
                        'reports/trust-boundaries.md','README.md'])
    req_path.write_text(json.dumps(req,indent=2)+'\n')
    if any(x['status']!='complete' for x in req['requirements']):raise RuntimeError('full requirement audit incomplete')
    r['complete']=True
    text=json.dumps(r,indent=2)+'\n'
    (BUILD/'verification-all.json').write_text(text);(ROOT/'reports/verification-all.json').write_text(text)
    # Update status text only after all unchanged acceptance conditions pass.
    repository=ROOT.parents[1]
    plans=repository/'docs/plans/verified-libc-evolution'
    for name in ['README.md','later-stages.md']:
        page=plans/name;rows=page.read_text().splitlines()
        for i,row in enumerate(rows):
            if row.startswith('状態:'):
                rows[i]='状態: **完了**。M1・M2・M3と[全体の監査](../../../prototypes/verified-libc-evolution/reports/audit.md)を完了した。E6bは実現性調査の完了であり、独立した証明再検査の機能は未達である。'
        page.write_text('\n'.join(rows)+'\n')
    page=plans/'phase-1-composition.md';text=page.read_text().replace('M2・M3を含む全体は実施中である。','M2・M3を含む[全体の監査](../../../prototypes/verified-libc-evolution/reports/audit.md)も完了した。');page.write_text(text)
    page=ROOT/'README.md';rows=page.read_text().splitlines()
    for i,row in enumerate(rows):
        if row.startswith('状態:'):
            rows[i]='状態: **M1・M2・M3と全体の監査を完了**。各段階の正しさ・実物・試験・評価をそろえ、`verify-all`で再実行した。独立した証明再検査の機能は未達であり、E6bは実現性調査として区別する。'
    page.write_text('\n'.join(rows)+'\n')
    page=repository/'docs/plans/README.md';rows=page.read_text().splitlines()
    for i,row in enumerate(rows):
        if '(verified-libc-evolution/README.md)' in row:
            rows[i]=row.replace('実施中・[記録]','完了・[記録]')
    page.write_text('\n'.join(rows)+'\n')
    page=ROOT.parent/'README.md';text=page.read_text().replace('[検証済みlibcの発展版](verified-libc-evolution/README.md)は実装中。B0・E0の証拠と、M1〜M3の未達を[実施記録](verified-libc-evolution/reports/progress.md)で管理する。','[検証済みlibcの発展版](verified-libc-evolution/README.md)はM1〜M3と[全体監査](verified-libc-evolution/reports/audit.md)を完了した。独立した証明再検査の機能は未達であり、調査の完了と区別する。');page.write_text(text)
    result=dict(complete=True,scope='full E0-E7 plan',requirements=82,independent_recheck_success=False,
        investigation_complete=True,timestamp=datetime.now(timezone.utc).isoformat(),
        full_run_nonce=r['nonce'],unit_audits=r['audits'],
        evidence_sha256={str(ROOT/p):digest(ROOT/p) for p in ['reports/verification-all.json',
            'reports/requirements.json','reports/audit.md','reports/trust-boundaries.md','README.md']})
    (ROOT/'reports/audit.json').write_text(json.dumps(result,indent=2)+'\n')
    p=ROOT/'reports/progress.md';text=p.read_text()
    text=text.replace('M2は[統合監査](m2/audit.md)を完了した。M3と全体は未完了。',
        'M1・M2・M3と[全体の監査](audit.md)を完了した。独立した証明再検査の機能は未達である。')
    p.write_text(text)
    print('Full E0-E7 plan complete: 82 requirements; independent proof replay remains explicitly unachieved',flush=True)
    return result


if __name__=='__main__':audit()
