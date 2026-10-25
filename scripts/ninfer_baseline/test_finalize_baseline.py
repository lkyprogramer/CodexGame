import json
from pathlib import Path
import tempfile
import unittest
import gzip
import hashlib
from unittest.mock import patch

import finalize_baseline as m


class FinalReportTest(unittest.TestCase):
    def test_aborted_and_fresh_attempt_costs_stay_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);collector=root/'remote/slim-v1/closed-loop-collector'
            headers=['google__gson-2158/repeat-1/ordinal-9','google__gson-2158/repeat-1/attempt-2/ordinal-9']
            records=[]
            canonical=lambda v:json.dumps(v,ensure_ascii=False,separators=(',',':')).encode()
            for i,header in enumerate(headers):
                d=collector/'requests'/str(i);d.mkdir(parents=True)
                body={'max_tokens':32768};(d/'request.json').write_text(json.dumps(body))
                (d/'raw.json.gz').write_bytes(gzip.compress(canonical({'parsed':{'tool_count':i+1}})))
                row={'id':str(i),'extra':{'local_case_header':header},'prompt_tokens':100*(i+1),
                     'completion_tokens':12 if i==0 else None,'result':{'prefix_cache_hit_tokens':80*(i+1)},
                     'elapsed_s':i+1,'raw_sha256':m.backup.digest(d/'raw.json.gz'),
                     'request_sha256':hashlib.sha256(canonical(body)).hexdigest()}
                (d/'record.json').write_text(json.dumps(row));records.append(row)
            (collector/'records.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
            audit={'records_sha256':m.backup.digest(collector/'records.jsonl'),
                   'groups':[{'header':h,'requests':1} for h in headers]}
            result=m.coding_metrics(root,audit)
            self.assertEqual(len(result),2)
            self.assertEqual(result[0]['total_tokens_sum'],112)
            self.assertEqual(result[1]['prompt_tokens_sum'],200)
            self.assertIsNone(result[1]['total_tokens_sum'])
            self.assertEqual([r['proposed_tool_calls'] for r in result],[1,2])
            (collector/'records.jsonl').write_text(json.dumps(records[0])+'\n')
            with self.assertRaisesRegex(RuntimeError,'frozen recovery audit'):
                m.coding_metrics(root,audit)

    def test_incomplete_reference_cannot_publish_a_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);snap=root/'snapshot';(snap/'remote/slim-v1').mkdir(parents=True)
            (snap/'remote/slim-v1/reference-report.json').write_text(json.dumps({'planned':278,'resolved':1,'pending':['missing'],'observations':[]}))
            (snap/'remote/slim-v1/manifest.json').write_text(json.dumps({'pairs':[],'pi_cases':[],'state_case_ids':[]}))
            out=root/'out';out.mkdir();evidence=root/'evidence'
            with patch.object(m,'EVIDENCE',evidence),patch.object(m,'OUT',out),patch.object(m.backup,'main',return_value={'root':str(snap)}):
                with self.assertRaisesRegex(RuntimeError,'incomplete'):
                    m.main()
            self.assertFalse((out/'FINAL-REPORT.md').exists())
            self.assertEqual(json.loads((evidence/'finalization-status.json').read_text())['state'],'FINALIZATION_NEEDS_ATTENTION')

    def test_verified_existing_report_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'out';out.mkdir();report=out/'FINAL-REPORT.md';report.write_text('completed report')
            prior={'state':'REPORT_READY_WITH_DISCLOSED_LIMITATIONS','report_sha256':m.backup.digest(report),
                   'artifact_hashes':{str(report):m.backup.digest(report)}}
            (root/'finalization-status.json').write_text(json.dumps(prior))
            with patch.object(m,'EVIDENCE',root),patch.object(m,'OUT',out),patch.object(m.backup,'main') as capture:
                self.assertEqual(m.main(),prior)
                capture.assert_not_called()

    def test_missing_companion_delivery_is_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'out';out.mkdir();report=out/'FINAL-REPORT.md';report.write_text('completed report')
            prior={'state':'REPORT_READY_WITH_DISCLOSED_LIMITATIONS','report_sha256':m.backup.digest(report),
                   'artifact_hashes':{str(report):m.backup.digest(report),str(out/'final-summary.json'):'missing'}}
            (root/'finalization-status.json').write_text(json.dumps(prior))
            with patch.object(m,'EVIDENCE',root),patch.object(m,'OUT',out),patch.object(m.backup,'main') as capture:
                with self.assertRaisesRegex(RuntimeError,'integrity'):
                    m.main()
                capture.assert_not_called()
            self.assertEqual(json.loads((root/'finalization-status.json').read_text())['state'],'FINALIZATION_NEEDS_ATTENTION')

    def test_record_integrity_rejects_tamper_and_keeps_null_metrics(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);directory=root/'remote/slim-v1/requests/request';directory.mkdir(parents=True)
            row={'id':'request','group':'core','failures':[],'timings_seconds':{},'elapsed_s':1}
            body={'max_tokens':32768};raw=b'original compressed bytes'
            encode=lambda v:json.dumps(v,ensure_ascii=False,separators=(',',':')).encode()
            (directory/'record.json').write_text(json.dumps(row));(directory/'request.json').write_text(json.dumps(body));(directory/'raw.json.gz').write_bytes(raw)
            observation={'logical_id':'logical','record':row,'evidence':{'source_root':m.REMOTE_PREFIX+'slim-v1','source_id':'request','mode':'COLLECTED','record_sha256':hashlib.sha256(encode(row)).hexdigest(),'raw_sha256':hashlib.sha256(raw).hexdigest(),'request_sha256':hashlib.sha256(encode(body)).hexdigest()}}
            m.verify_observation(root,observation)
            self.assertIsNone(m.metric_row(observation)['decode_tokens_per_s'])
            (directory/'raw.json.gz').write_bytes(b'changed')
            with self.assertRaisesRegex(RuntimeError,'raw hash'):
                m.verify_observation(root,observation)
