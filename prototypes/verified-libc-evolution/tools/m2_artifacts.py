"""M2 leaf spans with independent LLVM symbol-position comparisons."""
import re
import subprocess
from config import ROOT,BUILD,digest,environment
from build import MachO,words,check_span


def leaf(name,executables):
    expected=words(BUILD/(name+'.words'));records=[]
    for path in [BUILD/(name+'.o'),*[BUILD/n for n in executables]]:
        check_span(path,name,expected,object_only=path.suffix=='.o')
        parsed=MachO(path)
        listing=subprocess.check_output(['xcrun','llvm-objdump','--macho','--syms',str(path)],
            cwd=ROOT,env=environment(),text=True)
        for suffix in ['', '_end']:
            symbol='_'+name+suffix
            rows=re.findall(r'^([0-9a-f]+)\s+.*?\s'+re.escape(symbol)+r'$',listing,re.M)
            if len(rows)!=1 or int(rows[0],16)!=parsed.symbol(symbol).address:
                raise RuntimeError('LLVM and function extraction disagree: '+symbol)
        records.append(dict(path=str(path),sha256=digest(path),function=name,
            start=parsed.symbol('_'+name).address,body_bytes=len(expected)))
    return records
