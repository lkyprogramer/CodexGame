import time
class LruTtlCache:
    def __init__(self,max_size,ttl_seconds,clock=time.monotonic):
        self.data={}; self.max_size=max_size; self.ttl=ttl_seconds; self.clock=clock
    def put(self,key,value): self.data[key]=(value,self.clock()+self.ttl)
    def get(self,key,default=None):
        value,expires=self.data.get(key,(default,0)); return value if expires>self.clock() else default
    def __len__(self): return len(self.data)
