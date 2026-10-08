"""Budgeted argv-only orchestrator; command success is not a GPU qualification.

POSIX process groups are used deliberately: every stage is a foreground child,
and termination of this supervisor must first settle its current stage.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

class Interrupted(Exception):
    def __init__(self, signum):
        self.signum = signum

def stop_group(child: subprocess.Popen, grace: float = 5) -> None:
    """Terminate only the session this supervisor created, never other GPU users."""
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        child.wait()
        return
    try:
        child.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait()

def validate_plan(plan: dict) -> list[dict]:
    stages = plan.get('stages')
    if not isinstance(stages, list) or not stages:
        raise ValueError('stages must be a nonempty list')
    seen = set()
    for s in stages:
        name = s.get('id', '')
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', name) or name in seen:
            raise ValueError('stage id must be unique and a safe filename component')
        seen.add(name)
        argv = s.get('argv')
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and '\x00' not in x for x in argv):
            raise ValueError('argv must be a nonempty string array')
        limit = s.get('timeout_s')
        if not isinstance(limit, (int, float)) or not math.isfinite(limit) or limit <= 0:
            raise ValueError('timeout_s must be finite and positive')
    return stages

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--plan', required=True)
    p.add_argument('--out-dir', required=True)
    p.add_argument('--budget', type=int, default=3600)
    a = p.parse_args()
    if a.budget <= 0:
        raise ValueError('budget must be positive')
    plan = json.loads(Path(a.plan).read_text())
    declared = validate_plan(plan)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    stages = []
    def interrupt(signum, frame):
        raise Interrupted(signum)
    old = {s: signal.signal(s, interrupt) for s in (signal.SIGTERM, signal.SIGINT)}
    try:
        for stage in declared:
            left = a.budget - (time.monotonic() - start)
            if left <= 0:
                stages.append({'id': stage['id'], 'status': 'INCOMPLETE', 'reason': 'budget exhausted'})
                break
            name = stage['id']
            limit = min(left, stage['timeout_s'])
            print(f'[{len(stages)+1}/{len(declared)}] {name} START remaining={left:.0f}s', flush=True)
            t = time.monotonic()
            rc = 78
            child = None
            try:
                with (out / (name + '.log')).open('w') as log:
                    child = subprocess.Popen(stage['argv'], stdout=log, stderr=subprocess.STDOUT,
                                             start_new_session=True)
                    rc = child.wait(timeout=limit)
            except subprocess.TimeoutExpired:
                rc = 124
            except Interrupted as e:
                rc = 128 + e.signum
            except FileNotFoundError as e:
                (out / (name + '.log')).write_text(str(e))
                rc = 78
            finally:
                # Do not let a second signal interrupt cleanup and orphan a GPU process.
                for s in old:
                    signal.signal(s, signal.SIG_IGN)
                if child is not None:
                    stop_group(child)
                for s in old:
                    signal.signal(s, interrupt)
            status = ('COMMAND_OK' if rc == 0 else 'BLOCKED' if rc == 78 else
                      'INCOMPLETE' if rc in (124, 130, 143) else 'FAIL')
            rec = {'id': name, 'status': status, 'exit_code': rc, 'wall_s': time.monotonic()-t}
            stages.append(rec)
            print(f'[{len(stages)}/{len(declared)}] {name} {status} {rec["wall_s"]:.1f}s', flush=True)
            (out/'progress.json').write_text(json.dumps(stages, indent=2))
            if rc in (130, 143) or (rc and stage.get('required', True)):
                break
    except Interrupted:
        stages.append({'id': 'supervisor', 'status': 'INCOMPLETE', 'reason': 'interrupted between stages'})
    finally:
        for s, handler in old.items():
            signal.signal(s, handler)
        summary = {'stages': stages, 'wall_s': time.monotonic()-start,
                   'all_commands_completed': len(stages)==len(declared) and all(s['status']=='COMMAND_OK' for s in stages),
                   'production_promoted': False}
        (out/'suite.json').write_text(json.dumps(summary, indent=2))
    return 0 if summary['all_commands_completed'] else 78

if __name__ == '__main__':
    sys.exit(main())
