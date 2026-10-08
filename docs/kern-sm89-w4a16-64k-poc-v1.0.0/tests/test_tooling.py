import hashlib, json, math, struct, tempfile, unittest
from pathlib import Path
from poc_tools.core import memory_budget, sse_events, collect_stream, read_safetensors_header, check_poc_manifest, evaluate_evidence, resolve_constants, safe_relative

class MemoryTests(unittest.TestCase):
    def test_bf16_64k(self):
        r=memory_budget(16*2**30,65536,kv_bits=16,slots=4,workspace_bytes=2**30,headroom_bytes=2**30)
        self.assertEqual(r['kv_bytes'],4*2**30)
        self.assertTrue(r['fits'])
    def test_output_pool_is_included(self):
        r=memory_budget(16*2**30,73728,kv_bits=16,slots=4,workspace_bytes=2**30,headroom_bytes=2**30)
        self.assertEqual(r['kv_bytes'],int(4.5*2**30))
    def test_overbudget(self):
        self.assertFalse(memory_budget(20*2**30,73728)['fits'])
    def test_negative(self):
        with self.assertRaises(ValueError): memory_budget(-1,65536)
    def test_group_metadata(self):
        self.assertGreater(memory_budget(1,65536,kv_bits=4,kv_meta_bytes_per_token=128)['kv_bytes'],65536*16384)
    def test_invalid_bit(self):
        with self.assertRaises(ValueError):memory_budget(1,1,kv_bits=3)

class SseTests(unittest.TestCase):
    def test_split_frames_and_utf8(self):
        data=':comment\n\ndata: {"x":"汉字"}\n\ndata: [DONE]\n\n'.encode()
        self.assertEqual(list(sse_events([data[i:i+1] for i in range(len(data))])),[{'x':'汉字'},'[DONE]'])
    def test_crlf_multiline(self):
        self.assertEqual(list(sse_events([b'data: {\r\ndata: "a":1}\r\n\r\n'])),[{'a':1}])
    def test_bad_json(self):
        with self.assertRaises(ValueError):list(sse_events([b'data: {bad}\n\n']))
    def test_incomplete_stream(self):
        r=collect_stream([(0.1,{'choices':[{'delta':{'content':'a'}}]})],1.0)
        self.assertEqual(r['status'],'INCOMPLETE')
    def test_usage_not_event_count(self):
        events=[(0.1,{'choices':[{'delta':{'role':'assistant'}}]}),
          (0.2,{'choices':[{'delta':{'reasoning_content':'think'}}]}),
          (0.3,{'choices':[{'delta':{'content':'abc'}}]}),
          (0.4,{'choices':[{'delta':{},'finish_reason':'stop'}]}),
          (0.5,{'choices':[],'usage':{'prompt_tokens':65536,'completion_tokens':77}}),(0.6,'[DONE]')]
        r=collect_stream(events,0.7)
        self.assertEqual(r['output_tokens'],77);self.assertEqual(r['ttft_s'],0.2)
        self.assertIsNone(r['server_decode_tps'])
        self.assertEqual(r['status'],'COMPLETE')
    def test_error_object(self):
        r=collect_stream([(0.1,{'error':{'message':'failure'}}),(0.2,'[DONE]')],0.3)
        self.assertEqual(r['status'],'ERROR')
    def test_no_usage_not_zero(self):
        r=collect_stream([(0.1,{'choices':[{'text':'a','finish_reason':'stop'}]}),(0.2,'[DONE]')],0.2)
        self.assertIsNone(r['output_tokens'])
    def test_early_toolcall(self):
        r=collect_stream([(0.15,{'choices':[{'delta':{'tool_calls':[{'function':{'arguments':'{'}}]}}]}),(0.2,'[DONE]')],0.3)
        self.assertEqual(r['ttft_s'],0.15)

