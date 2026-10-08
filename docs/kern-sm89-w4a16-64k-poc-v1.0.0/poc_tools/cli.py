from __future__ import annotations
import argparse, json, os, platform, shutil, subprocess, sys, time
from pathlib import Path
from .core import audit_checkpoint, check_poc_manifest, evaluate_evidence, memory_budget, sha256_file

def emit(data,out):
    text=json.dumps(data,ensure_ascii=False,indent=2)
    if out:
        p=Path(out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text+'\n')
    print(text)

def command(args):
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=20)
        return {'exit_code':p.returncode,'stdout':p.stdout[-16000:],'stderr':p.stderr[-2000:]}
    except (OSError,subprocess.TimeoutExpired) as e:return {'exit_code':None,'error':str(e)}

def preflight(root):
    root=Path(root);disk=shutil.disk_usage(root)
    memory={}
    p=Path('/proc/meminfo')
    if p.exists():
        for line in p.read_text().splitlines():
            if line.startswith(('MemTotal:','MemAvailable:','SwapTotal:','SwapFree:')):
                k,v=line.split(':');memory[k]=int(v.split()[0])*1024
    queries={
      'nvidia_smi':command(['nvidia-smi']),
      'gpu':command(['nvidia-smi','--query-gpu=name,uuid,driver_version,memory.total,memory.free,power.limit,temperature.gpu','--format=csv,noheader,nounits']),
      'compute_processes':command(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader']),
      'nvcc':command(['nvcc','--version']), 'cargo':command(['cargo','--version']),
      'java':command(['java','-version']),'pi':command(['pi','--version']),
      'production':command(['systemctl','is-active','openclaw-qwen38-ninfer.service'])}
    return {'kind':'READ_ONLY_PREFLIGHT','observed_at_unix':time.time(),
      'user_declared':{'gpu':'RTX 4090','ram_gib':64,'ssd_gb':600,'kmd':'610.57.04','cuda_umd':'13.3'},
      'os':platform.platform(),'python':sys.version,'disk':{'total_bytes':disk.total,'free_bytes':disk.free},
      'host_memory':memory,'queries':queries,
      'note':'UMD is not nvcc. No driver, service, model, or GPU resource is changed by this command.'}

def main():
    p=argparse.ArgumentParser(description='Kern SM89 PoC support toolkit (not an inference engine)')
    sub=p.add_subparsers(dest='op',required=True)
    q=sub.add_parser('preflight');q.add_argument('--root',default='.');q.add_argument('--out')
    q=sub.add_parser('weights');q.add_argument('directory');q.add_argument('--out',required=True)
    q=sub.add_parser('memory');q.add_argument('--weight-gib',type=float,required=True);q.add_argument('--capacity',type=int,default=73728);q.add_argument('--kv-bits',type=int,default=16);q.add_argument('--slots',type=int,default=4);q.add_argument('--workspace-gib',type=float,default=1);q.add_argument('--out')
    q=sub.add_parser('lint');q.add_argument('manifest');q.add_argument('--out')
    q=sub.add_parser('report');q.add_argument('evidence');q.add_argument('--out',required=True)
    q=sub.add_parser('lock-model');q.add_argument('directory');q.add_argument('--out',required=True)
    a=p.parse_args()
    try:
        code=0
        if a.op=='preflight':data=preflight(a.root)
        elif a.op=='weights':data=audit_checkpoint(Path(a.directory))
        elif a.op=='memory':
            data=memory_budget(round(a.weight_gib*2**30),a.capacity,kv_bits=a.kv_bits,slots=a.slots,workspace_bytes=round(a.workspace_gib*2**30));code=0 if data['fits'] else 2
        elif a.op=='lint':
            errors=check_poc_manifest(json.loads(Path(a.manifest).read_text()));data={'lint_errors':errors,'status':'PASS' if not errors else 'FAIL','not_a_gpu_or_upstream_verifier':True};code=bool(errors)*2
        elif a.op=='lock-model':
            files=[]
            for f in sorted(Path(a.directory).rglob('*')):
                if f.is_file() and f.suffix in ('.safetensors','.json','.jinja'):
                    print('hashing '+f.name,file=sys.stderr,flush=True)
                    files.append({'path':str(f.relative_to(a.directory)),'bytes':f.stat().st_size,'sha256':sha256_file(f)})
            if not files:raise ValueError('no model files')
            import hashlib
            digest=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            data={'files':files,'model_sha256':digest,'meaning':'content identity, not a Hugging Face revision'}
        else:
            data=evaluate_evidence(json.loads(Path(a.evidence).read_text()),Path(a.evidence).parent);code={'POC_GO':0,'NO_GO':2,'BLOCKED':78}[data['decision']]
        emit(data,a.out);return code
    except Exception as e:
        emit({'status':'ERROR','error':str(e)},getattr(a,'out',None));return 2
if __name__=='__main__':sys.exit(main())
