#!/usr/bin/env python3
"""Local durable sequencer: wait for remote measurements, then isolated Pi fixtures.
No work starts unless main() is explicitly invoked without --dry-run.
"""
from __future__ import annotations
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import socket
import subprocess
import time
import textwrap
import urllib.request
import uuid

NODE = '/Users/luo/.nvm/versions/node/v22.19.0/bin/node'
SCRIPT = Path(__file__).with_name('closed_loop.mjs').resolve()
DEFAULT_REMOTE = '/home/hhtele/ninfer-baseline-20261020/formal'
SSH = ['ssh', '-oBatchMode=yes', '-oConnectTimeout=20']
SEEDS = [1701, 2901, 4101]
UNKNOWN_OUTCOME_STATUSES = {'TIMEOUT', 'BUDGET_OR_POLICY_STOP', 'AGENT_ERROR','BUDGET_HARD_STOP'}

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def atomic(path, obj):
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w') as f:
        json.dump(obj, f, indent=2)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def descendant_pids(parent, listing):
    children = {}
    for line in listing.splitlines():
        try:
            pid, ppid = map(int, line.split())
        except ValueError:
            continue
        children.setdefault(ppid, []).append(pid)
    result = []
    def visit(pid):
        for child in children.get(pid, []):
            visit(child)
        result.append(pid)
    visit(parent)
    return result


def terminate_case_tree(pid):
    # Pi creates its own process group; parent-group-only KILL would leak it.
    listing = subprocess.run(['/bin/ps', '-axo', 'pid=,ppid='], capture_output=True, text=True, timeout=5).stdout
    for child in descendant_pids(pid, listing):
        try:
            os.kill(child, signal.SIGKILL)
        except ProcessLookupError:
            pass


def private_root(value):
    p = Path(value).resolve()
    if not str(p).startswith(('/tmp/', '/private/tmp/')):
        raise ValueError('local root must be below /tmp')
    p.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(p, 0o700)
    return p

def measurement_ready(snapshot, stage='all'):
    s, w = snapshot['status'], snapshot['watchdog']
    if w.get('stage') != stage:
        raise RuntimeError('remote formal watchdog was not stage all')
    if s.get('state') == 'NEEDS_ATTENTION' or w.get('state') in ('NEEDS_ATTENTION', 'STOPPED', 'STOPPING'):
        raise RuntimeError('remote measurement/watchdog needs attention')
    if s.get('resource_monitor_error'):
        raise RuntimeError('remote resource monitor failed')
    if s.get('pid') != w.get('child_pid') or not s.get('pid'):
        raise RuntimeError('remote status/watchdog PID mismatch')
    ready = s.get('state') == 'MEASUREMENT_STAGES_FINISHED' and w.get('state') == 'MEASUREMENT_STAGES_FINISHED'
    if not ready and w.get('state') != 'MONITORING':
        raise RuntimeError('remote watchdog not monitoring or finished')
    if not ready:
        heartbeat = dt.datetime.fromisoformat(w['heartbeat_utc'].replace('Z', '+00:00'))
        if (dt.datetime.now(dt.timezone.utc) - heartbeat).total_seconds() > 900:
            raise RuntimeError('remote watchdog heartbeat stale')
    if stage in ('priority','remaining'):
        if s.get('stage') != stage or not snapshot.get('manifest_sha256') or s.get('manifest_sha256') != snapshot['manifest_sha256']:
            raise RuntimeError('slim stage/manifest identity mismatch')
    return ready

