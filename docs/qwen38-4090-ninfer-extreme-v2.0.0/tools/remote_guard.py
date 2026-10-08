#!/usr/bin/env python3
"""GPU-host maintenance lease. Explicit opt-in; only named service is privileged.
Runs on Debian GPU host with stdlib. Keep stdin open and send heartbeats.
EOF or TTL triggers cleanup/restore. SIGKILL/power loss needs journal recovery.
"""
import argparse,fcntl,json,os,re,select,signal,subprocess,sys,time,urllib.request
from pathlib import Path
UNIT='openclaw-qwen38-ninfer.service'
MODEL_ID='openclaw/Qwen3.8-27B-WORK'
# Both the compat proxy (18343, what systemd tracks) and the native engine (18030) must answer:
# a unit can stay 'active' while the container is gone if someone bypassed systemd with docker rm.
HEALTH_PORTS=(18343,18030)
# ExecStop=docker rm -f releases VRAM asynchronously; poll instead of reading nvidia-smi once.
FREE_MIB_REQUIRED=20000;FREE_POLL_SEC=30

def cmd(argv,check=True):
    r=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=90)
    if check and r.returncode:raise RuntimeError('command failed: '+argv[0]+' (credentials/output withheld)')
    return r

class ProductionLease:
    def __init__(self,active,stop,start):
        self.active=active;self.stop=stop;self.start=start;self.was_active=False;self.stop_attempted=False
    def acquire(self,allow):
        if not allow:raise RuntimeError('explicit production pause approval required')
        self.was_active=bool(self.active())
        if self.was_active:
            self.stop_attempted=True;self.stop()
    def restore(self):
        if self.was_active and self.stop_attempted:self.start()

def write_journal(p,d):
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(d,indent=2)+'\n');tmp.chmod(0o600);os.replace(tmp,p)

def restore_sequence(cleanup_action, restore_action, health_action):
    """Always attempt restoration even if candidate cleanup fails.
    Return redacted stage labels; never propagate raw command output/secrets.
    """
    errors=[]
    for label, action in [('cleanup',cleanup_action),('restore',restore_action),('health',health_action)]:
        try:action()
        except Exception:errors.append(label+'_failed')
    return errors

def models_endpoint_ok(port):
    try:
        with urllib.request.urlopen('http://127.0.0.1:%d/v1/models'%port,timeout=3) as r:
            value=json.loads(r.read(1<<20))
    except Exception:return False
    ids=[x.get('id') for x in value.get('data',[])]+[x.get('name') for x in value.get('models',[])]
    return MODEL_ID in ids

def check_production_ready(was_active,timeout_sec=120):
    if not was_active:return
    if cmd(['systemctl','is-active','--quiet',UNIT],False).returncode!=0:
        raise RuntimeError('production did not return active')
    until=time.monotonic()+timeout_sec
    while time.monotonic()<until:
        if all(models_endpoint_ok(p) for p in HEALTH_PORTS):return
        time.sleep(2)
    raise RuntimeError('production model endpoint not ready on all of ports %s'%','.join(map(str,HEALTH_PORTS)))

def wait_gpu_free(query=None,required_mib=FREE_MIB_REQUIRED,poll_sec=FREE_POLL_SEC,sleep=time.sleep,clock=time.monotonic):
    """Poll free VRAM until the paused service has actually released it. Never kills unknown PIDs."""
    query=query or (lambda:cmd(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits']).stdout.splitlines())
    until=clock()+poll_sec;last=None
    while True:
        free=query()
        if len(free)!=1:raise RuntimeError('unexpected nvidia-smi output (single GPU expected)')
        last=int(free[0].strip())
        if last>=required_mib:return last
        if clock()>=until:break
        sleep(2)
    raise RuntimeError('GPU not empty %ds after approved service pause (free=%d MiB); do not kill unknown workloads'%(poll_sec,last))

def cleanup(run_id):
    r=cmd(['docker','ps','-aq','--filter','label=qwen38.lab.run='+run_id],False)
    for ident in r.stdout.splitlines():
        if re.fullmatch('[0-9a-f]{12,64}',ident):cmd(['docker','stop','--time','10',ident],False)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-id',required=True);ap.add_argument('--allow-prod-pause',action='store_true');ap.add_argument('--ttl',type=int,default=3900);ap.add_argument('--recover',action='store_true');a=ap.parse_args()
    if not re.fullmatch('[A-Za-z0-9_-]{1,64}',a.run_id) or not 60<=a.ttl<=7200:raise SystemExit('invalid lease arguments')
    root=Path.home()/'.cache/qwen38-extreme';root.mkdir(parents=True,exist_ok=True);root.chmod(0o700)
    lock=(root/'gpu.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    jp=root/'maintenance.json'
    if jp.exists():
        old=json.loads(jp.read_text())
        if old.get('status') not in ['RESTORED','IDLE']:
            if not a.recover or a.run_id!=old.get('run_id'):raise SystemExit('unfinished maintenance journal; explicit matching --recover required')
            errors=restore_sequence(lambda:cleanup(a.run_id),lambda:cmd(['sudo','-n','systemctl','start',UNIT]) if old.get('was_active') else None,lambda:check_production_ready(old.get('was_active')))
            old['status']='RECOVERY_REQUIRED' if errors else 'RESTORED';old['recovery_errors']=errors;write_journal(jp,old)
            if errors:raise SystemExit('RECOVERY_REQUIRED')
            print('RECOVERED',flush=True);return
    if a.recover:raise SystemExit('no unfinished lease to recover')
    if not a.allow_prod_pause:raise SystemExit('production pause is not authorized')
    # Both stop and start must be authorized before either action happens.
    for action in ['stop','start']:
        cmd(['sudo','-n','-l','systemctl',action,UNIT])
    active=lambda:cmd(['systemctl','is-active','--quiet',UNIT],False).returncode==0
    lease=ProductionLease(active,lambda:cmd(['sudo','-n','systemctl','stop',UNIT]),lambda:cmd(['sudo','-n','systemctl','start',UNIT]))
    data=dict(run_id=a.run_id,unit=UNIT,status='ACQUIRING',was_active=active(),pid=os.getpid(),started=time.time())
    write_journal(jp,data)
    def interrupted(*_):raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    if hasattr(signal,'SIGHUP'):signal.signal(signal.SIGHUP,interrupted)
    try:
        lease.acquire(True)
        free_mib=wait_gpu_free()
        data.update(status='HELD',was_active=lease.was_active,free_mib_after_pause=free_mib);write_journal(jp,data);print('LEASE_READY',flush=True)
        deadline=time.monotonic()+a.ttl;heartbeat=time.monotonic()
        while time.monotonic()<deadline:
            ready,_,_=select.select([sys.stdin],[],[],1)
            if ready:
                line=sys.stdin.readline()
                if not line or line.strip()=='RELEASE':break
                if line.strip()=='PING':heartbeat=time.monotonic()
            if time.monotonic()-heartbeat>90:raise RuntimeError('controller heartbeat lost')
    finally:
        # Attempt restoration regardless of whether docker cleanup succeeded.
        errors=restore_sequence(lambda:cleanup(a.run_id),lease.restore,lambda:check_production_ready(lease.was_active))
        data['status']='RECOVERY_REQUIRED' if errors else 'RESTORED';data['recovery_errors']=errors
        write_journal(jp,data)
        if errors:raise RuntimeError('RECOVERY_REQUIRED: '+','.join(errors))
        print('LEASE_RESTORED',flush=True)
if __name__=='__main__':main()
