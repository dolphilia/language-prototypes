"""E4-only completion requires current proof, runtime and measurement evidence."""
from datetime import datetime,timezone
import json
import signal
from config import ROOT,BUILD,digest
from audit_m1 import validate_inputs
from verify_regions import require_m1


def expected_checks():
    blocks=[f'vp2_block_copy8_{n}' for n in [0,8,16,24]]+[
        'vp2_block_copy8_x3','vp2_block_copy8_indexed','vp2_block_copybyte_indexed']
    positive=['forward-unread-range','backward-unread-range','forward','backward','public',
        'zero-no-data','same-no-data','forward-access','backward-access','access-strong','access']
    negatives=['always-forward','always-backward','reverse-direction','missing-first','missing-last',
               'zero-decrement','overread','overwrite']
    return set(blocks+['memmove:'+n for n in positive]+
               [f'move-mut:{n}:{part}' for n in negatives for part in ['initial','numeric','execution']])


def verification():
    require_m1()
    r=json.loads((ROOT/'reports/m2/memmove-verification.json').read_text())
    if not r['verification_passed'] or set(r['proof']['checks'])!=expected_checks():
        raise RuntimeError('required E4 proof coverage missing')
    validate_inputs(r['proof']['inputs']);validate_inputs(r['native']['inputs'])
    validate_inputs(r['native_mutations']['inputs'])
    if r['native']['checks']<35000 or len(r['native_mutations']['results'])!=8:
        raise RuntimeError('E4 native coverage missing')
    for row in r['native_mutations']['results']:
        allowed={0} if row['kind']=='functional' else {-signal.SIGBUS,-signal.SIGSEGV}
        if row['normal_control_returncode']!=4 or row['mutation_returncode'] not in allowed:
            raise RuntimeError('mutation/control evidence inconsistent')
        if digest(BUILD/('move_negative_'+row['name']))!=row['executable_sha256']:
            raise RuntimeError('native mutation executable changed')
    for row in r['artifacts']:
        if digest(row['path'])!=row['sha256'] or row['body_bytes']>256:
            raise RuntimeError('E4 artifact identity/budget mismatch')
    return r


