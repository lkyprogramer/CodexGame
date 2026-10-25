import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import runner
import slim_runner as base
import slim_capacity_recovery as recovery


class CapacityTests(unittest.TestCase):
    def fixture(self, root):
        body = {"messages": [{"role": "user", "content": "fixture"}], "max_tokens": 32768, "stream": True}
        ident = "pi-fixture"
        directory = root / "requests" / ident
        directory.mkdir(parents=True)
        runner.atomic(directory / "request.json", body)
        raw = {"http_status": 400, "error": None, "response_request_id": None,
               "intentional_disconnect": False, "lines": [], "server_events": [], "observation_errors": [],
               "body": json.dumps({"error": recovery.ERROR}, separators=(',', ':')),
               "request_sha256": runner.sha(runner.encode(body))}
        raw["headers"] = {"Content-Length": str(len(raw["body"].encode()))}
        row = {"id": ident, "group": "pi_teacher_forced", "http_status": 400,
               "requested_output_tokens": 32768, "response_request_id": None,
               "foreign_requests_during_interval": 0,
               "failures": sorted(recovery.EXPECTED_OLD_GAPS), "request_sha256": raw["request_sha256"],
               "extra": {"projected_count": 275579, "count_projection_error": None}}
        (root / "calibration").mkdir()
        runner.atomic(root / "calibration" / (ident+".json"), {
            "chat_sha256": row["request_sha256"], "response": {"input_tokens": 275579}})
        self.persist(directory, raw, row)
        return body, raw, row

    def persist(self, directory, raw, row):
        with gzip.open(directory / "raw.json.gz", "wb") as stream:
            stream.write(runner.encode(raw))
        row["raw_sha256"] = runner.sha((directory / "raw.json.gz").read_bytes())
        runner.atomic(directory / "record.json", row)

    def test_exact_old_rejection_is_overlay_only_and_all_artifacts_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            body, raw, row = self.fixture(root)
            before = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            outcome = recovery.validate_rejection(base, root, row, body, 275579)
            self.assertFalse(outcome['performance_sample_eligible'])
            self.assertEqual(outcome['original_failures_retained'], row['failures'])
            self.assertEqual(before, {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_transport_unexpected_errors_admission_incomplete_and_small_count_rejected(self):
        mutations = [lambda r: r.update(error='timeout'), lambda r: r.update(http_status=500),
                     lambda r: r.update(body=json.dumps({'error': {**recovery.ERROR, 'code': 'other'}})),
                     lambda r: r.update(server_events=[{'event': 'request_done'}]),
                     lambda r: r.update(lines=[{'line': 'data: [DONE]'}]),
                     lambda r: r.update(headers={'Content-Length': '999'}),
                     lambda r: r.update(observation_errors=['log unavailable'])]
        for mutate in mutations:
            with self.subTest(mutation=mutate), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                body, raw, row = self.fixture(root)
                mutate(raw)
                self.persist(root/'requests'/row['id'], raw, row)
                with self.assertRaises((RuntimeError, ValueError)):
                    recovery.validate_rejection(base, root, row, body, 275579)
        with tempfile.TemporaryDirectory() as d:
            body, raw, row = self.fixture(Path(d))
            with self.assertRaises(RuntimeError):
                recovery.validate_rejection(base, Path(d), row, body, 262144)

    def make_collector(self, root, row):
        receipt = {'existing_rejections': {row['id']: runner.sha(runner.encode(row))}, 'receipt_sha256': 'frozen'}
        cls = recovery.recovery_class(base, receipt)
        obj = cls.__new__(cls)
        obj.root, obj.results, obj.resolutions = root, {row['id']: row}, {}
        case = {'id': 'fixture', 'payload_file': 'wire.json', 'source_sha256':'source', 'entry_id':'entry',
                'budget_provenance': 'frozen', 'mandatory_truncation': False}
        body = json.loads((root/'requests'/row['id']/'request.json').read_text())
        body['seed'] = 1
        body['stream_options'] = {'include_usage': True}
        # Match the actual frozen transformation and tokenizer calibration.
        runner.atomic(root/'requests'/row['id']/'request.json', body)
        row['request_sha256'] = runner.sha(runner.encode(body))
        with gzip.open(root/'requests'/row['id']/'raw.json.gz', 'rb') as f:
            raw = json.load(f)
        raw['request_sha256'] = row['request_sha256']
        self.persist(root/'requests'/row['id'], raw, row)
        runner.atomic(root/'calibration'/(row['id']+'.json'), {'chat_sha256':row['request_sha256'], 'response':{'input_tokens':275579}})
        receipt['existing_rejections'][row['id']] = runner.sha(runner.encode(row))
        (root/'pi-private').mkdir()
        runner.atomic(root/'pi-private/wire.json', body)
        case['payload_sha256'] = runner.sha((root/'pi-private/wire.json').read_bytes())
        obj.manifest = {'pi_cases':[case], 'priority_ids':[], 'pi_seed':1, 'pi_qualification':'fixture'}
        obj.status = {'manifest_sha256':'manifest'}
        obj.request, obj.count, obj.resolve, obj.report = Mock(), Mock(return_value=275579), Mock(), Mock()
        return obj, body

    def test_recovery_reuses_existing_row_without_request_or_count_and_retains_gaps(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _, _, row = self.fixture(root)
            obj, _ = self.make_collector(root, row)
            obj.collect_pi(False)
            obj.request.assert_not_called()
            obj.count.assert_not_called()
            obj.resolve.assert_called_once_with(row['id'], root, row)
            self.assertEqual(json.loads((root/'capacity-outcomes.json').read_text())['outcomes'][row['id']]['original_failures_retained'], row['failures'])

    def test_future_oversized_uses_expected400_and_full_budget_but_validates_response(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _, _, row = self.fixture(root)
            obj, body = self.make_collector(root, row)
            obj.results = {}
            row['failures'] = []
            runner.atomic(root/'requests'/row['id']/'record.json', row)
            obj.request.return_value = row
            obj.collect_pi(False)
            self.assertEqual(obj.request.call_args.kwargs['expected_status'], 400)
            self.assertEqual(obj.request.call_args.args[1]['max_tokens'], 32768)
            row['http_status'] = 500
            with self.assertRaises(RuntimeError):
                obj.collect_pi(False)

    def test_unlisted_old_rejection_fails_without_resend(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _, _, row = self.fixture(root)
            obj, _ = self.make_collector(root, row)
            row['failures'].append('TRANSPORT_ERROR')
            with self.assertRaises(RuntimeError):
                obj.collect_pi(False)
            obj.request.assert_not_called()

    def test_receipt_requires_original_bundle_manifest_drain_and_wrapper_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bundle = root/'bundle'
            bundle.mkdir()
            for name in ['runner.py', 'slim_runner.py', 'slim_plan.py', 'guardian.py']:
                (bundle/name).write_text('# frozen fixture\n')
            runner.atomic(root/'manifest.json', {'execution_plan':'slim_reference_v1'})
            runner.atomic(root/'drain.json', {'unresolved':[]})
            digest = lambda p: runner.sha(p.read_bytes())
            receipt = {'schema_version':1, 'lane_drained':True,
                       'wrapper_sha256':digest(Path(recovery.__file__)),
                       'manifest_sha256':digest(root/'manifest.json'),
                       'bundle_sha256':{p.name:digest(p) for p in bundle.iterdir()},
                       'drain':{'path':str(root/'drain.json'), 'sha256':digest(root/'drain.json')},
                       'existing_rejections':{'pi-fixture':'record-digest'}}
            target = root/'receipt.json'
            runner.atomic(target, receipt)
            # The fixture module is inert; successful import retains its original __file__.
            original_path = list(recovery.sys.path)
            try:
                module, validated = recovery.load_recovery(bundle, root, target)
                self.assertEqual(Path(module.__file__), bundle/'slim_runner.py')
                self.assertEqual(validated['receipt_sha256'], digest(target))
                for field, value in [('lane_drained', False), ('wrapper_sha256','wrong'),
                                     ('manifest_sha256','wrong'), ('existing_rejections',{})]:
                    bad = {**receipt, field:value}
                    runner.atomic(target, bad)
                    with self.assertRaises(RuntimeError):
                        recovery.load_recovery(bundle, root, target)
                runner.atomic(target, receipt)
                (bundle/'runner.py').write_text('# changed\n')
                with self.assertRaisesRegex(RuntimeError, 'bundle changed'):
                    recovery.load_recovery(bundle, root, target)
            finally:
                recovery.sys.path[:] = original_path

    def test_wrapper_strips_new_arguments_before_delegating_original_main(self):
        fake = Mock()
        fake.__file__ = '/frozen/slim_runner.py'
        with patch.object(recovery, 'load_recovery', return_value=(fake, {})), \
             patch.object(recovery.sys, 'argv', ['wrapper', '--root', '/root', '--stage', 'remaining',
                          '--frozen-bundle', '/frozen', '--recovery-receipt', '/receipt']):
            recovery.main()
            self.assertEqual(recovery.sys.argv, ['/frozen/slim_runner.py', '--root', '/root', '--stage', 'remaining'])
            fake.main.assert_called_once()

    def test_original_guardian_root_stage_only_arguments_use_versioned_fixed_paths(self):
        fake = Mock()
        fake.__file__ = '/frozen/slim_runner.py'
        with patch.object(recovery, 'load_recovery', return_value=(fake, {})) as load, \
             patch.object(recovery.sys, 'argv', ['wrapper', '--root', '/home/task/slim-v1', '--stage', 'remaining']):
            recovery.main()
            root = Path('/home/task/slim-v1').resolve()
            load.assert_called_once_with(Path(recovery.__file__).resolve().parent.parent/'slim-bin-v1', root,
                                         root/'recovery-capacity-v2/receipt.json')
            fake.main.assert_called_once()


if __name__ == '__main__':
    unittest.main()
