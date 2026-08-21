import threading,unittest
from flags.store import Store
from flags.service import FlagService
class Tests(unittest.TestCase):
 def test_isolation_cache_invalidate(self):
  store=Store({('a','x'):True,('b','x'):False});s=FlagService(store);self.assertTrue(s.enabled('a','x'));self.assertFalse(s.enabled('b','x'));self.assertTrue(s.enabled('a','x'));self.assertEqual(store.reads,2);store.data[('a','x')]=False;s.invalidate('a','x');self.assertFalse(s.enabled('a','x'));self.assertFalse(s.enabled('b','x'));self.assertEqual(store.reads,3)
 def test_invalid(self):
  s=FlagService(Store({('a','x'):'yes'}))
  with self.assertRaises(ValueError):s.enabled('a','x')
  with self.assertRaises(ValueError):s.enabled('','x')
 def test_concurrent(self):
  store=Store({('a','x'):True});s=FlagService(store);errs=[]
  def f():
   try:
    for _ in range(100):self.assertTrue(s.enabled('a','x'))
   except Exception as e:errs.append(e)
  ts=[threading.Thread(target=f) for _ in range(10)];[t.start() for t in ts];[t.join() for t in ts];self.assertFalse(errs)
if __name__=='__main__':unittest.main()
