import threading,time,unittest
from store import MemoryStore
from processor import WebhookProcessor
class Tests(unittest.TestCase):
 def test_concurrent_duplicate(self):
  p=WebhookProcessor(MemoryStore());calls=[];start=threading.Barrier(12);results=[]
  def worker():
   start.wait();results.append(p.handle('e',1,lambda x:(calls.append(x),time.sleep(.04))))
  ts=[threading.Thread(target=worker) for _ in range(12)];[t.start() for t in ts];[t.join() for t in ts];self.assertEqual(len(calls),1);self.assertEqual(results.count('processed'),1);self.assertEqual(results.count('duplicate'),11);self.assertEqual(p.handle('e',2,lambda _:calls.append(2)),'duplicate')
 def test_failure_retry(self):
  p=WebhookProcessor(MemoryStore());count=0
  def bad(_):raise RuntimeError('boom')
  with self.assertRaisesRegex(RuntimeError,'boom'):p.handle('x',None,bad)
  self.assertEqual(p.handle('x',None,lambda _:None),'processed')
 def test_different_ids_parallel(self):
  p=WebhookProcessor(MemoryStore());barrier=threading.Barrier(2)
  def h(_):barrier.wait(timeout=1)
  ts=[threading.Thread(target=lambda i=i:p.handle(str(i),None,h)) for i in range(2)];[t.start() for t in ts];[t.join() for t in ts]
if __name__=='__main__':unittest.main()
