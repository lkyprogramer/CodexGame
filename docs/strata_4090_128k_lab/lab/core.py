from __future__ import annotations
import contextlib, copy, hashlib, json, os, re, signal, socket, subprocess, time
from pathlib import Path
from urllib.parse import urlsplit

HARD_CONTEXT = 131072
ROOT = Path(__file__).resolve().parents[1]


def check_budget(prompt: int, output: int, context: int = HARD_CONTEXT, reserve: int = 4096) -> None:
    if any(isinstance(x, bool) or not isinstance(x, int) for x in (prompt, output, context, reserve)):
        raise ValueError('Token counts must be integers, not bool or estimates')
    if context < 1 or context > HARD_CONTEXT or prompt < 0 or output <= 0 or reserve < 0:
        raise ValueError('Invalid budget or context exceeds the 131072-token hardware ceiling')
    if prompt + output + reserve > context:
        raise ValueError(f'CONTEXT_LIMIT: {prompt}+{output}+{reserve}>{context}')


def argv(value) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(x,str) or '\0' in x for x in value):
        raise ValueError('Commands must be nonempty argv arrays; shell strings are not executed')
    return value


def loopback_url(value: str) -> str:
    u=urlsplit(value)
    if u.scheme != 'http' or u.hostname not in ('127.0.0.1','localhost','::1') or u.username or u.password:
        raise ValueError('Only unauthenticated loopback HTTP URLs are allowed; key is passed separately')
    if u.query or u.fragment or u.path not in ('','/'):
        raise ValueError('Give the server root, without /v1 or query parameters')
    return value.rstrip('/')


def check_separate(workspace, production) -> None:
    a,b=Path(workspace).expanduser().resolve(),Path(production).expanduser().resolve()
    if a == b or a in b.parents or b in a.parents:
        raise ValueError('Workspace and production repository must not overlap in either direction')


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''): h.update(block)
    return h.hexdigest()


def hash_obj(obj) -> str:
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def dump(path, value) -> None:
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    try: tmp.chmod(0o600)
    except OSError: pass
    os.replace(tmp,p)


def flag_value(args, flag):
    vals=[]
    for i,a in enumerate(args or []):
        if a==flag:
            if i+1>=len(args) or args[i+1].startswith('--'): raise ValueError(f'Missing value: {flag}')
            vals.append(args[i+1])
        elif a.startswith(flag+'='): vals.append(a.partition('=')[2])
    if len(vals)>1: raise ValueError(f'Duplicate flag {flag}; normalize explicitly first')
    return vals[0] if vals else None


def set_flag(args, flag, value):
    out=[]; i=0; args=list(args or [])
    while i<len(args):
        if args[i]==flag:
            i+=1
            if i<len(args) and not args[i].startswith('--'): i+=1
            continue
        if args[i].startswith(flag+'='): i+=1; continue
        out.append(args[i]); i+=1
    if value is not None: out += [flag,str(value)]
    return out


def normalized_config(cfg, context=HARD_CONTEXT):
    check_budget(0,1,context,0)
    c=copy.deepcopy(cfg)
    for key in ('args','user_args'):
        a=c.get(key,[])
        if not isinstance(a,list) or not all(isinstance(x,str) for x in a):
            raise ValueError(f'{key} must be a string list')
        a=set_flag(a,'--max-context',context)
        # Engine batch slots are explicitly absent in the default solo arm.
        a=set_flag(a,'--batch',None)
        a=set_flag(a,'--batch-mtp',None)
        c[key]=a
    c['parallel']=1; c['fit_max_tokens']=False
    c['host']='127.0.0.1'; c['open_browser']=False
    c['idle_unload_s']=0; c['lazy_load']=False
    return c


def redact(value):
    if isinstance(value,dict):
        return {k:('<redacted>' if re.search(r'key|secret|password|token$',k,re.I) and k not in ('max_tokens','completion_tokens','prompt_tokens','cache_tokens') else redact(v)) for k,v in value.items()}
    if isinstance(value,list): return [redact(v) for v in value]
    return value


