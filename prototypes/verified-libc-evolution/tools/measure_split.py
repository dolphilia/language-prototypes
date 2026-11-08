"""Predeclared checked-caller measurements, using only proved byte bundles."""
from datetime import datetime,timezone
import json
import platform
import random
import secrets
import sys
from config import ROOT,BUILD,digest
from measure_m1 import command,summary,compare,cpu_information
from call_artifacts import call_object,linked
from build import MachO,words,check_span
from audit_m1 import validate_inputs

LENGTHS=[0,1,2,4,7,8,9,15,16,17,31,32,33,63,64,255,256,1024,4096,32768,1048576]
MODES={'direct':0,'call':1,'checked':2}
MAX=(1<<64)-1
CASES=[dict(name=f'valid-{n}-{a}',capacity=2*n+64,split=n+32,n=n,offset=a,valid=True)
       for n in LENGTHS for a in [0,1]]+[
    dict(name=name,capacity=64,split=k,n=n,offset=0,valid=False) for name,k,n in [
        ('split-zero',0,0),('split-end',64,0),('n-over-input',16,17),('n-over-output',48,17),
        ('maximum-n',32,MAX),('maximum-split',MAX,0)]]


def build(verified):
    from audit_calls import verification as calls
    proved_call=calls();artifacts=[];sizes=[]
    objects={'direct':['vp2_memcpy_chunk8'],'call':['vp2_call_copy','vp2_memcpy_chunk8'],
             'checked':['vp2_copy_split','vp2_memcpy_chunk8']}
    common=['xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror','-fno-builtin','-fno-lto','-Iinclude']
    for variant,mode in MODES.items():
        target=BUILD/('benchmark_split_'+variant)
        command([*common,'-DVP_MODE='+str(mode),*[BUILD/(n+'.o') for n in objects[variant]],
                 'benchmarks/split.c','-o',target])
        symbol='vp2_copy_split' if variant=='checked' else 'vp2_call_copy'
        if variant=='direct':
            body=words(BUILD/'vp2_memcpy_chunk8.words');check_span(target,'vp2_memcpy_chunk8',body,object_only=False)
            record=dict(label=variant,path=str(target),sha256=digest(target),body_bytes=len(body))
        else:
            template=words(BUILD/(symbol+'.template.words'));obj=call_object(BUILD/(symbol+'.o'),symbol,template)
            record=linked(target,symbol,obj,template,variant)
            expected=verified['layouts']['layout'] if variant=='checked' else proved_call['layouts']['layouts'][0]
            if record['bundle_words']!=expected['bundle_words']:
                raise RuntimeError('measured checked/call code differs from proof')
        artifacts.append(record)
        disassembly=command(['xcrun','llvm-objdump','--macho','--disassemble',target])
        if '\tblr\t' not in disassembly:raise RuntimeError('indirect measurement calls not established')
        directory=BUILD/'sizes-split'/variant;directory.mkdir(parents=True,exist_ok=True);sized=directory/'size'
        command([*common,'-DVP_MODE='+str(mode),*[BUILD/(n+'.o') for n in objects[variant]],
                 'benchmarks/split_size.c','-o',sized]);command([sized])
        size_linked=None
        if variant!='direct':
            size_linked=linked(sized,symbol,obj,template,variant+'-size')
            if size_linked['bundle_words']!=expected['bundle_words']:
                raise RuntimeError('size artifact call code differs from proof')
        bodies=[]
        for name in objects[variant]:
            p=MachO(BUILD/(name+'.o'));start=p.symbol('_'+name);end=p.symbol('_'+name+'_end')
            section=p.sections[start.section-1]
            body=p.span(section.offset+start.address-section.address,end.address-start.address)
            if name=='vp2_memcpy_chunk8':check_span(sized,name,body,object_only=False)
            bodies.append(dict(name=name,body_bytes=len(body),object_bytes=(BUILD/(name+'.o')).stat().st_size,
                text_padding_bytes=section.size-len(body)))
        sizes.append(dict(variant=variant,path=str(sized),sha256=digest(sized),basename=sized.name,
                          executable_bytes=sized.stat().st_size,bodies=bodies,linked_artifact=size_linked))
    return artifacts,sizes


def invoke(variant,case,iterations):
    return json.loads(command([BUILD/('benchmark_split_'+variant),case['capacity'],case['split'],
        case['n'],case['offset'],iterations,'v1']))


