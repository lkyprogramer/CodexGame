from __future__ import annotations
import copy,json,threading,time
from pathlib import Path
from . import http
from .core import ROOT,check_budget,dump,gpu_lock
from .corpus import body
from .java_eval import evaluate
from .runner import OwnedServer,validate_counter
from .tokenizer import StrataCounter
from .workspace import baseline_dir,candidate_dir,validate_ready,lock
from .statistics import paired

TOOLS=[
 {'type':'function','function':{'name':'write_solution','description':'Replace the one synthetic Solution.java in this task; no other file access.', 'parameters':{'type':'object','properties':{'code':{'type':'string'}},'required':['code'],'additionalProperties':False}}},
 {'type':'function','function':{'name':'run_tests','description':'Compile and run the fixed Java oracle inside the isolated offline container.', 'parameters':{'type':'object','properties':{},'additionalProperties':False}}}
]


def java_agent(server,counter,c,task,folder):
    request=body(task['prompt'],max_tokens=3072,tools=TOOLS)
    request['messages'][0]['content']='You are a Java repair agent working on one synthetic file. Use write_solution then run_tests. Fix failures. No shell or other tools exist. Do not claim success before tests pass.'
    code='';events=[];tests=0;t0=time.perf_counter();ok=False
    for step in range(8):
        n=counter(request);check_budget(n,request['max_tokens'])
        response=http.chat(server.base,request,server.key,c['request_timeout_s'])
        events.append({'step':step,'response':response})
        if response.get('error') or not response.get('tools'):break
        assistant={'role':'assistant','content':response.get('text') or '', 'tool_calls':response['tools']}
        request['messages'].append(assistant)
        for call in response['tools']:
            fn=call.get('function',{});name=fn.get('name')
            try:args=json.loads(fn.get('arguments',''))
            except ValueError: return {'pass':False,'reason':'invalid tool args','events':events,'wall_s':time.perf_counter()-t0}
            if name=='write_solution' and isinstance(args,dict) and set(args)=={'code'} and isinstance(args['code'],str) and len(args['code'])<=100000:
                code=args['code'];result={'written':'Solution.java'}
            elif name=='run_tests' and args=={} and code and tests<3:
                tests+=1;result=evaluate(code,task['id'],c.get('java_image') if c.get('java_enabled') else '',folder)
                if result.get('pass') is None:return {'pass':None,'reason':'Java sandbox unavailable','events':events,'wall_s':time.perf_counter()-t0}
                ok=result.get('pass') is True
            else:return {'pass':False,'reason':'Unauthorized tool/schema/iteration limit','events':events,'wall_s':time.perf_counter()-t0}
            request['messages'].append({'role':'tool','tool_call_id':call.get('id',''),'content':json.dumps(result,ensure_ascii=False)[:6000]})
            if ok:return {'pass':True,'tests':tests,'events':events,'wall_s':time.perf_counter()-t0}
    return {'pass':False,'reason':'No passing test within bounded agent loop','tests':tests,'events':events,'wall_s':time.perf_counter()-t0}


def preemption(server,counter,c):
    long=body('Write a Java concurrency guide of at least 3000 words. Continue until the token budget is exhausted.',max_tokens=2048)
    short=body('Return only the integer result of 29*17.',max_tokens=32)
    for req in (long,short):check_budget(counter(req),req['max_tokens'])
    result={};first=threading.Event();t0=time.perf_counter()
    def worker():result['long']=http.chat(server.base,long,server.key,c['request_timeout_s'],on_first=first.set)
    th=threading.Thread(target=worker,daemon=True);th.start()
    if not first.wait(120):
        th.join(timeout=c['request_timeout_s']);return {'pass':False,'reason':'long request never reached decode','wall_s':time.perf_counter()-t0,'long':result.get('long')}
    time.sleep(.25)
    already_done=not th.is_alive()
    result['short']=http.chat(server.base,short,server.key,c['request_timeout_s'])
    th.join(timeout=c['request_timeout_s'])
    if th.is_alive():return {'pass':False,'reason':'long request did not finish after short','wall_s':time.perf_counter()-t0}
    result.update({'pass':not already_done and result['short'].get('text','').strip()=='493' and not result['short'].get('error') and not result['long'].get('error'),
                   'wall_s':time.perf_counter()-t0,'short_ttft_s':result['short'].get('first_s'),'overlap_was_real':not already_done})
    return result



