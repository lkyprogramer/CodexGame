"""Synthetic counterexamples, not target-machine validation."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))


class OfflineTests(unittest.TestCase):
    def mod(self, name):
        self.assertTrue((ROOT / 'tools' / (name + '.py')).is_file(), 'offline module not implemented: ' + name)
        return importlib.import_module(name)

    def fixture(self, name):
        return json.loads((ROOT / 'fixtures' / name).read_text())

    def test_interval_union_and_overhead(self):
        data = {'schema_version': 1, 'synthetic': True, 'window_ms': 1000,
                'critical_exposed_intervals': [[100, 300], [200, 400], [500, 550]],
                'measured_kernel_speedup': 2, 'added_overhead_ms': 20,
                'dependency_verified': True, 'unknown_intervals': []}
        result = self.mod('headroom').evaluate(data)
        self.assertEqual(result['exposed_ms'], 350)
        self.assertAlmostEqual(result['optimistic']['time_ratio'], 0.65)
        self.assertAlmostEqual(result['realistic']['time_improvement'], 0.155)
        self.assertFalse(result['deployment_approved'])
        for key, value in [('dependency_verified', False), ('unknown_intervals', [[700, 800]])]:
            changed = copy.deepcopy(data); changed[key] = value
            self.assertEqual(self.mod('headroom').evaluate(changed)['status'], 'INSUFFICIENT')
        for key, value in [('schema_version', True), ('window_ms', True), ('critical_exposed_intervals', [[200, 100]]),
                           ('critical_exposed_intervals', [[0, 1001]]), ('added_overhead_ms', -1),
                           ('measured_kernel_speedup', float('nan'))]:
            changed = copy.deepcopy(data); changed[key] = value
            with self.assertRaises(ValueError): self.mod('headroom').evaluate(changed)

    def test_exact_pairs_and_preregistered_noise_gate(self):
        mod = self.mod('paired_stats'); data = self.fixture('paired_synthetic.json')
        result = mod.evaluate(data)
        self.assertEqual(result['bootstrap_draws'], 46656)
        self.assertEqual(result['status'], 'PERFORMANCE_GATE_ONLY')
        self.assertAlmostEqual(result['metrics']['ttft_ms']['ratio_ci95'][1], 0.9)
        self.assertEqual(result['quality'], 'NOT_EVALUATED')
        self.assertFalse(result['deployment_approved'])
        data['preregistration']['aa_noise'] = 0.06
        self.assertEqual(mod.evaluate(data)['status'], 'PERFORMANCE_GATE_NOT_MET')

    def test_failed_or_incomplete_pairs_never_yield_inference(self):
        mod = self.mod('paired_stats'); original = self.fixture('paired_synthetic.json')
        changes = [lambda d: d.__setitem__('schema_version', True), lambda d: d['pairs'].pop(),
                   lambda d: d['pairs'].__setitem__(1, copy.deepcopy(d['pairs'][0])),
                   lambda d: d['pairs'][0]['candidate'].pop('run_valid'),
                   lambda d: d['pairs'][0]['candidate'].__setitem__('failure_kind', 'infrastructure'),
                   lambda d: d['pairs'][0]['candidate'].__setitem__('request_sha256', 'b' * 64),
                   lambda d: d['pairs'][0]['candidate'].__setitem__('output_tokens', 2047),
                   lambda d: d['pairs'][0]['candidate']['metrics'].__setitem__('wall_ms', float('nan')),
                   lambda d: d['pairs'][0]['candidate'].__setitem__('engine_id', 'A1'),
                   lambda d: d['pairs'][0].__setitem__('order', 'CA')]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                data = copy.deepcopy(original); change(data)
                with self.assertRaises(ValueError): mod.evaluate(data)

    def test_decode_primary_cannot_hide_ttft_regression(self):
        data = self.fixture('paired_synthetic.json')
        data['preregistration']['primary_metric'] = 'decode_ms'
        for pair in data['pairs']:
            pair['candidate']['metrics']['decode_ms'] = 1600
            pair['candidate']['metrics']['ttft_ms'] = 1100
        result = self.mod('paired_stats').evaluate(data)
        self.assertTrue(result['gates']['primary'])
        self.assertEqual(result['status'], 'PERFORMANCE_GATE_NOT_MET')
        self.assertFalse(result['gates']['ttft_ms'])

    def test_p24_rounded_sanity_is_not_raw_reproduction(self):
        result = self.mod('paired_stats').evaluate(self.fixture('p24_rounded_synthetic.json'))
        self.assertTrue(result['synthetic'])
        self.assertEqual(result['status'], 'PERFORMANCE_GATE_NOT_MET')
        self.assertAlmostEqual(result['metrics']['ttft_ms']['ratio'], 0.991756, delta=0.00001)
        self.assertGreater(result['metrics']['decode_ms']['ratio_ci95'][1], 1.06)

    def test_strict_json_and_exclusive_output(self):
        mod = self.mod('common')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'input.json'
            for text in ['{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}']:
                path.write_text(text)
                with self.assertRaises(ValueError): mod.load(path)
            path.write_text('{}')
            with self.assertRaises(FileExistsError): mod.emit({'x': 1}, path)
            self.assertEqual(path.read_text(), '{}')

    def test_package_links_dag_and_safety_policy(self):
        mod = self.mod('validate')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'config').mkdir(); (root / 'sources').mkdir(); (root / 'templates').mkdir()
            (root / 'a.md').write_text('[next](b.md)'); (root / 'b.md').write_text('# B')
            policy = json.loads((ROOT / 'config/policy.json').read_text())
            lock = json.loads((ROOT / 'sources/LOCK.json').read_text())
            dag = {'phases': [{'id': 'P0', 'depends_on': [], 'tasks': [
                {'id': 'T0', 'depends_on': [], 'doc': 'a.md'},
                {'id': 'T1', 'depends_on': ['T0'], 'doc': 'b.md'}]}]}
            candidates = {'candidates': [{'id': 'C1', 'title': 'Synthetic', 'status': 'INSUFFICIENT', 'numerical_class': 'E0', 'doc': 'a.md'}]}
            files = {'templates/PREREGISTRATION.json': json.loads((ROOT / 'templates/PREREGISTRATION.json').read_text()),
                     'config/policy.json': policy, 'sources/LOCK.json': lock,
                     'config/task_dag.json': dag, 'config/candidates.json': candidates}
            def write():
                for name, value in files.items(): (root / name).write_text(json.dumps(value))
            write(); self.assertEqual(mod.evaluate(root)['status'], 'PACKAGE_VALID')
            for mutation in ['cycle', 'missing_dependency', 'policy', 'threshold', 'order', 'cleanup_reserve', 'diagnostic_engines', 'diagnostic_requests', 'request_deadline', 'diagnostic_output', 'diagnostic_collection', 'primary_metric', 'calibration_pairs', 'deploy', 'sha', 'missing_sha', 'document', 'link']:
                saved = copy.deepcopy(files)
                if mutation == 'cycle': dag['phases'][0]['tasks'][0]['depends_on'] = ['T1']
                elif mutation == 'missing_dependency': dag['phases'][0]['tasks'][0]['depends_on'] = ['UNKNOWN']
                elif mutation == 'policy': policy['limits']['context_ceiling_tokens'] = 262144
                elif mutation == 'threshold': policy['qualification']['hard_reject_optimistic_gain_lt'] = 0.001
                elif mutation == 'order': policy['formal_performance']['order'] = ['AC'] * 6
                elif mutation == 'cleanup_reserve': policy['limits']['diagnostic_cleanup_reserve_seconds'] = 0
                elif mutation == 'diagnostic_engines': policy['limits']['max_initial_diagnostic_engine_starts'] = 4
                elif mutation == 'diagnostic_requests': policy['limits']['max_initial_diagnostic_work_requests'] = 8
                elif mutation == 'request_deadline': policy['limits']['diagnostic_request_deadline_seconds'] = 601
                elif mutation == 'diagnostic_output': policy['limits']['diagnostic_output_tokens'] = 4096
                elif mutation == 'diagnostic_collection': policy['diagnostic']['allow_extra_control_or_profiler'] = True
                elif mutation == 'primary_metric': policy['formal_performance']['primary_metric'] = 'ttft_ms'
                elif mutation == 'calibration_pairs': policy['formal_performance']['calibration_max_pairs'] = 4
                elif mutation == 'deploy': candidates['deployment_approved'] = True
                elif mutation == 'sha': lock['research_baseline']['sha'] = '5e8a4cc'
                elif mutation == 'missing_sha': lock['research_baseline'].pop('sha')
                elif mutation == 'document': candidates['candidates'][0]['doc'] = 'missing.md'
                else: (root / 'a.md').write_text('[bad](missing.md)')
                write()
                with self.subTest(mutation=mutation), self.assertRaises(ValueError): mod.evaluate(root)
                files = saved; policy = files['config/policy.json']; lock = files['sources/LOCK.json']; dag = files['config/task_dag.json']; candidates = files['config/candidates.json']
                (root / 'a.md').write_text('[next](b.md)'); write()

    def test_single_engine_diagnostic_rejects_expansion_and_weakened_request_contract(self):
        mod = self.mod('validate')
        original = json.loads((ROOT / 'templates/PREREGISTRATION.json').read_text())
        mod.validate_diagnostic_template(original)
        changes = [lambda d: d.__setitem__('max_engine_starts', 4),
                   lambda d: d.__setitem__('max_work_requests', 8),
                   lambda d: d.__setitem__('wall_budget_seconds', 3601),
                   lambda d: d.__setitem__('cleanup_reserve_seconds', 0),
                   lambda d: d.__setitem__('allow_extra_control_or_profiler', True),
                   lambda d: d.__setitem__('short_output_status', 'PASS'),
                   lambda d: d['matrix'].append(copy.deepcopy(d['matrix'][0])),
                   lambda d: d['matrix'][0]['requests'].pop(),
                   lambda d: d['matrix'][0]['requests'][0].__setitem__('context_target_tokens', 65536),
                   lambda d: d['matrix'][0]['requests'][1].__setitem__('request_deadline_seconds', 601),
                   lambda d: d['matrix'][0]['requests'][1].__setitem__('max_output_tokens', 4096),
                   lambda d: d['matrix'][0]['requests'][1].__setitem__('target_output_tokens', 32),
                   lambda d: d['matrix'][0]['requests'][1].__setitem__('actual_history_hash_policy', 'canonical_gold'),
                   lambda d: d['matrix'][0]['requests'][1].__setitem__('validate_before_send', 'recipe_only'),
                   lambda d: d['matrix'][0]['requests'][1].__setitem__('validate_after_response', 'ignore_short_eos'),
                   lambda d: d['matrix'][0].__setitem__('append_new_read_includes_pt0_history_reread', False)]
        for index, change in enumerate(changes):
            data = copy.deepcopy(original); change(data)
            with self.subTest(case=index), self.assertRaises(ValueError): mod.validate_diagnostic_template(data)

    def test_manifest_detects_content_extra_and_traversal(self):
        mod = self.mod('verify_manifest')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); file = root / 'a.md'; file.write_bytes(b'a')
            manifest = root / 'MANIFEST.sha256'; original = hashlib.sha256(b'a').hexdigest() + '  a.md\n'
            manifest.write_text(original)
            self.assertEqual(mod.verify(root, manifest)['files_verified'], 1)
            manifest.write_text(original * 2)
            with self.assertRaises(ValueError): mod.verify(root, manifest)
            manifest.write_text(original)
            file.write_bytes(b'b')
            with self.assertRaises(ValueError): mod.verify(root, manifest)
            file.write_bytes(b'a'); (root / 'extra').write_text('extra')
            with self.assertRaises(ValueError): mod.verify(root, manifest)
            (root / 'extra').unlink(); manifest.write_text(original.replace('a.md', '../a.md'))
            with self.assertRaises(ValueError): mod.verify(root, manifest)
            (root / 'link').symlink_to('a.md'); manifest.write_text(original + original.replace('a.md', 'link'))
            with self.assertRaises(ValueError): mod.verify(root, manifest)


if __name__ == '__main__': unittest.main()
