"""Tests for docpack helpers only. These do not certify the NInfer product."""
from __future__ import annotations
import copy, hashlib, importlib, itertools, json, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT/'tools'))

def module(name):
    try:return importlib.import_module(name)
    except ImportError:return None

class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.m=module('scan_semantics'); self.assertIsNotNone(self.m,'scanner specification helper not implemented')
    def test_small_id_not_longest(self):
        toks=[(301,b'<x>tail'),(300,b'<x>')]
        self.assertEqual(self.m.forward(b'<x>tail',toks)[0],[(0,3,300)])
    def test_leftmost_before_lower_id(self):
        self.assertEqual(self.m.forward(b'ab----cd',[(10,b'cd'),(20,b'ab')])[0][0],(0,2,20))
    def test_partial_marker(self):self.assertEqual(self.m.forward(b'<|im_sta',[(300,b'<|im_start|>')])[0],[])
    def test_adjacent_markers(self):self.assertEqual(len(self.m.forward(b'xxxx',[(300,b'xx')])[0]),2)
    def test_overlapping_markers(self):self.assertEqual(self.m.forward(b'ababa',[(300,b'aba'),(301,b'bab')])[0],[(0,3,300)])
    def test_empty(self):self.assertEqual(self.m.forward(b'',[(300,b'x')])[0],[])
    def test_empty_token_rejected(self):
        with self.assertRaises(ValueError):self.m.forward(b'a',[(300,b'')])
    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):self.m.forward(b'a',[(300,b'a'),(300,b'b')])
    def test_high_byte(self):self.assertEqual(self.m.forward(b'\xffx',[(300,b'\xff')])[0],[(0,1,300)])
    def test_all_cuts_lexical_model(self):
        toks=[(300,b'<x>'),(301,b'ab'),(302,b'aba')]
        for n in range(6):
            for chars in itertools.product(b'ab<>',repeat=n):
                d=bytes(chars)
                self.assertEqual(self.m.legacy(d,toks),self.m.forward(d,toks)[0])
                self.assertTrue(self.m.check_prefix_decomposition(d,toks))
    def test_scan_work_bounded(self):
        data=(b'<x>abc'*100)+b'q'*100
        _,w=self.m.forward(data,[(300,b'<x>'),(301,b'<absent>')])
        self.assertLessEqual(w['positions_visited'],len(data))
    def test_report_example_not_prefix(self):self.assertFalse(b'<tts_text_bos_single>'.startswith(b'<tts_text_bos>'))
    def test_random_seed_deterministic(self):self.assertEqual(self.m.random_check(7,200),self.m.random_check(7,200))

class GeneratorTests(unittest.TestCase):
    def setUp(self):self.m=module('generate_sessions');self.assertIsNotNone(self.m,'production-shaped generator not implemented')
    def recipe(self):return {'id':'test','messages':35,'turns_since_last_user':5,'history_user_every':8,'tool_bytes':128,'reasoning_bytes':64,'rounds':3,'tools':12,'seed':37}
    def test_deterministic(self):self.assertEqual(self.m.build_case(self.recipe()),self.m.build_case(self.recipe()))
    def test_recent_turns_exact(self):
        rows=self.m.build_case(self.recipe())
        for i,r in enumerate(rows):self.assertEqual(self.m.recent_assistant_count(r['request']['messages']),5+i)
    def test_message_count(self):self.assertEqual(len(self.m.build_case(self.recipe())[0]['request']['messages']),35)
    def test_hist_user_no_override(self):
        r=self.recipe();r['history_user_every']=1
        self.assertEqual(self.m.recent_assistant_count(self.m.build_case(r)[0]['request']['messages']),5)
    def test_request_hash(self):
        r=self.m.build_case(self.recipe())[0]
        self.assertEqual(r['input_sha256'],self.m.request_hash(r['request']))
    def test_unmeasured(self):self.assertEqual(self.m.build_case(self.recipe())[0]['token_count_status'],'UNMEASURED')
    def test_insufficient_messages(self):
        r=self.recipe();r['messages']=3
        with self.assertRaises(ValueError):self.m.build_case(r)
    def test_user_tool_wrapper_not_real(self):
        messages=[{'role':'user','content':'Q'},{'role':'assistant','content':'A'},{'role':'user','content':' <tool_response>x</tool_response> '}]
        self.assertEqual(self.m.recent_assistant_count(messages),1)
    def test_none_user_rejected(self):
        with self.assertRaises(ValueError):self.m.recent_assistant_count([{'role':'assistant','content':'x'}])

class CompareTests(unittest.TestCase):
    def setUp(self):self.m=module('compare_frontend_results');self.assertIsNotNone(self.m,'independent-output comparator not implemented')
    def row(self):return {'case_id':'x','input_sha256':'a'*64,'resources_sha256':'b'*64,'kind':'raw','status':'OK','semantic':{'token_ids':[1,2]}}
    def test_equal(self):self.assertEqual(self.m.compare([self.row()],[self.row()])['status'],'PASS')
    def test_token_mismatch(self):
        a=self.row();b=copy.deepcopy(a);b['semantic']['token_ids'][1]=3
        self.assertEqual(self.m.compare([a],[b])['status'],'FAIL')
    def test_missing_field(self):
        r=self.row();r['semantic']={}
        with self.assertRaises(ValueError):self.m.compare([r],[r])
    def test_duplicate(self):
        with self.assertRaises(ValueError):self.m.compare([self.row(),self.row()],[self.row()])
    def test_missing_pair(self):
        with self.assertRaises(ValueError):self.m.compare([self.row()],[])
    def test_identity_changed(self):
        b=self.row();b['resources_sha256']='c'*64
        with self.assertRaises(ValueError):self.m.compare([self.row()],[b])
    def test_error_exact(self):
        a=self.row();a.pop('semantic');a['status']='ERROR';a['error']={'phase':'boundary','class':'logic_error','message':'stable prefix is not an exact token prefix'}
        self.assertEqual(self.m.compare([a],[a])['status'],'PASS')
        b=copy.deepcopy(a);b['error']['message']='different'
        self.assertEqual(self.m.compare([a],[b])['status'],'FAIL')
    def test_failure_redacts_values(self):
        a=self.row();b=self.row();b['semantic']['token_ids']=[99]
        result=json.dumps(self.m.compare([a],[b]))
        self.assertNotIn('99',result)
    def test_empty_not_pass(self):
        with self.assertRaises(ValueError):self.m.compare([],[])

