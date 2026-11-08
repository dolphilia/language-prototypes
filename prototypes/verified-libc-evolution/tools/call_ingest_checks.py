"""Reproducible negative checks for the added linked-span ingestion boundary."""
import json
import struct
from config import BUILD


def prepare(report):
    l=report['layouts'][0];source=open(l['path'],'rb').read();folder=BUILD/'call-refusals'
    rows=[]
    for name,offset,value in [('magic',0,0),('architecture',4,0x01000007),
                              ('arm64e',8,2),('file-kind',12,1)]:
        data=bytearray(source);struct.pack_into('<I',data,offset,value)
        p=folder/('ingest-'+name);p.write_bytes(data)
        rows.append((name,str(p),l['bundle_file_offset'],l['bundle_bytes'],l['bundle_words'],
                     'linked span requires thin ordinary arm64 MH_EXECUTE'))
    for name,offset,length in [('header-as-code',0,4),('unaligned',l['bundle_file_offset']+1,4),
                               ('out-of-bounds',len(source)+4,4),('zero-length',l['bundle_file_offset'],0)]:
        rows.append((name,l['path'],offset,length,[],'linked span out of bounds'))
    rows.append(('changed-expected-word',l['path'],l['bundle_file_offset'],l['bundle_bytes'],
        [l['bundle_words'][0]^1,*l['bundle_words'][1:]],'dest_cons4:'))
    lines=['let ve_ingest_refusals = ref [];;',
        'let ve_expect_ingest_refusal label prefix thunk =',
        ' let diagnostic = try ignore(thunk()); "ACCEPTED" with Failure e -> e in',
        ' if String.length diagnostic < String.length prefix ||',
        '    String.sub diagnostic 0 (String.length prefix) <> prefix then failwith ("unexpected ingest result:"^label^":"^diagnostic);',
        ' ve_ingest_refusals := label :: !ve_ingest_refusals;;']
    for name,path,offset,length,words,prefix in rows:
        literal=';'.join(hex(w) for w in words)
        lines.append(f've_expect_ingest_refusal {json.dumps(name)} {json.dumps(prefix)} (fun () -> '
            f've_define_linked_span "ve_rejected_ingest" {json.dumps(path)} {offset} {length} [{literal}]);;')
    names=[r[0] for r in rows]
    lines += ['if List.rev !ve_ingest_refusals <> ['+';'.join(json.dumps(n) for n in names)+'] then failwith "ingest refusal coverage";;']
    path=BUILD/'call-ingest-checks.ml';path.write_text('\n'.join(lines)+'\n')
    return path,names,[r[1] for r in rows]
