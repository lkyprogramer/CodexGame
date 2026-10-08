"""Execute Pi on isolated fixture copies, then verify with controller-owned tests."""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile, time, signal
from pathlib import Path
from .core import sha256_file
ROOT=Path(__file__).resolve().parents[1]

def fingerprints(root,paths):
    out={}
    for rel in paths:
        p=root/rel
        if p.is_dir():
            for f in sorted(p.rglob('*')):
                if f.is_file():out[str(f.relative_to(root))]=sha256_file(f)
        elif p.is_file():out[rel]=sha256_file(p)
    return out

def summarize_pi(path):
    tools=set();assistant=[];seen=set();bad=0
    for i,line in enumerate(path.read_text(errors='replace').splitlines()):
        try:e=json.loads(line)
        except json.JSONDecodeError:bad+=1;continue
        t=e.get('type')
        if t in ('tool_execution_start','toolcall_start','tool_call_start','tool_start'):
            tools.add(e.get('toolCallId') or e.get('id') or f'line-{i}')
        if t=='message_end':
            m=e.get('message',{})
            if m.get('role')!='assistant':continue
            key=m.get('id') or f'line-{i}'
            if key not in seen:seen.add(key);assistant.append(m)
    sums={};known=False
    for m in assistant:
        u=m.get('usage',{})
        for k in ('input','output','cacheRead','cacheWrite'):
            if isinstance(u.get(k),(int,float)):sums[k]=sums.get(k,0)+u[k];known=True
    return {'tool_calls':len(tools),'assistant_messages':len(assistant),'usage_sum':sums if known else None,'unparsed_lines':bad}

def main():
    p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:18041/v1');p.add_argument('--model',default='qwen3.8-27b-kern-sm89-p0');p.add_argument('--pi',default='pi');p.add_argument('--timeout',type=int,default=240);p.add_argument('--out-dir',required=True);a=p.parse_args()
    pi=shutil.which(a.pi)
    if not pi:raise SystemExit('BLOCKED: Pi binary not installed')
    out=Path(a.out_dir).resolve();out.mkdir(parents=True,exist_ok=False)
    home=out/'pi-home';config=home/'.pi/agent';config.mkdir(parents=True)
    (config/'models.json').write_text(json.dumps({'providers':{'kern-poc':{'baseUrl':a.base_url,'api':'openai-completions','apiKey':os.environ.get('POC_API_KEY','local-only'),'compat':{'supportsDeveloperRole':False},'models':[{'id':a.model,'name':'Kern SM89 P0','reasoning':False,'input':['text'],'contextWindow':73728,'maxTokens':4096,'cost':{'input':0,'output':0,'cacheRead':0,'cacheWrite':0}}]}}},indent=2))
    records=[]
    for fixture in sorted((ROOT/'fixtures').glob('java-*')):
        case=out/fixture.name;work=case/'work';work.parent.mkdir(parents=True);shutil.copytree(fixture,work)
        protected=['src/test','verify.sh','TASK.md','AGENTS.md'];before=fingerprints(work,protected);source=fingerprints(work,['src/main'])
        # This original fixture must fail, otherwise the task cannot measure repair.
        initial=subprocess.run(['bash','verify.sh'],cwd=work,capture_output=True,text=True,timeout=25)
        (case/'initial.log').write_text(initial.stdout+initial.stderr)
        if initial.returncode==0:raise RuntimeError('fixture initially passes: '+fixture.name)
        env={**os.environ,'HOME':str(home),'PI_CODING_AGENT_DIR':str(config),'PI_SKIP_VERSION_CHECK':'1'}
        argv=[pi,'--mode','json','--no-session','--provider','kern-poc','--model',a.model,'--thinking','off','--tools','read,bash,edit,write,grep,find,ls','-p',(fixture/'TASK.md').read_text()]
        start=time.monotonic();rc=124
        with (case/'pi.jsonl').open('w') as log,(case/'stderr.log').open('w') as err:
            proc=subprocess.Popen(argv,cwd=work,env=env,stdout=log,stderr=err,start_new_session=True)
            def interrupted(signum,frame):raise SystemExit(128+signum)
            handlers={s:signal.signal(s,interrupted) for s in (signal.SIGTERM,signal.SIGINT)}
            try:rc=proc.wait(timeout=a.timeout)
            except subprocess.TimeoutExpired:rc=124
            finally:
                for s in handlers:signal.signal(s,signal.SIG_IGN)
                from .suite import stop_group
                stop_group(proc)
                for s,h in handlers.items():signal.signal(s,h)
        elapsed=time.monotonic()-start
        protected_ok=before==fingerprints(work,protected) and not any(x.is_symlink() for x in work.rglob('*'));changed=source!=fingerprints(work,['src/main'])
        # Never trust the agent's executable verifier: use a fresh original fixture and only its src/main.
        with tempfile.TemporaryDirectory(prefix='kern-controller-') as tmp:
            verify=Path(tmp)/'repo';shutil.copytree(fixture,verify);shutil.rmtree(verify/'src/main')
            shutil.copytree(work/'src/main',verify/'src/main')
            result=subprocess.run(['bash','verify.sh'],cwd=verify,capture_output=True,text=True,timeout=30)
        (case/'verified.log').write_text(result.stdout+result.stderr)
        m=summarize_pi(case/'pi.jsonl')
        record={'case':fixture.name,'pi_exit':rc,'verify_exit':result.returncode,'protected_ok':protected_ok,'source_changed':changed,'elapsed_s':elapsed,**m}
        marker={'java-01-idempotency':'PASS idempotency','java-02-retry':'PASS retry','java-03-reconnect':'PASS reconnect'}[fixture.name]
        record['status']='PASS' if rc==0 and result.returncode==0 and marker in result.stdout and protected_ok and changed else 'FAIL'
        records.append(record);print(json.dumps(record),flush=True)
    summary={'status':'PASS' if all(x['status']=='PASS' for x in records) else 'FAIL','cases':records,'passed':sum(x['status']=='PASS' for x in records)}
    (out/'summary.json').write_text(json.dumps(summary,indent=2));return 0 if summary['status']=='PASS' else 2
if __name__=='__main__':sys.exit(main())
