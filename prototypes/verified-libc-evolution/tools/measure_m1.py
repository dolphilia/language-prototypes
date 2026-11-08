"""Predeclared fresh-harness matrix; requires matching fresh kernel evidence."""
from datetime import datetime,timezone
import json
import platform
import random
import secrets
import statistics
import subprocess
from config import ROOT,BASE,BUILD,digest,environment
from build import check_span,MachO,words,M1_NAMES

LENGTHS=[0,1,2,4,7,8,9,15,16,17,31,32,33,63,64,255,256,1024,4096,32768,1048576]
ALIGNMENTS=[(0,0),(1,0),(0,1),(1,1),(7,7)]
VARIANTS=['scalar','exact8','chunk8','libc']


def command(args):
    return subprocess.check_output(list(map(str,args)),cwd=ROOT,env=environment(),text=True).strip()


def cpu_information():
    args=['/usr/sbin/sysctl','-n','machdep.cpu.brand_string']
    result=subprocess.run(args,cwd=ROOT,env=environment(),text=True,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return dict(name=result.stdout.strip() if result.returncode==0 else None,
                architecture=platform.machine(),query=args,returncode=result.returncode,
                diagnostic=result.stderr.strip(),
                limitation='CPU name unavailable when the host denies sysctl; no name is inferred')


def build():
    common=['xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror','-fno-builtin','-fno-lto','-Iinclude']
    objects={'scalar':(BASE/'build/vp_memcpy_scalar.o','vp_memcpy_scalar'),
             'exact8':(BASE/'build/vp_memcpy.o','vp_memcpy'),
             'chunk8':(BUILD/'vp2_memcpy_chunk8.o','vp2_memcpy_chunk8')}
    command([*common,'benchmarks/memory.c',*[p for p,n in objects.values()],BUILD/'vp2_memset.o','-o',BUILD/'benchmark'])
    for p,name in objects.values():
        expected=MachO(p).function(name,object_only=True)
        check_span(BUILD/'benchmark',name,expected,object_only=False)
    sizes=[]
    for variant,(obj,name) in objects.items():
        directory=BUILD/'sizes'/variant;directory.mkdir(parents=True,exist_ok=True)
        target=directory/'size'
        command([*common,'-DVP_COPY='+name,'benchmarks/size.c',obj,BUILD/'vp2_memset.o','-o',target])
        parsed=MachO(obj);section=parsed.sections[parsed.symbol('_'+name).section-1]
        body=parsed.function(name,object_only=True)
        check_span(target,name,body,object_only=False)
        check_span(target,'vp2_memset',words(BUILD/'vp2_memset.words'),object_only=False)
        sizes.append(dict(variant=variant,copy_body_bytes=len(body),fill_body_bytes=28,
            copy_text_padding=section.size-len(body),copy_object_bytes=obj.stat().st_size,
            fill_object_bytes=(BUILD/'vp2_memset.o').stat().st_size,
            executable_bytes=target.stat().st_size,executable_basename=target.name))
    disassembly=command(['xcrun','llvm-objdump','--macho','--disassemble',BUILD/'benchmark'])
    symbols=command(['xcrun','llvm-objdump','--macho','--syms',BUILD/'benchmark'])
    (BUILD/'benchmark.disassembly.txt').write_text(disassembly+'\n')
    (BUILD/'benchmark.symbols.txt').write_text(symbols+'\n')
    if '*UND* _memcpy' not in symbols or '\tblr\t' not in disassembly:
        raise RuntimeError('cannot establish external libc and indirect calls')
    return sizes


def summary(values):
    q=statistics.quantiles(values,n=4,method='inclusive')
    return dict(median=statistics.median(values),minimum=min(values),maximum=max(values),q1=q[0],q3=q[2])


def compare(a,b):
    if a['median']<.95*b['median'] and a['q3']<b['q1']: return '高速'
    if b['median']<.95*a['median'] and b['q3']<a['q1']: return '低速'
    return '不明'


def invoke(variant,n,sa,da,iterations):
    result=json.loads(command([BUILD/'benchmark',variant,n,sa,da,iterations]))
    if result['iterations']!=iterations or result['arena_bytes']>128*1024*1024:
        raise RuntimeError('benchmark violated its declared bounds')
    return result


def validate_proof(path):
    receipt=json.loads(path.read_text())
    required={'chunk8:public','chunk8:access','fill:public','fill:access','chunk8:zero-no-data'}
    if not required<=set(receipt['checks']): raise RuntimeError('required kernel proofs missing')
    for p,expected in receipt['inputs'].items():
        if digest(p)!=expected: raise RuntimeError('proof input no longer matches: '+p)
    return receipt


def measure(proof=BUILD/'proof-m1-verify.json'):
    gate=BUILD/'measurement-m1.json';gate.unlink(missing_ok=True)
    receipt=validate_proof(proof)
    from audit_m1 import validate_costs
    try:
        validate_costs(json.loads((ROOT/'reports/m1/proof-costs.json').read_text()))
    except (OSError,RuntimeError,ValueError):
        from verify_costs import verify as costs
        costs()
    sizes=build()
    # Re-run finite positive gates on exactly the proved and linked objects.
    from native import verify as native
    native_result=native()
    from artifacts import verify as artifacts
    artifact_result=artifacts()
    method_inputs={str(p):digest(p) for p in
        [ROOT/'benchmarks/memory.c',ROOT/'tools/measure_m1.py',ROOT/'reports/evaluation-protocol.md',BUILD/'benchmark']}
    report=dict(timestamp=datetime.now(timezone.utc).isoformat(),measurement_nonce=secrets.token_hex(24),proof_receipt=str(proof),
        proof_nonce=receipt['nonce'],benchmark_sha256=digest(BUILD/'benchmark'),
        proof_receipt_snapshot=receipt,
        method_sha256=digest(ROOT/'reports/evaluation-protocol.md'),
        method=dict(seed='0x19273645',samples=7,scalar_target_ns=8000000,
                    large_start_iterations=1,arena_limit_bytes=128*1024*1024,
                    warmup_limit_calls=4096,warmup_limit_bytes=4194304,
                    working_set='one slot below 32768 bytes; two 64 MiB arenas at/above 32768',
                    limitations='finite observations; no cold-cache guarantee or statistical confidence interval'),
        environment=dict(platform=platform.platform(),cpu=cpu_information(),
            compiler=command(['xcrun','clang','--version']),sdk=command(['xcrun','--show-sdk-version'])),
        native=native_result,artifacts=artifact_result,method_inputs=method_inputs,sizes=sizes,
        comparison_objects=[],cases=[])
    names=set(M1_NAMES)|{'vp2_copy16_direct','vp2_copy32_direct'}
    names.update(p.stem for p in BUILD.glob('vp2_edit_*.o'))
    for path in [BUILD/(name+'.o') for name in sorted(names)]:
        parsed=MachO(path);name=path.stem
        section=parsed.sections[parsed.symbol('_'+name).section-1]
        body=parsed.function(name,object_only=True)
        report['comparison_objects'].append(dict(name=name,body_bytes=len(body),
            text_padding_bytes=section.size-len(body),object_bytes=path.stat().st_size,
            selected=name in {'vp2_memcpy_chunk8','vp2_memset'},
            experimental_or_block=name not in {'vp2_memcpy_chunk8','vp2_memset'}))
    rng=random.Random(0x19273645)
    for n in LENGTHS:
        for sa,da in ALIGNMENTS:
            iterations=1 if n>=4096 else 1024;calibration=[]
            while True:
                raw=invoke('scalar',n,sa,da,iterations);calibration.append(raw)
                if raw['elapsed_ns']>=8000000: break
                iterations*=2
                if iterations>2**32: raise RuntimeError('calibration did not converge')
            samples={v:[] for v in VARIANTS};orders=[]
            for sample in range(7):
                order=VARIANTS.copy();rng.shuffle(order);orders.append(order)
                for variant in order:
                    samples[variant].append(invoke(variant,n,sa,da,iterations)|{'sample':sample})
            if len({r['checksum'] for rows in samples.values() for r in rows})!=1:
                raise RuntimeError('benchmark checksums disagree')
            summaries={v:summary([r['elapsed_ns']/iterations for r in rows]) for v,rows in samples.items()}
            report['cases'].append(dict(n=n,src_offset=sa,dst_offset=da,iterations=iterations,
                calibration=calibration,orders=orders,samples=samples,ns_per_call=summaries,
                chunk8_vs_scalar=compare(summaries['chunk8'],summaries['scalar']),
                chunk8_vs_exact8=compare(summaries['chunk8'],summaries['exact8']),
                chunk8_vs_libc=compare(summaries['chunk8'],summaries['libc'])))
        print(f'measured M1 n={n}',flush=True)
    validate_proof(proof)
    if any(digest(p)!=expected for p,expected in method_inputs.items()):
        raise RuntimeError('measurement inputs changed during the matrix')
    report['hypothesis_aligned']={str(c['n']):c['chunk8_vs_scalar'] for c in report['cases']
        if c['n'] in [64,256,4096] and c['src_offset']==c['dst_offset']==0}
    folder=ROOT/'reports/m1'
    (folder/'measurements.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    lines=['# M1の速度と容量','',f'実測UTC: {report["timestamp"]}',
        '', '[全生データ](measurements.json) · [事前の方法](../evaluation-protocol.md)',
        '', 'CPU名の取得結果・アーキテクチャ・取得コマンドの成否も生データへ保存する。環境の制限で取得できないCPU名は推定しない。',
        '', '各実装を別プロセスで7回。単位ns/呼び出し、中央値。四分位・最小最大・PID・順序・較正を生データへ保存。',
        '', '| 長さ・ずれ(src,dst) | 基本版 | 長さ8版 | 新版 | libc | 基本版比 | libc比 |',
        '| --- | ---: | ---: | ---: | ---: | --- | --- |']
    for c in report['cases']:
        s=c['ns_per_call'];values=' | '.join(f'{s[v]["median"]:.2f}' for v in VARIANTS)
        lines.append(f'| {c["n"]} ({c["src_offset"]},{c["dst_offset"]}) | {values} | {c["chunk8_vs_scalar"]} | {c["chunk8_vs_libc"]} |')
    lines+=['','選択した2関数の本体は104バイト。コピー76、埋め込み28。スタック・ヒープ・実行時の証明処理を含まない。',
        '', '128MiBの作業領域やウォームアップはキャッシュ状態の保証ではない。呼び出し・添字の計算も同じハーネスの測定に含まれる。性能仮説の判定と証明の完了を区別する。',
        '', '容量の内訳と、同じbasenameの実行ファイルの比較は生データの`sizes`へ保存した。OS向けヘッダー・起動コード・署名も実行ファイルの容量に含む。']
    (folder/'measurements.md').write_text('\n'.join(lines)+'\n')
    gate.write_text(json.dumps({'nonce':report['measurement_nonce'],
        'report_sha256':digest(folder/'measurements.json')},indent=2)+'\n')
    from audit_m1 import audit
    audit()
    return report


if __name__=='__main__': measure()
