#!/usr/bin/env python3
"""Generate deterministic synthetic Java/tool histories, without claiming exact token depth."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import random

def generate(recipe: dict) -> list[dict]:
    required=('recipe_id','seed','target_token_hint','target_message_count','approx_chars_per_token','turn_additions','suffix_chars')
    if any(k not in recipe for k in required):raise ValueError('incomplete recipe')
    n=recipe['target_message_count']
    if type(n) is not int or n<3 or n>10000:raise ValueError('target_message_count must be 3..10000')
    if recipe['target_token_hint']<=0 or recipe['approx_chars_per_token']<=0:raise ValueError('size hints must be positive')
    rng=random.Random(recipe['seed'])
    target_chars=int(recipe['target_token_hint']*recipe['approx_chars_per_token'])
    payload_len=max(20,target_chars//max(1,n//2))
    def payload(i: int, length: int) -> str:
        lines=[];count=0
        while count<length:
            code=rng.randrange(1000000)
            line=f'// fixture {recipe["recipe_id"]} file_{i}_{code}\npublic int compute{code}(int score) {{ return Math.max(0, score - {i%11}); }}\n'
            lines.append(line);count+=len(line)
        return ''.join(lines)[:length]
    messages=[{'role':'system','content':'Work on a synthetic Java repository. Use read_file to inspect, then explain the exact change.'},{'role':'user','content':'Inspect the grading service and preserve method names.'}]
    if n%2:
        messages.append({'role':'assistant','content':'I will inspect the available sources first.','reasoning_content':'Proceed using the same user request.'})
    initial_count=len(messages)
    for i in range(n-initial_count):
        if i%2==0:
            messages.append({'role':'assistant','content':'','reasoning_content':'Inspect the next file before changing the implementation.',
                             'tool_calls':[{'id':f'call_{i}','type':'function','function':{'name':'read_file','arguments':json.dumps({'path':f'src/Service{i}.java'},separators=(',',':'))}}]})
        else:
            messages.append({'role':'tool','tool_call_id':f'call_{i-1}','content':payload(i,payload_len)})
    tools=[{'type':'function','function':{'name':'read_file','description':'Read a synthetic source file','parameters':{'type':'object','properties':{'path':{'type':'string'}},'required':['path']}}}]
    result=[]
    for turn in range(recipe['turn_additions']+1):
        request={'messages':copy.deepcopy(messages),'tools':copy.deepcopy(tools),'enable_thinking':True,'reasoning_effort':'medium','preserve_thinking':True,'temperature':1.0,'top_p':.95,'top_k':20,'max_tokens':512,'stream':True}
        raw=json.dumps(request,ensure_ascii=False,separators=(',',':')).encode()
        result.append({'case_id':f'{recipe["recipe_id"]}-turn-{turn:02d}','session_id':recipe['recipe_id'],'turn':turn,'kind':'http-replay-input','input_sha256':hashlib.sha256(raw).hexdigest(),'canonicalization':'UTF-8 JSON compact ensure_ascii=False insertion order','token_count_status':'UNMEASURED','target_token_hint':recipe['target_token_hint'],'request':request})
        messages += [{'role':'assistant','content':'','reasoning_content':'Continue the same inspection task.',
                      'tool_calls':[{'id':f'next_{turn}','type':'function','function':{'name':'read_file','arguments':json.dumps({'path':f'src/Next{turn}.java'},separators=(',',':'))}}]},
                     {'role':'tool','tool_call_id':f'next_{turn}','content':payload(10000+turn,recipe['suffix_chars'])}]
    return result

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recipes',type=Path,default=Path(__file__).resolve().parents[1]/'data/session_recipes.json');p.add_argument('--out-dir',type=Path,required=True);p.add_argument('--only',help='one recipe_id');a=p.parse_args()
    try:
        spec=json.loads(a.recipes.read_text(encoding='utf-8'));rs=[r for r in spec['recipes'] if not a.only or r['recipe_id']==a.only]
        if not rs:raise ValueError('no matching recipe')
        a.out_dir.mkdir(parents=True,exist_ok=True);manifest=[]
        for recipe in rs:
            rows=generate(recipe);path=a.out_dir/(recipe['recipe_id']+'.jsonl')
            text=''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in rows)
            path.write_text(text,encoding='utf-8');manifest.append({'file':path.name,'sha256':hashlib.sha256(text.encode()).hexdigest(),'requests':len(rows),'actual_prompt_tokens':None,'token_count_status':'UNMEASURED'})
        (a.out_dir/'manifest.json').write_text(json.dumps({'schema_version':1,'entries':manifest,'warning':'Run pinned tokenizer calibration before claiming any context depth. Each input ends in a tool result or user message; validate rendered semantics with the pinned oracle.'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'generated_files':len(manifest),'out_dir':str(a.out_dir),'status':'INPUTS_ONLY'},ensure_ascii=False));return 0
    except (OSError,ValueError,KeyError) as e:p.exit(2,f'error: {e}\n')
if __name__=='__main__':raise SystemExit(main())
