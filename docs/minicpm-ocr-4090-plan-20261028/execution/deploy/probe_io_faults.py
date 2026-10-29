#!/usr/bin/env python3
"""Real F10 OS write faults for the shared atomic_json layer, without model calls.

Container invocation (after mounting CPU-only64KiB tmpfs /limited, a dedicated
read-only canary directory /readonly, and writable /work/evidence):
  PYTHONPATH=/work python /work/deploy/probe_io_faults.py \
    --readonly-dir /readonly --limited-dir /limited \
    --out /work/evidence/io-faults.json

Only these exclusive fixture directories are touched. No cleanup or deletion.
Evidence is written outside both fault mounts. Exit0 means both expected errors
and unchanged parseable canonical JSON were observed; exit1 means failure or
refused safety precondition. This is not a GPU, OCR quality or full HTTP test.
"""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import sys
import time


def sha(data):
    return hashlib.sha256(data).hexdigest()


def capacity(path):
    stat = os.statvfs(path)
    return {'path': str(path), 'f_bsize': stat.f_bsize, 'f_frsize': stat.f_frsize,
            'f_blocks': stat.f_blocks, 'f_bfree': stat.f_bfree, 'f_bavail': stat.f_bavail,
            'f_flag': stat.f_flag, 'total_bytes': stat.f_blocks * stat.f_frsize,
            'available_bytes': stat.f_bavail * stat.f_frsize,
            'free_bytes': stat.f_bfree * stat.f_frsize,
            'readonly_statvfs': bool(stat.f_flag & getattr(os, 'ST_RDONLY', 1))}


def final_state(final, before):
    data = final.read_bytes() if final.is_file() else None
    parsed = False
    if data is not None:
        try:
            json.loads(data)
            parsed = True
        except (ValueError, UnicodeError):
            pass
    temporary = final.with_name(final.name + '.tmp')
    return {'final_exists': data is not None, 'before_bytes': len(before),
            'before_sha256': sha(before),
            'final_bytes': len(data) if data is not None else None,
            'final_sha256': sha(data) if data is not None else None,
            'canonical_bytes_unchanged': data == before,
            'final_json_parseable': parsed,
            'temporary_exists': temporary.exists(),
            'temporary_bytes': temporary.stat().st_size if temporary.exists() else None,
            'temporary_allocated_bytes': temporary.stat().st_blocks * 512 if temporary.exists() else None,
            'temporary_is_never_success_artifact': True}


def attempt(atomic_json, final, payload, expected_errnos, before):
    error = None
    try:
        atomic_json(final, payload)
    except OSError as exc:
        error = {'type': type(exc).__name__, 'errno': exc.errno,
                 'errno_name': errno.errorcode.get(exc.errno, 'UNKNOWN'),
                 'message': str(exc)}
    except Exception as exc:
        error = {'type': type(exc).__name__, 'errno': None,
                 'errno_name': None, 'message': str(exc)}
    state = final_state(final, before)
    passed = (error is not None and error.get('errno') in expected_errnos
              and state['canonical_bytes_unchanged'] and state['final_json_parseable'])
    return {'target': str(final), 'expected_errnos': expected_errnos,
            'observed_error': error, 'write_returned_successfully': error is None,
            **state, 'expected_failure_verdict': 'PASS' if passed else 'FAIL'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--readonly-dir', type=Path, default=Path('/readonly'))
    ap.add_argument('--limited-dir', type=Path, default=Path('/limited'))
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    os.umask(0o077)
    ro, limited, output = args.readonly_dir.resolve(), args.limited_dir.resolve(), args.out.resolve()
    report = {'version': 'F10-atomic-os-faults-v1', 'test_layer': 'shared atomic_json filesystem write layer',
              'model_or_gpu_called': False, 'full_page_or_http_verified': False,
              'test_started_utc_epoch': time.time(), 'cases': [], 'status': 'REFUSED'}
    try:
        if not sys.platform.startswith('linux'):
            raise ValueError('CPU-only Linux fixture container required; local macOS execution refused')
        if ro != Path('/readonly') or limited != Path('/limited'):
            raise ValueError('exclusive fixture paths must be exactly /readonly and /limited')
        if not ro.is_dir() or not limited.is_dir():
            raise ValueError('both dedicated mount directories must already exist')
        if output == ro or ro in output.parents or output == limited or limited in output.parents:
            raise ValueError('evidence output must be outside both fault mounts')
        if output.exists():
            raise ValueError('evidence output already exists; use a new run evidence path')
        ro_capacity, limited_capacity = capacity(ro), capacity(limited)
        report['preflight'] = {'readonly': ro_capacity, 'limited': limited_capacity}
        if limited_capacity['available_bytes'] > 128 * 1024 or limited_capacity['total_bytes'] > 128 * 1024:
            raise ValueError('limited filesystem capacity exceeds128KiB: wrong fixture mount')
        if limited_capacity['available_bytes'] < 8192:
            raise ValueError('limited fixture lacks initial space for complete small canonical JSON')
        if any(limited.iterdir()):
            raise ValueError('limited directory must be new and empty; no existing files touched')
        canonical = ro / 'canonical.json'
        if not canonical.is_file() or canonical.is_symlink():
            raise ValueError('read-only fixture must contain regular canonical.json')
        if canonical.with_name('canonical.json.tmp').exists():
            raise ValueError('read-only temporary fixture path already exists')
        if not ro_capacity['readonly_statvfs'] and os.access(ro, os.W_OK):
            raise ValueError('read-only mount/permission precondition not established; refusing write')
        ro_before = canonical.read_bytes()
        json.loads(ro_before)
        # Import only after argparse/help and all mount preconditions. Never call a model.
        from ocrbench.client import atomic_json
        import ocrbench.client as client_module
        report['atomic_json_source_path'] = client_module.__file__
        report['atomic_json_module_sha256'] = sha(Path(client_module.__file__).read_bytes())
        ro_case = attempt(atomic_json, canonical, {'new_payload': 'must not replace read-only canary'},
                          [errno.EROFS, errno.EACCES], ro_before)
        ro_case.update(case='F10-READONLY', capacity_before=ro_capacity, capacity_after=capacity(ro))
        report['cases'].append(ro_case)
        final = limited / 'canonical.json'
        atomic_json(final, {'fixture': 'small-complete-canonical', 'version': 1})
        before = final.read_bytes()
        json.loads(before)
        before_capacity = capacity(limited)
        payload = {'new_payload': 'X' * (384 * 1024)}
        case = attempt(atomic_json, final, payload, [errno.ENOSPC], before)
        case.update(case='F10-ENOSPC', requested_payload_string_bytes=384 * 1024,
                    capacity_before=before_capacity, capacity_after=capacity(limited))
        report['cases'].append(case)
        report['status'] = 'PASS' if all(c['expected_failure_verdict'] == 'PASS' for c in report['cases']) else 'FAIL'
    except Exception as exc:
        report.update(status='REFUSED_OR_FAILED', harness_error={'type': type(exc).__name__, 'message': str(exc)})
    report['test_finished_utc_epoch'] = time.time()
    # Normal evidence path uses ordinary exclusive creation; never writes to /limited or /readonly.
    if output == ro or ro in output.parents or output == limited or limited in output.parents:
        print(json.dumps({'status': report['status'], 'evidence_write': 'REFUSED_UNSAFE_PATH'}))
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': report['status'], 'evidence': str(output),
                      'test_layer': report['test_layer'], 'cases': len(report['cases'])}))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
