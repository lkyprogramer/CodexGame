import unittest
from remaining_watch import validate


class WatchTest(unittest.TestCase):
    def test_requires_expected_supervisor_and_manifest_before_readiness(self):
        snap = {'watchdog': {'supervisor_pid': 42}, 'manifest_sha256': 'frozen'}
        self.assertTrue(validate(snap, 42, 'frozen', lambda s, stage: stage == 'remaining'))
        self.assertFalse(validate(snap, 42, 'frozen', lambda s, stage: False))
        for pid, digest in [(43, 'frozen'), (42, 'changed')]:
            with self.assertRaises(RuntimeError):
                validate(snap, pid, digest, lambda *_: self.fail('must reject before readiness'))