class LogTests(unittest.TestCase):
    def setUp(self):self.m=module('analyze_logs');self.assertIsNotNone(self.m,'metadata-only log analyzer not implemented')
    def row(self,id='1',end=10000,total=4.0):return {'schema_version':20,'event':'request_done','server_instance_id':'s','timestamp_unix_ms':end,'request':{'id':id,'message_count':4,'tool_count':12,'rendered_chars':1000},'result':{'prompt_tokens':100000,'prefix_cache_hit_tokens':99900,'prefix_reuse_path':'append_frontier','completion_tokens':10,'finish_reason':'stop_token'},'prepare_detail':{'tokenize':1.0,'template_render':.01},'timings_seconds':{'prepare':1.01,'prefill':.1,'ttft':1.2,'total':total,'decode':.1}}
    def test_dedup(self):
        r=self.row();out=self.m.summarize([r,r]);self.assertEqual(out['requests'],1);self.assertEqual(out['duplicate_records'],1)
    def test_duplicate_conflict(self):
        a=self.row();b=self.row();b['result']['prompt_tokens']=10
        with self.assertRaises(ValueError):self.m.summarize([a,b])
    def test_interval_union(self):
        out=self.m.summarize([self.row('1',10000,4),self.row('2',11000,3)])
        self.assertEqual(out['summed_request_seconds'],7);self.assertEqual(out['request_interval_union_seconds'],5);self.assertEqual(out['observed_span_seconds'],5)
    def test_start_is_first_end_minus_first_duration(self):
        out=self.m.summarize([self.row('1',10000,8),self.row('2',20000,1)])
        self.assertEqual(out['observed_span_seconds'],18)
    def test_zero_prompt(self):
        r=self.row();r['result']['prompt_tokens']=0;r['result']['prefix_cache_hit_tokens']=0
        self.assertEqual(self.m.summarize([r])['requests'],1)
    def test_missing_tokenize_not_zero(self):
        r=self.row();r['prepare_detail']={};o=self.m.summarize([r]);self.assertIsNone(o['tokenize']['sum']);self.assertEqual(o['tokenize']['n'],0)
    def test_wrong_schema_not_mixed(self):
        r=self.row();r['schema_version']=19
        self.assertEqual(self.m.summarize([r])['requests'],0)
    def test_no_reset_causal_inference(self):
        r=self.row();r['result']['prefix_reuse_path']='full_reset';r['result']['prefix_cache_hit_tokens']=0
        o=self.m.summarize([r]);self.assertEqual(o['reset_cause_status'],'UNCLASSIFIED_METADATA_ONLY')
    def test_nonfinite_rejected(self):
        r=self.row();r['prepare_detail']['tokenize']=float('nan')
        with self.assertRaises(ValueError):self.m.summarize([r])
    def test_type7(self):self.assertEqual(self.m.stats([1.,2.,3.,4.])['p50'],2.5)

class AuditTests(unittest.TestCase):
    def setUp(self):self.m=module('audit_review_assets');self.assertIsNotNone(self.m,'review evidence audit helper not implemented')
    def test_counts(self):
        o=self.m.audit(ROOT/'evidence/review-assets');self.assertEqual(o['session_rows'],28);self.assertEqual(o['raw_rows'],4)
    def test_b0_not_retained(self):self.assertEqual(self.m.audit(ROOT/'evidence/review-assets')['b0_retained_rows'],0)
    def test_reference_is_not_independent(self):self.assertGreater(self.m.audit(ROOT/'evidence/review-assets')['indirect_reference_rows'],0)
    def test_over_context(self):self.assertEqual(self.m.audit(ROOT/'evidence/review-assets')['over_context_rows'],12)

class ResourceTests(unittest.TestCase):
    def setUp(self):self.m=module('resource_fingerprint');self.assertIsNotNone(self.m,'resource fingerprint helper not implemented')
    def test_six_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            for name in self.m.NAMES:(Path(d)/name).write_bytes(name.encode())
            result=self.m.fingerprint(Path(d));self.assertEqual(len(result['files']),6)
            self.assertEqual(result['files']['tokenizer.json']['sha256'],hashlib.sha256(b'tokenizer.json').hexdigest())
    def test_missing_resource(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):self.m.fingerprint(Path(d))
    def test_raw_bytes_not_reformatted(self):
        with tempfile.TemporaryDirectory() as d:
            for name in self.m.NAMES:(Path(d)/name).write_bytes(b'{}\n')
            a=self.m.fingerprint(Path(d));(Path(d)/'tokenizer.json').write_bytes(b'{}')
            self.assertNotEqual(a['resources_sha256'],self.m.fingerprint(Path(d))['resources_sha256'])

if __name__=='__main__':unittest.main()
