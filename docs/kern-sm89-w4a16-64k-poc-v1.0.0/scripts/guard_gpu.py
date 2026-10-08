#!/usr/bin/env python3
"""Serialize this kit's GPU work; explicit production pause; restore on ordinary exit.
SIGKILL, power loss and machine failure cannot be handled by a Python finally block.
"""
import argparse, fcntl, json, os, signal, subprocess, sys, time, urllib.request
from pathlib import Path
UNIT='openclaw-qwen38-ninfer.service'
ROOT=Path(__file__).resolve().parents[1]

def run(cmd,**kw):return subprocess.run(cmd,**kw)
def main():
    p=argparse.ArgumentParser();p.add_argument('--allow-production-pause',action='store_true');p.add_argument('--timeout',type=int,default=3600);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    cmd=a.command
    if cmd and cmd[0]=='--':cmd=cmd[1:]
    if not cmd:raise SystemExit('A child command is required.')
    state=ROOT/'.state';state.mkdir(exist_ok=True)
    lock=open(Path(os.environ.get('XDG_RUNTIME_DIR',f'/tmp/kern-poc-{os.getuid()}'))/'kern-sm89-gpu0.lock','a') if os.environ.get('XDG_RUNTIME_DIR') else None
    if lock is None:
        d=Path(f'/tmp/kern-poc-{os.getuid()}');d.mkdir(mode=0o700,exist_ok=True);lock=(d/'kern-sm89-gpu0.lock').open('a')
    with lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        old_journal=state/'gpu-lease.json'
        if old_journal.exists():
            try:previous=json.loads(old_journal.read_text())
            except (ValueError,OSError):
                print('BLOCKED: previous maintenance journal is unreadable; inspect it before starting new work.');return 78
            if previous.get('restore_required'):
                print('BLOCKED: an earlier maintenance window has not been settled. Inspect .state/gpu-lease.json, verify production recovery, then archive the journal.');return 78
        status=run(['systemctl','is-active',UNIT],capture_output=True,text=True)
        was_active=status.returncode==0
        if was_active and not a.allow_production_pause:
            print('BLOCKED: production is active. Authorize a maintenance window explicitly; no service was stopped.');return 78
        journal={'guard_pid':os.getpid(),'unit':UNIT,'was_active':was_active,'restore_required':False,'started':time.time(),'command':cmd}
        journal_path=state/'gpu-lease.json'
        def save():journal_path.write_text(json.dumps(journal,indent=2))
        save();child=None;rc=78
        def interrupted(signum,frame):raise KeyboardInterrupt
        signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
        try:
            if was_active:
                # Write intent BEFORE stop; recovery must still run if stop/health checking fails.
                journal['restore_required']=True;save()
                run(['sudo','-n','systemctl','stop',UNIT],check=True)
            gpu=run(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],capture_output=True,text=True,check=True)
            if gpu.stdout.strip():raise RuntimeError('GPU still has compute processes; refusing to kill any process: '+gpu.stdout)
            child=subprocess.Popen(cmd,start_new_session=True)
            journal['child_pid']=child.pid;save()
            try:rc=child.wait(timeout=a.timeout)
            except subprocess.TimeoutExpired:print('INCOMPLETE: hard budget reached',flush=True);rc=124
        except KeyboardInterrupt:rc=130
        except Exception as e:print('ERROR: '+str(e),file=sys.stderr);rc=2
        finally:
            if child and child.poll() is None:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
            # The developer's stage must use foreground containers --rm, not detached daemons.
            if journal['restore_required']:
                try:
                    run(['sudo','-n','systemctl','start',UNIT],check=True)
                    deadline=time.monotonic()+300
                    while True:
                        try:
                            with urllib.request.urlopen('http://127.0.0.1:18343/v1/models',timeout=5) as resp:models=json.load(resp)
                            if any(x.get('id')=='openclaw/Qwen3.8-27B-WORK' for x in models.get('data',[])):break
                        except Exception:pass
                        if time.monotonic()>deadline:raise RuntimeError('production readiness did not recover')
                        time.sleep(2)
                    journal['restore_required']=False;journal['restored']=True
                except Exception as e:journal['restore_error']=str(e);rc=2
            journal['exit_code']=rc;journal['ended']=time.time();save()
        return rc
if __name__=='__main__':sys.exit(main())
