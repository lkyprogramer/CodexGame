import time
class Deduplicator:
 def __init__(self,ttl_seconds,clock=time.time):self.ttl=ttl_seconds;self.clock=clock;self.seen={}
 def first(self,tenant,event_id):
  now=self.clock()*1000
  expires=self.seen.get(event_id,0)
  if expires>now:return False
  self.seen[event_id]=now+self.ttl
  return True
