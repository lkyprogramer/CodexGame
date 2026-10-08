"""Run the ORIGINAL three Java fixtures from the Mac controller.
This is an experiment harness, not a security sandbox for a hostile agent.
The final verifier is reconstructed from the immutable control copy.
"""
import argparse,hashlib,json,os,shutil,signal,subprocess,time
from pathlib import Path
from .runner import stop_group

def digest_tree(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and not p.is_symlink()}

def assert_regular(root):
    if any(p.is_symlink() for p in root.rglob('*')):raise ValueError('symlink in project')

def run(argv,cwd,log,seconds,env=None):
    with log.open('w') as f:
        p=subprocess.Popen(argv,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        try:p.wait(timeout=seconds)
        except subprocess.TimeoutExpired:stop_group(p);return 124
        return p.returncode

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    c=json.loads(Path(a.config).read_text());root=Path(__file__).resolve().parents[1];out=Path(a.out).expanduser();out.mkdir(parents=True,exist_ok=False);out.chmod(0o700)
    pi=Path(c['pi_bin']).expanduser()
    if not pi.is_file() or not os.access(pi,os.X_OK):raise SystemExit('Pi executable absent on CONTROLLER')
    if not shutil.which('java') or not shutil.which('javac'):raise SystemExit('JDK17+ required on CONTROLLER')
    for name in ['models.json']:
        if not (Path(c['pi_config_dir']).expanduser()/name).is_file():raise SystemExit('missing isolated Pi config')
    env=os.environ.copy();env['PI_CODING_AGENT_DIR']=str(Path(c['pi_config_dir']).expanduser());env['PI_SKIP_VERSION_CHECK']='1';env['PI_TELEMETRY']='0'
    for k in list(env):
        if any(x in k.upper() for x in ['PASSWORD','API_KEY','ACCESS_TOKEN','SECRET']):env.pop(k,None)
    rows=[]
    for src in sorted((root/'fixtures').glob('java-agent-*')):
        assert_regular(src);dst=out/(src.name+'-work');shutil.copytree(src,dst);before=digest_tree(src/'src/main')
        protected=digest_tree(src/'src/test');verify_hash=hashlib.sha256((src/'verify.sh').read_bytes()).hexdigest()
        start=time.monotonic();p=['env', 'PATH='+c.get('controller_path',os.environ['PATH']),str(pi),*c['pi_args'],'--', (src/'TASK.md').read_text()]
        rc=run(p,dst,out/(src.name+'.pi-private.log'),c.get('java_timeout_sec',300),env)
        changed=before!=digest_tree(dst/'src/main') if (dst/'src/main').is_dir() else False
        safe=not any(x.is_symlink() for x in dst.rglob('*'))
        protected_ok=safe and (dst/'src/test').is_dir() and (dst/'verify.sh').is_file() and protected==digest_tree(dst/'src/test') and verify_hash==hashlib.sha256((dst/'verify.sh').read_bytes()).hexdigest()
        trusted=out/(src.name+'-verify');shutil.copytree(src,trusted)
        if safe and (dst/'src/main').is_dir():
            shutil.rmtree(trusted/'src/main');shutil.copytree(dst/'src/main',trusted/'src/main')
        vr=run(['bash','verify.sh'],trusted,out/(src.name+'.verify.log'),60) if safe else 126
        rows.append(dict(case=src.name,pi_exit=rc,verify_exit=vr,protected_ok=protected_ok,source_changed=changed,elapsed_s=time.monotonic()-start,pass_case=rc==0 and vr==0 and protected_ok and changed))
        print(json.dumps(rows[-1],ensure_ascii=False),flush=True)
    (out/'java-results.json').write_text(json.dumps({'run_id':os.environ.get('LAB_RUN_ID'),'cases':rows,'source':'LIVE_PI_CONTROLLER','note':'Three compatibility smoke tasks; not statistical proof of equal intelligence.'},indent=2)+'\n')
    raise SystemExit(0 if all(x['pass_case'] for x in rows) else 1)
if __name__=='__main__':main()
