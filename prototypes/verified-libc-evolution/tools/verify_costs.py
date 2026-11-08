"""Three genuinely new proof processes for the controlled edit matrix."""
import json
import re
import statistics
import time
from config import ROOT,BUILD,digest
from blocks import prepare as blocks
from composition import prepare as composition
from edit_experiments import prepare as edits
from prover import run_session


def native_edits():
    from build import run,check_span,words
    cases=[];declarations=[]
    for width in [16,32]:
        for family in ['offset','scratch','frame']:
            for variant in ['','_direct']:
                name=f'vp2_edit_{family}{width}{variant}'
                declarations.append(f'extern void *{name}(void *,const void *,size_t);')
                cases.append((name,width,family))
    source='''#include <stddef.h>
#include <stdio.h>
#include <string.h>
typedef void *(*fn)(void *,const void *,size_t);
extern int vp2_check_live_x3(fn,void *,const void *,size_t);
'''+ '\n'.join(declarations)+'''
int main(void) {
 _Alignas(64) unsigned char src[128],dst[128];
 memset(src,0x55,sizeof src);
'''
    for name,width,family in cases:
        source+=f'memset(dst,0xaa,sizeof dst);if({name}(dst,src,{width})!=dst) return 1;\n'
        for i in range(128):
            wanted=0x55 if i<width and not(family=='offset' and 8<=i<16) else 0xaa
            source+=f'if(dst[{i}]!={wanted}) return 2;\n'
        expected_live=1 if family=='scratch' else 0
        source+=f'if(vp2_check_live_x3({name},dst,src,{width})!={expected_live}) return 3;\n'
    source+='puts("native edit matrix: 12 code objects, offset counterexamples and X3 preservation/corruption reproduced");return 0;}\n'
    (BUILD/'edit-native.c').write_text(source)
    objects=[BUILD/(n+'.o') for n,w,f in cases]
    run(['xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror',
         '-fno-builtin','-fno-lto',BUILD/'edit-native.c',ROOT/'tests/live_x3.S',*objects,
         '-o',BUILD/'test_edit_matrix'])
    for name,width,family in cases:
        primary=name.removesuffix('_direct')
        check_span(BUILD/'test_edit_matrix',name,words(BUILD/(primary+'.words')),object_only=False)
    run([BUILD/'test_edit_matrix'])


def verify(samples=3):
    started=time.monotonic()
    b,bc=blocks();p,pc=composition();edit,ec=edits()
    metadata=json.loads((BUILD/'edit-experiments.json').read_text())
    sources=[b,p,edit]
    inputs=[*sources,ROOT/'proofs/blocks.ml',ROOT/'proofs/composition.ml',ROOT/'proofs/edit_specs.ml',
            ROOT/'generator/main.ml',ROOT/'generator/edits.ml',ROOT/'tools/verify_costs.py',
            *BUILD.glob('vp2_block_*.o'),*BUILD.glob('vp2_copy*.o'),*BUILD.glob('vp2_edit_*.o')]
    native_edits()
    results=[]
    for sample in range(samples):
        body='\n'.join('ve_timed '+json.dumps('module:'+s.name)+' (fun () -> loadt '+json.dumps(str(s))+');;' for s in sources)
        receipt=run_session(f'cost-{sample+1}',body,bc+pc+ec,inputs=inputs)
        output=(BUILD/f'proof-cost-{sample+1}.log').read_text()
        rejected=[dict(name=n,cpu_seconds=float(t),reason=reason)
            for n,t,reason in re.findall(r'VE_EDIT_REJECT (\S+) ([0-9.]+) ("[^\n]*")',output)]
        if [r['name'] for r in rejected]!=metadata['expected_rejections']:
            raise RuntimeError('missing or reordered edit rejection evidence')
        results.append(receipt|{'rejections':rejected})
    report=dict(samples=samples,seconds=time.monotonic()-started,preparation=metadata,
        proof_runs=results,native='12 objects checked for full-buffer content and X3 preservation',
        limitations=['CPU time, not human cognitive effort','no disk-cache flush; loaded separately in each process',
                     'first operation is automated preparation/build/check, not manual authoring time',
                     'same child theorems reused; no claim of a general reduction in development cost'])
    folder=ROOT/'reports/m1';folder.mkdir(exist_ok=True)
    (folder/'proof-costs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    lines=['# 合成と直接証明の修正実験','', '[全実行・入力ハッシュ・生データ](proof-costs.json)',
        '', '基盤をロードし直した3個のプロセス。依存は固定し、ディスクキャッシュは消去していない。CPU時間と壁時計時間を分けた。',
        '', '| 初期版の親 | 合成CPU秒の中央値 | 直接CPU秒の中央値 |', '| --- | ---: | ---: |']
    for width in [16,32]:
        def values(name): return [t['cpu_seconds'] for r in results for t in r['timings'] if t['name']==name]
        a=values(f'VP2_COPY{width}_COMPOSED');d=values(f'VP2_COPY{width}_DIRECT')
        if len(a)!=samples or len(d)!=samples: raise RuntimeError('missing baseline proof timings')
        lines.append(f'| Copy{width} | {statistics.median(a):.6f} | {statistics.median(d):.6f} |')
    lines+=['', 'オフセットは2番目の部品だけ8から0へ変える不正な編集。両方式で証明を拒否し、実機で未コピーの8バイトを確認した。',
        '', '一時レジスタは最初の部品をX4からX3へ変える正しい編集。許容変更範囲もX3・X4とする。直接版・合成版を別々に証明した。',
        '', '変更範囲は、X3を保存する要件へ戻す実験。X3使用版のままでは両方式が拒否し、実機の呼び出し元でも破壊を確認した。最初の部品をX4へ戻して要件を満たす版を再検査した。公開カーネルの契約は変更していない。',
        '', '合成では既存の子の定理を選び直し、親はRETだけを実行する。直接版は全ロード・ストアを実行する。各編集の追加ヒントは0、追加の子の定理も0。生成パラメータ・直接アセンブリ・変更した箇所と全入力を生データへ保存した。',
        '', '初回の自動適用・ビルド時間を保存した。方式自体を作る手作業の時間は測っておらず、この規模のCPU時間から一般の開発者の負担が減るとは結論しない。']
    (folder/'proof-costs.md').write_text('\n'.join(lines)+'\n')
    return report


if __name__=='__main__': verify()
