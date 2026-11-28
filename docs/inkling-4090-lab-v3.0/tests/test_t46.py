import json
import os
import sys
import tempfile
import unittest

try:
    import numpy as np
except ImportError:  # the 2C/1G workstation has no numpy; runs on the 4090 venv
    np = None

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "t46"))


@unittest.skipIf(np is None, "numpy not installed")
class T46Test(unittest.TestCase):
    def setUp(self):
        import t46
        self.t46 = t46
        self.d = tempfile.mkdtemp()
        rng = np.random.default_rng(7)
        self.V = 4000
        for sub in ("teach", "cand", "rep"):
            os.makedirs(os.path.join(self.d, sub))
        for i in range(6):
            z = rng.normal(0, 3, self.V).astype(np.float32)
            z.tofile(os.path.join(self.d, "teach", "p%02d_%d.step.f32" % (i, 10 + i)))
            (z + rng.normal(0, 0.05, self.V)).astype(np.float32).tofile(os.path.join(self.d, "cand", "p%02d_%d.step.f32" % (i, 10 + i)))
            (z + rng.normal(0, 0.001, self.V)).astype(np.float32).tofile(os.path.join(self.d, "rep", "p%02d_%d.step.f32" % (i, 10 + i)))

    def run_kl(self, k):
        c = os.path.join(self.d, "c%d.npz" % k)
        self.assertEqual(self.t46.main(["cache", os.path.join(self.d, "teach"), c, "--k", str(k)]), 0)
        o = os.path.join(self.d, "o%d.json" % k)
        rc = self.t46.main(["kl", c, os.path.join(self.d, "cand"), "--full", os.path.join(self.d, "teach"), "--repeat", os.path.join(self.d, "rep"), "--out", o])
        return rc, json.load(open(o))

    def test_lower_bound_and_convergence(self):
        rc, small = self.run_kl(8)
        self.assertEqual(rc, 0)
        self.assertTrue(small["lower_bound_holds"])
        rc, big = self.run_kl(3999)
        self.assertTrue(big["lower_bound_holds"])
        self.assertLess(abs(big["rel_gap_mean"]), 1e-3)
        self.assertLessEqual(small["kl_top"]["mean"], big["kl_top"]["mean"] + 1e-12)
        self.assertTrue(big["above_noise_max"])

    def test_identical_is_zero(self):
        c = os.path.join(self.d, "c.npz")
        self.t46.main(["cache", os.path.join(self.d, "teach"), c])
        o = os.path.join(self.d, "o.json")
        self.t46.main(["kl", c, os.path.join(self.d, "teach"), "--out", o])
        self.assertLess(json.load(open(o))["kl_top"]["max"], 1e-6)  # float32 cache floor

    def test_missing_candidate_is_incomplete(self):
        c = os.path.join(self.d, "c.npz")
        self.t46.main(["cache", os.path.join(self.d, "teach"), c])
        os.remove(os.path.join(self.d, "cand", "p03_13.step.f32"))
        self.assertEqual(self.t46.main(["kl", c, os.path.join(self.d, "cand")]), 2)

    def test_repetition(self):
        rep = self.t46.repetition
        self.assertIsNone(rep(list(range(300))))
        self.assertEqual(rep(list(range(50)) + [1, 2, 3, 4] * 40)[0], 4)
        self.assertEqual(rep([9] * 120)[0], 1)
        self.assertIsNone(rep(list(range(50)) + [1, 2, 3, 4] * 10))


if __name__ == "__main__":
    unittest.main()
