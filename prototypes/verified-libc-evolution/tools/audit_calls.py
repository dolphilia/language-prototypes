"""E5-only audit: all required evidence must still identify current inputs."""
from datetime import datetime,timezone
import json
import signal
from config import ROOT,BUILD,digest
from audit_m1 import validate_inputs
from verify_regions import require_m1
from call_artifacts import call_object,linked
from build import words


def expected_checks():
    blocks=[f'vp2_block_copy8_{n}' for n in [0,8,16,24]]+[
        'vp2_block_copy8_x3','vp2_block_copy8_indexed','vp2_block_copybyte_indexed']
    chunk=['tail','bulk','public','tail-access','bulk-access','access-strong','access']
    return blocks+['chunk8:'+n for n in chunk]+[
        f'calls:{layout}:{part}' for layout in ['a','b'] for part in ['embedding','functional','access']]+[
        f'calls:{layout}:{part}' for layout in ['a','b'] for part in ['initial','numeric']]+[
        f'call-mut:{name}:{part}' for name in ['stack','register','return'] for part in ['initial','numeric','execution']]


def verification():
    require_m1()
    r=json.loads((ROOT/'reports/m2/calls-verification.json').read_text())
    if not r['verification_passed'] or r['proof']['checks']!=expected_checks():
        raise RuntimeError('E5 closed theorem coverage missing')
    validate_inputs(r['proof']['inputs']);validate_inputs(r['mutations']['inputs'])
    validate_inputs(r['artifact_refusals']['inputs'])
    if json.loads((BUILD/'proof-calls.json').read_text())!=r['proof']:
        raise RuntimeError('current E5 proof receipt missing')
    template=words(BUILD/'vp2_call_copy.template.words')
    obj=call_object(BUILD/'vp2_call_copy.o','vp2_call_copy',template)
    if obj!=r['layouts']['object']:raise RuntimeError('call object changed')
    for l in r['layouts']['layouts']:
        actual=linked(l['path'],'vp2_call_copy',obj,template,l['label'])
        if any(l[k]!=v for k,v in actual.items()) or l['native_checks']!=10944:
            raise RuntimeError('linked/native call evidence changed')
    control=r['mutations']['control']
    if control!=linked(control['path'],'vp2_call_copy',obj,template,'control'):
        raise RuntimeError('unmodified call mutation control changed')
    if len(r['artifact_refusals']['results'])!=23 or len(r['linked_ingest_refusals'])!=9:
        raise RuntimeError('E5 artifact/ingestion refusal coverage missing')
    for row in r['artifact_refusals']['results']:
        if row['path'] and digest(row['path'])!=row['sha256']:raise RuntimeError('refusal fixture changed')
    if [r['name'] for r in r['mutations']['results']]!=['stack','register','return']:
        raise RuntimeError('caller mutation coverage missing')
    for row in r['mutations']['results']:
        allowed={-signal.SIGBUS,-signal.SIGSEGV} if row['name']=='return' else {0}
        if row['normal_control_returncode']!=4 or row['mutation_returncode'] not in allowed or \
           digest(row['path'])!=row['sha256'] or digest(row['object'])!=row['object_sha256']:
            raise RuntimeError('caller native mutation/control mismatch')
    return r


