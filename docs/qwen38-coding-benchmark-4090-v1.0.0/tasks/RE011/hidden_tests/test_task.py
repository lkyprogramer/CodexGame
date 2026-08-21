import hashlib,unittest
from flags.model import FlagConfig
from flags.evaluator import is_enabled
class Tests(unittest.TestCase):
 def test_exact_algorithm(self):
  c=FlagConfig('new-ui','s1',5000)
  for uid in ['a','用户-2','z']:
   bucket=int.from_bytes(hashlib.sha256(f's1:new-ui:{uid}'.encode()).digest()[:8],'big')%10000;self.assertEqual(is_enabled(uid,c),bucket<5000)
 def test_edges_and_override(self):
  self.assertFalse(is_enabled('u',FlagConfig('f','s',0)));self.assertTrue(is_enabled('u',FlagConfig('f','s',10000)));c=FlagConfig('f','s',0);o={'u':True};self.assertTrue(is_enabled('u',c,o));self.assertEqual(o,{'u':True})
 def test_validation(self):
  for c in [FlagConfig('','s',1),FlagConfig('f','',1),FlagConfig('f','s',10001),FlagConfig('f','s',True)]:
   with self.assertRaises(ValueError):is_enabled('u',c)
  with self.assertRaises(ValueError):is_enabled('',FlagConfig('f','s',1))
if __name__=='__main__':unittest.main()
