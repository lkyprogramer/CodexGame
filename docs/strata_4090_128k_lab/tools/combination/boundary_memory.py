"""Read-only phase-aligned Linux memory sampling for the boundary experiment."""
from pathlib import Path
import json
import os
import re
import threading
import time


def numeric_fields(text):
    values = {}
    for line in text.splitlines():
        match = re.fullmatch(r'([^:]+):\s+(\d+)(?:\s+(kB))?\s*', line)
        if match:
            key, value, unit = match.groups()
            values[key + ('_kib' if unit else '')] = int(value)
    return values


def process_memory(pid, full=False):
    root = Path('/proc') / str(pid)
    result = {'pid': pid}
    try:
        result['status'] = numeric_fields((root / 'status').read_text())
        result['smaps_rollup'] = numeric_fields((root / 'smaps_rollup').read_text())
        result['stat'] = (root / 'stat').read_text()
        if full:
            for name in ('smaps', 'maps', 'limits', 'cgroup', 'io'):
                result[name] = (root / name).read_text()
    except (FileNotFoundError, ProcessLookupError) as error:
        result['process_exited'] = str(error)
    return result


def system_memory():
    return {'meminfo': numeric_fields(Path('/proc/meminfo').read_text()),
            'vmstat': {a: int(b) for a, b in (line.split() for line in Path('/proc/vmstat').read_text().splitlines())},
            'pressure_memory': Path('/proc/pressure/memory').read_text()}


class MemorySampler:
    def __init__(self, folder, pids, interval=1.0):
        self.folder, self.pids, self.interval = Path(folder), pids, interval
        self.stage = 'initial'
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.thread = None
        self.error = None

    def sample(self, full=False):
        result = {'ts': time.time(), 'monotonic': time.monotonic(), 'stage': self.stage,
                  'system': system_memory(), 'processes': [process_memory(pid, full) for pid in self.pids()]}
        result['capture_finished_ts'] = time.time()
        return result

    def checkpoint(self, name):
        self.stage = name
        result = self.sample(full=True)
        (self.folder / (name + '.memory.json')).write_text(json.dumps(result) + '\n')
        return result

    def _run(self):
        try:
            with (self.folder / 'memory.jsonl').open('a') as destination:
                while not self.stop.is_set():
                    destination.write(json.dumps(self.sample()) + '\n')
                    destination.flush()
                    self.stop.wait(self.interval)
                os.fsync(destination.fileno())
        except BaseException as error:
            self.error = str(error)

    def __enter__(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(timeout=30)
        if self.thread.is_alive() or self.error:
            raise RuntimeError('MEMORY_SAMPLER_FAILED: ' + str(self.error))