class HeaderTests(unittest.TestCase):
    def make(self,root,header,payload=b'1234'):
        raw=json.dumps(header).encode();p=root/'t.safetensors';p.write_bytes(struct.pack('<Q',len(raw))+raw+payload);return p
    def test_good(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.make(Path(d),{'w':{'dtype':'I32','shape':[1],'data_offsets':[0,4]}})
            self.assertEqual(read_safetensors_header(p)['w']['stored_bytes'],4)
    def test_truncated(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.make(Path(d),{'w':{'dtype':'I32','shape':[2],'data_offsets':[0,8]}})
            with self.assertRaises(ValueError):read_safetensors_header(p)
    def test_overlap(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.make(Path(d),{k:{'dtype':'I32','shape':[1],'data_offsets':[0,4]} for k in ['a','b']})
            with self.assertRaises(ValueError):read_safetensors_header(p)
    def test_duplicate_key(self):
        with tempfile.TemporaryDirectory() as d:
            raw=b'{"w":{},"w":{}}';p=Path(d)/'x';p.write_bytes(struct.pack('<Q',len(raw))+raw)
            with self.assertRaises(ValueError):read_safetensors_header(p)
    def test_header_limit(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x';p.write_bytes(struct.pack('<Q',2**40))
            with self.assertRaises(ValueError):read_safetensors_header(p)
    def test_escape(self):
        with self.assertRaises(ValueError):safe_relative('../secret')

class ManifestTests(unittest.TestCase):
    def base(self):return {'schema_version':4,'vars':{'tokens':{'max':512}},'states':{},'ops':{'x':{'impl':{'launches':[{'module':'m','entry':'x','block':[128,1,1],'grid':[1,1,1]}]}}},'modules':{'m':{'source':'x.cubin','sha256':'a'*64}}}
    def test_ok(self):self.assertEqual(check_poc_manifest(self.base()),[])
    def test_pdl(self):
        m=self.base();m['ops']['x']['impl']['launches'][0]['pdl']=True
        self.assertTrue(check_poc_manifest(m))
    def test_cluster(self):
        m=self.base();m['ops']['x']['impl']['launches'][0]['cluster']=[2,1,1]
        self.assertTrue(check_poc_manifest(m))
    def test_tma(self):
        m=self.base();m['ops']['x']['impl']['launches'][0]['args']=[{'pack':{'tensormap':{}}}]
        self.assertTrue(check_poc_manifest(m))
    def test_smem(self):
        m=self.base();m['ops']['x']['impl']['launches'][0]['shared_mem']=120*1024
        self.assertTrue(check_poc_manifest(m))
    def test_huge_workspace_symbol(self):
        m=self.base();m['vars']['tokens']['max']=4096
        self.assertTrue(check_poc_manifest(m))
    def test_constants(self):
        m={'constants':{'N':512},'vars':{'tokens':{'max':'N'}}}
        self.assertEqual(resolve_constants(m)['vars']['tokens']['max'],512)
    def test_unknown_expression(self):
        m=self.base();m['ops']['x']['impl']['launches'][0]['shared_mem']={'unknown':[1,2]}
        self.assertTrue(check_poc_manifest(m))

class EvidenceTests(unittest.TestCase):
    def test_empty_blocks(self):self.assertEqual(evaluate_evidence({})['decision'],'BLOCKED')
    def test_failure_wins(self):
        self.assertEqual(evaluate_evidence({'gates':{'numeric':{'status':'FAIL'}}})['decision'],'NO_GO')
    def test_mock_not_real(self):
        self.assertEqual(evaluate_evidence({'hardware_verified':False})['decision'],'BLOCKED')
    def test_missing_evidence_file(self):
        data={'hardware_verified':True,'device_cc':'8.9','run_id':'x','profile':'p0-bf16-kv','model_sha256':'a'*64,'kern_commit':'b'*40,'gates':{k:{'status':'PASS','evidence':[]} for k in ['environment','artifact','numeric','context64k','cache','java','lifecycle','performance']}}
        self.assertNotEqual(evaluate_evidence(data)['decision'],'POC_GO')
    def test_no_draft_tokens_as_output(self):
        self.assertNotEqual(evaluate_evidence({'gates':{'performance':{'status':'PASS','count_basis':'draft'}}})['decision'],'POC_GO')

if __name__=='__main__': unittest.main()
