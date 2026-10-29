from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/hc_scratch'))
import lifecycle_patch
import managed_control_patch
import lifecycle


class LifecyclePatchTests(unittest.TestCase):
    def test_program_source_drift_rejected(self):
        with self.assertRaisesRegex(ValueError, 'LIFECYCLE_PROGRAM_SOURCE_DRIFT'):
            lifecycle_patch.program('unknown source')

    def test_lifecycle_trace_does_not_enable_raw_oracle(self):
        old = (ROOT / 'workspace/combination/hc-boundary-20261029/source-evidence/generate.cpp').read_text()
        new = lifecycle_patch.program(old)
        self.assertIn('if (' + lifecycle_patch.ORACLE + ') {\n                if (max_new != 1)', new)
        self.assertEqual(new.count(lifecycle_patch.LIFE), 4)
        self.assertIn('P21_REQUEST', new)

    def test_prefill_only_extends_existing_successful_batch_trace(self):
        old = (ROOT / 'workspace/combination/hc-boundary-20261029/source-evidence/prefill.cpp').read_text()
        old = managed_control_patch.transform(old)
        new = lifecycle_patch.prefill(old)
        self.assertEqual(new.replace(lifecycle_patch.LIFE, lifecycle_patch.ORACLE), old)

    def test_prefill_cancel_requires_real_progress_before_total(self):
        self.assertFalse(lifecycle.cancel_trigger('prefill', 'PP 16383 32773 10 1', 0))
        self.assertTrue(lifecycle.cancel_trigger('prefill', 'PP 16384 32773 10 1', 0))
        self.assertFalse(lifecycle.cancel_trigger('prefill', 'PP 32773 32773 10 1', 0))
        self.assertFalse(lifecycle.cancel_trigger('prefill', 'PP 16384 32773 10 1', 1))

    def test_decode_cancel_counts_native_tokens(self):
        self.assertFalse(lifecycle.cancel_trigger('decode', 'T 12', 7))
        self.assertTrue(lifecycle.cancel_trigger('decode', 'T 12', 8))
        self.assertFalse(lifecycle.cancel_trigger('decode', 'PP 16384 32773 10 1', 8))

    def test_done_tracks_actual_resume_and_read_extent(self):
        d = lifecycle.parse_done('DONE 0 32773 100 0 cancel 0 0 0 0 0 0 0 0.0 16384 0 chunk=16384 experts_streamed=123')
        self.assertEqual(d, {'produced': 0, 'input_tokens': 32773, 'finish': 'cancel', 'reused': 0,
                             'read_tokens': 16384, 'chunk': 16384})

    def test_memcheck_requires_all_summaries_zero(self):
        lifecycle.validate_memcheck('========= ERROR SUMMARY: 0 errors\n')
        for text in ['', 'ERROR SUMMARY: 1 error', 'ERROR SUMMARY: 0 errors\nERROR SUMMARY: 2 errors']:
            with self.subTest(text=text), self.assertRaisesRegex(RuntimeError, 'MEMCHECK_NOT_ZERO'):
                lifecycle.validate_memcheck(text)

    def test_prefill_cancel_rejects_late_stop_after_decode_or_prompt_complete(self):
        done = {'produced': 0, 'input_tokens': 32773, 'finish': 'cancel', 'reused': 0, 'read_tokens': 16384}
        lifecycle.validate_cancel('prefill', done, True)
        for change in [{'produced': 1}, {'read_tokens': 32773}, {'read_tokens': 16383}]:
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                lifecycle.validate_cancel('prefill', dict(done, **change), True)

    def test_instrumentation_cannot_change_effective_cache(self):
        expected = {k: str(i) for i, k in enumerate(lifecycle.INFO_FIELDS)}
        lifecycle.validate_startup(expected, expected)
        with self.assertRaisesRegex(RuntimeError, 'EFFECTIVE_NATIVE_CONFIG_CHANGED'):
            lifecycle.validate_startup(dict(expected, expert_slots='10271'), dict(expected, expert_slots='10272'))


if __name__ == '__main__':
    unittest.main()
