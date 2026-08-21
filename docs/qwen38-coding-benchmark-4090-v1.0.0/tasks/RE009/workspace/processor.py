class WebhookProcessor:
 def __init__(self,store):self.store=store
 def handle(self,event_id,payload,handler):
  if self.store.contains(event_id):return 'duplicate'
  handler(payload);self.store.add(event_id);return 'processed'
