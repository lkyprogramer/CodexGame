import threading
class _Flight:
 def __init__(self):self.event=threading.Event();self.error=None
class WebhookProcessor:
 def __init__(self,store):
  if store is None:raise ValueError('store required')
  self.store=store;self._lock=threading.Lock();self._flights={}
 def handle(self,event_id,payload,handler):
  if not isinstance(event_id,str) or not event_id.strip() or not callable(handler):raise ValueError('invalid input')
  if self.store.contains(event_id):return 'duplicate'
  with self._lock:
   if self.store.contains(event_id):return 'duplicate'
   flight=self._flights.get(event_id)
   if flight is None:flight=_Flight();self._flights[event_id]=flight;owner=True
   else:owner=False
  if not owner:
   flight.event.wait()
   if flight.error is not None:raise flight.error
   return 'duplicate'
  try:
   handler(payload);self.store.add(event_id);return 'processed'
  except BaseException as exc:
   flight.error=exc;raise
  finally:
   with self._lock:self._flights.pop(event_id,None)
   flight.event.set()
