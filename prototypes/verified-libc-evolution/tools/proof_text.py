"""Attach CPU timing to generated single-line proof declarations."""
import re


def timed_declarations(lines):
    result=[]
    for line in lines:
        match=re.match(r'let ([A-Z0-9_]+) = prove\(',line)
        if match:
            name=match[1]
            line=line.replace(' = prove(',f' = ve_timed "{name}" (fun () -> prove(',1)
            if not line.endswith(';;'): raise ValueError('expected a single-line declaration')
            line=line[:-2]+');;'
        result.append(line)
    return '\n'.join(result)+'\n'
