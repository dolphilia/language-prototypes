"""Evidence-based M1 audit; never treats M1 as completion of M2/M3."""
import json
from datetime import datetime,timezone
from config import ROOT,BUILD,digest


def validate_inputs(inputs):
    for name,expected in inputs.items():
        if digest(name)!=expected: raise RuntimeError('evidence input changed: '+name)


def cost_checks():
    children=[f'vp2_block_copy8_{n}' for n in [0,8,16,24]]+[
        'vp2_block_copy8_x3','vp2_block_copy8_indexed','vp2_block_copybyte_indexed']
    base=[f'vp2_copy{n}:{kind}' for n in [16,32] for kind in ['composed','direct']]+['vp2_copy16_x3:composed']
    edited=[f'edit:{family}{n}:{kind}' for n in [16,32]
            for family in ['scratch','frame'] for kind in ['composed','direct']]
    return set(children+base+edited)


def validate_costs(report):
    if report['samples']<3 or len(report['proof_runs'])<3:
        raise RuntimeError('three fresh proof-cost processes are required')
    if len({r['nonce'] for r in report['proof_runs']})!=len(report['proof_runs']):
        raise RuntimeError('proof-cost processes reused a receipt')
    for r in report['proof_runs']:
        if set(r['checks'])!=cost_checks(): raise RuntimeError('cost proof coverage missing')
        validate_inputs(r['inputs'])
        if [e['name'] for e in r['rejections']]!=report['preparation']['expected_rejections']:
            raise RuntimeError('edit rejection coverage missing')
    if len(report['preparation']['experiments'])!=6:
        raise RuntimeError('Copy16/32 × three edits are required')
    return report


def required_core_checks():
    old=[f'{name}:{part}' for name in ['return','callee','termination','overread','overwrite','short_fast','self_branch']
         for part in ['initial','prefix','numeric','execution']]
    fixed=[f'vp2_copy{n}:{kind}' for n in [16,32] for kind in ['composed','direct']]
    blocks=[f'vp2_block_copy8_{n}' for n in [0,8,16,24]]+[
        'vp2_block_copy8_x3','vp2_block_copy8_indexed','vp2_block_copybyte_indexed']
    mutations=[f'chunk-mut:{name}:{part}' for name in
        ['short-word','extra-word','missing-tail','return','frame','decrease']
        for part in ['initial','numeric','execution']]
    rest=['self_branch:stable','self_branch:nonreachability','equivalent:public',
        'vp2_copy16_x3:composed','composition:weak-flags-fixture','public:preserves_x19',
        'chunk8:tail','chunk8:bulk','chunk8:public','chunk8:tail-access','chunk8:bulk-access',
        'chunk8:access-strong','chunk8:access','fill:core','fill:public','fill:access-strong','fill:access',
        'chunk8:zero-no-data','chunk8:numeric-high-end','chunk8:numeric-large',
        'chunk8:wrap-outside-contract','chunk8:aligned-guard']
    return set(old+fixed+blocks+mutations+rest)


def validate_measurements(report):
    from measure_m1 import LENGTHS,ALIGNMENTS,VARIANTS,summary,compare
    validate_inputs(report['method_inputs'])
    validate_inputs(report['proof_receipt_snapshot']['inputs'])
    if not required_core_checks()<=set(report['proof_receipt_snapshot']['checks']):
        raise RuntimeError('measurements did not use all required proved kernels/witnesses')
    cases=report['cases']
    expected={(n,sa,da) for n in LENGTHS for sa,da in ALIGNMENTS}
    if {(c['n'],c['src_offset'],c['dst_offset']) for c in cases}!=expected or len(cases)!=len(expected):
        raise RuntimeError('performance matrix incomplete or duplicated')
    for c in cases:
        if c['calibration'][-1]['elapsed_ns']<8000000: raise RuntimeError('scalar calibration too short')
        if c['n']>=4096 and c['calibration'][0]['iterations']!=1:
            raise RuntimeError('large calibration did not start at one iteration')
        if set(c['samples'])!=set(VARIANTS): raise RuntimeError('comparison variant missing')
        for variant,rows in c['samples'].items():
            if len(rows)<7: raise RuntimeError('seven independent process samples required')
            if any(r['iterations']!=c['iterations'] or r['arena_bytes']>128*1024*1024 or
                   r['warmup_calls']>4096 or r['warmup_calls']*c['n']>4194304 for r in rows):
                raise RuntimeError('measurement bounds or shared iteration count violated')
            recalculated=summary([r['elapsed_ns']/c['iterations'] for r in rows])
            if recalculated!=c['ns_per_call'][variant]: raise RuntimeError('summary differs from raw data')
        s=c['ns_per_call']
        for other in ['scalar','exact8','libc']:
            if c['chunk8_vs_'+other]!=compare(s['chunk8'],s[other]):
                raise RuntimeError('performance classification differs from the declared rule')
    return report


