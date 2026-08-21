from collections import OrderedDict
class ExpiringLru:
    def __init__(self, capacity, ttl, clock):
        if capacity <= 0 or ttl <= 0: raise ValueError('capacity and ttl must be positive')
        self.capacity=capacity; self.ttl=ttl; self.clock=clock; self.data=OrderedDict()
    def _purge(self, now):
        for key in [k for k,(_,expires) in self.data.items() if expires <= now]: self.data.pop(key,None)
    def put(self,key,value):
        now=self.clock(); self._purge(now); self.data.pop(key,None); self.data[key]=(value,now+self.ttl)
        while len(self.data)>self.capacity: self.data.popitem(last=False)
    def get(self,key,default=None):
        now=self.clock(); item=self.data.get(key)
        if item is None:return default
        value,expires=item
        if expires <= now: self.data.pop(key,None); return default
        self.data.move_to_end(key); return value
    def __len__(self): self._purge(self.clock()); return len(self.data)
