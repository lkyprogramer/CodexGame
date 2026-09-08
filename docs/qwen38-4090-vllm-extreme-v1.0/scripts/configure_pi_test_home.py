#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
env={}
for line in (root/'configs/benchmark.env').read_text().splitlines() if (root/'configs/benchmark.env').exists() else (root/'configs/benchmark.env.example').read_text().splitlines():
    line=line.strip()
    if line and not line.startswith('#') and '=' in line:
        k,v=line.split('=',1); env[k]=v
home=root/'.state/pi-home'
p=(home/'.pi/agent'); p.mkdir(parents=True,exist_ok=True)
server=env.get('SERVER_URL','http://127.0.0.1:18020/v1')
provider=env.get('PI_PROVIDER','local-vllm')
model=env.get('PI_MODEL','qwen3.8-27b-local')
api=env.get('API_KEY','local-qwen-bench')
cfg={"providers":{provider:{
    "baseUrl":server,"api":"openai-completions","apiKey":api,
    "compat":{"supportsDeveloperRole":False},
    "models":[{"id":model,"name":"Qwen3.8 27B local benchmark","reasoning":True,
               "input":["text"],"contextWindow":200000,"maxTokens":8192,
               "cost":{"input":0,"output":0,"cacheRead":0,"cacheWrite":0}}]
}}}
(p/'models.json').write_text(json.dumps(cfg,indent=2),encoding='utf-8')
print(home)