def audit():
    verified=verification()
    from measure_memmove import CASES,VARIANTS,summary,compare
    folder=ROOT/'reports/m2'
    measured=json.loads((folder/'memmove-measurements.json').read_text())
    validate_inputs(measured['method_inputs']);validate_inputs(measured['proof_snapshot']['inputs'])
    if set(measured['proof_snapshot']['checks'])!=expected_checks():raise RuntimeError('measurement proof incomplete')
    cases=measured['cases']
    if len(cases)!=len(CASES) or {(c['n'],c['offset'],c['delta']) for c in cases}!=set(CASES):
        raise RuntimeError('E4 performance matrix missing or duplicated')
    for c in cases:
        if c['calibration'][-1]['elapsed_ns']<8000000:raise RuntimeError('E4 calibration too short')
        if c['n']>=4096 and c['calibration'][0]['iterations']!=1:raise RuntimeError('large calibration start differs')
        if set(c['samples'])!=set(VARIANTS) or len(c['orders'])!=7 or any(sorted(o)!=sorted(VARIANTS) for o in c['orders']):
            raise RuntimeError('E4 sample/order coverage missing')
        for variant,rows in c['samples'].items():
            if len(rows)!=7 or len({r['pid'] for r in rows})!=7:raise RuntimeError('separate E4 processes required')
            if any(r['iterations']!=c['iterations'] or r['arena_bytes']>128*1024*1024 or
                   r['warmup_calls']>4096 or r['warmup_calls']*c['n']>4194304 for r in rows):
                raise RuntimeError('E4 measurement bounds violated')
            if summary([r['elapsed_ns']/c['iterations'] for r in rows])!=c['ns_per_call'][variant]:
                raise RuntimeError('E4 summary differs from raw measurements')
        if c['new_vs_libc']!=compare(c['ns_per_call']['new'],c['ns_per_call']['libc']):
            raise RuntimeError('E4 classification differs from predeclared rule')
    gate=json.loads((BUILD/'measurement-memmove.json').read_text())
    if gate['nonce']!=measured['nonce'] or gate['sha256']!=digest(folder/'memmove-measurements.json'):
        raise RuntimeError('current E4 measurement receipt missing')
    for row in measured['artifacts']:
        if digest(row['path'])!=row['sha256']:raise RuntimeError('measured E4 artifact changed')
    if {s['basename'] for s in measured['sizes']}!={'size'}:raise RuntimeError('E4 size basenames differ')
    from build import MachO
    actual=len(MachO(BUILD/'vp2_memmove.o').function('vp2_memmove',object_only=True))
    if actual!=verified['body_bytes'] or actual>256:raise RuntimeError('E4 leaf body differs')
    counts={label:sum(c['new_vs_libc']==label for c in cases) for label in ['高速','低速','不明']}
    lines=['# E4の完了監査','', 'E4を完了と判定する。E5・E3bを含むM2全体は未完了。',
        '', '| 条件 | 証拠 |','| --- | --- |',
        '| 独立した重複の仕様と全経路の証明 | [42定理](memmove-proof.json)。開始時の入力、機能・有限復帰・保存・途中のアクセス |',
        '| 実物とABI | [検査結果](memmove-verification.json)。LLVMとの位置の照合、実機35,709件、全バッファ・libc・重複・ガード・保存状態 |',
        '| 誤実装 | 方向3例、欠落2例、ゼロ長の減算、過剰な読み書き。モデルの有効な初期状態と有限の違反、実機8例と正常対照 |',
        f'| 容量と資源 | 葉関数{actual}バイト、別枠の256バイト以下。専用スタック・ヒープ・証明用の実行費用なし |',
        f'| 性能 | [全{len(cases)}ケース](memmove-measurements.md)、各実装7プロセス。libc比の分類: {json.dumps(counts,ensure_ascii=False)} |',
        '', '同一アドレスとゼロ長はデータアクセスなし。重複時に入力領域全体を保存する仕様にはしていない。',
        '', '有限の最初の復帰時のデータ違反やアクセス違反を、一般のHOL Hoare命題の否定と同一視しない。通常RAM・有効性・寿命・排他的更新、ISAモデルと実機の対応等の外部契約は残る。',
        '', 'この逐次的なmemmoveの証明は、E3aの重複しない二つの借用をそのまま重複させられることを意味しない。重複を許す高水準APIの権限の構成は別に検討する。']
    (folder/'memmove-audit.md').write_text('\n'.join(lines)+'\n')
    verified['phase_complete']=True;verified['remaining']=[]
    (folder/'memmove-verification.json').write_text(json.dumps(verified,ensure_ascii=False,indent=2)+'\n')
    result=dict(scope='E4 only',complete=True,timestamp=datetime.now(timezone.utc).isoformat(),
        proof_nonce=verified['proof']['nonce'],measurement_nonce=measured['nonce'],
        evidence_sha256={str(folder/n):digest(folder/n) for n in
            ['memmove-verification.json','memmove-proof.json','memmove-measurements.json','memmove-audit.md']})
    (folder/'memmove-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    requirements=json.loads((ROOT/'reports/requirements.json').read_text())
    for item in requirements['requirements']:
        if item['id'].startswith('E4.'):
            item.update(status='complete',evidence=['reports/m2/memmove-audit.md','reports/m2/memmove-verification.json',
                'reports/m2/memmove-measurements.json'])
    (ROOT/'reports/requirements.json').write_text(json.dumps(requirements,indent=2)+'\n')
    progress=ROOT/'reports/progress.md';rows=progress.read_text().splitlines()
    for i,row in enumerate(rows):
        if row.startswith('| E4 |'):
            rows[i]=f'| E4 | 完了 | [監査](m2/memmove-audit.md)。42定理・実機35,709件・誤実装8例・68バイト・{len(cases)}ケース各7回の測定 |'
    progress.write_text('\n'.join(rows)+'\n')
    print('E4 audit complete; E5/E3b and M2 remain incomplete',flush=True)
    return result


if __name__=='__main__': audit()
