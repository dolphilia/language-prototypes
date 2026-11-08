"""One frozen exploration, then fresh selected proofs and separately saved confirmations."""
from datetime import datetime, timezone
import hashlib
import json
import platform
import random
import re
import secrets
import shutil
import statistics
import subprocess
import sys
import time
from config import ROOT, BASE, BUILD, digest, environment
from build import MachO, check_span
from audit_m1 import validate_inputs
from verify_search import require_pool, require_resources, verify, REPORT, FROZEN

LENGTHS=[0,1,2,4,7,8,9,15,16,17,31,32,33,63,64,255,256,1024,4096,32768,1048576]
ALIGNMENTS=[(0,0),(1,0),(0,1),(1,1),(7,7)]
VARIANTS=['scalar','original','candidate','libc']
EXPLORE_SEED=0x19273645
CONFIRM_SEED=0xc0ffee11


def command(args):
    return subprocess.check_output(list(map(str,args)),cwd=ROOT,env=environment(),text=True).strip()


def summary(values):
    q=statistics.quantiles(values,n=4,method='inclusive')
    return dict(median=statistics.median(values),minimum=min(values),maximum=max(values),q1=q[0],q3=q[2])


def compare(a,b):
    if a['median']<.95*b['median'] and a['q3']<b['q1']:return '高速'
    if b['median']<.95*a['median'] and b['q3']<a['q1']:return '低速'
    return '不明'


def method_inputs():
    return {str(p):digest(p) for p in [ROOT/'tools/measure_search.py',ROOT/'benchmarks/search.c',
         ROOT/'benchmarks/search_size.c',ROOT/'reports/m3/search-measurement-protocol.md',
         ROOT/'reports/m3/search-protocol.md',FROZEN,ROOT/'tools/build.py',BASE/'tools/macho.py']}


def build(name,nonce,seed):
    directory=BUILD/'search-bench'/nonce/name;directory.mkdir(parents=True,exist_ok=True)
    target=directory/'bench'
    original=name if name=='ve_opt_u1_mov' else 'vp2_memcpy_chunk8'
    common=['xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-Werror',
            '-fno-builtin','-fno-lto','-Iinclude','-DVE_CANDIDATE='+name]
    objects=[BASE/'build/vp_memcpy_scalar.o',BASE/'build/vp_memcpy.o',BUILD/'vp2_memset.o',BUILD/(name+'.o')]
    if original!=name:objects.append(BUILD/'vp2_memcpy_chunk8.o')
    command([*common,'-DVE_ORIGINAL='+original,'-DVE_DATA_SEED='+str(seed),
             ROOT/'benchmarks/search.c',*objects,'-o',target])
    body=MachO(BUILD/(name+'.o')).function(name)
    check_span(target,name,body,object_only=False)
    check_span(target,original,MachO(BUILD/'vp2_memcpy_chunk8.o').function('vp2_memcpy_chunk8'),object_only=False)
    check_span(target,'vp_memcpy_scalar',MachO(BASE/'build/vp_memcpy_scalar.o').function('vp_memcpy_scalar'),object_only=False)
    disassembly=command(['xcrun','llvm-objdump','--macho','--disassemble',target])
    symbols=command(['xcrun','llvm-objdump','--macho','--syms',target])
    if '*UND* _memcpy' not in symbols or '\tblr\t' not in disassembly:
        raise RuntimeError('external libc and indirect benchmark calls were not established')
    (directory/'disassembly.txt').write_text(disassembly+'\n')
    (directory/'symbols.txt').write_text(symbols+'\n')
    size=directory/'size'
    command([*common,ROOT/'benchmarks/search_size.c',BUILD/(name+'.o'),BUILD/'vp2_memset.o','-o',size])
    check_span(size,name,body,object_only=False)
    check_span(size,'vp2_memset',MachO(BUILD/'vp2_memset.o').function('vp2_memset'),object_only=False)
    positions=[]
    for file,listing,names in [(target,symbols,[name,original,'vp_memcpy_scalar','vp2_memset']),
            (size,command(['xcrun','llvm-objdump','--macho','--syms',size]),[name,'vp2_memset'])]:
        parsed_file=MachO(file)
        for function in sorted(set(names)):
            for suffix in ['', '_end']:
                symbol='_'+function+suffix
                found=re.findall(r'^([0-9a-f]+)\s+.*?\s'+re.escape(symbol)+r'$',listing,re.M)
                if len(found)!=1 or int(found[0],16)!=parsed_file.symbol(symbol).address:
                    raise RuntimeError('LLVM and measured function extraction disagree: '+symbol)
                positions.append(dict(path=str(file),symbol=symbol,address=int(found[0],16)))
    parsed=MachO(BUILD/(name+'.o'));section=parsed.sections[parsed.symbol('_'+name).section-1]
    return target,dict(name=name,copy_body_bytes=len(body),fill_body_bytes=28,
        combined_body_bytes=len(body)+28,copy_text_padding_bytes=section.size-len(body),
        copy_object_bytes=(BUILD/(name+'.o')).stat().st_size,
        executable_bytes=size.stat().st_size,executable_basename=size.name,
        body_sha256=hashlib.sha256(body).hexdigest(),object_sha256=digest(BUILD/(name+'.o')),
        benchmark=str(target),benchmark_sha256=digest(target),size_executable=str(size),size_sha256=digest(size),
        llvm_positions=positions,original_symbol=original,original_and_candidate_share_body=original==name)