class Orchestrator:
    def __init__(self, root, remote_root=DEFAULT_REMOTE, poll_s=300, case_timeout_s=600,
                 parent_timeout_s=2400, model='openclaw/Qwen3.8-27B-WORK', execute=subprocess.run,
                 sleeper=time.sleep, opener=urllib.request.urlopen, mode='full', external_manifest=None):
        self.root = private_root(root)
        self.mode=mode
        if mode not in ('full','slim'): raise ValueError('unknown plan mode')
        self.seeds=[1701] if mode=='slim' else SEEDS
        self.external_manifest=Path(external_manifest).resolve() if external_manifest else None
        self.remote_root = str(Path(remote_root))
        if not self.remote_root.startswith('/home/hhtele/ninfer-baseline-') or not self.remote_root.endswith('/slim-v1' if mode=='slim' else '/formal'):
            raise ValueError('unexpected remote measurement root')
        if poll_s < 1:
            raise ValueError('poll interval must be positive')
        if not 1 <= case_timeout_s <= 2280 or not case_timeout_s + 90 <= parent_timeout_s <= 2400:
            raise ValueError('parent timeout must cover case + 90s and be <=2400s')
        self.collector = self.remote_root + '/closed-loop-collector'
        self.bin = str(Path(self.remote_root).parent / ('slim-bin-v1' if mode=='slim' else 'bin'))
        self.pi_root = self.root / 'pi-business'
        self.execute, self.sleep, self.open = execute, sleeper, opener
        self.poll_s, self.case_timeout_s, self.parent_timeout_s = poll_s, case_timeout_s, parent_timeout_s
        if model!='openclaw/Qwen3.8-27B-WORK': raise ValueError('unknown baseline model')
        self.model = model
        self.state_path = self.root / 'status.json'
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {
            'schema_version': 1, 'state': 'PREPARING', 'owner_token': uuid.uuid4().hex,
            'started_utc': utc(), 'completed': [], 'bridge_pid': None, 'tunnel_pid': None,
        }
        self.tunnel = None
        self.state['orchestrator_pid'] = os.getpid()
        expected = {'remote_root': self.remote_root, 'collector': self.collector, 'script_sha256': digest(SCRIPT),
                    'orchestrator_sha256': digest(__file__), 'qcb_adapter_sha256':digest(SCRIPT.with_name('qcb_adapter.mjs')), 'public_verify_sha256':digest(SCRIPT.with_name('public_verify.mjs')), 'model': model, 'case_timeout_s': case_timeout_s,
                    'parent_timeout_s': parent_timeout_s, 'seeds': self.seeds, 'mode':mode, 'external_manifest':str(self.external_manifest) if self.external_manifest else None}
        identity = self.root / 'identity.json'
        if identity.exists() and json.loads(identity.read_text()) != expected:
            raise RuntimeError('frozen orchestrator configuration changed; use a new root')
        atomic(identity, expected)

    def update(self, **values):
        self.state.update(values, heartbeat_utc=utc())
        atomic(self.state_path, self.state)

    def event(self, kind, **data):
        with (self.root / 'events.jsonl').open('a') as f:
            f.write(json.dumps({'utc': utc(), 'event': kind, **data})+'\n'); f.flush(); os.fsync(f.fileno())

    def remote(self, code):
        r = self.execute(SSH + ['29', shlex.join(['python3', '-c', code])], capture_output=True, text=True, timeout=50)
        if r.returncode:
            raise RuntimeError('SSH command failed: ' + r.stderr[-1500:])
        return json.loads(r.stdout)

    def snapshot(self, root):
        # Exactly the two task-owned status files; no logs or unrelated configuration.
        return self.remote(f"import json,hashlib;from pathlib import Path;p=Path({root!r});data={{k:json.loads((p/(k+'.json')).read_text()) for k in ['status','watchdog']}};data['manifest_sha256']=hashlib.sha256((p/'manifest.json').read_bytes()).hexdigest() if (p/'manifest.json').exists() else None;print(json.dumps(data))")

    def checked_snapshot(self, collector=False, stage=None, startup=False):
        failures = 0
        startup_attempts = 0
        while True:
            try:
                snap = self.snapshot(self.collector if collector else self.remote_root)
                if collector:
                    s, w = snap['status'], snap['watchdog']
                    if w.get('stage') != 'bridge' or w.get('state') != 'MONITORING' or s.get('state') in ('NEEDS_ATTENTION', 'STOPPING') or s.get('resource_monitor_error'):
                        raise RuntimeError('bridge watchdog/status unhealthy')
                    if s.get('pid') != w.get('child_pid'):
                        raise RuntimeError('bridge PID mismatch')
                    if s.get('state') != 'BRIDGE_WAITING':
                        raise RuntimeError('bridge is not ready to accept a new model request')
                    heartbeat = dt.datetime.fromisoformat(w['heartbeat_utc'].replace('Z', '+00:00'))
                    if (dt.datetime.now(dt.timezone.utc)-heartbeat).total_seconds() > 900:
                        raise RuntimeError('bridge watchdog heartbeat stale')
                    with self.open('http://127.0.0.1:18091/health', timeout=15) as r:
                        if r.status != 200:
                            raise RuntimeError('bridge health not 200')
                else:
                    measurement_ready(snap,stage or ('priority' if self.mode=='slim' else 'all'))
                self.event('remote_snapshot', collector=collector, snapshot=snap)
                return snap
            except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError) as exc:
                if startup and collector:
                    startup_attempts += 1
                    self.update(state='BRIDGE_STARTING',bridge_startup_checks=startup_attempts,last_remote_error=str(exc))
                    if startup_attempts>=36:raise RuntimeError('bridge startup readiness deadline exceeded; no model request') from exc
                    self.sleep(5)
                    continue
                failures += 1
                self.event('remote_check_failure', consecutive=failures, error=str(exc), collector=collector)
                self.update(remote_consecutive_failures=failures, last_remote_error=str(exc))
                if failures >= 3:
                    raise RuntimeError('three consecutive remote failures; no model retry') from exc
                self.sleep(self.poll_s)

    def prepare(self):
        if not (self.pi_root / 'manifest.json').exists():
            r = self.execute([NODE, str(SCRIPT), 'prepare', str(self.pi_root), self.mode], capture_output=True, text=True, timeout=60)
            (self.root / 'prepare.stdout.log').write_text(r.stdout)
            (self.root / 'prepare.stderr.log').write_text(r.stderr)
            if r.returncode:
                raise RuntimeError('fixture preparation failed')
        manifest = json.loads((self.pi_root / 'manifest.json').read_text())
        if len(manifest['cases']) < (8 if self.mode=='slim' else 20) or manifest.get('seeds') != self.seeds or manifest.get('repetitions') != len(self.seeds):
            raise RuntimeError('unexpected fixture manifest')
        return manifest

    def start_bridge(self):
        # A token receipt makes an interrupted SSH launch recoverable by read-only inspection.
        code = f'''import json,os,shutil,subprocess,hashlib
from pathlib import Path
p=Path({self.collector!r});p.mkdir(mode=0o700,exist_ok=True)
receipt=p/'local-orchestrator-owner.json'
owner={self.state['owner_token']!r}
if receipt.exists():
 old=json.loads(receipt.read_text())
 if old['owner_token']!=owner:raise RuntimeError('collector belongs to another orchestrator')
 pid=old.get('pid')
 if pid and Path('/proc/'+str(pid)+'/cmdline').exists():
  args=Path('/proc/'+str(pid)+'/cmdline').read_bytes().split(b'\\0')
  if {str(Path(self.bin)/'guardian.py').encode()!r} in args and {self.collector.encode()!r} in args:
   print(json.dumps(old));raise SystemExit(0)
  raise RuntimeError('previous bridge PID reused')
source=Path({self.remote_root!r})/'expected-baseline.json'
target=p/'expected-baseline.json'
if target.exists() and target.read_bytes()!=source.read_bytes():raise RuntimeError('baseline identity mismatch')
if not target.exists():shutil.copyfile(source,target)
log=(p/'guardian-bridge.log').open('ab')
argv=['nohup','python3',{str(Path(self.bin)/'guardian.py')!r},'--root',str(p),'--runner',{str(Path(self.bin)/'runner.py')!r},'--stage','bridge']
child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
data={{'owner_token':owner,'pid':child.pid,'argv':argv}}
tmp=receipt.with_suffix('.tmp');tmp.write_text(json.dumps(data));os.replace(tmp,receipt)
print(json.dumps(data))'''
        self.update(bridge_launch_attempted=True)
        receipt = self.remote(code)
        self.update(bridge_pid=receipt['pid'])
        self.event('bridge_started', receipt=receipt)

    def start_tunnel(self):
        # Stop only our previously recorded tunnel, never a generic port owner.
        self.stop_tunnel()
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 18091))
        argv = SSH + ['-oExitOnForwardFailure=yes', '-oServerAliveInterval=30', '-oServerAliveCountMax=3',
                      '-N', '-L', '18091:127.0.0.1:18090', '29']
        log = (self.root / 'tunnel.log').open('ab')
        self.tunnel = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
        self.update(tunnel_pid=self.tunnel.pid, tunnel_argv=argv)
        for _ in range(30):
            if self.tunnel.poll() is not None:
                raise RuntimeError('own SSH tunnel exited')
            try:
                with socket.create_connection(('127.0.0.1', 18091), timeout=1):
                    return
            except OSError:
                self.sleep(1)
        raise RuntimeError('own SSH tunnel not listening')

    def stop_tunnel(self):
        pid = self.state.get('tunnel_pid')
        if not pid:
            return
        r = self.execute(['/bin/ps', '-p', str(pid), '-o', 'command='], capture_output=True, text=True, timeout=5)
        command = r.stdout.strip()
        if command and 'ssh ' in command and '18091:127.0.0.1:18090' in command and '-N' in command and command.endswith('29'):
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            self.event('tunnel_stopped', pid=pid)
        elif command:
            raise RuntimeError('tunnel PID command mismatch; refusing to kill')
        self.update(tunnel_pid=None)

    def stop_bridge(self):
        if not self.state.get('bridge_launch_attempted'):
            return
        code = f'''import json,os,signal,time
from pathlib import Path
p=Path({self.collector!r})/'local-orchestrator-owner.json'
if not p.exists():print(json.dumps({{'state':'NO_OWN_RECEIPT'}}));raise SystemExit(0)
r=json.loads(p.read_text())
if r['owner_token']!={self.state['owner_token']!r}:raise RuntimeError('bridge owner mismatch')
pid=r['pid'];proc=Path('/proc/'+str(pid)+'/cmdline')
if not proc.exists():print(json.dumps({{'state':'ALREADY_EXITED'}}));raise SystemExit(0)
a=proc.read_bytes().split(b'\\0')
if {str(Path(self.bin)/'guardian.py').encode()!r} not in a or {self.collector.encode()!r} not in a or b'bridge' not in a:raise RuntimeError('bridge PID command mismatch')
os.kill(pid,signal.SIGTERM)
for _ in range(35):
 if not proc.exists():break
 time.sleep(1)
print(json.dumps({{'state':'TERM_SENT','pid':pid,'still_present':proc.exists()}}))'''
        result = self.remote(code)
        self.event('bridge_cleanup', result=result)
        if result.get('still_present'):
            raise RuntimeError('own guardian still present after TERM; no unsafe KILL')
        self.update(bridge_pid=None, bridge_launch_attempted=False)

    def start_caffeinate(self):
        self.stop_caffeinate()
        argv = ['/usr/bin/caffeinate', '-i', '-w', str(os.getpid())]
        self.caffeinate = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                          stderr=subprocess.DEVNULL, start_new_session=True)
        self.update(caffeinate_pid=self.caffeinate.pid, caffeinate_watch_pid=os.getpid())
        self.event('caffeinate_started_for_pi_only', pid=self.caffeinate.pid)

    def stop_caffeinate(self):
        pid = self.state.get('caffeinate_pid')
        if not pid:
            return
        r = self.execute(['/bin/ps', '-p', str(pid), '-o', 'command='], capture_output=True, text=True, timeout=5)
        command = r.stdout.strip()
        if command:
            expected = ['/usr/bin/caffeinate', '-i', '-w', str(self.state['caffeinate_watch_pid'])]
            if shlex.split(command) != expected:
                raise RuntimeError('caffeinate PID command mismatch; refusing cleanup')
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            if getattr(self, 'caffeinate', None) is not None:
                self.caffeinate.wait(timeout=10)
            self.event('caffeinate_stopped', pid=pid)
        self.update(caffeinate_pid=None)

    def stop_case_parent(self):
        pid = self.state.get('case_parent_pid')
        if not pid:
            return
        result = self.execute(['/bin/ps', '-p', str(pid), '-o', 'command='], capture_output=True, text=True, timeout=5)
        command = result.stdout.strip()
        if command:
            if str(SCRIPT) not in command or str(self.pi_root) not in command or NODE not in command:
                raise RuntimeError('case parent PID command mismatch; refusing cleanup')
            terminate_case_tree(pid)
            self.event('case_parent_stopped', pid=pid)
        self.update(case_parent_pid=None)

    def case(self, case, repeat):
        path = self.pi_root / 'runs' / case / f'repeat-{repeat}'
        summary = path / 'summary.json'
        if summary.exists():
            data = json.loads(summary.read_text())
            identity = json.loads((path/'identity.json').read_text())
            if data['id'] != case or data['repeat'] != repeat or identity.get('seed') != self.seeds[repeat-1] or identity.get('samplingProfile') != 'PRODUCTION' or identity.get('thinking') != 'medium' or identity.get('maxTokens') != 32768 or identity.get('model') != self.model or identity.get('executionAttempt',1)!=self.state.get('external_attempts',{}).get(case,1):
                raise RuntimeError('durable case identity mismatch')
            self.event('case_already_recorded', case=case, repeat=repeat, status=data['status'])
            if data['status'] in UNKNOWN_OUTCOME_STATUSES:
                raise RuntimeError('recorded case may have unfinished upstream work; no automatic continuation')
            return data
        if path.exists():
            raise RuntimeError(f'incomplete case directory {case}/{repeat}; unknown model outcome, no retry')
        before = self.checked_snapshot(collector=True)
        self.update(state='PI_CASE_RUNNING', current_case=case, current_repeat=repeat, current_seed=self.seeds[repeat-1])
        self.event('case_start', case=case, repeat=repeat, remote=before)
        env = {k: os.environ[k] for k in ('PATH', 'LANG') if k in os.environ}
        env.update(BASELINE_TIMEOUT_MS=str(self.case_timeout_s*1000), BASELINE_MAX_TOKENS='32768',
                   BASELINE_THINKING='medium', BASELINE_SAMPLING_PROFILE='PRODUCTION',BASELINE_CASE_ORDINAL=str(self.state.get('current_ordinal','unset')),BASELINE_EXECUTION_ATTEMPT=str(self.state.get('external_attempts',{}).get(case,1)))
        # Capture the parent process and Pi subprocess in the same detached process group.
        log_root = self.root / 'case-logs'; log_root.mkdir(exist_ok=True)
        with (log_root/f'{case}-{repeat}.stdout.log').open('wb') as out, (log_root/f'{case}-{repeat}.stderr.log').open('wb') as err:
            process = subprocess.Popen([NODE, str(SCRIPT), 'run', str(self.pi_root), case, str(repeat),
                                        'http://127.0.0.1:18091/v1', self.model], env=env, stdout=out, stderr=err,
                                       start_new_session=True)
            self.update(case_parent_pid=process.pid, model_calls_attempted=True)
            try:
                code = process.wait(timeout=self.parent_timeout_s)
            except subprocess.TimeoutExpired:
                terminate_case_tree(process.pid); process.wait()
                raise RuntimeError(f'case parent timeout {case}/{repeat}; unknown result, no retry')
            except BaseException:
                terminate_case_tree(process.pid); process.wait(); raise
        self.update(case_parent_pid=None)
        if code or not summary.exists():
            raise RuntimeError(f'case executor failed {case}/{repeat}; no model retry')
        data = json.loads(summary.read_text())
        after = self.checked_snapshot(collector=True)
        atomic(path/'remote-metric-window.json', {'before': before, 'after': after,
               'qualification': 'SERIAL_REQUEST_WINDOW_NOT_PER_REQUEST_JOIN', 'case': case, 'repeat': repeat})
        self.event('case_finished', case=case, repeat=repeat, status=data['status'], remote=after)
        if data['status'] in UNKNOWN_OUTCOME_STATUSES:
            raise RuntimeError('case may have unfinished upstream work; no further model requests')
        return data

    def run_remaining(self):
        try:
            # Bridge and tunnel have been fully cleaned before handing back the GPU.
            self.update(state='STARTING_REMAINING')
            cases=self.state.get('completed',[])
            if len(cases)!=8 or len({c['id'] for c in cases})!=8 or any(c.get('repeat')!=1 or c.get('status') not in ('PASS','FAIL','OUTPUT_LIMIT') for c in cases):
                raise RuntimeError('remaining requires eight known coding outcomes')
            handoff={'known_completed_cases':8,'cases':cases,'unknown_outcomes':False,
                     'local_summary_sha256':digest(self.root/'summary.json'),'completed_utc':utc(),
                     'external_preparation':self.external_state()}
            code=f"""import json,os,subprocess,hashlib
    from pathlib import Path
    p=Path({self.remote_root!r});receipt=p/'local-remaining-owner.json';owner={self.state['owner_token']!r}
    handoff=json.loads({json.dumps(handoff)!r});handoff['manifest_sha256']=hashlib.sha256((p/'manifest.json').read_bytes()).hexdigest()
    hp=p/'coding-handoff.json'
    if hp.exists():
     old_handoff=json.loads(hp.read_text())
     for key in ['manifest_sha256','known_completed_cases','cases','unknown_outcomes','local_summary_sha256']:
      if old_handoff.get(key)!=handoff.get(key):raise RuntimeError('coding handoff identity changed')
    else:
     tmp=hp.with_suffix('.tmp');tmp.write_text(json.dumps(handoff));os.replace(tmp,hp)
    if receipt.exists():
     old=json.loads(receipt.read_text())
     if old['owner_token']!=owner:raise RuntimeError('remaining owner mismatch')
     print(json.dumps(old));raise SystemExit(0)
    argv=['nohup','python3',{str(Path(self.bin)/'guardian.py')!r},'--root',str(p),'--runner',{str(Path(self.bin)/'slim_runner.py')!r},'--stage','remaining']
    log=(p/'guardian-remaining.log').open('ab');child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);log.close()
    data={{'owner_token':owner,'pid':child.pid,'argv':argv}};tmp=receipt.with_suffix('.tmp');tmp.write_text(json.dumps(data));os.replace(tmp,receipt);print(json.dumps(data))"""
            code=textwrap.dedent('    '+code)
            compile(code,'remote_remaining_launch','exec')
            receipt=self.remote(code);self.event('remaining_started',receipt=receipt)
            self.update(state='WAITING_REMAINING',remaining_supervisor_pid=receipt['pid'])
            self.sleep(self.poll_s)
            while not measurement_ready(self.checked_snapshot(stage='remaining'),'remaining'):
                self.sleep(self.poll_s)
            self.update(state='REMAINING_RECORDED',remaining_done=True,finished_utc=utc(),external_repositories=self.external_state())
            self.continue_external()
        except BaseException as exc:
            self.update(state='NEEDS_ATTENTION',error=type(exc).__name__+': '+str(exc))
            raise

    def external_state(self):
        if not self.external_manifest or not self.external_manifest.exists():
            return {'status':'PENDING_SOURCE_MANIFEST','cases':[]}
        manifest=json.loads(self.external_manifest.read_text())
        cases=manifest.get('cases',[])
        return {'status':'READY' if len(cases)==2 and all(c.get('status')=='READY' for c in cases) else 'BLOCKED' if any(c.get('status')=='BLOCKED' for c in cases) else 'PENDING',
                'manifest_sha256':digest(self.external_manifest),
                'cases':[{'case_id':c['case_id'],'status':c.get('status','UNKNOWN')} for c in cases]}

    def external_cases_active(self):
        result=self.execute([NODE,str(SCRIPT),'add-external',str(self.pi_root),str(self.external_manifest)],capture_output=True,text=True,timeout=120)
        if result.returncode:raise RuntimeError('external preparation failed; no model request started')
        entries=json.loads(result.stdout)
        if len(entries)!=2:raise RuntimeError('expected two frozen external repositories')
        completed=[]
        for ordinal,entry in enumerate(entries,9):
            self.update(current_ordinal=ordinal)
            row=self.case(entry['id'],1)
            completed.append({'id':row['id'],'repeat':1,'status':row['status']})
            self.update(external_cases=completed)
        atomic(self.root/'external-summary.json',{'recorded_cases':len(completed),'planned_cases':2,'cases':completed,
                'qualification':'RECORDED_NOT_OPTIMIZATION_ACCEPTANCE','preparation_manifest_sha256':digest(self.external_manifest)})
        self.update(external_done=True)

    def continue_external(self):
        try:
            if self.state.get('external_done'):
                self.update(state='MEASUREMENTS_RECORDED_NOT_BASELINE_PASS',finished_utc=utc());return
            while True:
                state=self.external_state();self.update(state='WAITING_EXTERNAL_SOURCES',external_repositories=state)
                if state['status']=='BLOCKED':
                    self.update(state='EXTERNAL_REPOSITORIES_BLOCKED_NOT_BASELINE_PASS');return
                if state['status']=='READY':break
                if not self.external_manifest:
                    self.update(state='EXTERNAL_MANIFEST_UNCONFIGURED_NOT_BASELINE_PASS');return
                self.sleep(self.poll_s)
            errors=[]
            try:
                self.start_bridge();self.start_tunnel();self.checked_snapshot(collector=True,startup=True);self.start_caffeinate()
                self.external_cases_active()
            except BaseException as exc:
                errors.append(type(exc).__name__+': '+str(exc));self.update(state='NEEDS_ATTENTION',error=errors[-1]);raise
            finally:
                for cleanup in (self.stop_case_parent,self.stop_tunnel,self.stop_bridge,self.stop_caffeinate):
                    try:cleanup()
                    except Exception as exc:errors.append('cleanup: '+str(exc))
                if errors:self.update(state='NEEDS_ATTENTION',errors=errors)
            if errors:raise RuntimeError('external cleanup failed')
            self.update(state='MEASUREMENTS_RECORDED_NOT_BASELINE_PASS',finished_utc=utc(),external_repositories=state)
        except BaseException as exc:
            self.update(state='NEEDS_ATTENTION',error=type(exc).__name__+': '+str(exc))
            raise

    def verify_recovery_evidence(self):
        proof=json.loads((self.root/'recovery.json').read_text())
        if proof.get('schema_version')!=1 or proof.get('kind')!='KNOWN_CODING_PRE_MODEL_PREPARATION_RECOVERY':
            raise RuntimeError('unknown recovery evidence')
        source=Path(proof['source_root']).resolve()
        if not str(source).startswith(('/tmp/','/private/tmp/')):raise RuntimeError('unexpected recovery source')
        for relative,expected_hash in proof['source_artifacts'].items():
            if Path(relative).is_absolute() or '..' in Path(relative).parts:raise RuntimeError('unsafe recovery artifact')
            if digest(source/relative)!=expected_hash:raise RuntimeError('prior evidence changed; no recovery requests')
        for artifact,expected_hash in proof.get('related_evidence',{}).items():
            if not Path(artifact).is_absolute() or digest(artifact)!=expected_hash:raise RuntimeError('related recovery/drain evidence changed')
        expected_ids=[c['id'] for c in json.loads((source/'plan.json').read_text())['cases']]
        cases=proof['known_completed_cases']
        if len(expected_ids)!=8 or [c['id'] for c in cases]!=expected_ids or cases!=self.state.get('completed'):
            raise RuntimeError('recovery eight-case identity mismatch')
        for case in cases:
            saved=source/'pi-business'/'runs'/case['id']/'repeat-1'
            result=json.loads((saved/'summary.json').read_text());identity=json.loads((saved/'identity.json').read_text())
            if result.get('status')!=case['status'] or result.get('status') not in ('PASS','FAIL','OUTPUT_LIMIT') or identity.get('maxTokens')!=32768 or identity.get('seed')!=1701 or identity.get('thinking')!='medium':
                raise RuntimeError('unknown or changed prior model outcome')
        attempts=proof.get('authorized_external_attempts',{})
        if attempts:
            if set(attempts)!={'google__gson-2158','javaparser__javaparser-4561'} or any(type(v) is not int or v<1 for v in attempts.values()):raise RuntimeError('invalid explicit external attempts')
            if self.state.get('external_attempts')!=attempts:raise RuntimeError('external attempt authorization mismatch')
        self.event('known_coding_recovery_verified',source_root=str(source),recovery_sha256=digest(self.root/'recovery.json'),known_cases=8)

    def run(self, dry_run=False):
        if self.mode=='slim' and not dry_run:
            if self.state.get('state') == 'RECOVERED_KNOWN_CODING' or (self.root/'recovery.json').exists():
                if self.state.get('state')=='NEEDS_ATTENTION':raise RuntimeError('unknown or failed continuation requires explicit recovery; no automatic model retry')
                self.verify_recovery_evidence()
                if self.state.get('remaining_done') and self.state.get('external_done'):return
                if self.state.get('state') in ('STARTING_REMAINING','WAITING_REMAINING','CODING_RECORDED'):
                    self.run_remaining();return
                self.continue_external()
                if not self.state.get('external_done'):raise RuntimeError('external coding not completed; remaining not started')
                self.update(state='CODING_RECORDED')
                self.run_remaining();return
            if self.state.get('state') in ('STARTING_REMAINING','WAITING_REMAINING','CODING_RECORDED'):
                self.run_remaining();return
            if self.state.get('state') in ('REMAINING_RECORDED','WAITING_EXTERNAL_SOURCES'):
                self.continue_external();return
        manifest = self.prepare()
        plan = [{'id': c['id'], 'repeat': r, 'seed': self.seeds[r-1]} for c in (manifest['cases'][:8] if self.mode=='slim' else manifest['cases']) for r in range(1,len(self.seeds)+1)]
        atomic(self.root/'plan.json', {'cases': plan, 'count': len(plan), 'remote_root': self.remote_root,
               'collector': self.collector, 'endpoint': 'http://127.0.0.1:18091/v1', 'dry_run': dry_run})
        if dry_run:
            self.update(state=self.state['state'] if self.state['state'] in ('FINISHED', 'NEEDS_ATTENTION') else 'DRY_RUN_PREPARED', case_count=len(plan), remote_actions=False, model_calls=False)
            return
        if self.state.get('state') in ('NEEDS_ATTENTION', 'FINISHED','MEASUREMENTS_RECORDED_NOT_BASELINE_PASS','EXTERNAL_REPOSITORIES_BLOCKED_NOT_BASELINE_PASS'):
            raise RuntimeError('terminal local state; preserving results, no implicit restart')
        errors = []
        rows = []
        try:
            for item in plan:
                path = self.pi_root/'runs'/item['id']/f"repeat-{item['repeat']}"
                if path.exists() and not (path/'summary.json').exists():
                    raise RuntimeError('incomplete existing case; unknown model outcome, no retry: '+str(path))
            self.state.pop('model_calls', None)
            self.update(state='WAITING_REMOTE_MEASUREMENTS', remote_actions=True)
            while not measurement_ready(self.checked_snapshot(), 'priority' if self.mode=='slim' else 'all'):
                self.sleep(self.poll_s)
            self.start_bridge()
            self.start_tunnel()
            self.checked_snapshot(collector=True,startup=True)
            self.start_caffeinate()
            for ordinal,item in enumerate(plan,1):
                self.update(current_ordinal=ordinal)
                data = self.case(item['id'], item['repeat']); rows.append(data)
                self.update(completed=[{'id': x['id'], 'repeat': x['repeat'], 'status': x['status']} for x in rows])
            if self.mode=='slim' and self.external_state()['status']=='READY':
                self.external_cases_active()
            self.update(state='PI_CASES_RECORDED', current_case=None, current_repeat=None)
        except BaseException as exc:
            errors.append(type(exc).__name__+': '+str(exc))
            self.update(state='NEEDS_ATTENTION', error=errors[-1])
        finally:
            for cleanup in (self.stop_case_parent, self.stop_tunnel, self.stop_bridge, self.stop_caffeinate):
                try:
                    cleanup()
                except Exception as exc:
                    errors.append('cleanup: '+str(exc)); self.event('cleanup_failure', error=str(exc))
            durable = {(r['id'], r['repeat']): r for r in rows}
            for item in plan:
                saved = self.pi_root/'runs'/item['id']/f"repeat-{item['repeat']}"/'summary.json'
                if saved.exists():
                    try:
                        row = json.loads(saved.read_text())
                        if row['id'] != item['id'] or row['repeat'] != item['repeat']:
                            raise ValueError('case identity mismatch')
                        durable[(row['id'], row['repeat'])] = row
                    except (ValueError, KeyError) as exc:
                        errors.append('invalid durable summary '+str(saved)+': '+str(exc))
            rows = list(durable.values())
            self.update(completed=[{'id': x['id'], 'repeat': x['repeat'], 'status': x['status']} for x in rows])
            counts = {}
            for row in rows:
                counts[row['status']] = counts.get(row['status'], 0)+1
            atomic(self.root/'summary.json', {'recorded_cases': len(rows), 'planned_cases': len(plan),
                   'case_status_counts': counts, 'errors': errors, 'finished_utc': utc(),
                   'qualification': 'RECORDED_NOT_OPTIMIZATION_ACCEPTANCE', 'profile': 'ISOLATED_PI_FIXTURE', 'samplingProfile': 'PRODUCTION', 'thinking': 'medium', 'max_tokens': 32768, 'seeds': self.seeds, 'cases': self.state['completed'], 'remote_collector': self.collector})
            self.update(state='NEEDS_ATTENTION' if errors else ('CODING_RECORDED' if self.mode=='slim' else 'FINISHED'), finished_utc=utc(), errors=errors)
        if errors:
            raise RuntimeError('; '.join(errors))
        if self.mode=='slim':
            self.run_remaining()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', required=True)
    p.add_argument('--mode', choices=['full','slim'], default='full')
    p.add_argument('--external-manifest')
    p.add_argument('--remote-root')
    p.add_argument('--poll-seconds', type=int, default=300)
    p.add_argument('--case-timeout-seconds', type=int, default=600)
    p.add_argument('--parent-timeout-seconds', type=int, default=2400)
    p.add_argument('--model', default='openclaw/Qwen3.8-27B-WORK')
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args(); os.umask(0o077)
    root = private_root(a.root)
    with (root/'orchestrator.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        runner = Orchestrator(root, a.remote_root or ('/home/hhtele/ninfer-baseline-20261020/slim-v1' if a.mode=='slim' else DEFAULT_REMOTE), a.poll_seconds, a.case_timeout_seconds,
                              a.parent_timeout_seconds, a.model, mode=a.mode, external_manifest=a.external_manifest)
        def stop(signum, frame):
            raise RuntimeError('orchestrator interrupted by signal '+str(signum))
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        try:
            runner.run(a.dry_run)
        except BaseException as exc:
            runner.update(state='NEEDS_ATTENTION',error=type(exc).__name__+': '+str(exc))
            raise

if __name__ == '__main__':
    main()
