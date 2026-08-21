import base64,json,math
from datetime import date,datetime,timezone

def _convert(value,seen):
 if value is None or isinstance(value,(str,bool,int)):return value
 if isinstance(value,float):
  if not math.isfinite(value):raise ValueError('non-finite number')
  return value
 if isinstance(value,datetime):
  if value.tzinfo is None or value.utcoffset() is None:raise ValueError('naive datetime')
  return value.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
 if isinstance(value,date):return value.isoformat()
 if isinstance(value,(bytes,bytearray,memoryview)):return {'$bytes':base64.b64encode(bytes(value)).decode('ascii')}
 if id(value) in seen:raise ValueError('cycle')
 if isinstance(value,dict):
  seen.add(id(value))
  try:
   if not all(isinstance(k,str) for k in value):raise ValueError('keys must be strings')
   return {k:_convert(v,seen) for k,v in value.items()}
  finally:seen.remove(id(value))
 if isinstance(value,(list,tuple)):
  seen.add(id(value))
  try:return [_convert(v,seen) for v in value]
  finally:seen.remove(id(value))
 raise ValueError('unsupported value')
def serialize_event(event):
 if not isinstance(event,dict):raise ValueError('event must be object')
 converted=_convert(event,set())
 return json.dumps(converted,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
