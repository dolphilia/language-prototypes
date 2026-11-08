"""E3b implementation/evaluation audit; M2 command integration is separate."""
from datetime import datetime,timezone
import json
import signal
from config import ROOT,BUILD,digest
from audit_m1 import validate_inputs
from build_split import prerequisites
from call_artifacts import call_object,linked
from build import words
from verify_regions import REGION_CHECKS
from split_mutations import EDITS


def expected_checks():
    blocks=[f'vp2_block_copy8_{n}' for n in [0,8,16,24]]+[
        'vp2_block_copy8_x3','vp2_block_copy8_indexed','vp2_block_copybyte_indexed']
    return blocks+['chunk8:'+n for n in ['tail','bulk','public','tail-access','bulk-access','access-strong','access']]+[
        'regions:'+n for n in REGION_CHECKS]+['split:'+n for n in
        ['success','public','trace-root','success-access','access','region-protocol','machine-protocol']]+[
        'split:positive:initial','split:positive:numeric']+[
        f'split-mut:{name}:{part}' for name,*_ in EDITS for part in ['initial','numeric','execution']]


def verification():
    prerequisites();r=json.loads((ROOT/'reports/m2/split-verification.json').read_text())
    if not r['verification_passed'] or r['proof']['checks']!=expected_checks():
        raise RuntimeError('E3b required closed theorem coverage missing')
    validate_inputs(r['proof']['inputs']);validate_inputs(r['source_files']);validate_inputs(r['mutations']['inputs'])
    if json.loads((BUILD/'proof-split.json').read_text())!=r['proof']:
        raise RuntimeError('current E3b proof receipt missing')
    template=words(BUILD/'vp2_copy_split.template.words')
    obj=call_object(BUILD/'vp2_copy_split.o','vp2_copy_split',template)
    if obj!=r['layouts']['object']:raise RuntimeError('checked caller object changed')
    l=r['layouts']['layout'];actual=linked(l['path'],'vp2_copy_split',obj,template,'split')
    if any(l[k]!=v for k,v in actual.items()) or l['native_checks']!=184572:
        raise RuntimeError('checked caller linked/native evidence mismatch')
    if (l['caller_offset'],l['callee_offset'],l['caller_bytes'],l['callee_bytes'],l['call_offset'])!=(0,80,80,76,52):
        raise RuntimeError('checked caller layout differs from proof support')
    control=r['mutations']['control']
    if control!=linked(control['path'],'vp2_copy_split',obj,template,'control'):
        raise RuntimeError('checked caller mutation control changed')
    if [x['name'] for x in r['mutations']['results']]!=[e[0] for e in EDITS]:
        raise RuntimeError('checked caller mutation coverage missing')
    for row,edit in zip(r['mutations']['results'],EDITS):
        name,offset,opcode,k,n,kind,steps=edit;l=row['layout']
        if (row['split'],row['n'],row['kind'],row['steps'])!=(k,n,kind,steps):
            raise RuntimeError('mutation scenario differs from fixed witness')
        allowed={-signal.SIGBUS,-signal.SIGSEGV} if kind=='access' else {0}
        if row['normal_control_returncode']!=4 or row['mutation_returncode'] not in allowed or \
           digest(row['object'])!=row['object_sha256'] or digest(l['path'])!=l['sha256']:
            raise RuntimeError('checked caller mutation/control identity mismatch')
    return r


