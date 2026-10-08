import json,tempfile,unittest
from pathlib import Path
from tools.http_probe import SSEDecoder
from tools.runner import validate_plan
class SSETests(unittest.TestCase):
    def test_fragmented_utf8(self):
        raw=('data: '+json.dumps({'text':'汉字'},ensure_ascii=False)+'\n\n'+'data: [DONE]\n\n').encode()
        dec=SSEDecoder(); out=[]
        for b in raw: out+=dec.feed(bytes([b]))
        self.assertEqual(out,[{'text':'汉字'},'[DONE]'])
    def test_crlf(self):
        self.assertEqual(SSEDecoder().feed(b'data: {"a":1}\r\n\r\n'),[{'a':1}])
    def test_comment(self): self.assertEqual(SSEDecoder().feed(b': ping\n\n'),[])
    def test_bad(self):
        with self.assertRaises(ValueError): SSEDecoder().feed(b'data: not-json\n\n')
class PlanTests(unittest.TestCase):
    def test_not_ready(self):
        with self.assertRaises(ValueError):validate_plan({'ready':False})
    def test_missing_stages(self):
        with self.assertRaises(ValueError):validate_plan({'ready':True,'run_id':'abc','budget_sec':3600,'stages':[]})
    def test_no_shell_string(self):
        d={'ready':True,'run_id':'abc','budget_sec':3600,'stages':[{'id':'a','argv':'echo done','cwd':'/tmp','timeout_sec':10,'required_evidence':['/tmp/no']} ]}
        with self.assertRaises(ValueError):validate_plan(d)
    def test_invalid_id(self):
        with self.assertRaises(ValueError):validate_plan({'ready':True,'run_id':'../bad','budget_sec':30,'stages':[]})
    def test_valid(self):
        with tempfile.TemporaryDirectory() as td:
            d={'ready':True,'run_id':'abc','budget_sec':3600,'stages':[{'id':'a','argv':['python3','-V'],'cwd':td,'timeout_sec':10,'required_evidence':[td+'/report.json']}]}
            validate_plan(d)
if __name__=='__main__':unittest.main()
