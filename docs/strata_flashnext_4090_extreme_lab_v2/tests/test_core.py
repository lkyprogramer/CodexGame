import importlib, json, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class CoreTests(unittest.TestCase):
    def module(self, name):
        self.assertTrue((ROOT/'lab'/f'{name}.py').exists(), f'{name} implementation is missing')
        return importlib.import_module('lab.'+name)

    def test_context_accepts_reserved_output(self):
        m=self.module('core'); m.check_budget(122880,4096,131072,4096)
    def test_context_rejects_full_input_plus_output(self):
        m=self.module('core')
        with self.assertRaises(ValueError): m.check_budget(131072,1,131072,0)
    def test_context_rejects_above_hardware_limit(self):
        m=self.module('core')
        with self.assertRaises(ValueError): m.check_budget(5,5,262144,0)
    def test_context_rejects_unlimited_output(self):
        m=self.module('core')
        for n in [0,-1,True]:
            with self.assertRaises(ValueError): m.check_budget(20,n,131072,100)
    def test_only_loopback_is_allowed(self):
        m=self.module('core')
        m.loopback_url('http://127.0.0.1:18089')
        with self.assertRaises(ValueError): m.loopback_url('http://example.com:8080')
    def test_workspace_cannot_overlap_production(self):
        m=self.module('core')
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); (p/'prod').mkdir()
            with self.assertRaises(ValueError): m.check_separate(p/'prod/lab',p/'prod')
            with self.assertRaises(ValueError): m.check_separate(p,p/'prod')
            m.check_separate(p/'lab',p/'prod')
    def test_sse_tools_usage_and_comments(self):
        m=self.module('http')
        rows=[b': keepalive\n',b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"x","function":{"name":"lookup","arguments":"{\\\"id\\\":"}}]}}]}\n',b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"1}"}}]},"finish_reason":"tool_calls"}],"usage":{"prompt_tokens":20,"completion_tokens":7},"timings":{"predicted_per_second":5}}\n',b'data: [DONE]\n']
        r=m.parse_sse(rows)
        self.assertEqual(r['tools'][0]['function']['arguments'],'{"id":1}')
        self.assertEqual(r['usage']['completion_tokens'],7)
        self.assertEqual(r['finish_reason'],'tool_calls')
    def test_sse_does_not_count_events_as_tokens(self):
        m=self.module('http'); r=m.parse_sse([b'data: {"choices":[{"delta":{"content":"abc"}}]}\n',b'data: [DONE]\n'])
        self.assertIsNone(m.measurements(r).get('generated_tokens'))
    def test_sse_requires_done(self):
        m=self.module('http'); r=m.parse_sse([b'data: {"choices":[{"delta":{"content":"abc"}}]}\n'])
        self.assertTrue(r['error'])
    def test_tool_auth_rejects_undeclared(self):
        m=self.module('scoring')
        r={'tools':[{'function':{'name':'delete','arguments':'{}'}}],'text':'','finish_reason':'tool_calls'}
        self.assertFalse(m.score({'kind':'no_tools','expected':'OK'},r)['pass'])
    def test_exact_uses_visible_text_not_reasoning(self):
        m=self.module('scoring')
        r={'text':'','reasoning':'OK','tools':[],'finish_reason':'stop'}
        self.assertFalse(m.score({'kind':'exact','expected':'OK'},r)['pass'])
    def test_bootstrap_known_improvement(self):
        m=self.module('statistics'); r=m.paired([10]*6,[8]*6,seed=7)
        self.assertAlmostEqual(r['improvement_pct'],20.0)
        self.assertGreater(r['ci95'][0],19.9)
    def test_small_sample_cannot_promote(self):
        m=self.module('statistics'); r=m.paired([10,10],[8,8]); self.assertFalse(r['sufficient'])
    def test_stats_requires_matched_pairs(self):
        m=self.module('statistics')
        with self.assertRaises(ValueError): m.paired([10,20],[9])
    def test_no_shell_command_strings(self):
        m=self.module('core')
        with self.assertRaises(ValueError): m.argv('echo x; rm -rf x')
        self.assertEqual(m.argv(['echo','a b']),['echo','a b'])
    def test_case_generation_deterministic(self):
        m=self.module('corpus')
        self.assertEqual(m.ledger(200,7),m.ledger(200,7))
        self.assertNotEqual(m.ledger(200,7),m.ledger(200,8))
    def test_no_memory_large_defaults(self):
        m=self.module('core'); c=json.loads((ROOT/'config/lab.example.json').read_text())
        self.assertEqual(c['max_context'],131072)
        self.assertEqual(c['conversation_cache_mib'],0)
    def test_config_hard_cap_in_both_args_lists(self):
        m=self.module('core')
        c=m.normalized_config({'args':['--max-context','262144'],'user_args':['--max-context','200000'],'parallel':3},131072)
        for key in ('args','user_args'): self.assertEqual(m.flag_value(c[key],'--max-context'),'131072')
        self.assertEqual(c['parallel'],1)

if __name__=='__main__': unittest.main()