def audit():
    r=verification()
    from measure_calls import CASES,VARIANTS,summary,compare
    folder=ROOT/'reports/m2';m=json.loads((folder/'calls-measurements.json').read_text())
    validate_inputs(m['method_inputs']);validate_inputs(m['proof_snapshot']['inputs'])
    if m['proof_snapshot']['checks']!=expected_checks():raise RuntimeError('measured proof coverage missing')
    if len(m['cases'])!=len(CASES) or {(c['n'],c['offset']) for c in m['cases']}!=set(CASES):
        raise RuntimeError('E5 measurement cases incomplete')
    for c in m['cases']:
        if c['calibration'][-1]['elapsed_ns']<8000000 or set(c['samples'])!=set(VARIANTS) or \
           len(c['orders'])!=7 or any(sorted(o)!=sorted(VARIANTS) for o in c['orders']):
            raise RuntimeError('E5 measurement calibration/order coverage missing')
        if c['n']>=4096 and c['calibration'][0]['iterations']!=1:raise RuntimeError('large calibration start changed')
        for v,rows in c['samples'].items():
            if len(rows)!=7 or len({x['pid'] for x in rows})!=7:raise RuntimeError('fresh measurement processes required')
            if any(x['iterations']!=c['iterations'] or x['arena_bytes']>128*1024*1024 or
                   x['warmup_calls']>4096 or x['warmup_calls']*c['n']>4194304 for x in rows):
                raise RuntimeError('call measurement exceeded method bounds')
            if summary([x['elapsed_ns']/c['iterations'] for x in rows])!=c['ns_per_call'][v]:
                raise RuntimeError('call statistics differ from raw observations')
        if any(c['call_vs_direct'][v]!=compare(c['ns_per_call'][v],c['ns_per_call']['direct']) for v in ['call-a','call-b']):
            raise RuntimeError('call comparison classification inconsistent')
    for l in m['artifacts']:
        if digest(l['path'])!=l['sha256']:raise RuntimeError('measured call artifact changed')
        proved=next(p for p in r['layouts']['layouts'] if p['label']==l['label'])
        if l['bundle_words']!=proved['bundle_words']:raise RuntimeError('measured linked bundle differs from proof')
    gate=json.loads((BUILD/'measurement-calls.json').read_text())
    if gate!={'nonce':m['nonce'],'sha256':digest(folder/'calls-measurements.json')}:
        raise RuntimeError('current call measurement receipt missing')
    lines=['# E5の完了監査','',
        'E5を完了と判定する。検査付きの呼び出し元E3bとM2全体は未完了。','',
        '- 2配置のリンク後の命令列・埋め込み・実際のBL・有限復帰・SP/LR復元・フレーム・途中のアクセスを33個の閉じた定理と反例で確認。',
        '- 各配置で10,944件の実機チェック。改変成果物23例、取り込み境界9例、呼び出し元の誤実装3例と正常対照。',
        '- 共通ロード位置を量化。静的な直接呼び出し一つのみ。スタック枠16バイト、呼び出し元24バイト、コピー76バイト。',
        '- [測定](calls-measurements.md)は42ケース・4変種・各7プロセス。実行器の費用を含む。',
        '', '抽出器・小さなリンク後のバイト取り込み・リンカ・OSローダーは検証済みとはしない。再配置の一般定理も主張しない。公理の追加はない。',
        '', '[機械可読の検査結果](calls-verification.json) · [証明の入力](calls-proof.json)']
    (folder/'calls-audit.md').write_text('\n'.join(lines)+'\n')
    r['phase_complete']=True;r['scope']='E5 only, complete'
    (folder/'calls-verification.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    result=dict(scope='E5 only',complete=True,timestamp=datetime.now(timezone.utc).isoformat(),
        evidence_sha256={str(folder/n):digest(folder/n) for n in
            ['calls-verification.json','calls-proof.json','calls-measurements.json','calls-audit.md']})
    (folder/'calls-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    requirements=json.loads((ROOT/'reports/requirements.json').read_text())
    for item in requirements['requirements']:
        if item['id'].startswith('E5.'):
            item.update(status='complete',evidence=['reports/m2/calls-audit.md','reports/m2/calls-verification.json',
                'reports/m2/calls-measurements.json'])
    (ROOT/'reports/requirements.json').write_text(json.dumps(requirements,indent=2)+'\n')
    progress=ROOT/'reports/progress.md';rows=progress.read_text().splitlines()
    for i,row in enumerate(rows):
        if row.startswith('| E5 |'):
            rows[i]='| E5 | 完了 | [監査](m2/calls-audit.md)。2配置、リンク後33定理、各10,944件、改変23例・取り込み9例・誤実装3例、42ケース各7回 |'
    progress.write_text('\n'.join(rows)+'\n')
    print('E5 audit complete; E3b/M2 and M3 remain incomplete',flush=True)
    return result


if __name__=='__main__':audit()
