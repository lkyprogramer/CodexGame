#!/usr/bin/env python3
import json,sys
p=sys.argv[1]
tools=0; last_usage={}; events=0
with open(p,errors='replace') as f:
  for line in f:
    try:o=json.loads(line)
    except: continue
    events+=1
    t=o.get('type','')
    if t in ('toolcall_start','tool_call_start','tool_start'): tools+=1
    u=o.get('usage')
    if isinstance(u,dict): last_usage=u
    if t=='message_end' and isinstance(o.get('message'),dict):
      u=o['message'].get('usage')
      if isinstance(u,dict): last_usage=u
print(json.dumps({'events':events,'tool_calls':tools,'usage':last_usage}))
