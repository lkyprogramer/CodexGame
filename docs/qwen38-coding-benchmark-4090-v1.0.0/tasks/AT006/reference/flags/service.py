import threading
class FlagService:
 def __init__(self,store):
  if store is None:raise ValueError('store required')
  self.store=store;self.cache={};self.lock=threading.RLock()
 def _key(self,tenant,name):
  if not isinstance(tenant,str) or not tenant or not isinstance(name,str) or not name:raise ValueError('invalid key')
  return tenant,name
 def enabled(self,tenant,name):
  key=self._key(tenant,name)
  with self.lock:
   if key in self.cache:return self.cache[key]
  value=self.store.get(*key)
  if not isinstance(value,bool):raise ValueError('flag must be bool')
  with self.lock:return self.cache.setdefault(key,value)
 def invalidate(self,tenant,name):
  key=self._key(tenant,name)
  with self.lock:self.cache.pop(key,None)
