"""Exact spans plus an independent LLVM symbol-position cross-check."""
import json
import re
import subprocess
from config import ROOT,BUILD,digest,environment
from build import check_span,words,MachO


def verify(executables=('test_memory','benchmark')):
    records=[]
    for name in ['vp2_memcpy_chunk8','vp2_memset']:
        expected=words(BUILD/(name+'.words'))
        paths=[BUILD/(name+'.o'),*[BUILD/p for p in executables]]
        for path in paths:
            obj=path.suffix=='.o'
            actual=check_span(path,name,expected,object_only=obj)
            parsed=MachO(path)
            listing=subprocess.check_output(['xcrun','llvm-objdump','--macho','--syms',str(path)],
                cwd=ROOT,env=environment(),text=True)
            for suffix in ['', '_end']:
                symbol='_'+name+suffix
                positions=re.findall(r'^([0-9a-f]+)\s+.*?\s'+re.escape(symbol)+r'$',listing,re.M)
                if len(positions)!=1 or int(positions[0],16)!=parsed.symbol(symbol).address:
                    raise RuntimeError('LLVM and extraction disagree: '+symbol)
            (BUILD/(path.name+'.symbols.txt')).write_text(listing)
            records.append(dict(path=str(path),function=name,bytes=len(actual),sha256=digest(path),
                                symbol_position=parsed.symbol('_'+name).address))
    if sum(len(words(BUILD/(n+'.words'))) for n in ['vp2_memcpy_chunk8','vp2_memset'])>256:
        raise RuntimeError('selected function bodies exceed 256 bytes')
    (BUILD/'linked-artifacts.json').write_text(json.dumps(records,indent=2)+'\n')
    return records


if __name__=='__main__': verify()