def invoke(target,variant,n,sa,da,iterations):
    r=json.loads(command([target,variant,n,sa,da,iterations]))
    if r['iterations']!=iterations or not 0<r['elapsed_ns'] or r['arena_bytes']>128*1024*1024:
        # Very short calibration calls can round to zero; only their elapsed
        # value is allowed to be zero by the caller below.
        if r['iterations']!=iterations or r['elapsed_ns']<0 or r['arena_bytes']>128*1024*1024:
            raise RuntimeError('benchmark violated its bounds')
    return r


def trial(names,phase,seed):
    pool=require_pool();require_resources()
    nonce=secrets.token_hex(16);started=time.monotonic();inputs=method_inputs()
    cpu=subprocess.run(['/usr/sbin/sysctl','-n','machdep.cpu.brand_string'],cwd=ROOT,env=environment(),
                       text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    memory=subprocess.run(['/usr/bin/vm_stat'],cwd=ROOT,env=environment(),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    result=dict(phase=phase,nonce=nonce,timestamp=datetime.now(timezone.utc).isoformat(),
        method_inputs=inputs,seed=hex(seed),samples=7,proof_snapshot=pool['proof'],
        frozen_sha256=digest(FROZEN),environment=dict(platform=platform.platform(),architecture=platform.machine(),python=platform.python_version(),python_executable=sys.executable,
            cpu_name=cpu.stdout.strip() if cpu.returncode==0 else None,cpu_query_returncode=cpu.returncode,
            cpu_query_diagnostic=cpu.stderr.strip(),memory_query=dict(command=['/usr/bin/vm_stat'],returncode=memory.returncode,stdout=memory.stdout,stderr=memory.stderr),compiler=command(['xcrun','clang','--version']),
            sdk=command(['xcrun','--show-sdk-version'])),
        method=dict(scalar_target_ns=8000000,arena_limit_bytes=128*1024*1024,
            warmup_limit_calls=4096,warmup_limit_bytes=4194304,
            limitations='finite observations; no cold-cache guarantee, confidence interval, or global optimum'),
        candidates=[])
    rng=random.Random(seed);names=list(names);rng.shuffle(names)
    for name in names:
        target,sizes=build(name,nonce,seed);cases=[]
        matrix=[(n,sa,da) for n in LENGTHS for sa,da in ALIGNMENTS];rng.shuffle(matrix)
        for n,sa,da in matrix:
            iterations=1 if n>=4096 else 1024;calibration=[]
            while True:
                r=invoke(target,'scalar',n,sa,da,iterations);calibration.append(r)
                if r['elapsed_ns']>=8000000:break
                iterations*=2
                if iterations>2**30:raise RuntimeError('calibration budget exhausted')
            samples={v:[] for v in VARIANTS};order=[]
            for sample in range(7):
                variants=list(VARIANTS);rng.shuffle(variants);order.append(variants)
                for variant in variants:
                    r=invoke(target,variant,n,sa,da,iterations)
                    if r['elapsed_ns']<=0:raise RuntimeError('zero duration timed sample')
                    samples[variant].append(r|{'sample':sample})
            values={v:summary([r['elapsed_ns']/r['iterations'] for r in rs]) for v,rs in samples.items()}
            if any(len({r['pid'] for r in rs})!=7 for rs in samples.values()):
                raise RuntimeError('seven fresh processes per variant are required')
            cases.append(dict(n=n,sa=sa,da=da,iterations=iterations,calibration=calibration,
                order=order,samples=samples,ns_per_call=values,
                candidate_vs={v:compare(values['candidate'],values[v]) for v in ['scalar','original','libc']}))
        result['candidates'].append(dict(name=name,sizes=sizes,cases=cases))
        print(f'{phase}: {name}, 105 cases x 4 variants x 7 fresh processes',flush=True)
    validate_inputs(inputs);require_pool();require_resources()
    result['elapsed_seconds']=time.monotonic()-started
    result['complete']=True
    return result


def scores(exploration):
    answer={}
    for r in exploration['candidates']:
        ratios=[]
        for n in [64,256,4096]:
            c=next(c for c in r['cases'] if (c['n'],c['sa'],c['da'])==(n,0,0))
            ratios.append(c['ns_per_call']['candidate']['median']/c['ns_per_call']['scalar']['median'])
        answer[r['name']]=dict(score=statistics.mean(ratios),ratios=ratios,bytes=r['sizes']['copy_body_bytes'])
    best=min(r['score'] for r in answer.values())
    eligible=[n for n,r in answer.items() if r['score']<=best*1.05]
    selected=min(eligible,key=lambda n:(answer[n]['bytes'],answer[n]['score'],n))
    return answer,eligible,selected


def validate_trial(r):
    if not r['complete'] or r['samples']!=7:raise RuntimeError('incomplete measurement trial')
    validate_inputs(r['method_inputs']);validate_inputs(r['proof_snapshot']['inputs'])
    for candidate in r['candidates']:
        if {(c['n'],c['sa'],c['da']) for c in candidate['cases']}!={(n,sa,da) for n in LENGTHS for sa,da in ALIGNMENTS} or len(candidate['cases'])!=105:
            raise RuntimeError('measurement coverage differs')
        for c in candidate['cases']:
            for v in VARIANTS:
                rs=c['samples'][v]
                if len(rs)!=7 or len({s['pid'] for s in rs})!=7 or any(s['elapsed_ns']<=0 or s['iterations']!=c['iterations'] or s['arena_bytes']>128*1024*1024 for s in rs):
                    raise RuntimeError('measurement process coverage differs')
                if c['ns_per_call'][v]!=summary([s['elapsed_ns']/s['iterations'] for s in rs]):
                    raise RuntimeError('saved statistics differ from raw observations')
            if c['candidate_vs']!={v:compare(c['ns_per_call']['candidate'],c['ns_per_call'][v]) for v in ['scalar','original','libc']}:
                raise RuntimeError('saved performance classification differs')
    return r


def selection():
    pool=require_pool();path=REPORT/'selection.json';explore_path=REPORT/'exploration.json'
    if not explore_path.exists():
        exploration=trial(pool['proved'],'exploration',EXPLORE_SEED)
        exploration['generation_snapshot']=json.loads((BUILD/'search-preparation.json').read_text())
        explore_path.write_text(json.dumps(exploration,ensure_ascii=False,indent=2)+'\n')
    exploration=validate_trial(json.loads(explore_path.read_text()))
    values,eligible,chosen=scores(exploration)
    frozen=json.loads(FROZEN.read_text());row=next(r for r in frozen['candidates'] if r['name']==chosen)
    record=dict(selected=chosen,scores=values,eligible_within_5_percent=eligible,
        frozen_sha256=digest(FROZEN),exploration_sha256=digest(explore_path),method_inputs=method_inputs(),
        object_sha256=row['object_sha256'],words=row['words'],
        rule='minimum mean median candidate/scalar ratio at aligned 64/256/4096; within 5% prefer smaller body, then lower score',
        frozen_before_confirmation=True,confirmation_does_not_reselect=True)
    if path.exists():
        if json.loads(path.read_text())!=record:raise RuntimeError('frozen selection no longer agrees with the original exploration')
    else:path.write_text(json.dumps(record,indent=2)+'\n')
    if chosen not in pool['proved']:raise RuntimeError('selected body is no longer proved')
    print('frozen selection: '+chosen,flush=True)
    return record


def measure():
    REPORT.mkdir(exist_ok=True);(BUILD/'measurement-search.json').unlink(missing_ok=True)
    chosen=selection();name=chosen['selected']
    proof=verify(name)
    confirmation=trial([name],'confirmation',CONFIRM_SEED)
    confirmation['selected_proof_snapshot']=proof['proof']
    confirmation['selection_sha256']=digest(REPORT/'selection.json')
    confirmation['pool_proof_seconds']=require_pool()['proof']['elapsed_seconds']
    confirmation['selected_proof_seconds']=proof['proof']['elapsed_seconds']
    archive=REPORT/'confirmations';archive.mkdir(exist_ok=True)
    text=json.dumps(confirmation,ensure_ascii=False,indent=2)+'\n'
    (archive/(confirmation['nonce']+'.json')).write_text(text)
    (REPORT/'confirmation.json').write_text(text)
    (BUILD/'measurement-search.json').write_text(text)
    output=BUILD/'selected';output.mkdir(exist_ok=True)
    shutil.copyfile(BUILD/(name+'.o'),output/(name+'.o'))
    (output/'ve_selected.h').write_text('#include <stddef.h>\n#ifdef __cplusplus\nextern "C" {\n#endif\nvoid *'+name+'(void *, const void *, size_t);\n#ifdef __cplusplus\n}\n#endif\n#define VE_SELECTED_COPY '+name+'\n')
    print('selected body independently rechecked and remeasured; run audit_search.py',flush=True)
    return confirmation


if __name__=='__main__':measure()
