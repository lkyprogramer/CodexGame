import threading,time
class Deduplicator:
 def __init__(self,ttl_seconds,clock=time.monotonic):
  if ttl_seconds<=0 or not callable(clock):raise ValueError('invalid config')
  self.ttl=float(ttl_seconds);self.clock=clock;self.seen={};self.lock=threading.RLock()
 def first(self,tenant,event_id):
  if not isinstance(tenant,str) or not tenant or not isinstance(event_id,str) or not event_id:raise ValueError('invalid key')
  now=float(self.clock());key=(tenant,event_id)
  with self.lock:
   for k,expires in list(self.seen.items()):
    if expires<=now:self.seen.pop(k,None)
   expires=self.seen.get(key)
   if expires is not None and expires>now:return False
   self.seen[key]=now+self.ttl;return True
