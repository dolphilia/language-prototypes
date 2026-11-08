"""M2 objects have separate symbols/harnesses; keep measured M1 artifacts intact."""
from config import ROOT,BUILD,opam_command,validate_dependencies
from build import run,words,check_span


def prepare():
    validate_dependencies();BUILD.mkdir(exist_ok=True)
    run(opam_command(['ocamlc','-c','-o',BUILD/'generator.cmo',ROOT/'generator/main.ml']))
    run(opam_command(['ocamlc','-I',BUILD,'-c','-o',BUILD/'m2.cmo',ROOT/'generator/m2.ml']))
    run(opam_command(['ocamlc','-I',BUILD,BUILD/'generator.cmo',BUILD/'m2.cmo','-o',BUILD/'generate_m2']))
    run([BUILD/'generate_m2',BUILD])
    result=[]
    for name in ['vp2_memmove']:
        run(['xcrun','clang','-arch','arm64','-c',BUILD/(name+'.S'),'-o',BUILD/(name+'.o')])
        body=check_span(BUILD/(name+'.o'),name,words(BUILD/(name+'.words')))
        if len(body)>256: raise RuntimeError('memmove body exceeds its separate 256-byte budget')
        result.append({'name':name,'body_bytes':len(body),'leaf':True,'stack_bytes':0})
    return result


if __name__=='__main__': print(prepare())
