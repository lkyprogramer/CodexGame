import unittest
from lab.scoring import score


class StrictScoringTests(unittest.TestCase):
    def answer(self, text):
        return {'text': text, 'tools': [], 'finish_reason': 'stop'}

    def test_json_boolean_does_not_equal_zero_in_nested_arrays(self):
        case = {'kind': 'json', 'expected': {'values': [False, {'n': 1}]}}
        self.assertFalse(score(case, self.answer('{"values":[0,{"n":true}]}'))['pass'])

    def test_integer_answer_does_not_accept_float_representation(self):
        self.assertFalse(score({'kind': 'json', 'expected': {'count': 1}}, self.answer('{"count":1.0}'))['pass'])

    def test_duplicate_keys_are_invalid_even_when_last_value_matches(self):
        self.assertFalse(score({'kind': 'json', 'expected': {'ok': True}}, self.answer('{"ok":false,"ok":true}'))['pass'])

    def test_nonfinite_json_extension_is_rejected(self):
        self.assertFalse(score({'kind': 'json', 'expected': {'v': float('inf')}}, self.answer('{"v":Infinity}'))['pass'])

    def test_tool_arguments_enforce_boolean_and_integer_types(self):
        case = {'kind': 'tool', 'body': {'tools': [{'function': {'name': 'configure'}}]},
                'expected': {'name': 'configure', 'arguments': {'enabled': False, 'retries': 0}}}
        response = {'finish_reason': 'tool_calls', 'tools': [{'function': {
            'name': 'configure', 'arguments': '{"enabled":0,"retries":false}'}}]}
        self.assertFalse(score(case, response)['pass'])

    def test_well_typed_nested_json_keeps_passing(self):
        case = {'kind': 'json', 'expected': {'a': [False, 0, None, '订单', {'v': 1.5}]}}
        self.assertTrue(score(case, self.answer('{"a":[false,0,null,"订单",{"v":1.5}]}'))['pass'])

    def test_duplicate_tool_keys_are_rejected(self):
        case = {'kind': 'tool', 'body': {'tools': [{'function': {'name': 'configure'}}]},
                'expected': {'name': 'configure', 'arguments': {'enabled': False}}}
        response = {'finish_reason': 'tool_calls', 'tools': [{'function': {
            'name': 'configure', 'arguments': '{"enabled":true,"enabled":false}'}}]}
        self.assertFalse(score(case, response)['pass'])
