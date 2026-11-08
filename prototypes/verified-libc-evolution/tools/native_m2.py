"""Finite M2 runtime observations; not a substitute for the overlap proof."""
import json
import re
import subprocess
from config import ROOT,BUILD,digest,environment
from build import run,check_span,words
from build_m2 import prepare
from verify_regions import require_m1


def memmove():
    require_m1();prepare()
    sources=[ROOT/'generator/main.ml',ROOT/'generator/m2.ml',ROOT/'include/vp2_memory.h',
             ROOT/'include/vp2_evolution.h',ROOT/'tests/memmove.c',ROOT/'tests/abi.S',
             ROOT/'tools/native_m2.py',ROOT/'tools/build_m2.py',BUILD/'vp2_memmove.o']
    before={str(p):digest(p) for p in sources}
    run(['xcrun','clang','-arch','arm64','-c',ROOT/'tests/abi.S','-o',BUILD/'abi_m2.o'])
    run(['xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror','-fno-builtin','-fno-lto',
         '-I',ROOT/'include',ROOT/'tests/memmove.c',BUILD/'vp2_memmove.o',BUILD/'abi_m2.o',
         '-o',BUILD/'test_memmove'])
    output=subprocess.check_output([str(BUILD/'test_memmove')],env=environment(),cwd=ROOT,text=True)
    matched=re.search(r'native memmove: (\d+) checks passed',output)
    if matched is None or int(matched[1])<35000:raise RuntimeError('overlap/ABI test coverage missing')
    check_span(BUILD/'test_memmove','vp2_memmove',words(BUILD/'vp2_memmove.words'),object_only=False)
    if {str(p):digest(p) for p in sources}!=before:raise RuntimeError('M2 native inputs changed during verification')
    report=dict(status='finite native observations; formal overlap/termination/access proofs still required',
        checks=int(matched[1]),output=output.strip(),body_bytes=len(words(BUILD/'vp2_memmove.words')),
        executable_sha256=digest(BUILD/'test_memmove'),
        inputs=before|{str(BUILD/'test_memmove'):digest(BUILD/'test_memmove')})
    folder=ROOT/'reports/m2';folder.mkdir(exist_ok=True)
    (folder/'memmove-native.json').write_text(json.dumps(report,indent=2)+'\n')
    print(output.strip(),flush=True)
    return report


if __name__=='__main__': memmove()
