class FlagService:
 def __init__(self,store):self.store=store;self.cache={}
 def enabled(self,tenant,name):
  if name not in self.cache:self.cache[name]=self.store.get(tenant,name)
  return self.cache[name]
 def invalidate(self,tenant,name):self.cache.pop(name,None)
