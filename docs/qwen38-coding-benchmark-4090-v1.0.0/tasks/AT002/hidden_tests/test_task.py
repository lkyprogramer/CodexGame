import unittest
from app.config import resolve
class Tests(unittest.TestCase):
 def test_precedence_explicit_falsy(self):
  f={'debug':True,'port':9};e={'port':7};c={'debug':False,'port':0,'host':''};before=(dict(f),dict(e),dict(c));self.assertEqual(resolve(f,e,c),{'debug':False,'port':0,'host':''});self.assertEqual((f,e,c),before)
 def test_none_is_missing(self):self.assertEqual(resolve({'port':1},{'port':2},{'port':None})['port'],2)
 def test_unknown(self):
  with self.assertRaises(ValueError):resolve({}, {'wat':1}, {})
if __name__=='__main__':unittest.main()
