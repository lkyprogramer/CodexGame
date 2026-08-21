from collections import OrderedDict
class ExpiringLru:
    def __init__(self,capacity,ttl,clock): self.capacity=capacity;self.ttl=ttl;self.clock=clock;self.data=OrderedDict()
    def put(self,key,value):
        self.data[key]=(value,self.clock()+self.ttl)
        if len(self.data)>self.capacity:self.data.popitem(last=False)
    def get(self,key,default=None):
        item=self.data.get(key)
        if not item:return default
        value,expires=item
        if expires < self.clock(): return default
        self.data.move_to_end(key);return value
    def __len__(self): return len(self.data)
