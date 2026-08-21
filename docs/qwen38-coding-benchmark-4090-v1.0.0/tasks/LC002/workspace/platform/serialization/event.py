import json
def serialize_event(event):
 event['serialized']=True
 return json.dumps(event).encode()
