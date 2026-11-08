"""Interactive development session; never emits a verification receipt."""
import os
from config import DEPS, environment, opam_command

command=opam_command([DEPS/'hol-light/ocaml-hol','-init',DEPS/'hol-light/hol.ml',
                      '-I',DEPS/'hol-light'])
os.chdir(DEPS/'s2n-bignum')
os.execvpe(command[0],command,environment())