def audit():
    folder=ROOT/'reports/m1'
    active=BUILD/'verification-m1.json'
    verified=json.loads(active.read_text())
    if not verified['verification_passed'] or digest(active)!=digest(folder/'verification.json'):
        raise RuntimeError('current M1 verification receipt missing or inconsistent')
    validate_inputs(verified['source_files']);validate_inputs(verified['proof']['inputs'])
    if set(verified['proof']['checks'])!=required_core_checks():
        raise RuntimeError('required M1 theorem/witness coverage differs')
    for label,minimum in [('results',3),('artifacts',3),('proof_driver',5),('baseline_artifacts',9)]:
        if verified['tests'][label]<minimum: raise RuntimeError('required tests missing: '+label)
    if len(verified['native_mutations'])!=6 or len(verified['linked_artifacts'])!=6:
        raise RuntimeError('native mutation/artifact coverage missing')
    from registry import build_registry
    registry=json.loads((folder/'candidates.json').read_text())
    if registry!=build_registry(verified['proof']): raise RuntimeError('candidate registry differs from proof evidence')
    costs=validate_costs(json.loads((folder/'proof-costs.json').read_text()))
    measured=validate_measurements(json.loads((folder/'measurements.json').read_text()))
    gate=json.loads((BUILD/'measurement-m1.json').read_text())
    if gate['nonce']!=measured['measurement_nonce'] or gate['report_sha256']!=digest(folder/'measurements.json'):
        raise RuntimeError('current measurement receipt missing or stale')
    for r in measured['artifacts']:
        if digest(r['path'])!=r['sha256']: raise RuntimeError('linked artifact changed after measurement')
    if {r['executable_basename'] for r in measured['sizes']}!={'size'}:
        raise RuntimeError('size harness basenames differ')
    selected=next(r for r in measured['sizes'] if r['variant']=='chunk8')
    from build import MachO
    actual=[len(MachO(BUILD/(n+'.o')).function(n,object_only=True))
            for n in ['vp2_memcpy_chunk8','vp2_memset']]
    if [selected['copy_body_bytes'],selected['fill_body_bytes']]!=actual or sum(actual)>256:
        raise RuntimeError('selected body budget exceeded')
    assumptions=json.loads((ROOT/'reports/assumptions.json').read_text())
    if not assumptions['external'] or assumptions['change_from_baseline']['new_public_preconditions']:
        raise RuntimeError('trust boundary missing or public preconditions strengthened')
    requirements=json.loads((ROOT/'reports/requirements.json').read_text())
    evidence=['reports/m1/verification.json','reports/m1/proof-costs.json',
              'reports/m1/measurements.json','reports/assumptions.json','reports/m1/audit.md']
    for item in requirements['requirements']:
        if item['id'].startswith(('B0.','E0.','E1.','E2.')):
            item.update(status='complete',evidence=evidence)
    (ROOT/'reports/requirements.json').write_text(json.dumps(requirements,indent=2)+'\n')
    lines=['# M1の完了監査','', 'M1を完了と判定する。M2・M3はこの判定へ含めない。',
        '', '| 条件 | 証拠 |', '| --- | --- |',
        '| B0: 既存版の再現と分離 | [基準](../baseline.json)、既存ソースの一致を毎回確認 |',
        '| E0: 6変更・自己分岐・正しい変形・契約外 | [79定理の新規検査](verification.json)、分類と異常系の試験 |',
        '| E1: 子の再利用と全バイト一致 | Copy16/32・X3版、直接版との一致、RETだけの親の実行、拒否例 |',
        '| E2: 同じ任意長の公開契約 | 機能・有限復帰・保存・アクセス・ゼロ長・整列・端の数値例を検査 |',
        '| 実物・境界・ABI・破壊 | オブジェクトとリンク後6照合をLLVMと対照。正常1,109,765件、固定192例、破壊6例と正常対照 |',
        f'| 容量・資源 | 選択した本体{sum(actual)}バイト。余分なスタック・ヒープ・実行時証明なし。アクセス定理と実物の命令列から確認 |',
        '| 性能 | [全105ケース・生データ](measurements.json)、4実装を各7プロセス。短い／未整列の退行も残す |',
        '| 修正負担 | [3個の新しいプロセス](proof-costs.json)、各サイズで3編集。CPU時間と初回の自動操作時間を保存 |',
        '| 手順と信頼 | [README](../../README.md)、[前提と供給元](../assumptions.json)。OSの有効性やISA対応は外部への信頼として残る |',
        '', '整列済み64・256・4096バイトの基本版比: '+json.dumps(measured['hypothesis_aligned'],ensure_ascii=False)+'。',
        '', '子の内部命令の再シミュレーションは除去できた。一方、親のCPU時間の差は小さく、手動開発時間は測っていない。一般的な負担軽減や、どの用途でも最速という主張はしない。',
        '', '本監査の対象はM1のみ。後続と全体の状態は上位の実施記録・完了監査で判断する。']
    (folder/'audit.md').write_text('\n'.join(lines)+'\n')
    verified['phase_complete']=True
    verified['remaining_evaluation']='complete; see reports/m1/audit.json'
    text=json.dumps(verified,indent=2)+'\n'
    active.write_text(text);(folder/'verification.json').write_text(text)
    result={'scope':'M1 only','complete':True,'timestamp':datetime.now(timezone.utc).isoformat(),'proof_nonce':verified['proof']['nonce'],
            'measurement_nonce':measured['measurement_nonce'],'cost_processes':len(costs['proof_runs']),
            'evidence_sha256':{str(folder/n):digest(folder/n) for n in ['verification.json','proof-costs.json','measurements.json','audit.md']}}
    (folder/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    progress=ROOT/'reports/progress.md'
    rows=progress.read_text().splitlines()
    for i,line in enumerate(rows):
        if line.startswith('| E1 |'):
            rows[i]='| E1 | 完了 | [M1監査](m1/audit.md)。子の定理・合成・直接版の一致・3回の修正費用の比較 |'
        if line.startswith('| E2 |'):
            rows[i]='| E2 | 完了 | [M1監査](m1/audit.md)。同じ任意長の契約、実物、境界・ABI・破壊、104バイト、速度と費用の報告 |'
    progress.write_text('\n'.join(rows)+'\n')
    print('M1 audit complete; this audit does not determine M2/M3 completion',flush=True)
    return result


if __name__=='__main__': audit()
