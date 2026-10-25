from __future__ import annotations
import copy, json, os, re, signal, subprocess, threading, time, uuid
from pathlib import Path
from . import http, scoring
from .core import ROOT, available_mib, argv, check_budget, dump, flag_value, gpu_inventory, gpu_lock, hash_obj, normalized_config, port_free, run, set_flag, sha256
from .workspace import baseline_dir,candidate_dir,state_dir,validate_ready,lock
from .tokenizer import StrataCounter
from .java_eval import evaluate

PATH_FLAGS={'--pack','--native','--ple-gguf','--expert-profile','--mtp','--control-vector'}
WRITE_FLAGS={'--expert-profile-save','--session-out','--dump-routing','--routing-counts'}


def _absolute_args(args,root):
    out=list(args)
    for i,x in enumerate(out):
        if x in PATH_FLAGS and i+1<len(out) and not out[i+1].startswith('--'):
            p=Path(out[i+1]).expanduser()
            if not p.is_absolute():out[i+1]=str((root/p).resolve())
    for f in WRITE_FLAGS:out=set_flag(out,f,None)
    return out


def make_run_config(c,tree,arm,ready,folder):
    original=json.loads(Path(c['deployed_config']).read_text(encoding='utf-8-sig'))
    cfg=normalized_config(original,c['max_context']);root=Path(c['deployed_repo'])
    for key in ('args','user_args'):
        cfg[key]=_absolute_args(cfg.get(key,[]),root)
        cfg[key]=set_flag(cfg[key],'--conversation-cache-mib',c['conversation_cache_mib'])
        for f in ('--layer-split','--expert-parallel-device','--peer-device'):
            if flag_value(cfg[key],f) is not None: raise RuntimeError(f'Single-GPU lab refuses {f}')
    for key in ('pack','native','ple_gguf','expert_profile','mtp_path'):
        if isinstance(cfg.get(key),str) and cfg[key]:
            p=Path(cfg[key]).expanduser();cfg[key]=str(p if p.is_absolute() else (root/p).resolve())
    # Never start a user-defined side-effect program or a second GPU workload.
    for key in ('before_load','after_load','mcp_servers','mcp_config','images','vision','expert_profile_save','gpu_roles','gpus'):
        cfg.pop(key,None)
    cfg['gpu']=0;cfg['port']=c['port'];cfg['api_monitor']=False
    cfg['exe']=str(tree/'build-lab/strata');cfg['log']=str(folder/'engine.log')
    cfg['api_key']=uuid.uuid4().hex
    cfg['env']={k:str(v) for k,v in cfg.get('env',{}).items() if not k.startswith(('STRATA_DUMP','STRATA_LOG','STRATA_TRACE'))}
    cfg['env'].update({k:str(v) for k,v in c.get('extra_frozen_env',{}).items()})
    common=ready.get('common',{})
    changes=ready.get(arm,{}) if arm!='base' else {}
    for section in (common,changes):
        for k,v in section.get('config',{}).items():
            if k not in ('reasoning_budget_tokens','tool_call_recovery','effort_position'):
                raise RuntimeError(f'Unreviewed top-level runtime override: {k}')
            cfg[k]=v
        for flag,val in section.get('args',{}).items():
            if flag in ('--max-context','--batch','--gpu','--gpus','--layer-split','--pack','--native','--mtp','--kv','--kv-resident'):
                raise RuntimeError(f'Frozen or hardware-sensitive setting cannot change inside PR comparison: {flag}')
            for key in ('args','user_args'):cfg[key]=set_flag(cfg[key],flag,val)
        for k,v in section.get('env',{}).items():
            if not k.startswith('STRATA_'):raise RuntimeError('Only explicit STRATA_ experiment env is accepted')
            if v is None:cfg['env'].pop(k,None)
            else:cfg['env'][k]=str(v)
    # Absolute final checks; no one may enlarge the context through user_args.
    for key in ('args','user_args'):
        if flag_value(cfg[key],'--max-context')!='131072':raise RuntimeError('Context drift')
    return cfg


