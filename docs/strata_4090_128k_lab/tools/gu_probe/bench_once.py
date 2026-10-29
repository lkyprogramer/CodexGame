"""Ordinary-user arm runner: owner perf counters and same-stage process/system memory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/combination'))
from boundary_memory import MemorySampler
from run_boundaries import descendants
import run_boundaries as boundary
from lab.core import gpu_lock,gpu_inventory


def run(a):
    out=Path(a.out);task=out.parents[1];tree=task.parent/'trees/gu-probe-20261027'
    if os.geteuid()==0:raise RuntimeError('BENCH_MUST_RUN_AS_ORDINARY_USER')
    proof=json.loads((task/'correctness/COMPLETE.json').read_text())
    exe=tree/'build-lab/lab_gu_probe'
    if proof['state']!='PASS' or hashlib.sha256(exe.read_bytes()).hexdigest()!=proof['binary_sha256']:
        raise RuntimeError('CORRECTNESS_GATE_IDENTITY')
    c=json.loads((task/'config.json').read_text());combo=boundary.combo
    protected=json.loads((task/'selection/production-before.json').read_text())['hashes']
    combo.assert_service_inactive();combo.assert_protected(c,protected)
    env={k:v for k,v in os.environ.items() if not k.startswith('STRATA_')}
    env.update({k:str(v) for k,v in c['extra_frozen_env'].items()})
    for name in ['STRATA_LAB_GU_PROFILE','STRATA_LAB_GU_CAPTURE','LD_PRELOAD']:env.pop(name,None)
    command=[str(tree/'build-lab/lab_gu_probe'),a.scope,str(task/'fixtures.txt'),a.mode,str(a.warm),str(a.seconds)]
    events='cycles,ref-cycles,instructions,task-clock,page-faults,minor-faults,major-faults,context-switches,cpu-migrations'
    perf=['perf','stat','-x,','-e',events,'-o',str(out/'owner-perf.csv'),'--',*command]
    (out/'command.json').write_text(json.dumps({'command':perf,'uid':os.geteuid(),'started':time.time()},indent=2)+'\n')
    with gpu_lock(c.get('gpu_lock_workspace',c['workspace'])), (out/'stdout.log').open('w') as stdout,(out/'stderr.log').open('w') as stderr:
        if gpu_inventory(0)['compute_processes']:raise RuntimeError('GPU_LOAD_DURING_CPU_BENCH')
        child=subprocess.Popen(perf,stdout=stdout,stderr=stderr,env=env)
        fake=types.SimpleNamespace(process=child,engine_audit=[])
        with MemorySampler(out,lambda:descendants(fake)) as memory:
            memory.stage='load-warmup-measure';memory.checkpoint('before')
            deadline=time.monotonic()+a.warm+a.seconds+120
            while child.poll() is None:
                if time.monotonic()>deadline:child.terminate();raise RuntimeError('BENCH_ABSOLUTE_TIMEOUT')
                time.sleep(.5)
            memory.checkpoint('after')
        if child.returncode:raise RuntimeError('BENCH_FAILED '+str(child.returncode))
    rows=[json.loads(line) for line in (out/'stdout.log').read_text().splitlines() if line.startswith('{')]
    if len(rows)!=1 or rows[0]['state']!='COMPLETE' or rows[0]['mode']!=a.mode:raise RuntimeError('BENCH_RESULT_IDENTITY')
    combo.assert_service_inactive();combo.assert_protected(c,protected)
    (out/'result.json').write_text(json.dumps(rows[0],indent=2)+'\n');return rows[0]


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('scope',choices=['bench','row-bench']);p.add_argument('mode',choices=['off','on']);p.add_argument('warm',type=float);p.add_argument('seconds',type=float)
    args=p.parse_args();print(json.dumps(run(args)),flush=True)