def measure():
    from audit_split import verification
    verified=verification();gate=BUILD/'measurement-split.json';gate.unlink(missing_ok=True)
    artifacts,sizes=build(verified)
    inputs={str(p):digest(p) for p in [ROOT/'benchmarks/split.c',ROOT/'benchmarks/split_size.c',
        ROOT/'tools/measure_split.py',ROOT/'tools/audit_split.py',ROOT/'tools/measure_m1.py',
        ROOT/'tools/call_artifacts.py',ROOT/'reports/m2/split-protocol.md',
        *[a['path'] for a in artifacts],*[s['path'] for s in sizes]]}
    report=dict(timestamp=datetime.now(timezone.utc).isoformat(),nonce=secrets.token_hex(24),
        proof_snapshot=verified['proof'],method_inputs=inputs,artifacts=artifacts,sizes=sizes,
        method=dict(seed='0x19273645',samples=7,target_ns=8000000,arena_limit_bytes=128*1024*1024,
            note='API observations including harness and marshalling; invalid paths never call copy; no isolated-instruction or cold-cache guarantee'),
        environment=dict(platform=platform.platform(),python=sys.version,cpu=cpu_information(),
            compiler=command(['xcrun','clang','--version']),sdk=command(['xcrun','--show-sdk-version'])),cases=[])
    rng=random.Random(0x19273645)
    for c in CASES:
        variants=list(MODES) if c['valid'] else ['checked']
        iterations=1 if c['valid'] and c['n']>=4096 else 1024;calibration=[]
        while True:
            raw=invoke('checked',c,iterations);calibration.append(raw)
            if raw['elapsed_ns']>=8000000:break
            iterations*=2
            if iterations>2**32:raise RuntimeError('split calibration failed')
        samples={v:[] for v in variants};orders=[]
        for sample in range(7):
            order=variants.copy();rng.shuffle(order);orders.append(order)
            for variant in order:samples[variant].append(invoke(variant,c,iterations)|{'sample':sample})
        if len({r['checksum'] for rows in samples.values() for r in rows})!=1:raise RuntimeError('split checksums differ')
        stats={v:summary([r['elapsed_ns']/iterations for r in rows]) for v,rows in samples.items()}
        report['cases'].append(c|dict(iterations=iterations,calibration=calibration,orders=orders,samples=samples,
            ns_per_call=stats,checked_vs_direct=compare(stats['checked'],stats['direct']) if c['valid'] else None,
            checked_vs_call=compare(stats['checked'],stats['call']) if c['valid'] else None))
        print('measured split:',c['name'],flush=True)
    verification();validate_inputs(inputs);folder=ROOT/'reports/m2'
    (folder/'split-measurements.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    lines=['# 検査付き呼び出しの速度・容量','',f'実測UTC: {report["timestamp"]}',
        '', '[生データ](split-measurements.json) · [固定した方法](split-protocol.md)',
        '', '単位ns/呼び出し、中央値。正常値42ケースは同じ一つの領域を使う。不正値6ケースは検査付き版だけを実行する。',
        '', '| ケース | 直接 | 単純呼び出し | 検査付き | 直接比 | 単純呼び出し比 |',
        '| --- | ---: | ---: | ---: | --- | --- |']
    for c in report['cases']:
        def number(v):return f'{c["ns_per_call"][v]["median"]:.3f}' if v in c['ns_per_call'] else '—'
        lines.append('| '+c['name']+' | '+' | '.join(number(v) for v in MODES)+' | '+
            (c['checked_vs_direct'] or '—')+' | '+(c['checked_vs_call'] or '—')+' |')
    lines+=['','コピー本体76、単純な呼び出し24、検査付き呼び出し80バイト。M1の埋め込みとE4のmemmoveも残した全5関数の本体合計は276バイト。',
        '', '呼び出し元の専用枠はそれぞれ16バイト。検査付き版はM1コピーを直接呼ぶため、最大使用は16バイトである。ヒープと証明用の実行処理はない。',
        '', '直接・単純呼び出し・検査付きの差には引数設定・配置も含む。検査やBLだけの純粋な遅延ではない。不正値の経路にはコピー・専用枠へのアクセスがないが、外側のループと間接呼び出しは含む。',
        '', '容量用の実行ファイルは同じbasenameで比較し、生データへ本体・オブジェクト・配置余白・ファイル全体を保存した。']
    (folder/'split-measurements.md').write_text('\n'.join(lines)+'\n')
    gate.write_text(json.dumps(dict(nonce=report['nonce'],sha256=digest(folder/'split-measurements.json')),indent=2)+'\n')
    from audit_split import audit
    audit();return report


if __name__=='__main__':measure()
