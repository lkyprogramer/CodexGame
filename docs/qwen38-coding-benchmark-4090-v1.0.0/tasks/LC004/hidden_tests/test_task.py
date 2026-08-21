import threading,unittest
from platform.events.deduplicator import Deduplicator
class Clock:
 def __init__(self):self.t=0
 def __call__(self):return self.t
class Tests(unittest.TestCase):
 def test_tenant_and_ttl(self):
  c=Clock();d=Deduplicator(10,c);self.assertTrue(d.first('a','e'));self.assertFalse(d.first('a','e'));self.assertTrue(d.first('b','e'));c.t=9.999;self.assertFalse(d.first('a','e'));c.t=10;self.assertTrue(d.first('a','e'))
 def test_cleanup(self):
  c=Clock();d=Deduplicator(1,c);[d.first('t',str(i)) for i in range(100)];c.t=2;d.first('t','new');self.assertEqual(len(d.seen),1)
 def test_concurrent(self):
  c=Clock();d=Deduplicator(1,c);barrier=threading.Barrier(20);out=[]
  def f():barrier.wait();out.append(d.first('t','x'))
  ts=[threading.Thread(target=f) for _ in range(20)];[t.start() for t in ts];[t.join() for t in ts];self.assertEqual(out.count(True),1)
 def test_invalid(self):
  with self.assertRaises(ValueError):Deduplicator(0)
  d=Deduplicator(1,lambda:0)
  with self.assertRaises(ValueError):d.first('','x')
if __name__=='__main__':unittest.main()
