import gzip
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from runner import atomic, encode, sha
from slim_runner import intact
from slim_protocol_option_recovery import ERROR, validate_rejection, recovery_class

BASE = SimpleNamespace(atomic=atomic, encode=encode, sha=sha, intact=intact)


def saved(root, stream=False, mutation=None):
    ident = 'protocol-responses-'+str(stream)
    body = {'model':'openclaw/Qwen3.8-27B-WORK','input':'用中文回答1+1等于几？',
            'max_output_tokens':128,'stream':stream,'chat_template_kwargs':{'enable_thinking':False}}
    text = json.dumps({'error':ERROR})
    raw = {'http_status':400,'request_sha256':sha(encode(body)),'response_request_id':'response-id',
           'error':None,'intentional_disconnect':False,'lines':[],'server_events':[],'observation_errors':[],
           'body':text,'headers':{'Content-Length':str(len(text.encode()))}}
    raw.update(mutation or {})
    directory=root/'requests'/ident;directory.mkdir(parents=True,exist_ok=True)
    (directory/'request.json').write_bytes(encode(body));(directory/'raw.json.gz').write_bytes(gzip.compress(encode(raw)))
    row={'id':ident,'group':'protocol','http_status':raw['http_status'],'response_request_id':'response-id',
         'foreign_requests_during_interval':0,'failures':[] if stream else ['HTTP_STATUS','MISSING_REQUEST_DONE'],
         'request_sha256':sha(encode(body)),'raw_sha256':sha((directory/'raw.json.gz').read_bytes())}
    (directory/'record.json').write_bytes(encode(row))
    return row,body


class ProtocolOptionRecoveryTest(unittest.TestCase):
    def test_complete_specific_rejection_keeps_failure_and_coverage_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);row,body=saved(root);before=(root/'requests'/row['id']/'record.json').read_bytes()
            proof=validate_rejection(BASE,root,row,body)
            self.assertFalse(proof['successful_responses_protocol_coverage'])
            self.assertFalse(proof['performance_sample_eligible'])
            self.assertFalse(proof['request_resent'])
            self.assertEqual(before,(root/'requests'/row['id']/'record.json').read_bytes())

    def test_other_errors_truncation_transport_or_admission_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for mutation in [{'body':'{"error":{}}'}, {'headers':{'Content-Length':'1'}},
                             {'error':'timeout'}, {'http_status':500}, {'server_events':[{'event':'request_start'}]}]:
                row,body=saved(root,mutation=mutation)
                with self.subTest(mutation=mutation),self.assertRaises(RuntimeError):
                    validate_rejection(BASE,root,row,body)

    def test_future_stream_request_is_sent_unchanged_once_and_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);row,body=saved(root,stream=True);calls=[]
            class Parent:
                def request(self,case,request,**kwargs):
                    calls.append((case,request,kwargs));return row
            cls=recovery_class(BASE,Parent,{'receipt_sha256':'receipt'})
            runner=cls.__new__(cls);runner.root=root;runner.results={};runner.status={'manifest_sha256':'manifest'}
            runner.request(row['id'],body,group='protocol',path='/v1/responses')
            self.assertEqual(len(calls),1);self.assertIs(calls[0][1],body)
            self.assertEqual(calls[0][2]['expected_status'],400)
            self.assertTrue((root/'protocol-option-rejections-v5.json').exists())

    def test_completed_request_never_sent_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);row,body=saved(root,stream=True)
            class Parent:
                def request(self,*args,**kwargs):raise AssertionError('unexpected HTTP')
            cls=recovery_class(BASE,Parent,{'receipt_sha256':'receipt'})
            runner=cls.__new__(cls);runner.root=root;runner.results={row['id']:row};runner.status={'manifest_sha256':'manifest'}
            self.assertIs(runner.request(row['id'],body),row)
            self.assertTrue((root/'protocol-option-rejections-v5.json').exists())

    def test_stored_unexpected_true_response_cannot_bypass_validation_on_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);row,body=saved(root,stream=True,mutation={'http_status':500})
            class Parent:
                def request(self,*args,**kwargs):raise AssertionError('no resend')
            cls=recovery_class(BASE,Parent,{'receipt_sha256':'receipt'})
            runner=cls.__new__(cls);runner.root=root;runner.results={row['id']:row}
            with self.assertRaisesRegex(RuntimeError,'intact frozen'):
                runner.request(row['id'],body)


if __name__=='__main__':unittest.main()
