"""Local orchestrator; root password is consumed from the environment and never persisted."""
import argparse
import json
import os
from pathlib import Path
import select
import shlex
import subprocess
import time

TASK='/home/hhtele/strata-lab-4090/workspace/gu-probe-20261027'
PACKAGE='/home/hhtele/strata-lab-4090'


def root_command(command,password,log):
    args=['ssh','-tt','-o','BatchMode=yes','hhtele@192.168.10.29','su - root -c '+shlex.quote(command)]
    p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    sent=False;seen=b'';deadline=time.monotonic()+240
    with Path(log).open('wb') as dest:
        while True:
            if time.monotonic()>deadline:p.terminate();raise RuntimeError('ROOT_PERF_TIMEOUT')
            ready,_,_=select.select([p.stdout],[],[],1)
            if ready:
                part=os.read(p.stdout.fileno(),65536)
                if not part:break
                dest.write(part);dest.flush();seen=(seen+part)[-4096:]
                if not sent and b'assword:' in seen:p.stdin.write(password.encode()+b'\n');p.stdin.flush();sent=True
            if p.poll() is not None and not ready:break
    code=p.wait(timeout=10)
    if not sent or code:raise RuntimeError('ROOT_PERF_ARM_FAILED '+str(code))


def run(a):
    password=os.environ.pop('GU_PROBE_ROOT_AUTH',None)
    if password is None:raise RuntimeError('ROOT_CREDENTIAL_MISSING_IN_ENVIRONMENT')
    local=Path(a.local_out);local.mkdir(parents=True,exist_ok=False)
    orders=[['off','on'],['on','off'],['on','off'],['off','on'],['off','on'],['on','off']]
    count=3 if a.scope=='micro' else 6;mode='row-bench' if a.scope=='micro' else 'bench';warm=2 if a.scope=='micro' else 30;seconds=10 if a.scope=='micro' else 60
    completed=[]
    for r,order in enumerate(orders[:count]):
        for arm in order:
            out=f'{TASK}/{a.scope}/r{r}-{arm}'
            prepare=f'mkdir -p {shlex.quote(out)}'
            subprocess.run(['ssh','-o','BatchMode=yes','hhtele@192.168.10.29',prepare],check=True)
            command=shlex.join(['python3','-B',PACKAGE+'/tools/gu_probe/root_perf.py',out,mode,arm,str(warm),str(seconds)])
            root_command(command,password,local/f'r{r}-{arm}.console.log')
            completed.append({'round':r,'arm':arm,'remote':out});(local/'progress.json').write_text(json.dumps(completed,indent=2)+'\n')
            print(json.dumps(completed[-1]),flush=True)
    return completed


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('scope',choices=['micro','bench']);p.add_argument('local_out');a=p.parse_args();run(a)
