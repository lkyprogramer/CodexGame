import unittest
from registry import PluginRegistry
class Tests(unittest.TestCase):
 def test_order_and_once(self):
  r=PluginRegistry();calls=[];r.register('db',lambda:calls.append('db') or object());r.register('api',lambda:calls.append('api') or object(),['db']);r.register('cache',lambda:calls.append('cache') or object());self.assertEqual(r.resolve_order(),['cache','db','api']);first=r.start_all();second=r.start_all();self.assertEqual(calls,['cache','db','api']);self.assertEqual(set(first),set(second))
 def test_missing_cycle_duplicate(self):
  r=PluginRegistry();r.register('a',lambda:1,['x'])
  with self.assertRaisesRegex(ValueError,'x'):r.resolve_order()
  r=PluginRegistry();r.register('a',lambda:1,['b']);r.register('b',lambda:1,['a'])
  with self.assertRaisesRegex(ValueError,'a'):r.resolve_order()
  r=PluginRegistry();r.register('a',lambda:1)
  with self.assertRaises(ValueError):r.register('a',lambda:2)
 def test_failure_retry(self):
  r=PluginRegistry();count={'x':0};r.register('a',lambda:'a')
  def f():
   count['x']+=1
   if count['x']==1:raise RuntimeError('boom')
   return 'b'
  r.register('b',f,['a'])
  with self.assertRaises(RuntimeError):r.start_all()
  out=r.start_all();self.assertIn('b',out);self.assertEqual(count['x'],2)
if __name__=='__main__':unittest.main()