def audit():
    r=verification()
    from measure_split import CASES,MODES,summary,compare
    folder=ROOT/'reports/m2';m=json.loads((folder/'split-measurements.json').read_text())
    validate_inputs(m['method_inputs']);validate_inputs(m['proof_snapshot']['inputs'])
    if m['proof_snapshot']['checks']!=expected_checks():raise RuntimeError('measured E3b proof coverage missing')
    if len(m['cases'])!=len(CASES) or {c['name'] for c in m['cases']}!={c['name'] for c in CASES}:
        raise RuntimeError('checked caller measurement coverage missing')
    for c in m['cases']:
        expected=next(x for x in CASES if x['name']==c['name'])
        if any(c[k]!=v for k,v in expected.items()):raise RuntimeError('checked caller measurement inputs changed')
        variants=list(MODES) if c['valid'] else ['checked']
        if c['calibration'][-1]['elapsed_ns']<8000000 or set(c['samples'])!=set(variants) or \
           len(c['orders'])!=7 or any(sorted(o)!=sorted(variants) for o in c['orders']):
            raise RuntimeError('E3b calibration/order coverage missing')
        if c['valid'] and c['n']>=4096 and c['calibration'][0]['iterations']!=1:
            raise RuntimeError('E3b large calibration start changed')
        for v,rows in c['samples'].items():
            if len(rows)!=7 or len({x['pid'] for x in rows})!=7:raise RuntimeError('seven separate processes required')
            transferred=c['n'] if c['valid'] else 0
            if any(x['iterations']!=c['iterations'] or x['arena_bytes']>128*1024*1024 or
                   x['transferred_bytes_per_call']!=transferred or x['warmup_calls']>4096 or
                   x['warmup_calls']*transferred>4194304 for x in rows):
                raise RuntimeError('checked caller measurement method bounds exceeded')
            if summary([x['elapsed_ns']/c['iterations'] for x in rows])!=c['ns_per_call'][v]:
                raise RuntimeError('checked caller statistics differ from raw observations')
        for v,key in [('direct','checked_vs_direct'),('call','checked_vs_call')]:
            if c[key]!=(compare(c['ns_per_call']['checked'],c['ns_per_call'][v]) if c['valid'] else None):
                raise RuntimeError('checked caller speed classification inconsistent')
    for a in m['artifacts']:
        if digest(a['path'])!=a['sha256']:raise RuntimeError('checked caller measured code changed')
        if a['label']=='checked' and a['bundle_words']!=r['layouts']['layout']['bundle_words']:
            raise RuntimeError('measured checked caller differs from proof')
    if {s['basename'] for s in m['sizes']}!={'size'}:raise RuntimeError('size basenames differ')
    for s in m['sizes']:
        if digest(s['path'])!=s['sha256']:raise RuntimeError('size artifact changed')
    gate=json.loads((BUILD/'measurement-split.json').read_text())
    if gate!={'nonce':m['nonce'],'sha256':digest(folder/'split-measurements.json')}:
        raise RuntimeError('current checked caller measurement receipt missing')
    lines=['# E3bの実装・評価の監査','',
        'E3bの実装・証明・実物・評価を完了と判定する。M2のコマンド統合と全体監査はこの判定へ含めない。','',
        '- 公開事前条件には動的な長さのガードを追加していない。任意のsize_tを受け、実際の分岐からコピーの条件を導く。',
        '- 64定理を新規プロセスで検査。成功・失敗のデータ、有限復帰、SP/LRとABI、途中のアクセス、成功状態からの領域の権限、正例・反例の初期状態と実行。',
        '- 不正値の4経路は、コピー・専用枠・利用者のデータへのアクセスなし。1を返し、元の領域を保存する。',
        '- 実機184,572件。5つの誤実装に、モデル内の有効な初期状態と有限の違反、実機の正常対照がある。',
        '- 本体80バイト、M1コピー76バイト。専用枠16バイト。正常値42ケースの3変種と不正値6ケースを各7プロセスで測定。',
        '', '[検査結果](split-verification.json) · [証明の入力](split-proof.json) · [測定](split-measurements.md)',
        '', '所有する通常RAM・スタックの実在と有効性・寿命・排他的利用、台帳と実メモリの対応、ISAとCPU・実行器・OSローダーの対応は外部契約として残る。一般の借用検査器やOS・アロケータの検証ではない。']
    (folder/'split-audit.md').write_text('\n'.join(lines)+'\n')
    r['phase_complete']=True;r['scope']='E3b implementation/evaluation only; M2 command integration excluded'
    (folder/'split-verification.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    result=dict(scope='E3b implementation/evaluation only',complete=True,
        timestamp=datetime.now(timezone.utc).isoformat(),evidence_sha256={str(folder/n):digest(folder/n) for n in
            ['split-verification.json','split-proof.json','split-measurements.json','split-audit.md']})
    (folder/'split-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    requirements=json.loads((ROOT/'reports/requirements.json').read_text())
    for item in requirements['requirements']:
        if item['id'].startswith('E3b.') and item['id']!='E3b.m2_commands_and_audit':
            item.update(status='complete',evidence=['reports/m2/split-audit.md','reports/m2/split-verification.json',
                'reports/m2/split-measurements.json'])
    (ROOT/'reports/requirements.json').write_text(json.dumps(requirements,indent=2)+'\n')
    progress=ROOT/'reports/progress.md';rows=progress.read_text().splitlines()
    for i,row in enumerate(rows):
        if row.startswith('| E3b |'):
            rows[i]='| E3b | 実装・評価完了、M2統合未完 | [監査](m2/split-audit.md)。64定理、実機184,572件、誤実装5例、48ケース各7回 |'
    progress.write_text('\n'.join(rows)+'\n')
    print('E3b implementation/evaluation audit complete; M2 command integration and M3 remain incomplete',flush=True)
    return result


if __name__=='__main__':audit()
