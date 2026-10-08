"""Mac controller: own a remote guard and a local bounded stage runner."""
import argparse,json,os,select,shlex,signal,subprocess,sys,threading,time
from pathlib import Path
from .runner import validate_plan,stop_group

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--plan',required=True);ap.add_argument('--out',required=True);ap.add_argument('--allow-prod-pause',action='store_true');a=ap.parse_args()
    d=json.loads(Path(a.plan).read_text());validate_plan(d);c=json.loads(Path(a.config).read_text())
    if not a.allow_prod_pause:raise SystemExit('No production pause approval: nothing stopped')
    host=c['ssh_host'];guard_path=c['remote_guard'];
    if host.startswith('-') or any(x.isspace() for x in host):raise SystemExit('invalid ssh host')
    remote=['python3','-u',guard_path,'--run-id',d['run_id'],'--allow-prod-pause','--ttl',str(d['budget_sec']+300)]
    g=subprocess.Popen(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3',host,shlex.join(remote)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=None,text=True,bufsize=1,start_new_session=True)
    child=None;stop=threading.Event();ready=False;code=2;restore_ok=False
    def interrupted(*_):raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        deadline=time.monotonic()+180
        while time.monotonic()<deadline and g.poll() is None:
            r,_,_=select.select([g.stdout],[],[],1)
            if r:
                line=g.stdout.readline();print('[guard] '+line.strip(),flush=True)
                if line.strip()=='LEASE_READY':ready=True;break
        if not ready:raise RuntimeError('remote lease not granted')
        def beat():
            while not stop.wait(15):
                try:g.stdin.write('PING\n');g.stdin.flush()
                except (OSError,ValueError):return
        threading.Thread(target=beat,daemon=True).start()
        child=subprocess.Popen([sys.executable,'-u','-m','tools.runner',a.plan,'--out',a.out],start_new_session=True)
        while child.poll() is None:
            if g.poll() is not None:stop_group(child);raise RuntimeError('lost remote GPU lease')
            time.sleep(.5)
        code=child.returncode
    finally:
        if child is not None:stop_group(child)
        stop.set()
        try:g.stdin.write('RELEASE\n');g.stdin.flush();g.stdin.close()
        except (OSError,ValueError):pass
        until=time.monotonic()+300
        while time.monotonic()<until:
            r,_,_=select.select([g.stdout],[],[],.5)
            if r:
                line=g.stdout.readline()
                if line:
                    print('[guard] '+line.strip(),flush=True)
                    if line.strip()=='LEASE_RESTORED':restore_ok=True
            if g.poll() is not None:break
        if g.poll() is None or g.returncode!=0 or not restore_ok:
            print('RECOVERY_REQUIRED: inspect remote maintenance journal and health endpoint',flush=True)
            code=3
    raise SystemExit(code)
if __name__=='__main__':main()
