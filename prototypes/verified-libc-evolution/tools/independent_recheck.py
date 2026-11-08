"""Reproduce the pinned Proofrecording compatibility trial in an isolated tree.

This is a feasibility investigation, never an independent proof receipt.
No theorem is imported as an axiom. A successful future export must use an
independent checker and corruption tests before this status can change.
"""
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import secrets
import shutil
import subprocess
import tarfile
import time
from config import ROOT,BASE,DEPS,BUILD,digest,environment,opam_command,validate_dependencies


def investigate():
    validate_dependencies()
    started=time.monotonic()
    pin=json.loads((ROOT/'deps.lock').read_text())['hol-light']['commit']
    nonce=secrets.token_hex(12)
    target=BUILD/'recording-trials'/nonce
    target.mkdir(parents=True)
    archive=subprocess.check_output(['git','-C',str(DEPS/'hol-light'),'archive',pin])
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        source.extractall(target,filter='data')
    package=target/'Proofrecording'
    trial=package/'hol_light'
    exports=target/'exports';exports.mkdir()
    env=environment()|{'HOLLIGHT_DIR':str(trial),'HOLPROOFOBJECTS':'EXTENDED',
                       'HOLPROOFEXPORTDIR':str(exports)}
    folder=ROOT/'reports/m3/independent-recheck';folder.mkdir(parents=True,exist_ok=True)
    steps=[]

    def run(label,args,cwd,stdin=None):
        command=opam_command(args)
        result=subprocess.run(command,cwd=cwd,env=env,input=stdin,text=True,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        log=folder/('e6b-'+label+'.log');log.write_text(result.stdout)
        row=dict(name=label,command=list(map(str,command)),cwd=str(cwd),
                 returncode=result.returncode,log=str(log),output=result.stdout)
        steps.append(row)
        return row

    run('name-tool',['make','nametheorems.jar'],package/'tools/src')
    jar=package/'tools/src/nametheorems.jar'
    if not jar.is_file(): raise RuntimeError('Java helper unavailable; not the expected source incompatibility')
    shutil.copyfile(jar,package/'tools/nametheorems.jar')
    built=run('recording-build-after-jar',['make'],trial)
    script=folder/'ret-export.ml'
    script.write_text('load_path := '+json.dumps(str(DEPS/'s2n-bignum'))+' :: !load_path;;\n'+
        'loadt '+json.dumps(str(BASE/'proofs/probe_ret.ml'))+';;\n'+
        'ignore(save_thm "VE_RET_EXPORTED" VP_PROBE_RET_CORRECT);;\n'+
        'export_saved_proofs (Some "ve_ret");;\nexit 0;;\n')
    startup=run('recording-startup',[DEPS/'hol-light/ocaml-hol','-init',trial/'hol.ml',
                                    '-I',trial],trial,script.read_text())
    files=[str(p.relative_to(exports)) for p in exports.rglob('*') if p.is_file()]
    missing=[name for name in ['type.ml','term.ml'] if not (trial/name).exists()]
    # Recognize only the diagnosed compatibility result, never arbitrary failure.
    if built['returncode']==0 or 'pa_j_3.07.ml' not in built['output'] or \
       'Error: Unbound value or' not in startup['output'] or len(missing)!=2 or files:
        raise RuntimeError('compatibility result changed; investigate before recording completion')
    inputs=[Path(__file__).resolve(),ROOT/'deps.lock',BASE/'proofs/probe_ret.ml',BASE/'build/probe_ret.o',
            DEPS/'hol-light/Proofrecording/README',DEPS/'hol-light/Proofrecording/diffs/thm.ml',
            DEPS/'hol-light/Proofrecording/diffs/hol.ml']
    report=dict(timestamp=datetime.now(timezone.utc).isoformat(),nonce=nonce,
        source_commit=pin,archive_sha256=hashlib.sha256(archive).hexdigest(),
        seconds=time.monotonic()-started,inputs={str(p):digest(p) for p in inputs},
        script_sha256=digest(script),steps=steps,missing_core_files=missing,export_files=files,
        routes=['vendored Proofrecording EXTENDED XML','OpenTheory proof-logging HOL Light interface'],
        investigation_complete=True,independent_recheck_success=False,
        status='reproducible source/runtime incompatibility in the pinned environment',
        positive_replay='not reached: no proof was exported',
        corrupt_replay='not reached: no proof or compatible independent checker was produced',
        remaining_work=['port recording to the current fusion.ml and Camlp5/OCaml interfaces',
                        'export definitions, types, axioms and all ARM-model dependencies',
                        'pin a compatible independent checker; replay positive and corrupted proofs'])
    (folder/'trial.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    validate_dependencies()
    print('E6b feasibility trial recorded; independent proof replay remains unavailable',flush=True)
    return report


if __name__=='__main__': investigate()
