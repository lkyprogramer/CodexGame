"""Adapt the existing P5 passive counters to v0.2.7's arithmetic dispatch."""
from pathlib import Path
import importlib.util
import sys

PRIOR = Path(__file__).resolve().parents[1] / 'gu_probe/patch_profile.py'
spec = importlib.util.spec_from_file_location('p5_profile_patch', PRIOR)
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


def apply(tree):
    tree = Path(tree)
    p = tree / 'src/kernels/cpu/pool.cpp'
    text = p.read_text()
    branch = '''                    if (narithmetic_ == NativeArithmetic::WindowInvariant)
                        native_gu_rows_invariant(*nfmt, mjobs_[e].blob, mjobs_[e].nact, mjobs_[e].nt, ff, r0, r1);
                    else
                        native_gu_rows(*nfmt, mjobs_[e].blob, mjobs_[e].nact, mjobs_[e].nt, ff, r0, r1);'''
    old = '                    native_gu_rows(*nfmt, mjobs_[e].blob, mjobs_[e].nact, mjobs_[e].nt, ff, r0, r1);'
    p.write_text(prior.replace(text, branch, old))
    prior.apply(tree)
    text = p.read_text()
    p.write_text(prior.replace(text, old, branch))


if __name__ == '__main__':
    apply(sys.argv[1])
