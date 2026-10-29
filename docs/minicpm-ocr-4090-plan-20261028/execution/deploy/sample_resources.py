"""One-second GPU and whole candidate-container cgroup measurement."""
import argparse
import csv
import datetime
import json
import pathlib
import signal
import subprocess
import time


PROCESS_MEMORY_FIELDS = {
    'VmRSS': 'rss_bytes', 'VmHWM': 'hwm_bytes', 'RssAnon': 'anon_bytes',
    'RssFile': 'file_bytes', 'RssShmem': 'shmem_bytes',
}


def parse_process_status(text):
    """Retain only the process name and Linux status memory values, in bytes."""
    result = {}
    for line in text.splitlines():
        key, separator, value = line.partition(':')
        if not separator:
            continue
        if key == 'Name':
            result['name'] = value.strip()
        elif key in PROCESS_MEMORY_FIELDS:
            parts = value.split()
            if len(parts) != 2 or parts[1] != 'kB' or not parts[0].isdigit():
                raise ValueError(f'Invalid {key} memory value')
            result[PROCESS_MEMORY_FIELDS[key]] = int(parts[0]) * 1024
    required = {'name', *PROCESS_MEMORY_FIELDS.values()}
    if result.keys() != required:
        raise ValueError('Missing process name or memory fields: ' + ', '.join(sorted(required - result.keys())))
    return result


def read_process_rss(cgroup_root, proc_root=pathlib.Path('/proc')):
    """Sample every PID in this cgroup.procs snapshot; never sum a partial set."""
    result = {
        'process_rss': [], 'process_rss_status': 'UNAVAILABLE',
        'sum_rss_bytes_including_shared': None,
        'process_rss_note': 'Scope is the candidate cgroup.procs snapshot. Shared pages are counted '
                            'in each process and may be counted more than once.',
    }
    try:
        pids = [int(value) for value in (cgroup_root / 'cgroup.procs').read_text().split()]
    except (OSError, ValueError) as error:
        result['process_rss_error'] = f'{type(error).__name__}: {error}'
        return result
    for pid in pids:
        try:
            memory = parse_process_status((proc_root / str(pid) / 'status').read_text())
            result['process_rss'].append(dict(pid=pid, status='AVAILABLE', **memory))
        except (OSError, ValueError) as error:
            result['process_rss'].append({'pid': pid, 'status': 'UNAVAILABLE',
                                          'error': f'{type(error).__name__}: {error}'})
    if all(row['status'] == 'AVAILABLE' for row in result['process_rss']):
        result['process_rss_status'] = 'AVAILABLE'
        result['sum_rss_bytes_including_shared'] = sum(row['rss_bytes'] for row in result['process_rss'])
    else:
        result['process_rss_status'] = 'PARTIAL'
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--container', required=True)
    parser.add_argument('--out', type=pathlib.Path, required=True)
    args = parser.parse_args()
    stopped = False

    def stop(*_):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as output:
        while not stopped:
            started = time.monotonic()
            row = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'monotonic': started}
            try:
                gpu = subprocess.check_output([
                    'nvidia-smi', '--query-gpu=power.draw,memory.used,utilization.gpu,temperature.gpu,clocks.sm',
                    '--format=csv,noheader,nounits'], text=True, timeout=3).strip()
                values = next(csv.reader([gpu]))
                row['gpu'] = dict(zip(('power_watts', 'memory_mib', 'utilization_percent', 'temperature_c', 'sm_clock_mhz'),
                                      (float(v.strip()) for v in values)))
                pid = int(subprocess.check_output(['docker', 'inspect', '--format', '{{.State.Pid}}', args.container], text=True, timeout=3))
                cgroup = next(line.split(':', 2)[2].strip() for line in pathlib.Path(f'/proc/{pid}/cgroup').read_text().splitlines() if line.startswith('0::'))
                root = pathlib.Path('/sys/fs/cgroup') / cgroup.lstrip('/')
                row['cgroup'] = {name: (root/name).read_text().strip() for name in
                                 ('cpu.stat', 'memory.current', 'memory.peak', 'memory.events', 'memory.stat', 'io.stat') if (root/name).exists()}
                row.update(read_process_rss(root))
            except (subprocess.SubprocessError, OSError, ValueError, StopIteration) as exc:
                row['error'] = str(exc)
            output.write(json.dumps(row) + '\n')
            output.flush()
            time.sleep(max(0, 1 - (time.monotonic() - started)))


if __name__ == '__main__':
    main()
