"""Native bounds, ABI and full-buffer differential tests; not a proof."""
import json
import subprocess
from config import ROOT, BASE, BUILD, environment
from build import check_span,words


def run(args,*,capture=False):
    return subprocess.run(list(map(str,args)),cwd=ROOT,env=environment(),check=True,
        text=True,stdout=subprocess.PIPE if capture else None)


def verify():
    common=['xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror',
            '-fno-builtin','-fno-lto','-Iinclude']
    run([*common,'-c','tests/abi.S','-o',BUILD/'abi.o'])
    objects=[BASE/'build/vp_memcpy_scalar.o',BASE/'build/vp_memcpy.o',
             BUILD/'vp2_memcpy_chunk8.o',BUILD/'vp2_memset.o']
    run([*common,'tests/memory.c',BUILD/'abi.o',*objects,'-o',BUILD/'test_memory'])
    for name in ['vp2_memcpy_chunk8','vp2_memset']:
        check_span(BUILD/'test_memory',name,words(BUILD/(name+'.words')),object_only=False)
    normal=run([BUILD/'test_memory'],capture=True).stdout.strip()
    print(normal,flush=True)
    run([*common,'tests/short_fast.c',BUILD/'ve_mut_short_fast.o','-o',BUILD/'test_short_fast'])
    negative=run([BUILD/'test_short_fast'],capture=True).stdout.strip()
    print(negative,flush=True)
    result={'native':normal,'sentinel_mutation':negative,'seed':'0x19273645',
            'functions':['baseline scalar','baseline exact-8','chunk8','fill'],
            'alignment_pairs':'0..15 × 0..15 (all 64 modulo-8 pairs)',
            'lengths':'baseline plus b+r, b=0,8,16,32,64,256,4096; r=0..7; page±1',
            'evidence_kind':'finite_native_tests'}
    (BUILD/'native.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__': verify()