def run(cmd, cwd=None, timeout=120, log=None, env=None, check=True):
    """Execute only argv, keep diagnostic output, and reap this command's children on timeout."""
    cmd=argv(cmd)
    options={'start_new_session': True} if os.name=='posix' else {}
    p=subprocess.Popen(cmd,cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,**options)
    output=''
    try:
        output,_=p.communicate(timeout=timeout)
    except BaseException:
        # These are children of the process we just created, never discovered production processes.
        if os.name=='posix':
            try: os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError: pass
        else:
            try: subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
            except (OSError,subprocess.SubprocessError): p.kill()
        try: output,_=p.communicate(timeout=15)
        except subprocess.SubprocessError: output='Command terminated; remaining output unavailable.'
        raise
    finally:
        if log:
            Path(log).parent.mkdir(parents=True,exist_ok=True)
            Path(log).write_text(output or '',encoding='utf-8')
    result=subprocess.CompletedProcess(cmd,p.returncode,output,None)
    if check and result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}): {cmd[0]}; see {log or output[-1500:]}')
    return result


def load_config(path):
    p=Path(path).expanduser().resolve()
    c=json.loads(p.read_text(encoding='utf-8'))
    for key in ('workspace','deployed_repo','deployed_config','gguf','template','python'):
        if c.get(key):
            q=Path(c[key]).expanduser()
            c[key]=str((p.parent/q).resolve() if not q.is_absolute() else q.resolve())
    c['_config_path']=str(p)
    check_separate(c['workspace'],c['deployed_repo'])
    check_budget(0,1,int(c['max_context']),int(c['safety_tokens']))
    if c['max_context'] != HARD_CONTEXT: raise ValueError('This package is locked to 128K=131072. Edit the protocol deliberately for smaller limits.')
    if int(c['port']) < 1024: raise ValueError('Use a nonprivileged test port')
    return c


def port_free(port):
    with socket.socket() as s:
        try: s.bind(('127.0.0.1',int(port)))
        except OSError: raise RuntimeError(f'Test port {port} is busy; refusing to reuse/stop another service')


def available_mib():
    p=Path('/proc/meminfo')
    if not p.exists(): raise RuntimeError('Live runner currently requires Linux / WSL2; other OS needs a reviewed memory adapter')
    fields={k:int(v.split()[0]) for k,v in (ln.split(':',1) for ln in p.read_text().splitlines())}
    host=fields['MemAvailable']//1024
    # cgroup v2: cap availability by the limit minus current use plus reclaimable file cache.
    try:
        rel=next(x.split(':',2)[2] for x in Path('/proc/self/cgroup').read_text().splitlines() if x.startswith('0:'))
        cg=Path('/sys/fs/cgroup')/rel.lstrip('/')
        cap=(cg/'memory.max').read_text().strip()
        if cap!='max':
            current=int((cg/'memory.current').read_text())
            stats=dict(x.split() for x in (cg/'memory.stat').read_text().splitlines())
            reclaim=int(stats.get('inactive_file','0'))
            host=min(host,max(0,(int(cap)-current+reclaim)//1048576))
    except (OSError,StopIteration,ValueError): pass
    return host


def gpu_inventory(index='0'):
    p=run(['nvidia-smi','-i',str(index),'--query-gpu=name,uuid,memory.total,memory.used,driver_version,temperature.gpu,power.draw','--format=csv,noheader,nounits'])
    row=[x.strip() for x in p.stdout.strip().split(',')]
    if len(row)!=7: raise RuntimeError('Unrecognized nvidia-smi GPU inventory')
    q=run(['nvidia-smi','-i',str(index),'--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader,nounits'])
    return dict(zip(('name','uuid','total_mib','used_mib','driver','temperature_c','power_w'),row)) | {'compute_processes':[x for x in q.stdout.splitlines() if x.strip() and 'No running' not in x]}


@contextlib.contextmanager
def gpu_lock(workspace):
    import fcntl
    p=Path(workspace)/'.gpu.lock'; p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a+') as f:
        try: fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError('Another experiment owns this workspace GPU lock')
        try: yield
        finally: fcntl.flock(f,fcntl.LOCK_UN)
