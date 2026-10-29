"""Read system MSR counters while hhtele executes a single benchmark arm."""
import argparse
import json
import os
import pwd
import signal
import subprocess
import time

from bench_once import TASK, validate_request, stop_group


def command(a, out):
    wrapper = TASK.parents[1] / 'tools/gather_probe/bench_once.py'
    return ['perf', 'stat', '-a', '-C', '0-15', '-x,', '-I', '1000', '-e', 'msr/aperf/,msr/mperf/',
            '-o', str(out / 'aperf-mperf.csv'), '--', 'runuser', '-u', 'hhtele', '--', 'python3', '-B',
            str(wrapper), str(out), a.scope, a.mode, str(a.warm), str(a.seconds)]


def run(a):
    if os.geteuid() != 0:
        raise RuntimeError('ROOT_REQUIRED_FOR_SYSTEM_MSR_READ')
    out = validate_request(a)
    if out.stat().st_uid != pwd.getpwnam('hhtele').pw_uid:
        raise ValueError('PERF_OUTPUT_NOT_OWNED_BY_HHTELE')
    if (out / 'root-perf-start.json').exists():
        raise ValueError('PERF_ARM_ALREADY_STARTED')
    cmd = command(a, out)
    (out / 'root-perf-start.json').write_text(json.dumps({
        'epoch': time.time(), 'monotonic': time.monotonic(), 'command': cmd,
        'scope': 'read-only system MSRs on physical cores0-15; benchmark runs as hhtele'}, indent=2) + '\n')
    child = subprocess.Popen(cmd, start_new_session=True)
    try:
        return child.wait(timeout=a.warm + a.seconds + 180)
    finally:
        stop_group(child)


def terminated(*_):
    raise KeyboardInterrupt('ROOT_PERF_TERMINATED')


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, terminated)
    parser = argparse.ArgumentParser()
    parser.add_argument('out')
    parser.add_argument('scope', choices=['bench', 'row-bench'])
    parser.add_argument('mode', choices=['off', 'on'])
    parser.add_argument('warm', type=float)
    parser.add_argument('seconds', type=float)
    raise SystemExit(run(parser.parse_args()))
