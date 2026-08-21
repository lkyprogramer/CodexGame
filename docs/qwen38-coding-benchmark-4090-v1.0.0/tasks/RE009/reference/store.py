import threading
class MemoryStore:
 def __init__(self):self.processed=set();self.lock=threading.RLock()
 def contains(self,event_id):
  with self.lock:return event_id in self.processed
 def add(self,event_id):
  with self.lock:self.processed.add(event_id)
