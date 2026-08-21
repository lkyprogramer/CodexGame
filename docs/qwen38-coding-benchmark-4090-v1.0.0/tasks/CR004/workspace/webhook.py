import hashlib,hmac,json,time
seen=set()
def receive(body,headers,secret,handler):
 data=json.loads(body)
 expected=hmac.new(secret.encode(),json.dumps(data,sort_keys=True).encode(),hashlib.sha256).hexdigest()
 if expected!=headers.get('X-Signature'):return 401
 event_id=data['id']
 if event_id in seen:return 200
 handler(data)
 seen.add(event_id)
 return 200
