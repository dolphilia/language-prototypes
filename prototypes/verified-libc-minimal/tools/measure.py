"""Run the predeclared benchmark matrix; preserve raw independent samples."""
from pathlib import Path
import hashlib
import json
import platform
import random
import statistics
import subprocess
from datetime import datetime, timezone
from check_artifacts import check_primitives, ROOT, expected_bytes
from macho import MachO

LENGTHS = [0,1,2,7,8,9,15,16,17,31,32,63,64,255,256,1024]
SAMPLES = 7


def command(*args):
    return subprocess.check_output(list(args), text=True).strip()


def invoke(kind, variant, n, sa, da, iterations):
    return json.loads(command(str(ROOT/'build/benchmark'),kind,variant,
                             str(n),str(sa),str(da),str(iterations)))


def summary(values):
    quartiles=statistics.quantiles(values,n=4,method='inclusive')
    return dict(median=statistics.median(values),minimum=min(values),
                maximum=max(values),q1=quartiles[0],q3=quartiles[2])


def compare(a,b):
    if a['median'] < .95*b['median'] and a['q3'] < b['q1']: return '高速'
    if b['median'] < .95*a['median'] and b['q3'] < a['q1']: return '低速'
    return '不明'


def sizes():
    records=[]
    for name in ['vp_memcpy_scalar','vp_memcpy','vp_memset']:
        path=ROOT/'build'/f'{name}.o'
        obj=MachO(path)
        section=obj.sections[obj.symbol('_'+name).section-1]
        body=len(expected_bytes(name))
        records.append(dict(name=name,body_bytes=body,
            text_padding_bytes=section.size-body,object_bytes=path.stat().st_size))
    return dict(functions=records,
        scalar_executable_bytes=(ROOT/'build/size_scalar').stat().st_size,
        optimized_executable_bytes=(ROOT/'build/size_optimized').stat().st_size,
        selected_body_bytes=len(expected_bytes('vp_memcpy'))+len(expected_bytes('vp_memset')))


def main():
    check_primitives(('test_memory','benchmark'))
    scalar=MachO(ROOT/'build/size_scalar')
    if scalar.function('vp_memcpy') != expected_bytes('vp_memcpy_scalar'):
        raise RuntimeError('size harness scalar bytes mismatch')
    opt=MachO(ROOT/'build/size_optimized')
    if opt.function('vp_memcpy') != expected_bytes('vp_memcpy'):
        raise RuntimeError('size harness optimized bytes mismatch')
    for obj in [scalar,opt]:
        if obj.function('vp_memset') != expected_bytes('vp_memset'):
            raise RuntimeError('size harness memset bytes mismatch')
    # Keep the native tool's complete listing for independent inspection.
    disassembly=command('xcrun','llvm-objdump','--macho','--disassemble',str(ROOT/'build/benchmark'))
    (ROOT/'build/benchmark.disassembly.txt').write_text(disassembly+'\n')
    symbols=command('xcrun','llvm-objdump','--macho','--syms',str(ROOT/'build/benchmark'))
    if '*UND* _memcpy' not in symbols or '*UND* _memset' not in symbols or '\tblr\t' not in disassembly:
        raise RuntimeError('cannot establish indirect calls to external libc')
    report=dict(timestamp=datetime.now(timezone.utc).isoformat(),
        environment=dict(platform=platform.platform(),machine=platform.machine(),
          cpu=command('/usr/sbin/sysctl','-n','machdep.cpu.brand_string'),
          compiler=command('xcrun','clang','--version'),sdk=command('xcrun','--show-sdk-version')),
        method_sha256=hashlib.sha256((ROOT/'benchmarks/method.md').read_bytes()).hexdigest(),
        executable_sha256=hashlib.sha256((ROOT/'build/benchmark').read_bytes()).hexdigest(),
        samples_per_variant=SAMPLES,sizes=sizes(),cases=[])
    rng=random.Random(0x19273645)
    for kind in ['copy','fill']:
        alignments=[(0,0),(1,0),(0,1),(1,1)] if kind=='copy' else [(0,0),(0,1)]
        for n in LENGTHS:
            for sa,da in alignments:
                iterations=20000
                while invoke(kind,'scalar',n,sa,da,iterations)['elapsed_ns']<8000000:
                    iterations*=2
                    if iterations>200000000: raise RuntimeError('calibration failed')
                variants=['scalar','optimized','libc'] if kind=='copy' else ['scalar','libc']
                samples={v:[] for v in variants}
                for sample in range(SAMPLES):
                    order=variants.copy();rng.shuffle(order)
                    for v in order:
                        raw=invoke(kind,v,n,sa,da,iterations)
                        raw['sample']=sample
                        samples[v].append(raw)
                summaries={v:summary([r['elapsed_ns']/iterations for r in samples[v]]) for v in variants}
                if len({r['checksum'] for rows in samples.values() for r in rows})!=1:
                    raise RuntimeError('benchmark outputs disagree')
                report['cases'].append(dict(kind=kind,n=n,src_offset=sa,dst_offset=da,
                    iterations=iterations,samples=samples,ns_per_call=summaries,
                    optimized_vs_scalar=compare(summaries['optimized'],summaries['scalar']) if kind=='copy' else None,
                    selected_vs_libc=compare(summaries['optimized' if kind=='copy' else 'scalar'],summaries['libc'])))
            print(f'measured {kind} n={n}',flush=True)
    (ROOT/'reports/measurements.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    lines=['# 速度・容量の実測','',f'実測日時（UTC）: {report["timestamp"]}',
        '',f'機器: {report["environment"]["cpu"]} / {report["environment"]["platform"]}',
        '', '[測定方法](../benchmarks/method.md) · [全ケース・生データ](measurements.json)',
        '', '単位はns/呼び出し。中央値［最小–最大］。独立したプロセスで各7回。',
        '', '| 操作・長さ・ずれ(src,dst) | 基本版 | 最適化版 | libc | 基本版比 | libc比 |',
        '| --- | ---: | ---: | ---: | --- | --- |']
    def fmt(d): return f'{d["median"]:.2f} [{d["minimum"]:.2f}–{d["maximum"]:.2f}]'
    for case in report['cases']:
        s=case['ns_per_call'];key=f'{case["kind"]} {case["n"]} ({case["src_offset"]},{case["dst_offset"]})'
        lines.append(f'| {key} | {fmt(s["scalar"])} | '+
            (fmt(s['optimized']) if 'optimized' in s else '—')+
            f' | {fmt(s["libc"])} | {case["optimized_vs_scalar"] or "—"} | {case["selected_vs_libc"]} |')
    lines += ['', '## 容量','', '| 関数 | 本体 | text内余白 | オブジェクト全体 |',
        '| --- | ---: | ---: | ---: |']
    for r in report['sizes']['functions']:
        lines.append(f'| {r["name"]} | {r["body_bytes"]} | {r["text_padding_bytes"]} | {r["object_bytes"]} |')
    lines += ['',f'選択した2関数の本体合計: {report["sizes"]["selected_body_bytes"]}バイト。',
        f'同じハーネスの実行ファイル全体: 基本版{report["sizes"]["scalar_executable_bytes"]}バイト、最適化版{report["sizes"]["optimized_executable_bytes"]}バイト。',
        '', '実行ファイルにはOS向けヘッダー・コード署名・Cの起動処理等も含む。',
        '証明データは実行ファイルへリンクしていない。関数本体にスタック・ヒープ操作や外部呼び出しはない。']
    (ROOT/'reports/measurements.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__': main()
