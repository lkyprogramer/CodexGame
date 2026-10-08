#!/usr/bin/env python3
"""Deterministic synthetic sessions with explicit recent real-user distance. No model calls."""
from __future__ import annotations
import argparse, hashlib, json, random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CORPORA={
 'en_docs':'An append operation retains the exact preceding state. Verify the input contract, compare the observed result, and keep the test deterministic. The repository contains controller, service, and storage modules.\n',
 'zh_docs':'这是合成的接口说明，不是生产数据。请求需要保持幂等性，失败时保留原始错误；验证路径、事务边界和工具参数，不能仅凭最终回答判断测试通过。\n',
 'cpp_code':'public final class SessionStore {\n  private final Map<String, Long> versions = new HashMap<>();\n  public synchronized boolean update(String id, long expected) {\n    Long current = versions.get(id);\n    if (current == null || current != expected) return false;\n    versions.put(id, expected + 1);\n    return true;\n  }\n}\n',
 'json_logs':'{"level":"INFO","event":"synthetic_test","module":"order-service","requestId":"case-17","values":[1,2,3],"ok":true,"path":"src/main/java/com/example/OrderService.java"}\n'}

def request_hash(request: dict)->str:
    return hashlib.sha256(json.dumps(request,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def block(kind: str,n: int,salt: int)->str:
    text=f'Fixture section {salt:06d}\n'+CORPORA[kind]
    raw=(text*((max(n,0)//len(text.encode()))+2)).encode()
    return raw[:max(0,n)].decode('utf-8',errors='ignore')

def recent_assistant_count(messages: list[dict])->int:
    for i in range(len(messages)-1,-1,-1):
        r=messages[i]
        if r.get('role')=='user':
            t=r.get('content','').strip(' \t\r\n\v\f')
            if not(t.startswith('<tool_response>') and t.endswith('</tool_response>')):
                return sum(x.get('role')=='assistant' for x in messages[i+1:])
    raise ValueError('no real user')

def build_case(recipe:dict)->list[dict]:
    target=int(recipe['messages']);recent=int(recipe['turns_since_last_user']);every=int(recipe.get('history_user_every',60));rounds=int(recipe.get('rounds',4));tool_count=int(recipe.get('tools',12))
    if target<2+2*recent or recent<0 or every<1 or rounds<1 or tool_count<1:raise ValueError('invalid session geometry')
    rng=random.Random(int(recipe.get('seed',20260925)))
    hist=max(0,(target-2-2*recent)//2)
    while 1+2*hist+((hist+every-1)//every if hist else 0)+1+2*recent>target:hist-=1
    messages=[{'role':'system','content':block('en_docs',int(recipe.get('system_bytes',600)),0)}]
    tools=[{'type':'function','function':{'name':f'tool_{i}','description':f'Synthetic tool {i}','parameters':{'type':'object','properties':{'path':{'type':'string'},'query':{'type':'string'}},'required':['path']}}} for i in range(tool_count)]
    def add_round(t:int):
        kind=rng.choice(tuple(CORPORA))
        messages.append({'role':'assistant','content':'','reasoning_content':block('en_docs',int(recipe.get('reasoning_bytes',350)),t),
        'tool_calls':[{'id':f'call_{t}','type':'function','function':{'name':f'tool_{t%tool_count}','arguments':json.dumps({'path':f'src/module{t}/Case{t}.java','query':'inspect contract'},ensure_ascii=False,separators=(',',':'))}}]})
        messages.append({'role':'tool','tool_call_id':f'call_{t}','content':block(kind,int(recipe.get('tool_bytes',900)),t)})
    for t in range(hist):
        if t%every==0:messages.append({'role':'user','content':f'Historical synthetic task {t}. Preserve the contract.'})
        add_round(t)
    missing=target-(len(messages)+1+2*recent)
    for i in range(missing):messages.append({'role':'user','content':f'Historical supplementary requirement {i}.'})
    messages.append({'role':'user','content':'Current synthetic task: verify the update contract and inspect relevant sources.'})
    for t in range(hist,hist+recent):add_round(t)
    rows=[]
    for j in range(rounds):
        if j:add_round(hist+recent+j-1)
        request={'messages':json.loads(json.dumps(messages)), 'tools':tools,'reasoning_effort':'medium','preserve_thinking':True}
        rows.append({'case_id':f"{recipe['id']}-turn-{j:02d}",'fixture_id':recipe['id'],'turn':j,'provenance':'SYNTHETIC_NOT_PRODUCTION','token_count_status':'UNMEASURED','declared_use':recipe.get('use','CPU_AND_CALIBRATED_HTTP'),
         'logical_turns_since_last_user':recent_assistant_count(messages),'hint_count_status':'RENDERER_MUST_MEASURE','request':request,'input_sha256':request_hash(request)})
    return rows

def generate(recipes:dict,out:Path,only:str|None=None)->dict:
    out.mkdir(parents=True,exist_ok=True);manifest={'version':2,'token_count_status':'UNMEASURED','files':[]}
    for r in recipes['sessions']:
        if only and r['id']!=only:continue
        rows=build_case(r);f=out/(r['id']+'.jsonl');f.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in rows),encoding='utf-8')
        manifest['files'].append({'path':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'rows':len(rows),'measured_prompt_tokens':None,'http_eligible':False})
    if not manifest['files']:raise ValueError('no matching recipe')
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return manifest

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recipes',type=Path,default=ROOT/'data/session_recipes.json');p.add_argument('--out-dir',type=Path,required=True);p.add_argument('--only');a=p.parse_args()
    try:print(json.dumps(generate(json.loads(a.recipes.read_text()),a.out_dir,a.only),ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,KeyError) as e:p.exit(2,f'error: {e}\n')
if __name__=='__main__':raise SystemExit(main())
