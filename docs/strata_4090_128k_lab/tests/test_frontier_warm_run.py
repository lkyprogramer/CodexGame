import copy
import unittest
from tools.frontier.warm_run import Budget,append_request,request_outcome,assert_control_config

class AdapterTests(unittest.TestCase):
    def test_one_engine_and_three_requests(self):
        now=[0.0];b=Budget(clock=lambda:now[0]);b.start_engine()
        with self.assertRaises(RuntimeError):b.start_engine()
        for _ in range(3):b.before_request(600)
        with self.assertRaises(RuntimeError):b.before_request(600)
    def test_deadline_reserves_cleanup(self):
        now=[0.0];b=Budget(clock=lambda:now[0]);now[0]=2881
        with self.assertRaises(RuntimeError):b.before_request(600)
        self.assertEqual(b.requests,0)
        for invalid in (601,True,0):
            with self.assertRaises(ValueError):Budget().before_request(invalid)
    def test_short_failure_and_nonwarm_stop(self):
        c={'max_context':131072,'safety_tokens':4096}
        r={'done':True,'usage':{'prompt_tokens':100000,'completion_tokens':2048,'prompt_tokens_details':{'cached_tokens':0}},'timings':{'prompt_n':100000}}
        self.assertEqual(request_outcome(r,100000,c,0),'REQUEST_COMPLETE')
        self.assertEqual(request_outcome(r,100000,c,1),'INSUFFICIENT_NO_WARM_REUSE')
        r['usage']['completion_tokens']=12
        self.assertEqual(request_outcome(r,100000,c,0),'INSUFFICIENT_SHORT_OUTPUT')
        r['error']='guard terminated'
        with self.assertRaises(RuntimeError):request_outcome(r,100000,c,0)
    def test_no_tools_or_counter_drift(self):
        c={'max_context':131072,'safety_tokens':4096}
        r={'done':True,'usage':{'prompt_tokens':100000,'completion_tokens':2048},'tools':[{'function':{'name':'bad'}}]}
        with self.assertRaises(RuntimeError):request_outcome(r,100000,c,0)
        r.pop('tools')
        with self.assertRaises(RuntimeError):request_outcome(r,90000,c,0)
    def test_control_config_drift_rejected(self):
        import tempfile,hashlib
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'config.json';path.write_text('frozen control config')
            identity={'config':{'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}}
            assert_control_config(path,identity)
            path.write_text('extra unfrozen STRATA env')
            with self.assertRaisesRegex(RuntimeError,'CONTROL_CONFIG_DRIFT'):assert_control_config(path,identity)

    def test_release_uses_remaining_cleanup_reserve(self):
        now=[0.0];b=Budget(clock=lambda:now[0]);now[0]=100
        self.assertEqual(b.begin_cleanup(),220)
        now[0]=145;self.assertEqual(b.cleanup_remaining(),75)
        now[0]=219;self.assertEqual(b.cleanup_remaining(),1)

    def test_actual_history_preserved_without_tool_execution(self):
        from lab.core import hash_obj
        prior={'messages':[{'role':'user','content':'real prompt'}],'max_tokens':2048,'tool_choice':'none'}
        user={'role':'user','content':'real followup'}
        recipe={'append_user_message':user,'append_user_message_sha256':hash_obj(user),'padding_allowed':False}
        response={'text':'actual answer','reasoning':'actual thinking'};before=copy.deepcopy(prior)
        result=append_request(prior,response,recipe)
        self.assertEqual(prior,before);self.assertEqual(result['messages'][-2]['content'],'actual answer');self.assertEqual(result['messages'][-2]['reasoning_content'],'actual thinking');self.assertEqual(result['messages'][-1],user)
        with self.assertRaises(RuntimeError):append_request(prior,dict(response,tools=[{}]),recipe)
        with self.assertRaises(RuntimeError):append_request(prior,response,dict(recipe,padding_allowed=True))

if __name__=='__main__':unittest.main()
