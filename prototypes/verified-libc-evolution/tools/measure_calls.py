"""Frozen E5 call overhead measurements, separately for two linked layouts."""
from datetime import datetime,timezone
import json
import platform
import random
import secrets
import sys
from config import ROOT,BUILD,digest
from measure_m1 import command,summary,compare,cpu_information
from audit_m1 import validate_inputs
from call_artifacts import linked
from build import words

LENGTHS=[0,1,2,4,7,8,9,15,16,17,31,32,33,63,64,255,256,1024,4096,32768,1048576]
CASES=[(n,a) for n in LENGTHS for a in [0,1]]
VARIANTS=['direct','call-a','call-b','libc']


def build(verified):
    artifacts=[];template=words(BUILD/'vp2_call_copy.template.words')
    for label,objects in [('a',['vp2_call_copy','vp2_memcpy_chunk8']),
                          ('b',['vp2_memcpy_chunk8','vp2_link_padding','vp2_call_copy'])]:
        target=BUILD/('benchmark_calls_'+label)
        command(['xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror','-fno-builtin','-fno-lto',
            '-Iinclude',*[BUILD/(n+'.o') for n in objects],'benchmarks/calls.c','-o',target])
        l=linked(target,'vp2_call_copy',verified['layouts']['object'],template,label)
        proved=next(p for p in verified['layouts']['layouts'] if p['label']==label)
        if l['bundle_words']!=proved['bundle_words']:raise RuntimeError('measured code differs from linked proof')
        l['executable_bytes']=target.stat().st_size;artifacts.append(l)
        symbols=command(['xcrun','llvm-objdump','--macho','--syms',target])
        disassembly=command(['xcrun','llvm-objdump','--macho','--disassemble',target])
        if '*UND* _memcpy' not in symbols or '\tblr\t' not in disassembly:
            raise RuntimeError('external libc/indirect timed calls not established')
    return artifacts


def invoke(variant,n,offset,iterations):
    label='b' if variant=='call-b' else 'a'
    actual='call' if variant.startswith('call-') else variant
    return json.loads(command([BUILD/('benchmark_calls_'+label),actual,n,offset,offset,iterations]))


def measure():
    from audit_calls import verification
    verified=verification();gate=BUILD/'measurement-calls.json';gate.unlink(missing_ok=True)
    artifacts=build(verified)
    inputs={str(p):digest(p) for p in [ROOT/'benchmarks/calls.c',ROOT/'tools/measure_calls.py',
        ROOT/'tools/audit_calls.py',ROOT/'tools/measure_m1.py',ROOT/'tools/call_artifacts.py',
        ROOT/'reports/m2/calls-protocol.md',*[a['path'] for a in artifacts]]}
    report=dict(timestamp=datetime.now(timezone.utc).isoformat(),nonce=secrets.token_hex(24),
        proof_snapshot=verified['proof'],method_inputs=inputs,artifacts=artifacts,
        method=dict(seed='0x19273645',samples=7,target_ns=8000000,arena_limit_bytes=128*1024*1024,
            note='API-call observations including harness; no cold-cache or BL-only timing claim'),
        environment=dict(platform=platform.platform(),python=sys.version,cpu=cpu_information(),
            compiler=command(['xcrun','clang','--version']),sdk=command(['xcrun','--show-sdk-version'])),cases=[])
    rng=random.Random(0x19273645)
    for n,offset in CASES:
        iterations=1 if n>=4096 else 1024;calibration=[]
        while True:
            raw=invoke('call-a',n,offset,iterations);calibration.append(raw)
            if raw['elapsed_ns']>=8000000:break
            iterations*=2
            if iterations>2**32:raise RuntimeError('call calibration failed')
        samples={v:[] for v in VARIANTS};orders=[]
        for sample in range(7):
            order=VARIANTS.copy();rng.shuffle(order);orders.append(order)
            for variant in order:samples[variant].append(invoke(variant,n,offset,iterations)|{'sample':sample})
        if len({r['checksum'] for rows in samples.values() for r in rows})!=1:raise RuntimeError('call checksums differ')
        summaries={v:summary([r['elapsed_ns']/iterations for r in rows]) for v,rows in samples.items()}
        report['cases'].append(dict(n=n,offset=offset,iterations=iterations,calibration=calibration,orders=orders,
            samples=samples,ns_per_call=summaries,
            call_vs_direct={v:compare(summaries[v],summaries['direct']) for v in ['call-a','call-b']}))
        if offset==1:print(f'measured calls n={n}',flush=True)
    verification();validate_inputs(inputs);folder=ROOT/'reports/m2'
    (folder/'calls-measurements.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    lines=['# 呼び出しの速度・容量','',f'実測UTC: {report["timestamp"]}',
        '', '[生データ](calls-measurements.json) · [固定した方法](calls-protocol.md)',
        '', '単位ns/呼び出し、中央値。直接はM1カーネル、a・bは同じ24バイトの呼び出し元の異なる配置。',
        '', '| n | ずれ | 直接 | 呼び出しa | 呼び出しb | libc | aの直接比 | bの直接比 |',
        '| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |']
    for c in report['cases']:
        lines.append('| '+str(c['n'])+' | '+str(c['offset'])+' | '+
            ' | '.join(f'{c["ns_per_call"][v]["median"]:.3f}' for v in VARIANTS)+
            ' | '+c['call_vs_direct']['call-a']+' | '+c['call_vs_direct']['call-b']+' |')
    lines+=['','呼び出し元24バイト、コピー76バイト。配置aの束100バイト、bは実験用NOP 256バイトを加え356バイト。',
        '', '配布用のM1コピー・埋め込み・memmove・呼び出し元の本体合計は196バイト。専用スタックは呼び出し元の16バイトのみ。',
        '', 'Cの測定器、パディング、Mach-Oのメタデータ、動的libc等は本体合計と分ける。実行ファイル全体の容量は生データへ記録。',
        '', '時間はループ・間接呼び出し・添字計算を含み、純粋なBL単体の遅延ではない。モデルの命令ステップ数や実時間の上限とも異なる。']
    (folder/'calls-measurements.md').write_text('\n'.join(lines)+'\n')
    gate.write_text(json.dumps(dict(nonce=report['nonce'],sha256=digest(folder/'calls-measurements.json')),indent=2)+'\n')
    from audit_calls import audit
    audit();return report


if __name__=='__main__':measure()
