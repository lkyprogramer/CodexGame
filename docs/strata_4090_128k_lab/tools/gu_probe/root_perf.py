"""Root reads MSR counters; runuser drops privileges before the benchmark wrapper."""
import argparse
import json
import os
from pathlib import Path
import pwd
import subprocess
import time


def run(a):
    if os.geteuid()!=0:raise RuntimeError('ROOT_REQUIRED_FOR_SYSTEM_MSR_READ')
    out=Path(a.out).resolve();task=out.parents[1];expected=Path('/home/hhtele/strata-lab-4090/workspace/gu-probe-20261027')
    if task!=expected or out.parent.name not in ['bench','micro'] or out.stat().st_uid!=pwd.getpwnam('hhtele').pw_uid:
        raise ValueError('PERF_OUTPUT_OUTSIDE_OWNED_TASK')
    if a.warm<0 or a.warm>30 or not 1<=a.seconds<=60:raise ValueError('PERF_DURATION')
    wrapper=task.parents[1]/'tools/gu_probe/bench_once.py'
    cmd=['perf','stat','-a','-C','0-15','-x,','-I','1000','-e','msr/aperf/,msr/mperf/',
         '-o',str(out/'aperf-mperf.csv'),'--','runuser','-u','hhtele','--','python3','-B',str(wrapper),
         str(out),a.scope,a.mode,str(a.warm),str(a.seconds)]
    (out/'root-perf-start.json').write_text(json.dumps({'epoch':time.time(),'monotonic':time.monotonic(),'command':cmd,
         'scope':'systemwide MSR read only; benchmark subprocess runs as hhtele; no permission or frequency changes'},indent=2)+'\n')
    return subprocess.run(cmd,check=False).returncode


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('scope',choices=['bench','row-bench']);p.add_argument('mode',choices=['off','on']);p.add_argument('warm',type=float);p.add_argument('seconds',type=float)
    raise SystemExit(run(p.parse_args()))