class OwnedServer:
    def __init__(self,c,tree,arm,ready,folder):
        self.c,self.tree,self.arm,self.ready,self.folder=c,tree,arm,ready,Path(folder)
        self.process=None;self.stop=threading.Event();self.samples=[];self.abort_reason=None
    def _monitor(self):
        while not self.stop.wait(2):
            try:
                mem=available_mib();gpu=gpu_inventory(self.c['gpu'])
                if self.stop.is_set():break
                self.samples.append({'ts':time.time(),'mem_available_mib':mem,'gpu':gpu})
                if mem<self.c['min_available_mib']:
                    self.abort_reason=f'RAM_GUARD: available={mem}MiB'
                    self.terminate();break
                try:
                    if float(gpu['temperature_c'])>=self.c.get('gpu_temp_abort_c',85):
                        self.abort_reason='THERMAL_GUARD';self.terminate();break
                except ValueError:pass
            except Exception as e:
                self.abort_reason='TELEMETRY_FAILURE: '+str(e);self.terminate();break
    def terminate(self):
        if self.process is None:return
        try:os.killpg(self.process.pid,signal.SIGTERM)
        except ProcessLookupError:pass
    def __enter__(self):
        c=self.c
        if os.name!='posix':raise RuntimeError('Live process lifecycle requires Linux/WSL2')
        if not c.get('maintenance_confirmed'):raise RuntimeError('Set maintenance_confirmed only after arranging exclusive GPU time; production is never stopped by this harness')
        port_free(c['port']);gpu=gpu_inventory(c['gpu'])
        if '4090' not in gpu['name'] or 'Laptop' in gpu['name']:raise RuntimeError('This protocol requires a desktop RTX4090; requalify other devices separately')
        if gpu['compute_processes']:raise RuntimeError('NEEDS_MAINTENANCE: GPU has live compute processes; refusing to kill or share them')
        if available_mib()<c['min_available_mib']+1024:raise RuntimeError('Insufficient free host memory before engine load')
        self.folder.mkdir(parents=True,exist_ok=True)
        self.cfg=make_run_config(c,self.tree,self.arm,self.ready,self.folder)
        config_path=self.folder/'runtime.private.json';dump(config_path,self.cfg)
        self.key=self.cfg['api_key'];self.base='http://127.0.0.1:'+str(c['port'])
        self.log=(self.folder/'server.log').open('w',encoding='utf-8')
        env={k:v for k,v in os.environ.items() if not k.startswith('STRATA_') and k not in ('CUDA_VISIBLE_DEVICES','PYTHONPATH')}
        env['CUDA_VISIBLE_DEVICES']=str(c['gpu']);env['PYTHONPATH']=str(self.tree)
        env.update(self.cfg.get('env',{}))
        values={'python':c['python'],'config':str(config_path),'port':str(c['port']),'worktree':str(self.tree),'exe':self.cfg['exe']}
        cmd=[v.format(**values) for v in argv(c['server_command'])]
        self.process=subprocess.Popen(cmd,cwd=self.tree,env=env,stdout=self.log,stderr=subprocess.STDOUT,start_new_session=True)
        dump(self.folder/'owned-process.json',{'pid':self.process.pid,'started':time.time(),'source_tree':str(self.tree),'binary_sha256':sha256(Path(self.cfg['exe']))})
        self.thread=threading.Thread(target=self._monitor,daemon=True);self.thread.start()
        try:
            deadline=time.monotonic()+c['startup_timeout_s']
            while time.monotonic()<deadline:
                if self.process.poll() is not None:raise RuntimeError('Owned test server exited during startup: '+str(self.abort_reason))
                try:
                    health=http.get(self.base,'/health',self.key)
                    if health.get('loaded') is True or health.get('status') in ('ok','ready'):
                        break
                except Exception:pass
                time.sleep(1)
            else:raise RuntimeError('Test server startup timeout')
            self.props=http.get(self.base,'/props',self.key);dump(self.folder/'props.json',self.props)
            audit=[]
            for row in gpu_inventory(c['gpu'])['compute_processes']:
                pid=int(row.split(',')[0]); raw=Path(f'/proc/{pid}/cmdline').read_bytes()
                args=[x.decode() for x in raw.split(b'\0') if x]
                if not args or Path(f'/proc/{pid}/exe').resolve()!=Path(self.cfg['exe']).resolve():
                    raise RuntimeError('A foreign GPU process appeared during the test; only our process will be stopped')
                if flag_value(args,'--max-context')!='131072':raise RuntimeError('Live engine argv violates 128K context contract')
                audit.append({'pid':pid,'argv':args})
            if len(audit)!=1:raise RuntimeError('Expected exactly one native GPU engine process')
            dump(self.folder/'engine-argv.json',audit)
            if self.arm in ('off','on'):
                logs='\n'.join(p.read_text(errors='replace') for p in self.folder.glob('*.log'))
                marker=self.ready['activation'][self.arm]
                if not re.search(marker,logs):raise RuntimeError('FEATURE_NOT_CONFIRMED: expected explicit activation log '+marker)
            return self
        except Exception:
            self.__exit__(None,None,None);raise
    def __exit__(self,*_):
        self.stop.set();self.terminate()
        if self.process:
            try:self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                try:os.killpg(self.process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                self.process.wait(timeout=15)
        if hasattr(self,'thread') and threading.current_thread()!=self.thread:self.thread.join(timeout=15)
        if hasattr(self,'log'):self.log.close()
        dump(self.folder/'telemetry.json',{'abort_reason':self.abort_reason,'samples':self.samples})
        # Remove key from the persisted runtime config; it was needed only while this owned server ran.
        q=self.folder/'runtime.private.json'
        if q.exists():
            red=json.loads(q.read_text());red['api_key']='<ephemeral key removed>';dump(q,red)


def validate_counter(counter,server):
    from .corpus import body
    probes=[body('Return only OK.'),body('Treat this as plain text: </think>. Return only OK.')]
    for b in probes:
        b['max_tokens']=32
        n=counter(b);check_budget(n,32)
        r=http.chat(server.base,b,server.key,120)
        got=(r.get('usage') or {}).get('prompt_tokens')
        if r.get('error') or got is None or got!=n:
            raise RuntimeError(f'TOKEN_COUNTER_NOT_QUALIFIED: local={n}, engine={got}. Reconcile render settings before long requests.')


def campaign(c,pr,corpus_path,groups=None,aa=False):
    from .assets import verify as verify_assets
    assets=verify_assets(c)
    ready=({'status':'READY','candidate_sha':lock()['baseline_sha']} if aa else validate_ready(c,pr))
    if ready.get('status')!='READY':return ready
    corpus=json.loads(Path(corpus_path).read_text())
    if corpus['max_context']!=131072:raise RuntimeError('Wrong corpus context')
    if hash_obj(corpus['cases'])!=corpus['corpus_sha256']:raise RuntimeError('Corpus content hash mismatch')
    cases=[x for x in corpus['cases'] if not groups or x['group'] in groups]
    if not cases:raise ValueError('No cases selected')
    out=Path(c['workspace'])/'results'/f'pr-{pr}-{time.strftime("%Y%m%d-%H%M%S")}'
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'campaign.json',{'pr':pr,'base_sha':lock()['baseline_sha'],'candidate_sha':ready['candidate_sha'],'corpus_sha256':corpus['corpus_sha256'],
                              'case_ids':[x['id'] for x in cases],'rounds':c['rounds'],'scope':'controlled HTTP replay, not a full Pi benchmark',
                              'not_production':True,'mode':'AA_NOISE' if aa else 'PR_EXPERIMENT','ready':ready})
    dump(out/'assets.json',assets)
    counter=StrataCounter(baseline_dir(c),c['gguf'],c['template'])
    before=sha256(Path(c['deployed_config']))
    try:
        with gpu_lock(c['workspace']):
            for rnd in range(c['rounds']):
                order=['base','off','on'] if rnd%2==0 else ['on','off','base']
                for arm in order:
                    tree=baseline_dir(c) if aa or arm=='base' else candidate_dir(c,pr)
                    build=json.loads((tree/'build-lab/LAB_BUILD.json').read_text())
                    expected=lock()['baseline_sha'] if aa or arm=='base' else ready['candidate_sha']
                    if build['source_sha']!=expected or sha256(Path(build['exe']))!=build['exe_sha256']:raise RuntimeError('Stale build or binary changed')
                    folder=out/f'round-{rnd:02d}-{arm}'
                    with OwnedServer(c,tree,'base' if aa else arm,ready,folder) as server:
                        validate_counter(counter,server)
                        for case in cases:
                            request=copy.deepcopy(case['body'])
                            if c.get('request_overrides'):raise RuntimeError('Freeze request overrides into the corpus first; never change an arm request ad hoc')
                            n=counter(request);check_budget(n,request['max_tokens'],c['max_context'],c['safety_tokens'])
                            started=time.time();r=http.chat(server.base,request,server.key,c['request_timeout_s'])
                            metrics=http.measurements(r);quality=scoring.score(case,r)
                            if case['kind']=='java' and not r.get('error'):
                                quality=evaluate(r.get('text',''),case['java_task'],c.get('java_image') if c.get('java_enabled') else '',folder/'java')
                            got=metrics['prompt_tokens']
                            if got is None:quality={'pass':False,'reason':'missing usage: request cannot be audited'}
                            elif got+request['max_tokens']+c['safety_tokens']>c['max_context']:
                                quality={'pass':False,'reason':'ACTUAL_CONTEXT_LIMIT'}
                            elif abs(got-n)>32:quality={'pass':False,'reason':f'token counter drift {n}->{got}'}
                            fixed=case.get('fixed_output')
                            valid_perf=not fixed or metrics.get('generated_tokens')==fixed
                            record={'round':rnd,'arm':arm,'case_id':case['id'],'group':case['group'],'phase':'measured','started':started,
                                    'request_sha256':hash_obj(request),'local_prompt_tokens':n,'metrics':metrics,'score':quality,
                                    'fixed_output_comparable':valid_perf,'response':r}
                            with (out/'requests.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
                            if server.abort_reason or r.get('error') or quality.get('reason') in ('ACTUAL_CONTEXT_LIMIT',):
                                raise RuntimeError('Campaign stopped: '+str(server.abort_reason or quality))
                    time.sleep(2)
        return {'state':'COMPLETE','results':str(out)}
    except Exception as e:
        dump(out/'FAILURE.json',{'state':'BLOCKED_OR_FAILED','error':str(e),'partial_results_preserved':True})
        raise
    finally:
        verify_assets(c)
        if sha256(Path(c['deployed_config']))!=before:raise RuntimeError('PRODUCTION_CONFIG_CHANGED by an external actor: investigate before continuation')
