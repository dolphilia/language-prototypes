"""Predeclared E4 comparison on exactly the proved/checked machine code."""
from datetime import datetime,timezone
import json
import platform
import random
import secrets
import sys
from config import ROOT,BUILD,digest
from measure_m1 import command,summary,compare,cpu_information
from m2_artifacts import leaf
from build import MachO,check_span,words
from audit_m1 import validate_inputs

LENGTHS=[0,1,2,4,7,8,9,15,16,17,31,32,33,63,64,255,256,1024,4096,32768,1048576]
OFFSETS=[0,1,7]
VARIANTS=['new','libc']
CASES=[(n,a,d) for n in LENGTHS for a in OFFSETS for d in sorted({0,-1,1,-n,n})]


def build():
    common=['xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror',
            '-fno-builtin','-fno-lto','-Iinclude']
    command([*common,'benchmarks/memmove.c',BUILD/'vp2_memmove.o','-o',BUILD/'benchmark_memmove'])
    disassembly=command(['xcrun','llvm-objdump','--macho','--disassemble',BUILD/'benchmark_memmove'])
    symbols=command(['xcrun','llvm-objdump','--macho','--syms',BUILD/'benchmark_memmove'])
    if '*UND* _memmove' not in symbols or '\tblr\t' not in disassembly:
        raise RuntimeError('external memmove and indirect calls not established')
    sizes=[]
    for label,objects in [('memmove',['vp2_memmove']),
                          ('with-m1',['vp2_memmove','vp2_memcpy_chunk8','vp2_memset'])]:
        directory=BUILD/'sizes-m2'/label;directory.mkdir(parents=True,exist_ok=True)
        target=directory/'size'
        command([*common,'benchmarks/memmove_size.c',*[BUILD/(n+'.o') for n in objects],'-o',target])
        command([target])
        bodies=[]
        for name in objects:
            body=MachO(BUILD/(name+'.o')).function(name,object_only=True)
            check_span(target,name,body,object_only=False)
            obj=MachO(BUILD/(name+'.o'));section=obj.sections[obj.symbol('_'+name).section-1]
            bodies.append(dict(name=name,body_bytes=len(body),object_bytes=(BUILD/(name+'.o')).stat().st_size,
                               text_padding_bytes=section.size-len(body)))
        sizes.append(dict(variant=label,executable=str(target),basename=target.name,
                          executable_bytes=target.stat().st_size,sha256=digest(target),bodies=bodies))
    return sizes,leaf('vp2_memmove',['test_memmove','benchmark_memmove'])


def invoke(variant,n,offset,delta,iterations):
    return json.loads(command([BUILD/'benchmark_memmove',variant,n,offset,delta,iterations,'v1']))


def measure():
    from audit_memmove import verification
    verified=verification()
    gate=BUILD/'measurement-memmove.json';gate.unlink(missing_ok=True)
    sizes,artifacts=build()
    paths=[ROOT/'benchmarks/memmove.c',ROOT/'benchmarks/memmove_size.c',
           ROOT/'tools/measure_memmove.py',ROOT/'tools/audit_memmove.py',ROOT/'tools/measure_m1.py',
           ROOT/'reports/m2/evaluation-protocol.md',BUILD/'benchmark_memmove',
           *[s['executable'] for s in sizes]]
    inputs={str(p):digest(p) for p in paths}
    report=dict(timestamp=datetime.now(timezone.utc).isoformat(),nonce=secrets.token_hex(24),
        proof_snapshot=verified['proof'],method_inputs=inputs,sizes=sizes,artifacts=artifacts,
        method=dict(seed='0x19273645',samples=7,target_ns=8000000,arena_limit_bytes=128*1024*1024,
                    warmup_limit_calls=4096,warmup_limit_bytes=4194304,
                    limitations='finite API-call observations including loop/indirect-call/index costs; no cold-cache guarantee'),
        environment=dict(platform=platform.platform(),python=sys.version,cpu=cpu_information(),
            compiler=command(['xcrun','clang','--version']),sdk=command(['xcrun','--show-sdk-version'])),cases=[])
    rng=random.Random(0x19273645)
    for n,offset,delta in CASES:
        iterations=1 if n>=4096 else 1024;calibration=[]
        while True:
            raw=invoke('new',n,offset,delta,iterations);calibration.append(raw)
            if raw['elapsed_ns']>=8000000:break
            iterations*=2
            if iterations>2**32:raise RuntimeError('calibration failed')
        samples={v:[] for v in VARIANTS};orders=[]
        for sample in range(7):
            order=VARIANTS.copy();rng.shuffle(order);orders.append(order)
            for variant in order:
                samples[variant].append(invoke(variant,n,offset,delta,iterations)|{'sample':sample})
        if len({r['checksum'] for rows in samples.values() for r in rows})!=1:
            raise RuntimeError('memmove checksums differ')
        summaries={v:summary([r['elapsed_ns']/iterations for r in rows]) for v,rows in samples.items()}
        report['cases'].append(dict(n=n,offset=offset,delta=delta,iterations=iterations,
            calibration=calibration,orders=orders,samples=samples,ns_per_call=summaries,
            new_vs_libc=compare(summaries['new'],summaries['libc'])))
        if offset==7 and delta==max({0,-1,1,-n,n}):print(f'measured memmove n={n}',flush=True)
    verification();validate_inputs(inputs)
    folder=ROOT/'reports/m2'
    (folder/'memmove-measurements.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    lines=['# memmoveの速度・容量','',f'実測UTC: {report["timestamp"]}',
        '', '[生データ](memmove-measurements.json) · [事前の方法](evaluation-protocol.md)',
        '', '各実装を7個の別プロセスで測定。単位ns/呼び出し、中央値。正の差は後ろ向き、負は前向き、差0は同一アドレス。',
        '', '| n | 元のずれ | コピー先との差 | 新版 | libc | 新版の判定 |',
        '| ---: | ---: | ---: | ---: | ---: | --- |']
    for c in report['cases']:
        lines.append(f'| {c["n"]} | {c["offset"]} | {c["delta"]} | {c["ns_per_call"]["new"]["median"]:.3f} | {c["ns_per_call"]["libc"]["median"]:.3f} | {c["new_vs_libc"]} |')
    lines+=['','本体は68バイト。M1の選択した2関数104バイトを含む本体合計は172バイト。',
        '', '容量用の同じbasenameの実行ファイルと、オブジェクト・配置余白は生データへ保存した。システムlibcの共有コードはこの本体合計に含まず、実行ファイルの大小からlibc全体との容量優劣を推定しない。',
        '', '測定区間には間接呼び出し・ループ・大きい領域を回す添字計算も含む。キャッシュ状態や実時間の上限を保証する測定ではない。']
    (folder/'memmove-measurements.md').write_text('\n'.join(lines)+'\n')
    gate.write_text(json.dumps(dict(nonce=report['nonce'],sha256=digest(folder/'memmove-measurements.json')),indent=2)+'\n')
    from audit_memmove import audit
    audit()
    return report


if __name__=='__main__': measure()
