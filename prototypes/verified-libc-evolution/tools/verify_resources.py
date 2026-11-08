"""Fresh kernel acceptance of exact steps/data amounts and real cost mutations."""
import json
import struct
from config import ROOT, BASE, BUILD, digest
from build import MachO
from prover import run_session
from resource_mutations import prepare as mutations
from verify_regions import require_m1


def prepare():
    objects=[('vp_memcpy_scalar',BASE/'build/vp_memcpy_scalar.o','vp_memcpy_scalar'),
             ('vp_memset',BASE/'build/vp_memset.o','vp_memset'),
             ('ve_resource_exact',BASE/'build/vp_memcpy.o','vp_memcpy'),
             ('vp2_memcpy_chunk8',BUILD/'vp2_memcpy_chunk8.o','vp2_memcpy_chunk8')]
    if MachO(objects[1][1]).function('vp_memset') != MachO(BUILD/'vp2_memset.o').function('vp2_memset'):
        raise RuntimeError('baseline and M1 fill bodies differ')
    lines=[]
    for name,path,symbol in objects:
        data=MachO(path).function(symbol)
        literal=';'.join(hex(w) for w in struct.unpack('<'+'I'*(len(data)//4),data))
        lines += [f'let {name}_mc=define_assert_from_elf "{name}_mc" '+json.dumps(str(path))+f' [{literal}];;',
                  f'let {name.upper()}_EXEC=ARM_MK_EXEC_RULE {name}_mc;;']
    for source in ['memory.ml','costs.ml','resource_tail.ml','resource_bulk.ml',
                   'resource_composition.ml','resource_chunk.ml','resource_exact8.ml']:
        lines.append('loadt '+json.dumps(str(ROOT/'proofs'/source))+';;')
    checks=['cost:trace-additive','cost:composition']
    lines += [r'''ve_check "cost:trace-additive"
 `!(a:uarch_event list) b.
   ve_read_bytes(APPEND a b) = ve_read_bytes a + ve_read_bytes b /\
   ve_write_bytes(APPEND a b) = ve_write_bytes a + ve_write_bytes b` VE_BYTE_COUNTS_APPEND;;''',
      r'''ve_check "cost:composition"
 `!step (P:S->bool) Q C R s a b.
   P s /\ (!t. Q t /\ C s t ==> eventually_n step b R t)
   ==> ensures_n step P Q C (\t. a)
   ==> eventually_n step (a+b) R s` VE_COUNTED_BIGSTEP;;''']
    cases=[
        ('scalar','ve_resource_contract `vp_memcpy_scalar_mc` `5*val(n:int64)+3` false',
         've_scalar_cost_tac VP_MEMCPY_SCALAR_EXEC false'),
        ('fill','ve_resource_contract `vp_memset_mc` `4*val(n:int64)+3` true',
         've_scalar_cost_tac VP_MEMSET_EXEC true'),
        ('tail','ve_tail_resource_spec `vp2_memcpy_chunk8_mc` 44',
         've_tail_resource_tac VP2_MEMCPY_CHUNK8_EXEC 44'),
        ('bulk','ve_bulk_resource_spec `vp2_memcpy_chunk8_mc` 1',
         've_bulk_resource_tac VP2_MEMCPY_CHUNK8_EXEC 1'),
        ('chunk','ve_resource_contract `vp2_memcpy_chunk8_mc` (ve_chunk_count 1) false',
         've_chunk_resource_tac vp2_memcpy_chunk8_mc VP2_MEMCPY_CHUNK8_EXEC 1 VE_COST_BULK VE_COST_TAIL'),
        ('exact8','ve_resource_contract `ve_resource_exact_mc` ve_exact_count false',
         've_exact_resource_tac ve_resource_exact_mc VE_RESOURCE_EXACT_EXEC vp_memcpy_scalar_mc VE_COST_SCALAR')]
    for label,spec,tactic in cases:
        lines += [f'let ve_cost_{label}_spec = {spec};;',
                  f'let VE_COST_{label.upper()}=ve_timed "cost:{label}" (fun () -> prove(ve_cost_{label}_spec,{tactic}));;',
                  f've_check "cost:{label}" ve_cost_{label}_spec VE_COST_{label.upper()};;']
        checks.append('cost:'+label)
    mutant,extra=mutations();checks+=extra
    lines.append('loadt '+json.dumps(str(mutant))+';;')
    path=BUILD/'resource-proofs.ml';path.write_text('\n'.join(lines)+'\n')
    return path,checks,[p for _,p,_ in objects]+[BUILD/'vp2_memset.o',mutant]


def verify():
    require_m1()
    (BUILD/'proof-resources.json').unlink(missing_ok=True)
    path,checks,objects=prepare()
    sources=[ROOT/'tools'/n for n in ['verify_resources.py','resource_mutations.py']]
    sources += [ROOT/'proofs'/n for n in ['memory.ml','costs.ml','resource_tail.ml','resource_bulk.ml',
                 'resource_composition.ml','resource_chunk.ml','resource_exact8.ml','witnesses.ml']]
    inputs=[path,*sources,*objects,*BUILD.glob('ve_cost_*.o')]
    proof=run_session('resources','loadt '+json.dumps(str(path))+';;',checks,inputs=inputs)
    require_m1()
    report={'complete':True,'scope':'E7a model steps and data amounts; no elapsed-time bound',
            'proof':proof,'mutations':json.loads((BUILD/'resource-mutations.json').read_text()),
            'formulas':{'scalar':'5*n+3','fill':'4*n+3',
                        'exact8':'n!=8: 5*n+5; n=8 and aligned: 8; n=8 and unaligned: 48',
                        'chunk8':'aligned: 7*(n DIV 8)+5*(n MOD 8)+10; unaligned: 5*n+7'},
            'data_bytes':{'copy':{'read':'n','write':'n'},'fill':{'read':0,'write':'n'}},
            'private_stack_bytes':0,'heap_bytes':0,
            'stack_basis':'leaf bodies contain no SP-relative load/store or SP update; counted theorem frame excludes SP',
            'instruction_count_semantics':'exact number of ARM relation steps through RET; not a first-PC-hit time',
            'external_assumptions':['ordinary RAM remains valid','pinned ARM ISA model','kernel/runtime/hardware correspondence'],
            'source_inputs':{str(p):digest(p) for p in sources}}
    folder=ROOT/'reports/m3/resources';folder.mkdir(exist_ok=True)
    (folder/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    requirements=json.loads((ROOT/'reports/requirements.json').read_text())
    for item in requirements['requirements']:
        if item['id'].startswith('E7a.'):
            item.update(status='complete',evidence=['reports/m3/resources/verification.json',
                        'proofs/costs.ml','proofs/resource_chunk.ml','tools/resource_mutations.py'])
    (ROOT/'reports/requirements.json').write_text(json.dumps(requirements,indent=2)+'\n')
    page=folder/'README.md'
    if page.exists():
        rows=page.read_text().splitlines()
        for i,row in enumerate(rows):
            if row.startswith('状態:'):
                rows[i]=f'状態: **完了**。新規HOLプロセスで20件の閉じた定理を{proof["elapsed_seconds"]:.1f}秒で検査し、追加公理なしを確認した。[証明の入力と結果](verification.json)を保存している。'
        page.write_text('\n'.join(rows)+'\n')
    progress=ROOT/'reports/progress.md';rows=progress.read_text().splitlines()
    for i,row in enumerate(rows):
        if row.startswith('| E7a |'):
            rows[i]=f'| E7a | 完了 | [資源の定理](m3/resources/README.md)。任意長・経路別のステップ数とデータ量、追加・削除の反例を新規20件・{proof["elapsed_seconds"]:.1f}秒で再検査 |'
    progress.write_text('\n'.join(rows)+'\n')
    print('E7a complete: exact counts, data byte amounts, and add/delete counterexamples; M3 still incomplete',flush=True)
    return report


if __name__=='__main__':verify()
