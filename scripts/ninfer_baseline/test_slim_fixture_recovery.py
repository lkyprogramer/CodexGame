import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import runner
import slim_runner as base
import slim_capacity_recovery as prior
import slim_fixture_recovery as recovery


class FixtureTests(unittest.TestCase):
    def fixture(self, root, arguments='{"broken":'):
        body = {"messages": [{"role":"assistant", "tool_calls":[{"type":"function", "function":{
            "name":"fixture", "arguments":arguments}}]}], "max_tokens":32768,
            "stream":True, "stream_options":{"include_usage":True}, "seed":1}
        ident = 'pi-fixture'
        directory = root/'requests'/ident
        directory.mkdir(parents=True)
        runner.atomic(directory/'request.json', body)
        (root/'pi-private').mkdir()
        runner.atomic(root/'pi-private/wire.json', body)
        raw = {'http_status':400, 'error':None, 'response_request_id':None, 'intentional_disconnect':False,
               'lines':[], 'server_events':[], 'observation_errors':[],
               'request_sha256':runner.sha(runner.encode(body)),
               'body':json.dumps({'error':recovery.ERROR}, separators=(',', ':'))}
        raw['headers'] = {'Content-Length': str(len(raw['body'].encode()))}
        row = {'id':ident,'group':'pi_teacher_forced','requested_output_tokens':32768,
               'http_status':400,'response_request_id':None,'foreign_requests_during_interval':0,
               'failures':sorted(prior.EXPECTED_OLD_GAPS),'request_sha256':raw['request_sha256'],
               'extra':{'projected_count':None,'count_projection_error':'JSONDecodeError: fixture'}}
        self.persist(directory, row, raw)
        return body, row, raw

    def persist(self, directory, row, raw):
        with gzip.open(directory/'raw.json.gz', 'wb') as stream:
            stream.write(runner.encode(raw))
        row['raw_sha256'] = runner.sha((directory/'raw.json.gz').read_bytes())
        runner.atomic(directory/'record.json', row)

    def collector(self, root, row):
        old = {'existing_rejections':{},'receipt_sha256':'prior-receipt'}
        new = {'existing_rejections':{row['id']:runner.sha(runner.encode(row))},'receipt_sha256':'new-receipt'}
        cls = recovery.recovery_class(base, prior, old, new)
        obj = cls.__new__(cls)
        obj.root, obj.results, obj.resolutions = root, {row['id']:row}, {}
        obj.status = {'manifest_sha256':'manifest'}
        obj.manifest = {'pi_cases':[{'id':'fixture','payload_file':'wire.json',
                        'payload_sha256':runner.sha((root/'pi-private/wire.json').read_bytes()),
                        'source_sha256':'source','entry_id':'entry','budget_provenance':'frozen',
                        'mandatory_truncation':False}], 'priority_ids':[], 'pi_seed':1,'pi_qualification':'frozen'}
        obj.request, obj.count, obj.resolve, obj.report = Mock(), Mock(side_effect=ValueError('malformed')), Mock(), Mock()
        return obj

    def test_static_proof_only_json_string_object_valid(self):
        for value in ['{}', '{"valid":1}']:
            body = {'messages':[{'role':'assistant','tool_calls':[{'type':'function','function':{'arguments':value}}]}]}
            self.assertEqual(recovery.invalid_arguments(body), [])
        for value, reason in [('[]','NON_OBJECT_ARGUMENTS'),('null','NON_OBJECT_ARGUMENTS'),
                              ('broken','INVALID_JSON_ARGUMENTS'),({},'NON_STRING_ARGUMENTS')]:
            body['messages'][0]['tool_calls'][0]['function']['arguments'] = value
            self.assertEqual(recovery.invalid_arguments(body),[{'message_index':0,'tool_index':0,'reason':reason}])

    def test_existing_complete_rejection_reuses_without_resend_or_rewrite_prior_overlay(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            body, row, raw = self.fixture(root)
            prior_overlay = root/'capacity-outcomes.json'
            prior_overlay.write_text('{"prior":"preserved"}')
            before = {str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            obj = self.collector(root,row)
            obj.collect_pi(False)
            obj.request.assert_not_called()
            obj.count.assert_not_called()
            obj.resolve.assert_called_once_with(row['id'],root,row)
            for name, value in before.items():
                self.assertEqual(Path(name).read_bytes(), value)
            outcome = json.loads((root/'fixture-rejections-v3.json').read_text())['outcomes'][row['id']]
            self.assertEqual(outcome['outcome'],'INVALID_FROZEN_TOOL_ARGUMENTS')
            self.assertFalse(outcome['performance_sample_eligible'])
            self.assertEqual(outcome['original_failures_retained'],row['failures'])

    def test_future_malformed_expected400_preserves_budget_then_validates_actual(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            body,row,raw = self.fixture(root)
            obj = self.collector(root,row)
            obj.results = {}
            row['failures'] = []
            self.persist(root/'requests'/row['id'],row,raw)
            obj.request.return_value = row
            obj.collect_pi(False)
            self.assertEqual(obj.request.call_args.kwargs['expected_status'],400)
            self.assertEqual(obj.request.call_args.args[1],body)
            self.assertEqual(obj.request.call_args.args[1]['max_tokens'],32768)

    def test_valid_fixture_cannot_be_reclassified_and_raw_error_variants_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            body,row,raw = self.fixture(Path(d),'{}')
            with self.assertRaises(RuntimeError):
                recovery.validate_fixture(base,prior,Path(d),row,body)
        mutations = [lambda r:r.update(error='timeout'),lambda r:r.update(http_status=500),
                     lambda r:r.update(body=json.dumps({'error':{**recovery.ERROR,'message':'other'}})),
                     lambda r:r.update(body=json.dumps({'error':{**recovery.ERROR,'code':'other'}})),
                     lambda r:r.update(server_events=[{'event':'request_done'}]),
                     lambda r:r.update(headers={'Content-Length':'999'}),
                     lambda r:r.update(lines=[{'line':'data: [DONE]'}])]
        for mutate in mutations:
            with self.subTest(mutation=mutate), tempfile.TemporaryDirectory() as d:
                root=Path(d)
                body,row,raw=self.fixture(root)
                mutate(raw)
                self.persist(root/'requests'/row['id'],row,raw)
                with self.assertRaises(RuntimeError):
                    recovery.validate_fixture(base,prior,root,row,body)

    def test_unapproved_row_never_retried(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            body,row,raw=self.fixture(root)
            obj=self.collector(root,row)
            row['failures'].append('TRANSPORT_ERROR')
            with self.assertRaises(RuntimeError):
                obj.collect_pi(False)
            obj.request.assert_not_called()

    def test_guardian_only_args_resolve_versioned_receipt_and_original_main(self):
        fake=Mock()
        fake.__file__='/frozen/slim_runner.py'
        with patch.object(recovery,'load_recovery',return_value=(fake,prior,{'existing_rejections':{}}, {'existing_rejections':{}})) as load, \
             patch.object(recovery.sys,'argv',['wrapper','--root','/home/task/slim-v1','--stage','remaining']):
            recovery.main()
            root=Path('/home/task/slim-v1').resolve()
            load.assert_called_once_with(root.parent/'slim-bin-v1',root,root/'recovery-fixture-v3/receipt.json')
            self.assertEqual(recovery.sys.argv,['/frozen/slim_runner.py','--root','/home/task/slim-v1','--stage','remaining'])
            fake.main.assert_called_once()

    def test_receipt_binds_v2_wrapper_receipt_new_drain_and_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            bundle=root/'bundle'
            bundle.mkdir()
            runner.atomic(root/'manifest.json',{'execution_plan':'slim_reference_v1'})
            runner.atomic(root/'old-receipt.json',{'fixture':'v2'})
            runner.atomic(root/'drain.json',{'unresolved':[]})
            old_wrapper=root/'prior.py'
            old_wrapper.write_text('def load_recovery(bundle, root, receipt):\n    return "original-base", {"receipt_sha256":"old"}\n')
            digest=lambda p:runner.sha(p.read_bytes())
            receipt={'schema_version':1,'lane_drained':True,
                     'wrapper_sha256':digest(Path(recovery.__file__)),
                     'manifest_sha256':digest(root/'manifest.json'),
                     'prior_wrapper':{'path':str(old_wrapper),'sha256':digest(old_wrapper)},
                     'prior_receipt':{'path':str(root/'old-receipt.json'),'sha256':digest(root/'old-receipt.json')},
                     'drain':{'path':str(root/'drain.json'),'sha256':digest(root/'drain.json')},
                     'existing_rejections':{'pi-fixture':'canonical-row-hash'}}
            target=root/'receipt.json'
            runner.atomic(target,receipt)
            result=recovery.load_recovery(bundle,root,target)
            self.assertEqual(result[0],'original-base')
            self.assertEqual(result[3]['receipt_sha256'],digest(target))
            for field in ['prior_wrapper','prior_receipt','drain']:
                bad=copy.deepcopy(receipt)
                bad[field]['sha256']='changed'
                runner.atomic(target,bad)
                with self.assertRaisesRegex(RuntimeError,'dependency changed'):
                    recovery.load_recovery(bundle,root,target)
            for field,value in [('lane_drained',False),('wrapper_sha256','changed'),
                                ('manifest_sha256','changed'),('existing_rejections',{})]:
                runner.atomic(target,{**receipt,field:value})
                with self.assertRaises(RuntimeError):
                    recovery.load_recovery(bundle,root,target)


if __name__=='__main__':
    unittest.main()
