import unittest
from persistent_remaining_watch import observe


class PersistentWatchTest(unittest.TestCase):
    def test_expected_pid_and_manifest_required_without_launching_work(self):
        snapshot = {'manifest_sha256': 'fixed', 'watchdog': {'supervisor_pid': 6382}}
        config = {'manifest_sha256': 'fixed', 'supervisor_pid': 6382}
        self.assertTrue(observe(snapshot, config, lambda s, stage: stage == 'remaining'))
        self.assertFalse(observe(snapshot, config, lambda *_: False))
        for change in [{'manifest_sha256': 'other'}, {'supervisor_pid': 1}]:
            with self.assertRaises(RuntimeError):
                observe(snapshot, {**config, **change}, lambda *_: self.fail('identity must reject first'))
