from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/hc_scratch'))
import managed_control_patch as control
import managed_control


class ManagedControlTests(unittest.TestCase):
    def test_source_drift_rejected(self):
        with self.assertRaisesRegex(ValueError, 'MANAGED_CONTROL_SOURCE_DRIFT'):
            control.transform('unknown source')

    def test_only_shadow_allocation_changes(self):
        source = (ROOT / 'workspace/combination/hc-boundary-20261029/source-evidence/prefill.cpp').read_text()
        new = control.transform(source)
        self.assertEqual(new.replace(control.NEW, control.OLD, 1), source)
        self.assertIn('cudaDevAttrConcurrentManagedAccess', new)
        self.assertIn('cache_attr.type == cudaMemoryTypeDevice', new)
        self.assertIn('a.type == cudaMemoryTypeManaged', new)
        self.assertIn('p0 == 0 && T == 16384 && m.T == T', new)
        self.assertNotIn('require(free_bytes >= required_bytes', new)
        self.assertIn('private HC final synchronization', new)
        self.assertIn('cudaFree(p)', new)

    def test_missing_managed_marker_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'MANAGED_CONTROL_NOT_ACTUALLY_EXECUTED'):
            managed_control.validate_managed([])

    def test_unmanaged_or_changed_cache_rejected(self):
        for key, value in [('managed_allocations', 0), ('concurrent_managed_access', 0),
                           ('cache_memory_type', 3), ('cache_slots', 10271), ('bytes', 1038091263)]:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                managed_control.validate_managed([dict(managed_control.MARKER, **{key: value})])

    def test_exact_managed_marker_accepted(self):
        managed_control.validate_managed([dict(managed_control.MARKER)])


if __name__ == '__main__':
    unittest.main()
