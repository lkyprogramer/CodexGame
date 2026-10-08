"""Bounded controller-side stage runner. Does NOT pause production automatically.
A ready local plan must supply real commands and fresh evidence. GPU tasks use
remote_guard.py separately; examples are intentionally not ready for GPU work.
"""
import argparse,json,os,re,signal,subprocess,time,hashlib,select,shutil
from pathlib import Path
from .security import redact

def validate_plan(d):
    if d.get('ready') is not True:raise ValueError('plan not ready: finish adapters and preflight first')
    if not re.fullmatch('[a-zA-Z0-9_-]{1,64}',d.get('run_id','')):raise ValueError('invalid run_id')
    if not 10<=d.get('budget_sec',0)<=3600:raise ValueError('budget must be 10..3600 seconds')
    stages=d.get('stages')
    if not stages:raise ValueError('empty stage plan')
    ids=set()
    for s in stages:
        if not re.fullmatch('[a-zA-Z0-9_-]{1,64}',s.get('id','')):raise ValueError('invalid stage id')
        if s['id'] in ids:raise ValueError('duplicate stage id')
        ids.add(s['id'])
        a=s['argv']
        if not isinstance(a,list) or not a or not all(isinstance(x,str) and x for x in a):raise ValueError('argv array required')
        if not shutil.which(a[0]):raise ValueError('executable is not available on controller')
        if not Path(s['cwd']).expanduser().is_dir():raise ValueError('missing cwd')
        if not 1<=s['timeout_sec']<=3600:raise ValueError('bad timeout')
        evidence=s.get('required_evidence')
        if not isinstance(evidence,list) or not evidence or not all(isinstance(x,str) and x and Path(x).is_absolute() for x in evidence):raise ValueError('absolute evidence paths required')
        if any(Path(x).exists() or Path(x).is_symlink() for x in evidence):raise ValueError('refusing stale evidence before maintenance')

def stop_group(p):
    if p.poll() is not None:return
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=8)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid,signal.SIGKILL);p.wait()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('--out',required=True);a=ap.parse_args()
    d=json.loads(Path(a.plan).read_text());validate_plan(d)
    root=Path(a.out);root.mkdir(parents=True,exist_ok=False);root.chmod(0o700)
    start=time.monotonic(); outcomes=[]
    for i,s in enumerate(d['stages']):
        left=d['budget_sec']-(time.monotonic()-start)
        if left<1:outcomes.append({'id':s['id'],'status':'NOT_RUN_BUDGET'});break
        print(f"[{i+1}/{len(d['stages'])}] START {s['id']}",flush=True)
        for f in s['required_evidence']:
            if Path(f).exists():raise RuntimeError('refusing stale evidence; choose fresh run paths')
        stamp=time.time();timed=False;env=os.environ.copy();env['LAB_RUN_ID']=d['run_id']
        p=subprocess.Popen(s['argv'],cwd=Path(s['cwd']).expanduser(),env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
        deadline=time.monotonic()+min(left,s['timeout_sec']);pending=b''
        with (root/(s['id']+'.log')).open('w') as log:
            try:
                while p.poll() is None:
                    if time.monotonic()>deadline:timed=True;stop_group(p);break
                    ready,_,_=select.select([p.stdout],[],[],.25)
                    if ready:
                        part=os.read(p.stdout.fileno(),65536);pending+=part
                        while b'\n' in pending:
                            line,pending=pending.split(b'\n',1);clean=redact(line.decode('utf-8','replace'))
                            log.write(clean+'\n');log.flush();print(clean,flush=True)
                # Do not block forever on descendants retaining stdout after parent exit.
                end_drain=time.monotonic()+2
                while time.monotonic()<end_drain:
                    rd,_,_=select.select([p.stdout],[],[],.1)
                    if not rd:break
                    part=os.read(p.stdout.fileno(),65536)
                    if not part:break
                    pending+=part
                if pending:log.write(redact(pending.decode('utf-8','replace')))
            finally:stop_group(p)
        ev=[]; missing=[]
        for f in s['required_evidence']:
            pth=Path(f)
            if pth.is_symlink() or not pth.is_file() or pth.stat().st_mtime<stamp-1:missing.append(f);continue
            ev.append({'path':str(pth),'sha256':hashlib.sha256(pth.read_bytes()).hexdigest()})
        status='TIMEOUT' if timed else ('COMMAND_FAILED' if p.returncode else ('INCOMPLETE' if missing else 'EVIDENCE_COLLECTED'))
        outcomes.append(dict(id=s['id'],status=status,exit=p.returncode,evidence=ev,missing=missing))
        (root/'progress.json').write_text(json.dumps(outcomes,indent=2)+'\n')
        print(f"[{i+1}/{len(d['stages'])}] {status} {s['id']}",flush=True)
        if status!='EVIDENCE_COLLECTED':break
    complete=len(outcomes)==len(d['stages']) and all(x['status']=='EVIDENCE_COLLECTED' for x in outcomes)
    result={'run_id':d['run_id'],'complete':complete,'elapsed_s':time.monotonic()-start,'stages':outcomes,'verdict':'REVIEW_REQUIRED' if complete else 'BLOCKED','note':'Commands and evidence collected. Numerical, quality and promotion gates are separate.'}
    (root/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n');print(result['verdict'],flush=True)
    raise SystemExit(0 if complete else 2)
if __name__=='__main__':main()
