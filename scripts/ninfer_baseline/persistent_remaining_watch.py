#!/usr/bin/env python3
"""Durable read-only observer. It cannot launch a collector or model request."""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def observe(snapshot, config, ready):
    if snapshot['manifest_sha256'] != config['manifest_sha256']:
        raise RuntimeError('manifest identity changed')
    if snapshot['watchdog']['supervisor_pid'] != config['supervisor_pid']:
        raise RuntimeError('supervisor identity changed')
    return ready(snapshot, 'remaining')


def main(root):
    os.umask(0o077)
    config = json.loads((root/'config.json').read_text())
    if sha(root/'frozen_orchestrator.py') != config['helper_sha256']:
        raise RuntimeError('frozen readiness helper changed')
    if sha(config['external_evidence']) != config['external_evidence_sha256']:
        raise RuntimeError('external result evidence changed')
    evidence = json.loads(Path(config['external_evidence']).read_text())
    if {r['id'] for r in evidence['external_scores']} != {'google__gson-2158', 'javaparser__javaparser-4561'}:
        raise RuntimeError('external results missing')
    spec = importlib.util.spec_from_file_location('frozen_readiness', root/'frozen_orchestrator.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    remote_root = '/home/hhtele/ninfer-baseline-20261020/slim-v1'
    code = ("import json,hashlib;from pathlib import Path;p=Path("+repr(remote_root)+
            ");d={k:json.loads((p/(k+'.json')).read_text()) for k in ['status','watchdog']};"
            "d['manifest_sha256']=hashlib.sha256((p/'manifest.json').read_bytes()).hexdigest();print(json.dumps(d))")
    import shlex
    command = ['ssh', '-oBatchMode=yes', '-oConnectTimeout=20', '29', shlex.join(['python3', '-c', code])]
    failures = 0
    with (root/'watch.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=50, check=True)
                snapshot = json.loads(result.stdout)
                complete = observe(snapshot, config, module.measurement_ready)
                failures = 0
                state = 'MEASUREMENTS_RECORDED_NOT_BASELINE_PASS' if complete else 'WAITING_REMAINING'
                status = {'state': state, 'pid': os.getpid(), 'heartbeat_utc': module.utc(),
                          'model_requests_allowed': False, 'external_results_recorded': True,
                          'snapshot': snapshot}
            except Exception as error:
                failures += 1
                status = {'state': 'NEEDS_ATTENTION' if failures >= 3 else 'REMOTE_CHECK_RETRY',
                          'pid': os.getpid(), 'heartbeat_utc': module.utc(),
                          'consecutive_failures': failures, 'error': type(error).__name__+': '+str(error)}
                complete = False
            module.atomic(root/'status.json', status)
            with (root/'events.jsonl').open('a') as stream:
                stream.write(json.dumps(status)+'\n')
                stream.flush()
                os.fsync(stream.fileno())
            if complete and config.get('finalizer_command'):
                try:
                    for path, expected in config['finalizer_hashes'].items():
                        if sha(path) != expected:
                            raise RuntimeError('frozen finalizer changed: '+path)
                    status.update(state='FINALIZING_REPORT', heartbeat_utc=module.utc())
                    module.atomic(root/'status.json', status)
                    with (root/'finalizer.log').open('ab') as log:
                        result = subprocess.run(config['finalizer_command'],stdout=log,stderr=subprocess.STDOUT,timeout=1200)
                    final = json.loads(Path(config['finalization_status']).read_text())
                    if result.returncode or final['state']!='REPORT_READY_WITH_DISCLOSED_LIMITATIONS':
                        raise RuntimeError('final report generation failed; inspect finalizer.log')
                    status.update(state=final['state'], final_report=final['report'],
                                  final_backup=final['final_backup'], heartbeat_utc=module.utc())
                except Exception as error:
                    status.update(state='FINALIZATION_NEEDS_ATTENTION',heartbeat_utc=module.utc(),
                                  error=type(error).__name__+': '+str(error))
                module.atomic(root/'status.json',status)
                with (root/'events.jsonl').open('a') as stream:
                    stream.write(json.dumps(status)+'\n')
                    stream.flush()
                    os.fsync(stream.fileno())
            if complete or failures >= 3:
                return
            time.sleep(300)


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
