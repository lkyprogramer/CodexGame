import copy
import unittest
from lab import cli
import importlib.util


def plan_fixture():
    return {'schema_version':1,'kind':'park_restore','engine_adapter':None,'max_context':131072,
            'safety_tokens':4096,'min_available_mib':4096,'max_active_gpu_contexts':1,
            'sessions':['A','B'],
            'required_receipts':['request_sha256','session_identity','usage_prompt_tokens','usage_completion_tokens',
                                 'park_count','restore_count','evict_count','snapshot_bytes','heap_rss_mib',
                                 'mem_available_mib','swap_mib','read_tokens','reused_tokens','ttft_s',
                                 'park_ms','restore_ms','trim_ms','quality_assertion'],
            'steps':[{'id':str(i),'session':session,'counted_prompt_tokens':100,
                      'request':{'messages':[{'role':'user','content':'Return only OK.'}],'max_tokens':16},
                      'expected_events':events}
                     for i,(session,events) in enumerate([('A',[]),('B',['park']),('A',['restore'])])]}


class OfflinePlanTests(unittest.TestCase):
    def validate(self, plan):
        self.assertIsNotNone(importlib.util.find_spec('lab.plans'), 'Park/restore needs an offline plan validator')
        from lab.plans import validate_plan
        return validate_plan(plan)

    def test_valid_plan_does_not_claim_live_or_tokenizer_validation(self):
        result=self.validate(plan_fixture())
        self.assertEqual(result['status'],'OFFLINE_PLAN_VALID')
        self.assertFalse(result['live_ready'])
        self.assertFalse(result['tokenizer_verified'])
        self.assertEqual(result['execution_result'],'NOT_RUN')

    def test_prompt_plus_output_cannot_exceed_total_128k(self):
        plan=plan_fixture();plan['steps'][0]['counted_prompt_tokens']=131072
        with self.assertRaises(ValueError):self.validate(plan)

    def test_plan_must_revisit_a_previously_switched_session(self):
        plan=plan_fixture();plan['steps'][2]['session']='B'
        with self.assertRaises(ValueError):self.validate(plan)

    def test_memory_and_restore_receipts_cannot_be_omitted(self):
        plan=plan_fixture();plan['required_receipts'].remove('snapshot_bytes')
        with self.assertRaises(ValueError):self.validate(plan)

    def test_claiming_an_implemented_adapter_is_rejected(self):
        plan=plan_fixture();plan['engine_adapter']='ready'
        with self.assertRaises(ValueError):self.validate(plan)

    def test_boolean_token_count_is_not_an_integer_budget(self):
        plan=plan_fixture();plan['steps'][0]['counted_prompt_tokens']=True
        with self.assertRaises(ValueError):self.validate(plan)
