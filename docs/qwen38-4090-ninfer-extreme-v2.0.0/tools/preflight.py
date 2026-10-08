"""Read-only facts. Run locally on the GPU host; remote invocation is in docs."""
import argparse,json,os,platform,shutil,subprocess,time
from pathlib import Path
from .security import redact

def probe(argv):
    try:
        r=subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15)
        return {'argv':argv,'exit':r.returncode,'output':redact(r.stdout)[:20000]}
    except (OSError,subprocess.TimeoutExpired) as e: return {'argv':argv,'error':str(e)}

def collect():
    cmds=[['nvidia-smi'],['nvidia-smi','--query-gpu=name,uuid,driver_version,memory.total,memory.free,pcie.link.gen.current,pcie.link.gen.max,pcie.link.width.current,power.limit','--format=csv'],['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv'],['/usr/local/cuda-12.3/bin/nvcc','--version'],['systemctl','is-active','openclaw-qwen38-ninfer.service'],['docker','ps','--format','{{.Names}} {{.Image}} {{.Status}}'],['java','-version'],['sh','-c','cat /proc/meminfo | head -5'],['df','-h',str(Path.home())]]
    return {'observed_at_unix':time.time(),'host':platform.node(),'platform':platform.platform(),'declared':{'gpu':'RTX4090','driver':'610.57.04','cuda_umd':'13.3','pcie':'Gen3 x16','ram_gib':62.5},'observed':[probe(c) for c in cmds],'note':'No install, no sudo, no model loading, no production pause.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True); a=p.parse_args(); Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(collect(),indent=2)+'\n')
