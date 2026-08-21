import threading
class JobQueue:
 def __init__(self,queue=[]):
  self.queue=queue;self.lock=threading.Lock();self.ready=threading.Condition(self.lock);self.closed=False
 def put(self,job):
  with self.lock:
   if self.closed:raise RuntimeError('closed')
   self.queue.append(job);self.ready.notify()
 def take_and_run(self):
  with self.lock:
   if not self.queue:self.ready.wait()
   job=self.queue.pop(0)
   job()
 def close(self):
  self.closed=True
  with self.lock:self.ready.notify()
