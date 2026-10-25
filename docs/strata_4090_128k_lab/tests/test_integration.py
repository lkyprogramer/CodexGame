import json, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from lab import http
from lab.statistics import summarize
from lab.core import hash_obj
from lab.scoring import score

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_POST(self):
        b=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
        self.wfile.write(b': heartbeat\n\n')
        data=[{'choices':[{'delta':{'reasoning_content':'checking'}}]},
              {'choices':[{'delta':{'content':'O'}}]}, {'choices':[{'delta':{'content':'K'},'finish_reason':'stop'}]},
              {'choices':[],'usage':{'prompt_tokens':12,'completion_tokens':3},'timings':{'prompt_n':12,'cache_n':0,'predicted_ms':30,'predicted_per_second':100}}]
        for d in data:self.wfile.write(('data: '+json.dumps(d)+'\n\n').encode())
        self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()

class Integration(unittest.TestCase):
    def test_real_local_http_stream(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
        try:
            r=http.chat(f'http://127.0.0.1:{server.server_port}',{'messages':[],'max_tokens':4})
            self.assertEqual(r['text'],'OK');self.assertEqual(r['reasoning'],'checking');self.assertIsNone(r['error'])
            self.assertEqual(http.measurements(r)['generated_tokens'],3)
            self.assertTrue(score({'kind':'exact','expected':'OK'},r)['pass'])
        finally:server.shutdown();server.server_close();t.join()
    def test_failed_pair_is_visible_and_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);rows=[]
            for rnd in range(5):
                for arm,dt in [('base',10),('off',10),('on',8)]:
                    rows.append({'phase':'measured','round':rnd,'arm':arm,'case_id':'Q','group':'quality','request_sha256':'same',
                                 'metrics':{'wall_s':dt,'prompt_tokens':12},'score':{'pass':not(rnd==3 and arm=='on'),'reason':'test'}})
            (p/'requests.jsonl').write_text('\n'.join(json.dumps(x) for x in rows))
            report=summarize(p)
            self.assertEqual(report['decision'],'REJECT_OR_FIX');self.assertEqual(report['failures'],1)
            self.assertTrue(report['invalid_pairs']);self.assertTrue((p/'requests.csv').exists())
    def test_clean_pairs_remain_screening_only(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);rows=[]
            for rnd in range(5):
                for arm,dt in [('base',10),('off',10),('on',8)]:
                    rows.append({'phase':'measured','round':rnd,'arm':arm,'case_id':'Q','group':'quality','request_sha256':'same',
                                 'metrics':{'wall_s':dt,'prompt_tokens':12},'score':{'pass':True,'reason':'test'}})
            (p/'requests.jsonl').write_text('\n'.join(json.dumps(x) for x in rows))
            self.assertEqual(summarize(p)['decision'],'CANDIDATE_FOR_HOLDOUT_NOT_PRODUCTION')

if __name__=='__main__':unittest.main()
