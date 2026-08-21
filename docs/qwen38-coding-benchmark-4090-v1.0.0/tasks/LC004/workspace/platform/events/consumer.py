class Consumer:
 def __init__(self,dedup,handler):self.dedup=dedup;self.handler=handler
 def consume(self,tenant,event):
  if self.dedup.first(tenant,event['id']):self.handler(event)