def reply_chain(server,counter,c):
    history=[];events=[];start=time.perf_counter()
    for i in range(20):
        literal=("java.util.Map<Long,String> 中文🙂 e\u0301 İ 0000123 9223372036854775807; "*5)+str(i)
        request=body('Repeat the following data exactly, no quotes or markdown:\n'+literal,max_tokens=1024)
        request['messages']=request['messages'][:1]+history+[request['messages'][-1]]
        check_budget(counter(request),request['max_tokens'])
        r=http.chat(server.base,request,server.key,c['request_timeout_s'])
        events.append({'turn':i,'response':r,'metrics':http.measurements(r)})
        if r.get('error') or r.get('tools') or r.get('text','').strip()!=literal:
            return {'pass':False,'reason':'reply-chain content mismatch','events':events,'wall_s':time.perf_counter()-start}
        history.extend([request['messages'][-1],{'role':'assistant','content':r['text']}])
    return {'pass':True,'events':events,'wall_s':time.perf_counter()-start}

def run_scenario(c,pr,name):
    from .assets import verify
    assets=verify(c)
    r=validate_ready(c,pr)
    if r.get('status')!='READY':return r
    if name=='java-agent' and (not c.get('java_enabled') or not c.get('java_image')):raise RuntimeError('Java scenario requires an existing local Docker JDK image')
    out=Path(c['workspace'])/'results'/f'pr-{pr}-{name}-{time.strftime("%Y%m%d-%H%M%S")}';out.mkdir(parents=True)
    dump(out/'assets.json',assets)
    counter=StrataCounter(baseline_dir(c),c['gguf'],c['template'])
    tasks=json.loads((ROOT/'fixtures/java/tasks.json').read_text())
    records=[]
    with gpu_lock(c['workspace']):
        for rnd in range(c['rounds']):
            for arm in (['base','off','on'] if rnd%2==0 else ['on','off','base']):
                tree=baseline_dir(c) if arm=='base' else candidate_dir(c,pr)
                from .core import sha256
                build=json.loads((tree/'build-lab/LAB_BUILD.json').read_text())
                expected=lock()['baseline_sha'] if arm=='base' else r['candidate_sha']
                if build['source_sha']!=expected or sha256(Path(build['exe']))!=build['exe_sha256']:raise RuntimeError('Stale scenario build')
                folder=out/f'round-{rnd:02d}-{arm}'
                with OwnedServer(c,tree,arm,r,folder) as server:
                    validate_counter(counter,server)
                    cases=tasks if name=='java-agent' else [{'id':'long-short'}]
                    for t in cases:
                        answer=java_agent(server,counter,c,t,folder/'java') if name=='java-agent' else (preemption(server,counter,c) if name=='preemption' else reply_chain(server,counter,c))
                        row={'round':rnd,'arm':arm,'task':t['id'],'scenario':name,'result':answer};records.append(row)
                        with (out/'scenarios.jsonl').open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    metrics=['wall_s']+(['short_ttft_s'] if name=='preemption' else [])
    report={'scenario':name,'quality_failures':sum(x['result'].get('pass') is not True for x in records),'comparisons':{},'decision':'SCREEN_ONLY'}
    for a,b in [('base','off'),('off','on')]:
        for metric in metrics:
            pairs=[]
            for rnd in range(c['rounds']):
                aa=[x for x in records if x['round']==rnd and x['arm']==a];bb=[x for x in records if x['round']==rnd and x['arm']==b]
                if not aa or not bb or any(x['result'].get('pass') is not True or x['result'].get(metric) is None for x in aa+bb):continue
                pairs.append((sum(x['result'][metric] for x in aa),sum(x['result'][metric] for x in bb)))
            report['comparisons'][a+'_'+b+'_'+metric]=paired([x[0] for x in pairs],[x[1] for x in pairs]) if pairs else None
    dump(out/'summary.json',report)
    (out/'REPORT.md').write_text('# '+name+'\n\n```json\n'+json.dumps(report,ensure_ascii=False,indent=2)+'\n```\n\n这是受控合成任务，不等于用户真实 Pi 仓库通过率。\n')
    return {'results':str(out),'report':report}
