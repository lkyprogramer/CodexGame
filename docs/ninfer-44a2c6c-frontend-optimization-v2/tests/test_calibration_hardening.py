from __future__ import annotations
import hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import calibrate_fixtures as c

def pair():
    req={'messages':[{'role':'user','content':'a'}]}
    h=hashlib.sha256(json.dumps(req,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    a={'case_id':'x','input_sha256':h,'request':req}
    b={'case_id':'x','input_sha256':h,'resources_sha256':'b'*64,'prompt_tokens':10,'render_bytes':30,'checkpoint_hints':2,'boundary_queries':4}
    return a,b

class CalibrationHardening(unittest.TestCase):
    def test_payload_hash_verified(self):
        a,b=pair();a['request']['messages'][0]['content']='changed'
        with self.assertRaises(ValueError):c.calibrate([a],[b])
    def test_cpu_stress_not_http(self):
        a,b=pair();a['declared_use']='CPU_STRESS_NOT_PRODUCTION_REPRESENTATIVE'
        row=c.calibrate([a],[b])['cases'][0]
        self.assertFalse(row['http_eligible']);self.assertEqual(row['validation_use'],'CPU_ONLY_BY_POLICY')
    def test_resource_batch_consistency(self):
        a,b=pair();d,e=pair();d['case_id']=e['case_id']='y';e['resources_sha256']='c'*64
        with self.assertRaises(ValueError):c.calibrate([a,d],[b,e])
    def test_full_input_hash_required(self):
        a,b=pair();a.pop('request');a['input_sha256']=b['input_sha256']='short'
        with self.assertRaises(ValueError):c.calibrate([a],[b])
    def test_valid_payload(self):
        a,b=pair();self.assertTrue(c.calibrate([a],[b])['cases'][0]['http_eligible'])
if __name__=='__main__':unittest.main()
