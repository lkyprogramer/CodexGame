import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/v027'))
import compare_versions as compare


class VersionCompareTests(unittest.TestCase):
    def test_counter_uses_runtime_pt0_instead_of_inherited_pt1(self):
        config = {'env': {'STRATA_REPLY_REUSE': '1', 'STRATA_PRESERVE_THINKING': '0'}}
        c = {'gguf': 'weights.gguf', 'template': 'chat.jinja'}
        observed = []
        def factory(*args):
            observed.append((os.environ['STRATA_REPLY_REUSE'], os.environ['STRATA_PRESERVE_THINKING'], args))
            return 'counter'
        with patch.dict(os.environ, {'STRATA_REPLY_REUSE': '0', 'STRATA_PRESERVE_THINKING': '1'}), patch.object(compare, 'StrataCounter', side_effect=factory):
            self.assertEqual(compare.make_counter(c, Path('/tree'), config), 'counter')
        self.assertEqual(observed, [('1', '0', (Path('/tree'), 'weights.gguf', 'chat.jinja'))])

    def test_counter_reads_both_defaults_from_runtime(self):
        config = {'env': {'STRATA_REPLY_REUSE': '0', 'STRATA_PRESERVE_THINKING': '1'}}
        c = {'gguf': 'weights.gguf', 'template': 'chat.jinja'}
        with patch.dict(os.environ, {}, clear=True), patch.object(compare, 'StrataCounter') as factory:
            compare.make_counter(c, Path('/tree'), config)
            self.assertEqual(os.environ['STRATA_REPLY_REUSE'], '0')
            self.assertEqual(os.environ['STRATA_PRESERVE_THINKING'], '1')
            factory.assert_called_once()

    def test_closed_campaign_rejects_replay_before_loading_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            (out / 'PREREGISTRATION.json').write_text('{}')
            (out / 'STATE.json').write_text(json.dumps({'state': 'CLOSED'}))
            with patch.object(compare, 'inputs') as inputs:
                with self.assertRaisesRegex(RuntimeError, 'CAMPAIGN_REPLAY_FORBIDDEN'):
                    compare.run(ROOT, out)
                inputs.assert_not_called()


if __name__ == '__main__':
    unittest.main()
