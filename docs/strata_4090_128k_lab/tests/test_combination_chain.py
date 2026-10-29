import copy
import contextlib
import json
from types import SimpleNamespace
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

MODULE_PATH = Path(__file__).resolve().parents[1] / 'tools/combination/run_chain.py'
spec = importlib.util.spec_from_file_location('combination_chain_tested', MODULE_PATH)
chain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chain)


class CombinationChainTests(unittest.TestCase):
    def test_request_preserves_real_history_and_uses_exact_token_budget(self):
        history = [{'role': 'system', 'content': 'system'},
                   {'role': 'assistant', 'content': 'module', 'reasoning_content': 'old thinking'}]
        before = copy.deepcopy(history)
        request, count = chain.request_for_turn(history, 'next requirement', 43, lambda body: 100000,
                                               {'max_context': 131072, 'safety_tokens': 4096})
        self.assertEqual(count, 100000)
        self.assertEqual(request['max_tokens'], 26976)
        self.assertEqual(request['seed'], 43)
        self.assertEqual(request['messages'][:-1], history)
        self.assertEqual(history, before)
        request['messages'][1]['content'] = 'modified'
        self.assertEqual(history, before)
        self.assertEqual(request['reasoning_effort'], 'xhigh')
        self.assertNotIn('reasoning_budget_tokens', request)
        self.assertNotIn('chat_template_kwargs', request)

    def test_context_exhaustion_is_recordable_before_sending_request(self):
        with self.assertRaisesRegex(RuntimeError, 'CONTEXT_LIMIT'):
            chain.request_for_turn([], 'next', 42, lambda body: 126000,
                                   {'max_context': 131072, 'safety_tokens': 4096})

    def test_full_module_is_only_sent_to_existing_isolated_grader(self):
        response = {'finish_reason': 'stop', 'text': '```python\nprint("model code")\n```', 'tools': []}
        with patch.object(chain.chain, 'grade', return_value=[True, False]) as grade:
            score = chain.score_response(response, 2, 'sha256:immutable')
        grade.assert_called_once_with('print("model code")\n', 2, 'sha256:immutable')
        self.assertEqual(score['passed'], [True, False])
        self.assertFalse(score['pass'])
        self.assertTrue(score['graded'])

    def test_truncation_tool_or_ambiguous_code_cannot_pass_or_execute(self):
        cases = [
            {'finish_reason': 'length', 'text': '```python\npass\n```'},
            {'finish_reason': 'stop', 'text': '```python\npass\n```', 'tools': [{}]},
            {'finish_reason': 'stop', 'text': '```python\npass\n```\n```python\npass\n```'},
        ]
        with patch.object(chain.chain, 'grade') as grade:
            for response in cases:
                self.assertFalse(chain.score_response(response, 1, 'sha256:immutable')['pass'])
        grade.assert_not_called()

    def test_grader_missing_or_invalid_output_is_infrastructure_error(self):
        response = {'finish_reason': 'stop', 'text': '```python\npass\n```'}
        for result in (None, [1], [], [True, True]):
            with patch.object(chain.chain, 'grade', return_value=result):
                with self.assertRaisesRegex(RuntimeError, 'GRADER_NOT_AUDITABLE'):
                    chain.score_response(response, 1, 'sha256:immutable')

    def test_failed_or_incomplete_chain_is_budget_penalized(self):
        rows = [{'score': {'pass': True}, 'metrics': {'wall_s': 2}, 'grading_wall_s': 1} for _ in range(8)]
        passed = chain.summarize_chain(rows, 25, 2400)
        self.assertTrue(passed['task_success'])
        self.assertEqual(passed['restricted_time_to_success_s'], 25)
        rows[-1]['score']['pass'] = False
        failed = chain.summarize_chain(rows, 25, 2400)
        self.assertFalse(failed['task_success'])
        self.assertEqual(failed['restricted_time_to_success_s'], 2400)
        self.assertFalse(chain.summarize_chain(rows[:-1], 20, 2400)['task_success'])
        self.assertFalse(chain.summarize_chain(rows, 2401, 2400)['task_success'])

    def fake_runtime(self, root):
        @contextlib.contextmanager
        def managed(c, tree, arm, ready, folder):
            Path(folder).mkdir(parents=True, exist_ok=True)
            yield SimpleNamespace(abort_reason=None, folder=Path(folder))
        combo = SimpleNamespace(combination_server=managed, history_counter_probe=lambda *a: None,
                                validate_startup=lambda *a: {'confirmed': True},
                                resource_sample=lambda *a: {'MemAvailable_kib': 8192 * 1024})
        config = {'gguf': 'unused', 'template': 'unused', 'request_timeout_s': 1800,
                  'max_context': 131072, 'safety_tokens': 4096}
        response = {'error': None, 'finish_reason': 'stop', 'text': '```python\npass\n```',
                    'reasoning': 'reasoning sent back in the next request', 'tools': [],
                    'usage': {'prompt_tokens': 100, 'completion_tokens': 10},
                    'timings': {'predicted_ms': 10}, 'total_s': .1}
        return managed, combo, config, response

    def test_live_chain_saves_raw_history_and_scores_only_in_the_grader(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            managed, combo, config, response = self.fake_runtime(root)
            with patch.object(chain, 'StrataCounter', return_value=lambda request: 100), \
                 patch.object(chain, 'validate_counter'), \
                 patch.object(chain, 'audited_chat', return_value=response) as chat, \
                 patch.object(chain.chain, 'grade', side_effect=lambda code, upto, image: [True] * upto) as grade, \
                 patch('builtins.print'):
                summary = chain.one_chain(config, root / 'tree', 'cfg', {}, root / 'run', 1, 43,
                                          'sha256:immutable', 2400, combo)
            self.assertTrue(summary['task_success'])
            self.assertEqual(chat.call_count, 8)
            self.assertEqual(grade.call_count, 8)
            request = json.loads((root / 'run/turn-01.request.json').read_text())
            self.assertEqual(request['seed'], 43)
            self.assertEqual(request['messages'][-2]['reasoning_content'], response['reasoning'])
            self.assertEqual(request['messages'][-2]['content'], response['text'])
            self.assertEqual(json.loads((root / 'run/turn-00.response.json').read_text()), response)
            self.assertEqual(len((root / 'run/requests.jsonl').read_text().splitlines()), 8)

    def test_grader_infrastructure_failure_keeps_response_and_failed_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            managed, combo, config, response = self.fake_runtime(root)
            with patch.object(chain, 'StrataCounter', return_value=lambda request: 100), \
                 patch.object(chain, 'validate_counter'), \
                 patch.object(chain, 'audited_chat', return_value=response), \
                 patch.object(chain.chain, 'grade', side_effect=RuntimeError('container failed')), \
                 patch('builtins.print'):
                with self.assertRaisesRegex(RuntimeError, 'CHAIN_GRADER_INFRASTRUCTURE'):
                    chain.one_chain(config, root / 'tree', 'base', {}, root / 'run', 0, 42,
                                    'sha256:immutable', 2400, combo)
            saved = json.loads((root / 'run/chain.json').read_text())
            self.assertFalse(saved['summary']['task_success'])
            self.assertEqual(saved['summary']['restricted_time_to_success_s'], 2400)
            self.assertIn('container failed', saved['summary']['error'])
            self.assertTrue((root / 'run/turn-00.response.json').is_file())
            self.assertEqual(len((root / 'run/requests.jsonl').read_text().splitlines()), 1)

    def test_valid_task_failures_keep_all_planned_paired_arms(self):
        for token_count, budget, expected_error in ((100, 100, 'TASK_BUDGET'),
                                                    (126000, 2400, 'CONTEXT_LIMIT')):
            with self.subTest(error=expected_error), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                tree = (root / 'tree').resolve()
                managed, combo, config, response = self.fake_runtime(root)
                combo.combination_server = Mock(wraps=managed)
                combo.validate_tree = lambda path: {'source_sha': 'fixed', 'exe_sha256': 'fixed'}
                combo.ready_spec = lambda: {}
                combo.assert_same_except_kvres = lambda *args: None
                combo.protected_hashes = lambda c: {'production': 'unchanged'}
                combo.assert_protected = lambda c, before: before
                combo.assert_service_inactive = lambda: {'ActiveState': 'inactive'}
                combo.wait_cool = lambda c: []
                config.update(port=18089, min_available_mib=4096, deployed_repo=str(tree),
                              workspace=str(root / 'workspace'))
                with patch.object(chain, 'load_config', return_value=config), \
                     patch.object(chain, 'load_module', return_value=combo), \
                     patch.object(chain, 'make_run_config', return_value={'cwd': str(tree)}), \
                     patch.object(chain, 'verify_assets', return_value={}), \
                     patch.object(chain, 'gpu_lock', side_effect=lambda *args: contextlib.nullcontext()), \
                     patch.object(chain, 'evidence_lifecycle', side_effect=lambda *args: contextlib.nullcontext()), \
                     patch.object(chain, 'StrataCounter', return_value=lambda request: token_count), \
                     patch.object(chain, 'validate_counter'), \
                     patch.object(chain.chain, 'image_id', return_value='sha256:immutable'), \
                     patch.object(chain, 'audited_chat') as chat:
                    result = chain.run('config', tree, root / 'out', 2,
                                       'sha256:immutable', budget, execute=True)
                self.assertEqual(result['state'], 'COMPLETE')
                self.assertEqual(len(result['chains']), 4)
                self.assertEqual([call.args[2] for call in combo.combination_server.call_args_list],
                                 ['base', 'cfg', 'cfg', 'base'])
                chat.assert_not_called()
                for item in result['chains']:
                    self.assertFalse(item['task_success'])
                    self.assertEqual(item['restricted_time_to_success_s'], budget)
                    self.assertIn(expected_error, item['error'])
                    saved = json.loads((root / 'out' / f"pair-{item['pair']:02d}-{item['arm']}" /
                                        'chain.json').read_text())
                    self.assertIn(expected_error, saved['summary']['error'])

    def test_raw_jsonl_record_is_durable_and_replay_index_is_preserved(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'requests.jsonl'
            row = {'request_sha256': 'f' * 64, 'request_file': 'turn-00.request.json',
                   'response_file': 'turn-00.response.json', 'score': {'pass': False}}
            chain.append_record(path, row)
            self.assertEqual(json.loads(path.read_text()), row)


if __name__ == '__main__':
    unittest.main()
