"""29 task-owned offline/fault/recovery validation. Plan only unless --execute.
No remote access. Run on the target host with exclusive GPU ownership.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('/data/ocr/dual-ocr-20261028')
CPU = 'onnxocr-ppocrv6-small-cpu-compat'
STANDARD = {'mini': 'ocr29-mini-20261029', 'ovis': 'ocr29-ovis-20261029'}
OFFLINE = {c: f'ocr29-{c}-offline-20261029' for c in STANDARD}
# The child records no response body, prompt, image, environment, or payload.
FAULT_CHILD = r'''
import json, pathlib, sys, urllib.request
sys.path.insert(0, '/work')
from probe_cancel import prepare_prior
candidate, directory, port = sys.argv[1:]
out = pathlib.Path(directory)
prior, payload, provenance = prepare_prior(pathlib.Path('/work/results') / (candidate+'-probe-c0-v3/probe-result.json'))
budget = provenance['output_budget']
input_tokens = provenance['actual_input_tokens_reused']
if (type(budget) is not int or not 0 < budget <= 8192
        or payload['min_tokens'] != budget or payload['max_tokens'] != budget
        or type(input_tokens) is not int or input_tokens <= 0
        or input_tokens + budget + 512 > 16384):
    raise RuntimeError('Fault request must retain the verified bounded prior output budget')
(out/'fault-prepared.json').write_text(json.dumps({'status':'PREPARED', 'provenance':provenance,
    'fault_only': {'min_tokens':budget,'ignore_eos':True,'max_tokens':budget}}))
request = urllib.request.Request('http://127.0.0.1:'+port+'/v1/chat/completions',
    data=json.dumps(payload).encode(), headers={'Content-Type':'application/json','Authorization':'Bearer local-only'})
try:
    with urllib.request.urlopen(request, timeout=180) as response:
        response.read()
    (out/'fault-child-result.json').write_text(json.dumps({'status':'UNEXPECTED_COMPLETION'}))
    sys.exit(3)
except Exception as error:
    (out/'fault-child-result.json').write_text(json.dumps({'status':'REQUEST_FAILED','error_type':type(error).__name__}))
    sys.exit(7)
'''
HTTP_CHILD = r'''
import sys, urllib.request
request=urllib.request.Request(sys.argv[1],headers={'Authorization':'Bearer local-only'})
with urllib.request.urlopen(request,timeout=3) as response:
    print(response.read().decode())
'''


def write(path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(path)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def clone_command(info, candidate):
    """Clone the observed service config without publishing host ports."""
    config, host = info['Config'], info['HostConfig']
    expected = {'NanoCpus': 8000000000, 'CpusetCpus': '0-7', 'Memory': 32 * 1024**3,
                'ShmSize': 8 * 1024**3}
    if any(host.get(key) != value for key, value in expected.items()):
        raise RuntimeError('Standard CPU/RAM/shm limits differ from the frozen common policy')
    devices = host.get('DeviceRequests') or []
    if (len(devices) != 1 or devices[0].get('DeviceIDs') != ['0']
            or devices[0].get('Driver') not in ('nvidia', '')):
        raise RuntimeError('Standard container must explicitly use GPU device 0')
    if len(config.get('Entrypoint') or []) > 1:
        raise RuntimeError('Multiargument entrypoint cannot be cloned while preserving Config.Cmd')
    if any(mount['Type'] != 'bind' for mount in info['Mounts']):
        raise RuntimeError('Only existing bind mounts are supported; refusing an incomplete clone')
    args = ['docker', 'create', '--name', OFFLINE[candidate], '--network', 'none',
            '--cpus', '8', '--cpuset-cpus', '0-7', '--memory', '32g', '--shm-size', '8g',
            '--gpus', 'device=0']
    if config.get('Entrypoint'):
        args += ['--entrypoint', config['Entrypoint'][0]]
    if config.get('WorkingDir'):
        args += ['--workdir', config['WorkingDir']]
    if config.get('User'):
        args += ['--user', config['User']]
    for item in config.get('Env') or []:
        args += ['--env', item]
    for mount in info['Mounts']:
        if ',' in mount['Source'] or ',' in mount['Destination']:
            raise RuntimeError('Unsupported comma in bind mount')
        value = f"type=bind,src={mount['Source']},dst={mount['Destination']}"
        if not mount['RW']:
            value += ',readonly'
        propagation = mount.get('Propagation')
        if propagation:
            value += ',bind-propagation=' + propagation
        args += ['--mount', value]
    return args + [info['Image']] + (config.get('Cmd') or [])


def verify_clone(original, cloned):
    environments = []
    for info in (original, cloned):
        values = {}
        for item in info['Config'].get('Env') or []:
            key, separator, value = item.partition('=')
            if not separator or not key or key in values:
                raise RuntimeError('Duplicate or invalid environment key; clone refused')
            values[key] = value
        environments.append(values)
    if environments[0] != environments[1]:
        raise RuntimeError('Clone config mismatch: Env')
    for key in ('Cmd', 'Entrypoint', 'User', 'WorkingDir'):
        if original['Config'].get(key) != cloned['Config'].get(key):
            raise RuntimeError('Clone config mismatch: ' + key)
    if original['Image'] != cloned['Image']:
        raise RuntimeError('Clone image ID mismatch')
    mounts = lambda x: sorted((m['Type'],m['Source'],m['Destination'],m['RW'],m.get('Propagation')) for m in x['Mounts'])
    if mounts(original) != mounts(cloned):
        raise RuntimeError('Clone mount mismatch')
    for key in ('NanoCpus','CpusetCpus','Memory','ShmSize','DeviceRequests'):
        if original['HostConfig'].get(key) != cloned['HostConfig'].get(key):
            raise RuntimeError('Clone resource mismatch: ' + key)
    if cloned['HostConfig']['NetworkMode'] != 'none' or cloned['HostConfig'].get('PortBindings'):
        raise RuntimeError('Offline isolation mismatch')


class Runner:
    def __init__(self, root, evidence, helper, standard):
        self.root, self.evidence, self.helper, self.standard = root, evidence, helper, standard
        self.owned = {}  # exact IDs, only after successful create/inspect
        self.active_standard = {}
        self.sequence = 0
        self.state = {'status':'RUNNING','candidates':[], 'quality_scope':'dev4 startup smoke only; no scored quality or performance acceptance'}

    def run(self, args, timeout=60):
        # Never persist argv: docker create includes the original Env values.
        try:
            result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f'Command timed out ({args[0]} {args[1]}); timeout_seconds={timeout}') from None
        if result.returncode:
            raise RuntimeError(f'Command failed ({args[0]} {args[1]}); exit={result.returncode}')
        return result.stdout

    def inspect(self, name):
        return json.loads(self.run(['docker','inspect',name]))[0]

    def checkpoint(self):
        write(self.evidence/'state.json',self.state)

    def cpu(self, phase):
        info = self.inspect(CPU)
        if not info['State']['Running'] or info['State'].get('Health',{}).get('Status') != 'healthy':
            raise RuntimeError('Existing CPU OCR must remain running and healthy')
        record = {'phase':phase,'id':info['Id'],'started_at':info['State']['StartedAt'], 'healthy':True}
        if hasattr(self,'cpu_initial') and any(record[k] != self.cpu_initial[k] for k in ('id','started_at')):
            raise RuntimeError('CPU OCR identity/start time changed')
        self.cpu_initial = record
        self.state.setdefault('cpu_checks',[]).append(record)
        self.checkpoint()

    def http(self, candidate, container, endpoint):
        port = str(self.helper.PORTS[candidate])
        return self.run(['docker','exec',container,'python3','-c',HTTP_CHILD,
                         'http://127.0.0.1:'+port+endpoint],timeout=10)

    def metrics(self, candidate, container, phase):
        raw = self.http(candidate, container, '/metrics')
        self.sequence += 1
        (self.evidence/f'{self.sequence:04d}-{candidate}-{phase}.prom').write_text(raw)
        import re
        values = {}
        for key in ('running','waiting'):
            rows = [float(m.group(1)) for line in raw.splitlines()
                    if (m := re.match(r'^vllm:num_requests_'+key+r'(?:\{[^}]*\})?\s+(\S+)',line))]
            if not rows or any(not __import__('math').isfinite(x) or x < 0 for x in rows):
                raise RuntimeError('Missing/invalid queue metrics')
            values[key] = sum(rows)
        return values

    def idle(self, c, name):
        if self.metrics(c,name,'idle') != {'running':0,'waiting':0}:
            raise RuntimeError('Service is not idle')

    def ready(self,c,name):
        deadline=time.monotonic()+600
        while time.monotonic()<deadline:
            if not self.inspect(name)['State']['Running']:
                raise RuntimeError('Service exited during startup')
            try:
                self.http(c,name,'/health')
                data=json.loads(self.http(c,name,'/v1/models'))
                if self.helper.MODELS[c] in {x.get('id') for x in data.get('data',[])}:
                    self.idle(c,name)
                    return
            except (RuntimeError,ValueError):
                pass
            time.sleep(1)
        raise TimeoutError('600s startup deadline exceeded')

    def stop_owned(self,c,force=False):
        name=OFFLINE[c]
        info=self.inspect(name)  # Unknown state fails closed, never assume stopped.
        if info['Id'] != self.owned[c]:
            raise RuntimeError('Owned container ID changed; refusing stop')
        if info['State']['Running']:
            if not force:
                self.idle(c,name)
            self.run(['docker','stop','--time','0' if force else '30',name],timeout=60)
        if self.inspect(name)['State']['Running']:
            raise RuntimeError('Owned container stop did not reach terminal state')

    def dev(self,c,name,label):
        out=self.root/'results'/f'{c}-{self.evidence.name}-{label}'
        if out.exists():
            raise RuntimeError('Output exists; refusing overwrite')
        policy_path=self.evidence/f'{c}-{label}-runtime.json'
        self.run([sys.executable,str(self.root/'deploy/capture_runtime_policy.py'),
                  '--container',name,'--out',str(policy_path)])
        policy=json.loads(policy_path.read_text())
        if policy['cpuset'] != '0-7':
            raise RuntimeError('Unexpected cpuset')
        plan={'manifest_mount':'/work/corpus/development-manifest.json',
              'warmup_mount':'/work/corpus/development-manifest.json','page_admission':1,
              'region_limit':4,'timing_scope':'D0','profile':'C0-S0-ops-dev4'}
        containers=dict(self.helper.CONTAINERS)
        try:
            self.helper.CONTAINERS[c]=name
            args=self.helper.trial_command(self.root,plan,{'candidate':c},out,policy['policy'])
        finally:
            self.helper.CONTAINERS=containers
        # No warmup: this gate requires exactly the four actual development pages once.
        index=args.index('--warmup-manifest')
        del args[index:index+2]
        with (self.evidence/f'{c}-{label}-dev.log').open('x') as log:
            result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
        summary=json.loads((out/'summary.json').read_text())
        accepted=result.returncode==0 and self.standard.dev_complete(summary,out)
        self.state['candidates'][-1].setdefault('dev4',[]).append({'stage':label,'out':str(out),
               'exit_code':result.returncode,'status':'PASS' if accepted else 'FAIL'})
        self.checkpoint()
        if not accepted:
            raise RuntimeError('Development four-page gate failed')
        self.idle(c,name)

    def fault(self,c):
        name=OFFLINE[c]
        self.idle(c,name)
        directory=self.evidence/f'{c}-fault'
        directory.mkdir()
        child=None
        with (directory/'child.log').open('x') as log:
            try:
                child=subprocess.Popen(['docker','exec','-e','PYTHONPATH=/work',name,
                    self.helper.PYTHONS[c],'-c',FAULT_CHILD,c,self.helper.mounted(self.root,directory),
                    str(self.helper.PORTS[c])],stdout=log,stderr=subprocess.STDOUT)
                deadline=time.monotonic()+120
                while time.monotonic()<deadline:
                    if child.poll() is not None:
                        raise RuntimeError('Fault request terminated before active request observed')
                    values=self.metrics(c,name,'fault-active')
                    if values['running']>0:
                        write(directory/'active-observed.json',{'status':'PASS','metrics':values,'wall_time':time.time()})
                        self.stop_owned(c,force=True)
                        code=child.wait(timeout=30)
                        result_path=directory/'fault-child-result.json'
                        child_result=json.loads(result_path.read_text()) if result_path.exists() else None
                        expected=(code in (7,137) and (child_result is None or child_result.get('status')=='REQUEST_FAILED')
                                  and (directory/'fault-prepared.json').is_file())
                        write(directory/'child-terminal.json',{'exit_code':code,'expected_failure':expected,
                            'child_result':child_result,'container_stopped':True,'status':'PASS' if expected else 'FAIL'})
                        if not expected:
                            raise RuntimeError('Fault client terminal state does not prove the expected failure')
                        return
                    time.sleep(.2)
                raise TimeoutError('No running request observed within 120 seconds; fault not exercised')
            finally:
                if child is not None and child.poll() is None:
                    # Stop the owned service before terminating the local docker-exec wrapper.
                    try:
                        self.stop_owned(c,force=True)
                    finally:
                        child.terminate()
                        try:
                            code=child.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            child.kill()
                            code=child.wait(timeout=5)
                        write(directory/'child-cleanup-terminal.json',{'exit_code':code,'status':'FAIL'})

    def candidate(self,c):
        record={'candidate':c,'status':'RUNNING'}
        self.state['candidates'].append(record)
        self.checkpoint()
        original=self.inspect(STANDARD[c])
        if original['State']['Running']:
            raise RuntimeError('Both standard containers must be stopped before each candidate')
        mounts={m['Destination']:m['Source'] for m in original['Mounts']}
        if mounts.get('/work') != str(self.root):
            raise RuntimeError('Standard /work mount mismatch')
        # Absence must be proven by full docker name inventory, not a failed inspect.
        names=self.run(['docker','ps','-a','--format','{{.Names}}']).splitlines()
        if OFFLINE[c] in names:
            raise RuntimeError('Offline container already exists; refusing reuse')
        self.run(clone_command(original,c))
        clone=self.inspect(OFFLINE[c])
        self.owned[c]=clone['Id']
        record['clone_id']=clone['Id']
        self.checkpoint()
        verify_clone(original,clone)
        write(self.evidence/f'{c}-clone-proof.json',{'status':'PASS','source_id':original['Id'],
            'clone_id':clone['Id'],'image_id':clone['Image'],'network_mode':clone['HostConfig']['NetworkMode'],
            'port_bindings':clone['HostConfig'].get('PortBindings'),'config_env_cmd_mounts_equal':True,
            'cpus':8,'cpuset':'0-7','ram_gib':32,'shm_gib':8,'device':'0'})
        self.run(['docker','start',OFFLINE[c]])
        self.ready(c,OFFLINE[c])
        self.dev(c,OFFLINE[c],'f11-offline')
        self.fault(c)
        self.run(['docker','start',OFFLINE[c]])
        self.ready(c,OFFLINE[c])
        self.dev(c,OFFLINE[c],'f12-recovered')
        self.stop_owned(c)
        self.active_standard[c]=original['Id']
        self.run(['docker','start',STANDARD[c]])
        try:
            self.ready(c,STANDARD[c])
            self.dev(c,STANDARD[c],'standard-restored')
        finally:
            info=self.inspect(STANDARD[c])
            if info['Id']!=original['Id']:
                raise RuntimeError('Standard ID changed')
            if info['State']['Running']:
                self.idle(c,STANDARD[c])
                self.run(['docker','stop','--time','30',STANDARD[c]],timeout=60)
            if self.inspect(STANDARD[c])['State']['Running']:
                raise RuntimeError('Standard stop state unknown')
            del self.active_standard[c]
        self.cpu(c+'-complete')
        self.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'])
        record['status']='PASS'
        self.checkpoint()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--name',default='ops-r1')
    args=parser.parse_args(argv)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',args.name):
        parser.error('name must be safe ASCII and at most 64 characters')
    plan={'root':str(ROOT),'candidates':list(STANDARD),'standard':STANDARD,'offline':OFFLINE,
          'stages':['F11 network=none cold-start dev4','F08 kill owned container while running>0',
                    'F12 restart offline dev4','restore standard dev4 then stop'],
          'ready_timeout_seconds':600,'execute':args.execute,
          'evidence':str(ROOT/'evidence'/args.name),'no_model_retries':True}
    if not args.execute:
        print(json.dumps(plan,indent=2))
        return 0
    if ROOT.resolve()!=ROOT or not ROOT.is_dir():
        raise RuntimeError('Fixed taskroot missing or symlinked')
    with (ROOT/'evidence/.campaign.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        helper=load_module('ops_campaign_helper',ROOT/'deploy/run_campaign.py')
        standard=load_module('ops_standard_helper',ROOT/'deploy/run_standard_validation.py')
        helper.guard(ROOT)
        for path in (ROOT/'evidence').rglob('*-job.json'):
            if json.loads(path.read_text()).get('status')=='RUNNING':
                raise RuntimeError('RUNNING task job: '+str(path.relative_to(ROOT)))
        for name in STANDARD.values():
            if helper.inspect(name)['State']['Running']:
                raise RuntimeError('Standards must be stopped; caller must establish exclusive idle GPU')
        evidence=ROOT/'evidence'/args.name
        evidence.mkdir(exist_ok=False)
        runner=Runner(ROOT,evidence,helper,standard)
        write(evidence/'plan.json',plan)
        write(evidence/'source.json',{'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
        try:
            runner.cpu('before')
            gpu=runner.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'])
            (evidence/'gpu-before.txt').write_text(gpu)
            if gpu.strip():
                raise RuntimeError('GPU has compute applications; stop before any candidate')
            for c in STANDARD:
                runner.candidate(c)
                gpu=runner.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'])
                (evidence/f'{c}-gpu-after.txt').write_text(gpu)
                if gpu.strip():
                    raise RuntimeError('GPU not idle after candidate; do not continue')
            runner.state['status']='PASS'
        except BaseException as error:
            runner.state.update(status='FAIL',error_type=type(error).__name__,error=str(error))
            if runner.state['candidates']:
                runner.state['candidates'][-1]['status']='FAIL'
            # Bounded cleanup only for exact IDs created by this process. Never continue on uncertainty.
            for c in runner.owned:
                try:
                    runner.stop_owned(c,force=True)
                except Exception as cleanup:
                    runner.state.setdefault('cleanup_failures',[]).append({'candidate':c,'error':str(cleanup)})
        finally:
            for c, identity in runner.active_standard.items():
                try:
                    info=runner.inspect(STANDARD[c])
                    if info['Id'] != identity:
                        raise RuntimeError('Standard ID changed; cleanup refused')
                    if info['State']['Running']:
                        runner.run(['docker','stop','--time','30',STANDARD[c]],timeout=60)
                    if runner.inspect(STANDARD[c])['State']['Running']:
                        raise RuntimeError('Standard still running after cleanup')
                except Exception as error:
                    runner.state.update(status='FAIL')
                    runner.state.setdefault('cleanup_failures',[]).append({'standard':c,'error':str(error)})
            try:
                final_gpu=runner.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'])
                (evidence/'gpu-final.txt').write_text(final_gpu)
                if final_gpu.strip():
                    raise RuntimeError('GPU not idle at final handback')
                runner.state['gpu_final_idle']=True
            except Exception as error:
                runner.state.update(status='FAIL',gpu_final_idle=False,gpu_final_error=str(error))
            runner.state['wall_end']=time.time()
            try:
                runner.cpu('finally')
            except Exception as error:
                runner.state.update(status='FAIL',cpu_final_error=str(error))
            runner.checkpoint()
        print(json.dumps({'status':runner.state['status'],'evidence':str(evidence)}))
        return 0 if runner.state['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
