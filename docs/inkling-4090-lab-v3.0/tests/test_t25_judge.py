"""T41: fail-closed behaviour of tools/t25/t25_judge.py on synthetic run directories (needs numpy)."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    import numpy as np
except ImportError:  # the 2-core dev box has no numpy; the 4090 venv runs these
    np = None

ROOT = Path(__file__).resolve().parents[1]
JUDGE = ROOT / "tools/t25/t25_judge.py"
RULE = ROOT / "tools/t25/rule_num4l.json"
EXPECT = ROOT / "tools/t25/negs_expect.json"
N, NSAMP = 600, 9


def make(d, cases=2, negs=("dp4a", "r2"), r2_scale=10.0, nan=False, dup=False, drop_neg=False):
    rng = np.random.default_rng(0)
    first = json.load(open(RULE))["first"]
    (Path(d) / "negs.txt").write_text("\n".join(negs) + "\n")
    for i in range(cases):
        name = "e%d" % i
        w = Path(d, name); w.mkdir()
        (w / "ids.txt").write_text(" ".join(["1"] * N))
        (w / "sample.tsv").write_text("s\t" + ",".join(map(str, range(NSAMP))) + "\n")
        (w / "lens.json").write_text(json.dumps({"len": N, "prompt_len": N}))
        js = {}
        base = {m: rng.exponential(0.2, m) + 1e-3 for m in (N - 1 - first, NSAMP)}
        for k in range(8 + len(negs)):
            m = (N - 1 - first) if k < 5 or k >= 8 else NSAMP
            js[str(k)] = {"positions": m}
            if drop_neg and k == 8 + len(negs) - 1 and i == 0:
                continue
            pos = np.arange(m)
            if dup and k == 1:
                pos[1] = pos[0]
            kl = base[m].copy()  # every pair equals its reference: ratios are exactly 1
            if k >= 8 and negs[k - 8] == "r2":
                kl = kl * r2_scale
            if nan and k == 1:
                kl[3] = np.nan
            np.savez(Path(d, "%s.json.%d.npz" % (name, k)), pos=pos, kl=kl, agree=np.ones(m, bool), ref_margin=np.ones(m))
        Path(d, name + ".json").write_text(json.dumps(js))


def judge(d, *extra):
    return subprocess.run([sys.executable, "-I", str(JUDGE), d, "e", str(RULE), "--negs-expect", str(EXPECT), *extra],
                          capture_output=True, text=True)


@unittest.skipIf(np is None, "numpy not installed")
class T25JudgeFailClosed(unittest.TestCase):
    def run_case(self, want, extra=(), **kw):
        with tempfile.TemporaryDirectory() as d:
            make(d, **kw)
            r = judge(d, *extra)
            self.assertEqual(r.returncode, want, r.stdout[-2000:] + r.stderr[-2000:])
            return json.loads(r.stdout)

    def test_clean_run_passes(self):
        v = self.run_case(0, ("--cases", "2"))
        self.assertEqual(v["verdict"], "PASS")

    def test_expected_negative_not_caught_is_invalid(self):
        self.assertEqual(self.run_case(3, r2_scale=1.0)["verdict"], "INVALID")

    def test_unregistered_negative_is_invalid(self):
        self.assertEqual(self.run_case(3, negs=("dp4a", "r2", "mystery"))["verdict"], "INVALID")

    def test_no_power_negative_is_invalid(self):
        self.assertEqual(self.run_case(3, negs=("dp4a",))["verdict"], "INVALID")

    def test_nan_duplicate_missing_are_incomplete(self):
        self.assertEqual(self.run_case(2, nan=True)["verdict"], "INCOMPLETE")
        self.assertEqual(self.run_case(2, dup=True)["verdict"], "INCOMPLETE")
        self.assertEqual(self.run_case(2, drop_neg=True)["verdict"], "INCOMPLETE")
        self.assertEqual(self.run_case(2, ("--cases", "3"))["verdict"], "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
