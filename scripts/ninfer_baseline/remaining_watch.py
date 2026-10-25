#!/usr/bin/env python3
"""Observe an explicitly launched recovery; never launch or resend model work."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import time
from pathlib import Path


def validate(snapshot, supervisor, manifest_sha, ready):
    if snapshot['watchdog'].get('supervisor_pid') != supervisor:
        raise RuntimeError('recovery supervisor identity changed')
    if snapshot.get('manifest_sha256') != manifest_sha:
        raise RuntimeError('recovery manifest changed')
    return ready(snapshot, 'remaining')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', required=True)
    p.add_argument('--frozen-runtime', required=True)
    p.add_argument('--supervisor-pid', required=True, type=int)
    p.add_argument('--manifest-sha256', required=True)
    a = p.parse_args()
    root = Path(a.root).resolve()
    runtime = Path(a.frozen_runtime).resolve()
    source = runtime.parent
    expected = json.loads((source/'identity.json').read_text())
    source_status = json.loads((source/'status.json').read_text())
    external_summary = json.loads((source/'external-summary.json').read_text())
    cases = external_summary.get('cases', [])
    if (source_status.get('external_done') is not True or len(cases) != 2
            or {c['id'] for c in cases} != {'google__gson-2158', 'javaparser__javaparser-4561'}
            or any(c['status'] not in ('PASS', 'FAIL', 'OUTPUT_LIMIT') for c in cases)):
        raise RuntimeError('two completed external outcomes required for observation')
    for name, key in [('local_orchestrator.py', 'orchestrator_sha256'),
                      ('closed_loop.mjs', 'script_sha256'),
                      ('qcb_adapter.mjs', 'qcb_adapter_sha256'),
                      ('public_verify.mjs', 'public_verify_sha256')]:
        if hashlib.sha256((runtime/name).read_bytes()).hexdigest() != expected[key]:
            raise RuntimeError('frozen watch dependency changed: '+name)
    spec = importlib.util.spec_from_file_location('frozen_orchestrator', runtime/'local_orchestrator.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = module.private_root(root)
    with (root/'watch.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        observer = module.Orchestrator(root, remote_root=expected['remote_root'], mode='slim',
                    external_manifest=expected['external_manifest'], case_timeout_s=1800,
                    parent_timeout_s=2400)
        identity = {'supervisor_pid': a.supervisor_pid, 'manifest_sha256': a.manifest_sha256,
                    'watcher_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    'source_root': str(source), 'source_identity_sha256': module.digest(source/'identity.json'),
                    'external_summary_sha256': module.digest(source/'external-summary.json'),
                    'external_completion_status_sha256': module.digest(source/'status.json'),
                    'model_requests_allowed': False}
        identity_path = root/'watch-identity.json'
        if identity_path.exists() and json.loads(identity_path.read_text()) != identity:
            raise RuntimeError('watch configuration changed')
        module.atomic(identity_path, identity)
        observer.update(state='WAITING_REMAINING', remaining_supervisor_pid=a.supervisor_pid,
                        external_done=True, model_requests_allowed=False)
        try:
            while True:
                snapshot = observer.checked_snapshot(stage='remaining')
                if validate(snapshot, a.supervisor_pid, a.manifest_sha256, module.measurement_ready):
                    observer.update(state='MEASUREMENTS_RECORDED_NOT_BASELINE_PASS', remaining_done=True)
                    return
                time.sleep(300)
        except BaseException as exc:
            observer.update(state='NEEDS_ATTENTION', error=type(exc).__name__+': '+str(exc))
            raise


if __name__ == '__main__':
    main()
