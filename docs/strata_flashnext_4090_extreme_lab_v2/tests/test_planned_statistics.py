import copy
import json
import tempfile
import unittest
from pathlib import Path
from lab.core import hash_obj
from lab.statistics import summarize


def request_hash(content):
    return hash_obj({'messages': [{'role': 'user', 'content': content}], 'max_tokens': 512})


class PlannedStatisticsTests(unittest.TestCase):
    def fixture(self, folder, cases=None, arms=('p', 'base'), rounds=5):
        cases = cases or [{'id': 'q', 'group': 'decode', 'cache_state': 'no_reuse',
                           'scenario': 'fixed_http', 'context_bucket': '4k',
                           'request_sha256': request_hash('frozen-q'), 'fixed_output': 512}]
        manifest = {'schema_version': 2, 'mode': 'MIGRATION', 'arms': list(arms),
                    'comparisons': [[arms[0], arms[1]]], 'rounds': rounds,
                    'case_ids': [x['id'] for x in cases], 'cases': cases, 'primary_metric': 'wall_s'}
        rows = []
        for rnd in range(rounds):
            for arm in arms:
                for case in cases:
                    rows.append({'round': rnd, 'arm': arm, 'case_id': case['id'], 'phase': 'measured',
                                 'group': case['group'], 'cache_state': case['cache_state'],
                                 'scenario': case['scenario'], 'context_bucket': case['context_bucket'],
                                 'request_sha256': case['request_sha256'], 'fixed_output_comparable': True,
                                 'metrics': {'wall_s': 10 if arm == arms[0] else 8,
                                             'decode_ms': 9000 if arm == arms[0] else 7000,
                                             'prompt_tokens': 4000, 'generated_tokens': 512},
                                 'score': {'pass': True, 'reason': 'fixture'}})
        (folder/'campaign.json').write_text(json.dumps(manifest))
        (folder/'COMPLETION.json').write_text('{"state":"COMPLETE","final_audit":"PASS"}')
        self.write(folder, rows)
        return rows

    def write(self, folder, rows):
        (folder/'requests.jsonl').write_text('\n'.join(json.dumps(row) for row in rows))

    def test_migration_pair_is_not_forced_into_off_on(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t); self.fixture(p)
            report = summarize(p)
            self.assertIsNotNone(report['comparisons'].get('p_vs_base'))
            self.assertAlmostEqual(report['comparisons']['p_vs_base']['improvement_pct'], 20)
            self.assertEqual(report['invalid_pairs'], [])

    def test_missing_case_in_both_arms_cannot_look_complete(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t); rows = self.fixture(p, arms=('base', 'off', 'on'), rounds=6)
            self.write(p, [r for r in rows if r['round'] != 5])
            self.assertTrue(summarize(p)['invalid_pairs'])

    def test_duplicate_rows_are_not_extra_samples(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t); rows = self.fixture(p, arms=('base', 'off', 'on'))
            self.write(p, rows + [copy.deepcopy(rows[0])])
            self.assertTrue(any('duplicate' in x.lower() for x in summarize(p)['invalid_pairs']))

    def test_cold_and_warm_never_pool_into_one_speedup(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            cases = [{'id': 'cold', 'group': 'decode', 'cache_state': 'no_reuse',
                      'scenario': 'fixed_http', 'context_bucket': '4k', 'request_sha256': request_hash('cold')},
                     {'id': 'warm', 'group': 'decode', 'cache_state': 'prefix_reuse',
                      'scenario': 'fixed_http', 'context_bucket': '4k', 'request_sha256': request_hash('warm')}]
            self.fixture(p, cases=cases)
            report = summarize(p)
            self.assertIsNone(report['comparisons'].get('p_vs_base'))
            self.assertEqual(len(report.get('strata_comparisons', {})), 2)

    def test_completion_receipt_is_required_for_new_campaigns(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t); self.fixture(p); (p/'COMPLETION.json').unlink()
            self.assertTrue(any('completion' in x.lower() for x in summarize(p)['invalid_pairs']))

    def test_failed_round_cannot_be_hidden_by_successful_rounds(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t); rows = self.fixture(p)
            rows[0]['score']['pass'] = False; self.write(p, rows)
            report = summarize(p)
            self.assertEqual(report['decision'], 'REJECT_OR_FIX')
            self.assertGreater(report['failures'], 0)

    def test_metric_missing_or_nan_is_not_a_valid_pair(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t); rows = self.fixture(p, arms=('base', 'off', 'on'))
            rows[0]['metrics']['wall_s'] = float('nan'); self.write(p, rows)
            try:
                report = summarize(p)
            except ValueError as error:
                self.fail('Invalid metric must be retained in the audit report: ' + str(error))
            self.assertTrue(report['invalid_pairs'])

    def test_plan_request_hash_is_checked_even_if_arms_match_each_other(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t); rows = self.fixture(p, arms=('base', 'off', 'on'))
            for r in rows: r['request_sha256'] = request_hash('changed-both')
            self.write(p, rows)
            self.assertTrue(any('hash' in x.lower() for x in summarize(p)['invalid_pairs']))

    def test_schema2_missing_plan_hash_rejects_otherwise_complete_candidate(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t); rows = self.fixture(p, arms=('base', 'off', 'on'))
            plan = json.loads((p/'campaign.json').read_text())
            plan.update(mode='PR_EXPERIMENT', comparisons=[['base', 'off'], ['off', 'on']])
            for row in rows:
                row['metrics']['wall_s'] = 8 if row['arm'] == 'on' else 10
            self.write(p, rows)
            (p/'campaign.json').write_text(json.dumps(plan))
            self.assertEqual(summarize(p)['decision'], 'CANDIDATE_FOR_HOLDOUT_NOT_PRODUCTION')
            del plan['cases'][0]['request_sha256']
            (p/'campaign.json').write_text(json.dumps(plan))
            report = summarize(p)
            self.assertEqual(report['decision'], 'INCOMPLETE_OR_INVALID')
            self.assertTrue(any('planned request_sha256' in x for x in report['invalid_pairs']))

    def test_schema2_invalid_plan_hash_rejects_matching_record_hashes(self):
        invalid_hashes = ['', 'frozen-q', 'a'*63, 'a'*65, 'g'*64, 'a'*64+'\n',
                          None, False, 123, [], {}]
        for bad_hash in invalid_hashes:
            with self.subTest(request_sha256=bad_hash), tempfile.TemporaryDirectory() as t:
                p = Path(t); rows = self.fixture(p)
                plan = json.loads((p/'campaign.json').read_text())
                plan['cases'][0]['request_sha256'] = bad_hash
                for row in rows:
                    row['request_sha256'] = bad_hash
                (p/'campaign.json').write_text(json.dumps(plan))
                self.write(p, rows)
                report = summarize(p)
                self.assertEqual(report['decision'], 'INCOMPLETE_OR_INVALID')
                self.assertTrue(any('planned request_sha256' in x for x in report['invalid_pairs']))

    def test_schema2_accepts_complete_hex_digest_in_either_case(self):
        for uppercase in (False, True):
            with self.subTest(uppercase=uppercase), tempfile.TemporaryDirectory() as t:
                p = Path(t); rows = self.fixture(p)
                plan = json.loads((p/'campaign.json').read_text())
                digest = request_hash('frozen-q')
                if uppercase:
                    digest = digest.upper()
                plan['cases'][0]['request_sha256'] = digest
                for row in rows:
                    row['request_sha256'] = digest
                (p/'campaign.json').write_text(json.dumps(plan))
                self.write(p, rows)
                self.assertEqual(summarize(p)['invalid_pairs'], [])

    def test_unplanned_legacy_rows_are_descriptive_only(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t); self.fixture(p, arms=('base', 'off', 'on')); (p/'campaign.json').unlink()
            report = summarize(p)
            self.assertTrue(report['invalid_pairs'])
            self.assertNotEqual(report['decision'], 'CANDIDATE_FOR_HOLDOUT_NOT_PRODUCTION')
