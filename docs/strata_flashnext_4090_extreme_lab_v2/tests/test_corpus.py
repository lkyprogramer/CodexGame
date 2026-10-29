import json,unittest
from lab.corpus import build
from lab.core import check_budget,hash_obj

class CorpusTests(unittest.TestCase):
 def test_full_suite_shape_under_fake_counter(self):
  # This cheap counter tests generator structure only, never target-model token lengths.
  fake=lambda b:len(json.dumps(b,ensure_ascii=False).encode())//4
  c=build(fake,suite='full')
  self.assertEqual(len(c['cases']),82)
  self.assertEqual(hash_obj(c['cases']),c['corpus_sha256'])
  self.assertEqual(len({x['id'] for x in c['cases']}),82)
  for x in c['cases']:check_budget(x['counted_prompt_tokens'],x['body']['max_tokens'])
 def test_smoke_is_not_falsely_full_java(self):
  c=build(lambda b:100,suite='smoke')
  self.assertEqual(len(c['cases']),21)
  self.assertFalse(any(x['kind']=='java' for x in c['cases']))
