#!/usr/bin/env python3
"""Production monitor for the 4090 Strata service: a one-minute sampler, a daily rollup and bounded retention.

    strata_monitor.py sample                      # cron, every minute: one JSON line in DATA/samples/YYYY-MM-DD.jsonl
    strata_monitor.py daily [--date D] [--force]  # cron, 00:17: requests + report of each finished day, gzip, prune
    strata_monitor.py prune [--dry-run]           # retention and the size cap (daily runs it)
    strata_monitor.py status                      # last sample, disk use, cron block, last report's warnings
    strata_monitor.py cron show|install|remove    # the crontab lines, between marker comments

A sample reads /proc, cgroup v2, nvidia-smi and the server's /metrics, and writes only under DATA: host CPU, iowait,
MemAvailable, swap, AnonHugePages and PSI; the production unit's CPU, memory, swap, PSI and disk IO; the engine's RSS,
swap, major faults and CPU; every docker scope's CPU and memory (the co-tenants); GPU temperature, power, clocks, PCIe
link and clock-event reasons; /metrics live state and running totals; and the engine log's size.  The log size dates
the requests: the daily job parses the engine log with ../prodlog.py (the one parser of that log) and gives each request
the sample interval in which its summary line was written, plus the co-tenant and host load while it ran.

During a lab run (a strata engine outside the unit, or one of LAB_SCRIPTS running) a sample is `mode: lab` and skips
nvidia-smi and /metrics.  Disk: raw samples ~1.5 MB a day, gzipped once the day is done; samples are kept 30 days,
requests and reports 180; the data directory is capped at 200 MB (oldest files go first), one day's raw file at 20 MB.
Stdlib only (Python 3.9+).
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

UNIT = 'openclaw-qwen38-next.service'
LAB_SCRIPTS = frozenset({'upgrade_gate.py', 'gate17.py', 'quant_quality.py', 'pisim.py', 'session_bench.py', 'chain_bench.py'})
KEEP_DAYS = {'samples': 30, 'requests': 180, 'reports': 180}
CAP_BYTES = 200 << 20       # the whole data directory; prune removes the oldest files down to 90% of it
DAY_RAW_CAP = 20 << 20      # one day's raw samples; past it the sampler stops writing that day
LOG_CAP = 1 << 20           # monitor.log; the cron line moves it to monitor.log.1 past this size
MARGIN = 64 << 10           # engine-log bytes read around a day's window (decode timing precedes its summary line)
WARN = dict(coverage=0.95, avail_mib=3072, swap_free_frac=0.10, gpu_temp=85, unit_mem_full_s=5.0, decode_drop=0.85,
            decode_min_requests=10, trailing_days=7, cotenant_busy=1.0)
REASONS = {0x1: 'idle', 0x2: 'app_clocks', 0x4: 'sw_power_cap', 0x8: 'hw_slowdown', 0x10: 'sync_boost',
           0x20: 'sw_thermal', 0x40: 'hw_thermal', 0x80: 'hw_power_brake', 0x100: 'display_clocks'}
REASONS_BAD = 0x8 | 0x20 | 0x40 | 0x80
GPU_QUERY = (('temp', 'temperature.gpu'), ('util', 'utilization.gpu'), ('mem_util', 'utilization.memory'),
             ('mem_used_mib', 'memory.used'), ('power_w', 'power.draw'), ('sm_mhz', 'clocks.sm'), ('mem_mhz', 'clocks.mem'),
             ('pcie_gen', 'pcie.link.gen.current'), ('pcie_width', 'pcie.link.width.current'),
             ('reasons', 'clocks_event_reasons.active'), ('fan', 'fan.speed'))
TOTALS = ('since', 'requests', 'prompt_tokens', 'reused', 'output_tokens', 'prompt_ms', 'decode_ms', 'drafts_accepted', 'drafts_offered')
HERE = Path(__file__).resolve().parent
PRODLOG = HERE.parent / 'prodlog.py'
BEGIN, END = '# >>> strata_monitor', '# <<< strata_monitor'
SCHEMA = 1
TCK = os.sysconf('SC_CLK_TCK') if hasattr(os, 'sysconf') else 100


# ---------------------------------------------------------------- small readers
def rd(p):
    try:
        with open(p, errors='replace') as f:
            return f.read()
    except OSError:
        return None


def num(s):
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


def mib_kb(kb):
    return None if kb is None else kb // 1024


def mib_b(b):
    return None if b is None else b >> 20


def int_file(p):
    return num((rd(p) or '').strip())


def flat_kv(text):
    """'key value' lines (cgroup cpu.stat)."""
    out = {}
    for line in (text or '').splitlines():
        p = line.split()
        if len(p) == 2 and num(p[1]) is not None:
            out[p[0]] = int(p[1])
    return out


def meminfo(text):
    """'Key:   123 kB' lines (/proc/meminfo, /proc/PID/status) -> {key: int}."""
    out = {}
    for line in (text or '').splitlines():
        k, _, v = line.partition(':')
        p = v.split()
        if p and num(p[0]) is not None:
            out[k.strip()] = int(p[0])
    return out


def psi(text):
    """A pressure file -> {'some': total_us, 'full': total_us}."""
    out = {}
    for line in (text or '').splitlines():
        p = line.split()
        if p and p[0] in ('some', 'full'):
            for x in p[1:]:
                if x.startswith('total='):
                    out[p[0]] = num(x[6:])
    return out


def io_stat(text):
    """cgroup io.stat -> rbytes and wbytes summed over devices."""
    r = w = 0
    for line in (text or '').splitlines():
        for x in line.split()[1:]:
            k, _, v = x.partition('=')
            if k == 'rbytes':
                r += num(v) or 0
            elif k == 'wbytes':
                w += num(v) or 0
    return dict(r=r, w=w)


def proc_cpu(text):
    """/proc/stat -> ticks of all CPUs (total of the first eight fields, idle, iowait) and the CPU count."""
    out, n = None, 0
    for line in (text or '').splitlines():
        if line.startswith('cpu '):
            v = [int(x) for x in line.split()[1:9]]
            out = dict(total=sum(v), idle=v[3], iowait=v[4])
        elif line.startswith('cpu') and line[3:4].isdigit():
            n += 1
    if out:
        out['n'] = n
    return out


def pid_stat(text):
    """/proc/PID/stat: the fields after the comm's last ')' -> minflt, majflt, utime, stime, start (clock ticks)."""
    f = text.rsplit(')', 1)[1].split()
    return dict(minflt=int(f[7]), majflt=int(f[9]), utime=int(f[11]), stime=int(f[12]), start=int(f[19]))


def rate(cur, prev, dt_s, scale=1.0):
    if dt_s is None or cur is None or prev is None or cur < prev:
        return None
    return round((cur - prev) * scale / dt_s, 3)


def psi_rates(p, pp, dt_s):
    """Stall time per second of the interval, from PSI totals (us)."""
    out = {}
    for res, short in (('cpu', 'cpu'), ('memory', 'mem'), ('io', 'io')):
        for k in ('some', 'full'):
            if res == 'cpu' and k == 'full':
                continue
            out['%s_%s' % (short, k)] = rate((p.get(res) or {}).get(k), ((pp or {}).get(res) or {}).get(k), dt_s, 1e-6)
    return out


def local_date(ts):
    return time.strftime('%Y-%m-%d', time.localtime(ts))


def iso(ts):
    return time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(ts))


def midnight(d):
    return time.mktime((d.year, d.month, d.day, 0, 0, 0, 0, 0, -1))


def day_bounds(day):
    d = dt.date.fromisoformat(day)
    return midnight(d), midnight(d + dt.timedelta(days=1))


def load_json(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def write_atomic(p, data: bytes):
    p = Path(p)
    tmp = p.with_name(p.name + '.tmp')
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, p)


@contextlib.contextmanager
def locked(path, block):
    with open(path, 'a+') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | (0 if block else fcntl.LOCK_NB))
        except BlockingIOError:
            yield False
            return
        yield True


# ---------------------------------------------------------------- one sample
def processes(root):
    """{pid: argv} of every process with a command line."""
    out = {}
    proc = Path(root) / 'proc'
    try:
        names = os.listdir(proc)
    except OSError:
        return out
    for n in names:
        if n.isdigit():
            c = rd(proc / n / 'cmdline')
            if c and c.strip('\0'):
                out[int(n)] = c.rstrip('\0').split('\0')
    return out


def lab_markers(procs, unit_pids):
    """A strata engine outside the production unit, or a python process running one of LAB_SCRIPTS."""
    found = set()
    for pid, argv in procs.items():
        exe = os.path.basename(argv[0])
        if exe == 'strata' and pid not in unit_pids:
            found.add('engine:%d' % pid)
        elif exe.startswith('python'):
            script = next((a for a in argv[1:] if not a.startswith('-')), '')
            if os.path.basename(script) in LAB_SCRIPTS:
                found.add(os.path.basename(script))
    return sorted(found)


def host_part(root, prev, dt_s, cur):
    root = Path(root)
    cpu = proc_cpu(rd(root / 'proc/stat'))
    mi = meminfo(rd(root / 'proc/meminfo'))
    load = (rd(root / 'proc/loadavg') or '').split()
    p = {r: psi(rd(root / 'proc/pressure' / r)) for r in ('cpu', 'memory', 'io')}
    cur['cpu'], cur['psi'] = cpu, p
    swap = mi['SwapTotal'] - mi['SwapFree'] if 'SwapTotal' in mi and 'SwapFree' in mi else None
    out = dict(cpu=None, iowait=None, load1=float(load[0]) if load else None, avail_mib=mib_kb(mi.get('MemAvailable')),
               swap_total_mib=mib_kb(mi.get('SwapTotal')), swap_used_mib=mib_kb(swap), anon_huge_mib=mib_kb(mi.get('AnonHugePages')),
               psi=psi_rates(p, prev.get('psi'), dt_s))
    pc = prev.get('cpu')
    if cpu and pc and dt_s and cpu['total'] > pc['total']:
        d = cpu['total'] - pc['total']
        idle, iow = cpu['idle'] - pc['idle'], max(0, cpu['iowait'] - pc['iowait'])   # iowait can step back
        out['cpu'] = round(max(0, d - idle - iow) / d * cpu['n'], 3)
        out['iowait'] = round(iow / d * cpu['n'], 3)
    return out


def unit_part(root, unit, procs, prev, dt_s, cur):
    """(unit, engine, server argv) of the production unit; (None, None, None) when it has no process."""
    d = Path(root) / 'sys/fs/cgroup/system.slice' / unit
    pids = [int(x) for x in (rd(d / 'cgroup.procs') or '').split() if x.isdigit()]
    if not pids:
        return None, None, None, pids
    try:
        ino = os.stat(d).st_ino
    except OSError:
        ino = None
    usage = flat_kv(rd(d / 'cpu.stat')).get('usage_usec')
    p = {r: psi(rd(d / ('%s.pressure' % r))) for r in ('cpu', 'memory', 'io')}
    io = io_stat(rd(d / 'io.stat'))
    cur['unit'] = dict(ino=ino, usage=usage, psi=p, io=io)
    pu = prev.get('unit') or {}
    if pu.get('ino') != ino:
        pu = {}
    unit = dict(cpu=rate(usage, pu.get('usage'), dt_s, 1e-6), mem_mib=mib_b(int_file(d / 'memory.current')),
                swap_mib=mib_b(int_file(d / 'memory.swap.current')), psi=psi_rates(p, pu.get('psi'), dt_s),
                read_mib_s=rate(io['r'], (pu.get('io') or {}).get('r'), dt_s, 1 / 1048576),
                write_mib_s=rate(io['w'], (pu.get('io') or {}).get('w'), dt_s, 1 / 1048576))
    eng = next((x for x in pids if os.path.basename(procs.get(x, [''])[0]) == 'strata'), None)
    srv = next((procs[x] for x in pids if any(a.endswith('server.py') for a in procs.get(x, []))), None)
    engine = None
    if eng is not None:
        st = pid_stat(rd(Path(root) / 'proc' / str(eng) / 'stat') or '')
        m = meminfo(rd(Path(root) / 'proc' / str(eng) / 'status'))
        pe = prev.get('engine') or {}
        same = pe.get('pid') == eng and pe.get('start') == st['start']
        ticks = st['utime'] + st['stime']
        engine = dict(pid=eng, start=st['start'], rss_mib=mib_kb(m.get('VmRSS')), anon_mib=mib_kb(m.get('RssAnon')),
                      swap_mib=mib_kb(m.get('VmSwap')), threads=m.get('Threads'),
                      cpu=rate(ticks, pe.get('ticks') if same else None, dt_s, 1 / TCK),
                      majflt=st['majflt'] - pe['majflt'] if same and st['majflt'] >= pe.get('majflt', 0) else None)
        cur['engine'] = dict(pid=eng, start=st['start'], ticks=ticks, majflt=st['majflt'])
    return unit, engine, srv, pids


def docker_part(root, prev, dt_s, cur):
    """{container id (12): {name, cpu cores, mem_mib}} from the docker-*.scope cgroups (the co-tenants)."""
    root = Path(root)
    out, c = {}, {}
    for d in sorted((root / 'sys/fs/cgroup/system.slice').glob('docker-*.scope')):
        cid = d.name[len('docker-'):-len('.scope')][:12]
        pids = (rd(d / 'cgroup.procs') or '').split()
        name = (rd(root / 'proc' / pids[0] / 'comm') or '?').strip() if pids else '-'
        usage = flat_kv(rd(d / 'cpu.stat')).get('usage_usec')
        c[cid] = usage
        out[cid] = dict(name=name, cpu=rate(usage, (prev.get('docker') or {}).get(cid), dt_s, 1e-6),
                        mem_mib=mib_b(int_file(d / 'memory.current')))
    cur['docker'] = c
    return out


def server_config(argv):
    """The run config of a server.py command line -> (config dict, path)."""
    if argv and '--config' in argv:
        i = argv.index('--config')
        if i + 1 < len(argv):
            return json.loads(Path(argv[i + 1]).read_text()), argv[i + 1]
    return None, None


def parse_gpu(line):
    out = {}
    for (k, _), v in zip(GPU_QUERY, [x.strip() for x in line.split(',')]):
        if k == 'reasons':
            out[k] = int(v, 16) if v.startswith('0x') else None
            continue
        try:
            out[k] = float(v) if '.' in v else int(v)
        except ValueError:
            out[k] = None                      # [N/A]
    return out


def gpu_query(index=0, timeout=10):
    exe = next((p for p in ('/usr/bin/nvidia-smi', '/usr/local/bin/nvidia-smi') if os.path.exists(p)), 'nvidia-smi')
    r = subprocess.run([exe, '--id=%d' % index, '--query-gpu=' + ','.join(f for _, f in GPU_QUERY), '--format=csv,noheader,nounits'],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError('nvidia-smi rc=%s %s' % (r.returncode, (r.stdout + r.stderr).strip()[:120]))
    return parse_gpu(r.stdout.strip().splitlines()[0])


def metrics_subset(d):
    live, tot, cc = d.get('live') or {}, d.get('totals') or {}, d.get('conversation_cache') or {}
    return dict(state=live.get('state'), queued=live.get('queued'), phase=live.get('phase'), totals={k: tot.get(k) for k in TOTALS},
                conv={k: cc.get(k) for k in ('parked', 'bytes', 'parks', 'restores', 'evictions', 'refused_total')},
                requests_kept=d.get('requests_kept'))


def metrics_query(host, port, timeout=2.0):
    from urllib.request import urlopen
    with urlopen('http://%s:%d/metrics' % (host, port), timeout=timeout) as r:
        return metrics_subset(json.loads(r.read(4 << 20)))


def take_sample(root, state, now, gpu=gpu_query, metrics=metrics_query, unit=UNIT):
    """-> (sample, counters for the next sample's rates, engine log path)."""
    errs, cur = [], {}
    prev = state.get('counters') or {}
    last = state.get('ts')
    dt_s = now - last if isinstance(last, (int, float)) and 0 < now - last <= 3600 else None
    s = dict(schema=SCHEMA, ts=round(now, 1), t=iso(now), dt=round(dt_s, 1) if dt_s else None)

    def step(name, fn, *a):
        try:
            return fn(*a)
        except Exception as e:                 # one source failing must not lose the rest of the sample
            errs.append('%s: %s: %s' % (name, type(e).__name__, str(e)[:160]))
            return None

    procs = step('procs', processes, root) or {}
    s['host'] = step('host', host_part, root, prev, dt_s, cur)
    u = step('unit', unit_part, root, unit, procs, prev, dt_s, cur) or (None, None, None, [])
    s['unit'], s['engine'] = u[0], u[1]
    lab = lab_markers(procs, set(u[3]))
    s['mode'] = 'lab' if lab else ('prod' if s['engine'] else 'down')
    if lab:
        s['lab'] = lab
    s['docker'] = step('docker', docker_part, root, prev, dt_s, cur)
    cfg = None
    if u[2]:
        got = step('config', server_config, u[2])
        cfg = got[0] if got else None
    logp = (cfg or {}).get('log') or state.get('log_path')
    s['log'] = None
    if logp:
        try:
            st = os.stat(logp)
            s['log'] = dict(path=logp, ino=st.st_ino, size=st.st_size, live=bool(cfg))
        except OSError as e:
            errs.append('log: %s' % e)
    s['gpu'] = step('gpu', gpu, (cfg or {}).get('gpu', 0)) if s['mode'] != 'lab' else None
    s['metrics'] = (step('metrics', metrics, cfg.get('host') or '127.0.0.1', int(cfg['port']))
                    if cfg and cfg.get('port') and s['mode'] == 'prod' else None)
    if errs:
        s['errors'] = errs
    return s, cur, logp


def cmd_sample(data, root='/', now=None, gpu=gpu_query, metrics=metrics_query):
    data = Path(data)
    for sub in ('samples', 'requests', 'reports'):
        (data / sub).mkdir(parents=True, exist_ok=True)
    with locked(data / '.sample.lock', block=False) as ok:
        if not ok:
            print(iso(time.time()), 'sample: previous sample still running; skipped')
            return 0
        state = load_json(data / 'state.json') or {}
        now = time.time() if now is None else now
        s, cur, logp = take_sample(root, state, now, gpu, metrics)
        day = local_date(now)
        raw = data / 'samples' / (day + '.jsonl')
        if raw.exists() and raw.stat().st_size >= DAY_RAW_CAP:
            if state.get('cap_day') != day:
                print(iso(now), 'sample: %s reached %d bytes; no more samples today' % (raw.name, DAY_RAW_CAP))
            state['cap_day'] = day
        else:
            with open(raw, 'a') as f:
                f.write(json.dumps(s, separators=(',', ':')) + '\n')
        errs = sorted(e.split(':', 1)[0] for e in s.get('errors', []))
        if errs != state.get('errors', []):    # report a change of failing sources, not every minute
            print(iso(now), 'sample errors:' if errs else 'sample errors cleared', '; '.join(s.get('errors', [])))
        state.update(ts=now, counters=cur, log_path=logp, errors=errs)
        write_atomic(data / 'state.json', json.dumps(state).encode())
    return 0


# ---------------------------------------------------------------- daily rollup
def load_prodlog(path=PRODLOG):
    import importlib.util
    if not Path(path).exists():
        return None
    spec = importlib.util.spec_from_file_location('prodlog', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def load_samples(data, day):
    import gzip
    for p in (Path(data) / 'samples' / (day + '.jsonl'), Path(data) / 'samples' / (day + '.jsonl.gz')):
        if p.exists():
            out = []
            with (gzip.open(p, 'rt', errors='replace') if p.suffix == '.gz' else open(p, errors='replace')) as f:
                for line in f:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        pass                   # a torn last line
            return out
    return []


def intervals(seq):
    """Byte ranges of the engine log written between two samples that saw the same file:
    [((path, ino), lo, hi, t_lo, t_hi)], plus counts of file switches and shrinks (no range spans those)."""
    last, out, switches, shrinks, cur_key = {}, [], 0, 0, None
    for s in seq:
        lg = s.get('log')
        if not lg:
            continue
        k = (lg['path'], lg['ino'])
        if cur_key is not None and k != cur_key:
            switches += 1
        cur_key = k
        if k in last and lg['size'] < last[k][0]:
            shrinks += 1
        elif k in last and lg['size'] > last[k][0]:
            out.append((k, last[k][0], lg['size'], last[k][1], s['ts']))
        last[k] = (lg['size'], s['ts'])
    return out, switches, shrinks


def log_requests(path, ino, ranges, prodlog):
    """prodlog requests whose summary line ends inside one of ranges [(lo, hi, t_lo, t_hi)] of this file, each with
    _lo/_hi (the sample times around it).  None when the file is gone or was replaced."""
    import bisect
    try:
        if os.stat(path).st_ino != ino:
            return None
    except OSError:
        return None
    ranges = sorted(ranges)
    start, stop = max(0, ranges[0][0] - MARGIN), ranges[-1][1] + MARGIN
    lines, ends, head = [], [], None
    with open(path, 'rb') as f:
        off = 0
        for raw in f:
            end = off + len(raw)
            if end <= start:
                if b'engine started:' in raw:
                    head = raw                 # the epoch the window starts in
            elif off < stop:
                lines.append(raw.decode('utf-8', 'replace'))
                ends.append(end)
            else:
                break
            off = end
    pre = [head.decode('utf-8', 'replace')] if head else []
    reqs = prodlog.parse(pre + lines)
    sums = [e for line, e in zip(lines, ends) if prodlog.PROMPT.search(line) and not prodlog.START.search(line)]
    if len(sums) != len(reqs):
        raise RuntimeError('prodlog gave %d requests for %d summary lines' % (len(reqs), len(sums)))
    los = [r[0] for r in ranges]
    out = []
    for r, e in zip(reqs, sums):
        i = bisect.bisect_left(los, e) - 1     # the range with lo < e
        if i >= 0 and ranges[i][0] < e <= ranges[i][1]:
            r['_lo'], r['_hi'] = ranges[i][2], ranges[i][3]
            out.append(r)
    return out


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def col(samples, *path):
    out = []
    for s in samples:
        v = s
        for k in path:
            v = v.get(k) if isinstance(v, dict) else None
        if _num(v):
            out.append(v)
    return out


def pct(xs, q):
    xs = sorted(x for x in xs if _num(x))
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else None


def mean(xs):
    xs = [x for x in xs if _num(x)]
    return round(sum(xs) / len(xs), 3) if xs else None


def cotenant(s):
    v = [d['cpu'] for d in (s.get('docker') or {}).values() if _num(d.get('cpu'))]
    return round(sum(v), 3) if v else None


def context(r, seq):
    """Load while the request ran.  It ran inside (t_lo - its own time, t_hi]; the samples whose interval overlaps that
    window count, the means weighted by the overlap, the maxima and the fault sum over all of them (an upper bound)."""
    dur = (r['prompt_ms'] + r['decode_ms']) / 1000
    a, b = r['_lo'] - dur, r['_hi']
    win, wts = [], []
    for s in seq:
        ov = min(s['ts'], b) - max(s['ts'] - (s.get('dt') or 60), a)
        if ov > 0:
            win.append(s)
            wts.append(ov)

    def wmean(vals):
        p = [(v, x) for v, x in zip(vals, wts) if _num(v)]
        tot = sum(x for _, x in p)
        return round(sum(v * x for v, x in p) / tot, 3) if tot else None

    co = [cotenant(s) for s in win]
    maj = col(win, 'engine', 'majflt')
    return dict(samples=len(win), cotenant_cpu_mean=wmean(co), cotenant_cpu_max=max((x for x in co if _num(x)), default=None),
                host_cpu_mean=wmean([(s.get('host') or {}).get('cpu') for s in win]), engine_majflt=sum(maj) if maj else None,
                unit_mem_full_max=max(col(win, 'unit', 'psi', 'mem_full'), default=None),
                swap_used_mib_max=max(col(win, 'host', 'swap_used_mib'), default=None),
                gpu_temp_max=max(col(win, 'gpu', 'temp'), default=None), modes=sorted({s.get('mode') for s in win if s.get('mode')}))


def seconds(samples, *path):
    """Sum of a per-second figure times each sample's interval."""
    return round(sum(v * s['dt'] for s in samples if _num(s.get('dt')) for v in col([s], *path)), 1)


def metrics_deltas(seq):
    """Positive differences of /metrics running totals between consecutive samples of the same server run."""
    out, last = {k: 0 for k in TOTALS if k != 'since'}, None
    for s in seq:
        t = (s.get('metrics') or {}).get('totals') or {}
        if t.get('since') is None:
            continue
        if last is not None and last.get('since') == t['since']:
            for k in out:
                if _num(t.get(k)) and _num(last.get(k)) and t[k] >= last[k]:
                    out[k] += t[k] - last[k]
        last = t
    return out


def contention(reqs, prodlog, busy):
    """Requests split by the co-tenants' CPU while they ran: decode speed by prompt bucket and CPU ms per expert entry."""
    out = {}
    for name, keep in (('cotenant_below_%g' % busy, lambda x: x < busy), ('cotenant_at_least_%g' % busy, lambda x: x >= busy)):
        rs = [r for r in reqs if _num(r['ctx'].get('cotenant_cpu_mean')) and keep(r['ctx']['cotenant_cpu_mean'])]
        per = [t['cpu_experts'] / t['cpu_entries'] for r in rs for t in r['timing'] if t.get('cpu_entries')]
        out[name] = dict(requests=len(rs), cpu_ms_per_entry=pct(per, 0.5) if per else None,
                         decode_tok_s={b: v['decode_tok_s'] for b, v in prodlog.summarize(rs)['by_prompt_bucket'].items()} if rs else {})
    return out


def trailing_decode(data, day, days):
    """Median over the previous reports of each bucket's decode tok/s median."""
    d0, by = dt.date.fromisoformat(day), {}
    for i in range(1, days + 1):
        rep = load_json(Path(data) / 'reports' / ((d0 - dt.timedelta(days=i)).isoformat() + '.json')) or {}
        for b, v in ((((rep.get('requests') or {}).get('summary')) or {}).get('by_prompt_bucket') or {}).items():
            if _num(v.get('decode_tok_s')):
                by.setdefault(b, []).append(v['decode_tok_s'])
    return {b: pct(v, 0.5) for b, v in by.items()}


def hourly(samples, reqs):
    rows = {}
    for s in samples:
        h = rows.setdefault(time.localtime(s['ts']).tm_hour, dict(minutes=0, modes={}, co=[], cpu=[], temp=[], requests=0, generated=0, decode_s=0.0))
        h['minutes'] += 1
        h['modes'][s.get('mode')] = h['modes'].get(s.get('mode'), 0) + 1
        h['co'].append(cotenant(s))
        h['cpu'] += col([s], 'host', 'cpu')
        h['temp'] += col([s], 'gpu', 'temp')
    for r in reqs:
        h = rows.setdefault(time.localtime(r['_hi']).tm_hour, dict(minutes=0, modes={}, co=[], cpu=[], temp=[], requests=0, generated=0, decode_s=0.0))
        h['requests'] += 1
        h['generated'] += r['generated']
        h['decode_s'] += r['decode_ms'] / 1000
    return [dict(hour=k, minutes=v['minutes'], modes=v['modes'], requests=v['requests'], generated=v['generated'],
                 decode_s=round(v['decode_s'], 1), cotenant_cpu_mean=mean(v['co']), cotenant_cpu_max=max((x for x in v['co'] if _num(x)), default=None),
                 host_cpu_mean=mean(v['cpu']), gpu_temp_max=max(v['temp'], default=None)) for k, v in sorted(rows.items())]


def build_report(data, day, samples, seq, reqs, prodlog, logs):
    a, b = day_bounds(day)
    expected = round((b - a) / 60)
    edges = [a] + [s['ts'] for s in samples] + [b]
    gaps = [dict(start=iso(x), end=iso(y), minutes=round((y - x) / 60)) for x, y in zip(edges, edges[1:]) if y - x > 150]
    modes = {}
    for s in samples:
        modes[s.get('mode')] = modes.get(s.get('mode'), 0) + 1
    prod = [s for s in samples if s.get('mode') == 'prod']
    swap_frac = [(s['host']['swap_total_mib'] - s['host']['swap_used_mib']) / s['host']['swap_total_mib'] for s in samples
                 if _num((s.get('host') or {}).get('swap_used_mib')) and _num(s['host'].get('swap_total_mib')) and s['host']['swap_total_mib'] > 0]
    host = dict(cpu_p50=pct(col(samples, 'host', 'cpu'), 0.5), cpu_p95=pct(col(samples, 'host', 'cpu'), 0.95),
                cpu_max=max(col(samples, 'host', 'cpu'), default=None), iowait_p95=pct(col(samples, 'host', 'iowait'), 0.95),
                avail_mib_min=min(col(samples, 'host', 'avail_mib'), default=None),
                swap_used_mib=dict(first=(col(samples, 'host', 'swap_used_mib') or [None])[0], max=max(col(samples, 'host', 'swap_used_mib'), default=None),
                                   last=(col(samples, 'host', 'swap_used_mib') or [None])[-1]),
                swap_free_frac_min=round(min(swap_frac), 3) if swap_frac else None,
                anon_huge_mib_min=min(col(samples, 'host', 'anon_huge_mib'), default=None),
                psi_s={k: seconds(samples, 'host', 'psi', k) for k in ('cpu_some', 'mem_some', 'mem_full', 'io_some', 'io_full')})
    unit = dict(cpu_p50=pct(col(prod, 'unit', 'cpu'), 0.5), cpu_p95=pct(col(prod, 'unit', 'cpu'), 0.95),
                mem_mib_max=max(col(samples, 'unit', 'mem_mib'), default=None), swap_mib_max=max(col(samples, 'unit', 'swap_mib'), default=None),
                psi_s={k: seconds(samples, 'unit', 'psi', k) for k in ('cpu_some', 'mem_some', 'mem_full', 'io_some')},
                read_mib=seconds(samples, 'unit', 'read_mib_s'), write_mib=seconds(samples, 'unit', 'write_mib_s'))
    runs = []
    for s in samples:
        e = s.get('engine')
        if e and (not runs or runs[-1] != [e['pid'], e['start']]):
            runs.append([e['pid'], e['start']])
    maj = col(samples, 'engine', 'majflt')
    engine = dict(runs=len({tuple(r) for r in runs}), rss_mib_max=max(col(samples, 'engine', 'rss_mib'), default=None),
                  swap_mib_max=max(col(samples, 'engine', 'swap_mib'), default=None), swap_mib_last=(col(samples, 'engine', 'swap_mib') or [None])[-1],
                  majflt=sum(maj), majflt_max_per_sample=max(maj, default=None), cpu_p95=pct(col(prod, 'engine', 'cpu'), 0.95))
    docker = {}
    for s in samples:
        for cid, v in (s.get('docker') or {}).items():
            d = docker.setdefault(cid, dict(names={}, cpu=[], mem=[]))
            d['names'][v.get('name')] = d['names'].get(v.get('name'), 0) + 1
            d['cpu'] += [v['cpu']] if _num(v.get('cpu')) else []
            d['mem'] += [v['mem_mib']] if _num(v.get('mem_mib')) else []
    docker = {cid: dict(name=max(d['names'], key=d['names'].get), cpu_p50=pct(d['cpu'], 0.5), cpu_p95=pct(d['cpu'], 0.95),
                        cpu_max=max(d['cpu'], default=None), busy_minutes=sum(1 for x in d['cpu'] if x >= WARN['cotenant_busy']),
                        mem_mib_max=max(d['mem'], default=None)) for cid, d in docker.items()}
    reasons = {}
    for s in prod:
        bits = (s.get('gpu') or {}).get('reasons')
        if _num(bits):
            for bit, name in REASONS.items():
                if bits & bit:
                    reasons[name] = reasons.get(name, 0) + 1
    gpu = dict(temp_p95=pct(col(samples, 'gpu', 'temp'), 0.95), temp_max=max(col(samples, 'gpu', 'temp'), default=None),
               power_w_p95=pct(col(samples, 'gpu', 'power_w'), 0.95), power_w_max=max(col(samples, 'gpu', 'power_w'), default=None),
               util_p95=pct(col(samples, 'gpu', 'util'), 0.95), mem_used_mib_max=max(col(samples, 'gpu', 'mem_used_mib'), default=None),
               reason_minutes_prod=reasons)
    summary = prodlog.summarize(reqs) if prodlog else None
    md = metrics_deltas(seq)
    rep = dict(schema=SCHEMA, date=day, generated=iso(time.time()), monitor_sha256=sha256(Path(__file__)),
               coverage=dict(samples=len(samples), expected=expected, ratio=round(len(samples) / expected, 3), gaps=gaps[:24], modes=modes),
               requests=dict(attributed=len(reqs), metrics_totals=md, log=logs, summary=summary),
               host=host, unit=unit, engine=engine, docker=docker, gpu=gpu, hourly=hourly(samples, reqs),
               contention=contention(reqs, prodlog, WARN['cotenant_busy']) if prodlog else None)
    errs = {}
    for s in samples:
        for e in s.get('errors', []):
            errs[e.split(':', 1)[0]] = errs.get(e.split(':', 1)[0], 0) + 1
    rep['sample_errors'] = errs
    rep['warnings'] = warnings(rep, trailing_decode(data, day, WARN['trailing_days']))
    return rep


def warnings(rep, trailing):
    w, W = [], WARN
    c = rep['coverage']
    if c['ratio'] < W['coverage']:
        w.append('coverage %.2f < %.2f: %d of %d minutes sampled' % (c['ratio'], W['coverage'], c['samples'], c['expected']))
    h, g = rep['host'], rep['gpu']
    if _num(h['avail_mib_min']) and h['avail_mib_min'] < W['avail_mib']:
        w.append('MemAvailable min %d MiB < %d' % (h['avail_mib_min'], W['avail_mib']))
    if _num(h['swap_free_frac_min']) and h['swap_free_frac_min'] < W['swap_free_frac']:
        w.append('swap free min %.0f%% < %.0f%%' % (100 * h['swap_free_frac_min'], 100 * W['swap_free_frac']))
    if _num(g['temp_max']) and g['temp_max'] >= W['gpu_temp']:
        w.append('GPU temperature max %s >= %d' % (g['temp_max'], W['gpu_temp']))
    bad = {k: v for k, v in g['reason_minutes_prod'].items() if any(REASONS[b] == k for b in REASONS if b & REASONS_BAD)}
    if bad:
        w.append('GPU clock-event reasons in production minutes: %s' % bad)
    if rep['unit']['psi_s']['mem_full'] > W['unit_mem_full_s']:
        w.append('production unit memory full-stall %.1f s > %.1f s' % (rep['unit']['psi_s']['mem_full'], W['unit_mem_full_s']))
    if rep['engine']['runs'] > 1:
        w.append('engine ran as %d processes (restarted)' % rep['engine']['runs'])
    lg = rep['requests']['log']
    if lg.get('switches') or lg.get('shrinks') or lg.get('unavailable'):
        w.append('engine log: %s' % lg)
    md, n = rep['requests']['metrics_totals'].get('requests', 0), rep['requests']['attributed']
    if md - n > 2:                             # the log can hold more (the server's thinking-budget continuations), not fewer
        w.append('requests: %d dated from the log, %d counted by /metrics' % (n, md))
    for b, v in (((rep['requests'].get('summary') or {}).get('by_prompt_bucket')) or {}).items():
        ref = trailing.get(b)
        if _num(ref) and _num(v.get('decode_tok_s')) and v['requests'] >= W['decode_min_requests'] and v['decode_tok_s'] < W['decode_drop'] * ref:
            w.append('decode %s median %.1f tok/s < %.2f x trailing %.1f (%d requests)' % (b, v['decode_tok_s'], W['decode_drop'], ref, v['requests']))
    if rep['sample_errors']:
        w.append('sample errors: %s' % rep['sample_errors'])
    return w


def sha256(p):
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build_day(data, day, prodlog):
    import gzip
    data = Path(data)
    samples = load_samples(data, day)
    prev = load_samples(data, (dt.date.fromisoformat(day) - dt.timedelta(days=1)).isoformat())[-1:]
    seq = prev + samples
    ivs, switches, shrinks = intervals(seq)
    by_key, reqs, unavailable = {}, [], []
    for k, lo, hi, t_lo, t_hi in ivs:
        by_key.setdefault(k, []).append((lo, hi, t_lo, t_hi))
    for (path, ino), rs in by_key.items():
        got = log_requests(path, ino, rs, prodlog) if prodlog else None
        if got is None:
            unavailable.append(path)
        else:
            reqs += got
    reqs.sort(key=lambda r: r['_hi'])          # stable: log order within a sample interval
    for r in reqs:
        r['ctx'] = context(r, seq)
    rep = build_report(data, day, samples, seq, reqs, prodlog,
                       dict(switches=switches, shrinks=shrinks, unavailable=unavailable, files=sorted({k[0] for k in by_key})))
    rows = []
    for r in reqs:
        lo, hi = r.pop('_lo'), r.pop('_hi')
        rows.append(json.dumps(dict(t=iso(hi), t_after=iso(lo), ts=round(hi, 1), **r), separators=(',', ':')))
    write_atomic(data / 'requests' / (day + '.jsonl.gz'), gzip.compress(('\n'.join(rows) + '\n' if rows else '').encode(), 6))
    write_atomic(data / 'reports' / (day + '.json'), (json.dumps(rep, indent=1) + '\n').encode())
    return rep


def gzip_raw(data, today):
    """Gzip the raw samples of every finished day (the report is built first; a day that failed keeps raw 2 days)."""
    import gzip
    import shutil
    done = []
    t = dt.date.fromisoformat(today)
    for p in sorted((Path(data) / 'samples').glob('*.jsonl')):
        d = file_day(p.name)
        if d is None or d >= t:
            continue
        if not (Path(data) / 'reports' / (p.name[:10] + '.json')).exists() and (t - d).days < 3:
            continue
        gz = p.with_name(p.name + '.gz')
        tmp = gz.with_name(gz.name + '.tmp')
        with open(p, 'rb') as src, gzip.open(tmp, 'wb', 6) as dst:
            shutil.copyfileobj(src, dst)
        os.replace(tmp, gz)
        p.unlink()
        done.append(gz.name)
    return done


def cmd_daily(data, date=None, force=False, now=None):
    data = Path(data)
    for sub in ('samples', 'requests', 'reports'):
        (data / sub).mkdir(parents=True, exist_ok=True)
    now = time.time() if now is None else now
    today = local_date(now)
    with locked(data / '.daily.lock', block=True):
        if date:
            if date >= today:
                raise SystemExit('daily: %s is not finished yet (today is %s)' % (date, today))
            days = [date]
        else:
            days = sorted({p.name[:10] for p in (data / 'samples').iterdir() if file_day(p.name)} - {today})
            days = [d for d in days if d < today and (force or not (data / 'reports' / (d + '.json')).exists())]
        prodlog = load_prodlog()
        for d in days:
            try:
                rep = build_day(data, d, prodlog)
                print(iso(now), 'daily %s: %d requests, coverage %.2f, warnings: %s' % (d, rep['requests']['attributed'], rep['coverage']['ratio'], rep['warnings'] or 'none'))
            except Exception as e:             # keep the day from being retried forever; --force rebuilds it
                write_atomic(data / 'reports' / (d + '.json'), (json.dumps(dict(schema=SCHEMA, date=d, error='%s: %s' % (type(e).__name__, e)), indent=1) + '\n').encode())
                print(iso(now), 'daily %s failed: %s: %s' % (d, type(e).__name__, e))
        gz = gzip_raw(data, today)
        pr = prune(data, today)
        if gz or pr['removed']:
            print(iso(now), 'daily: gzipped %s; pruned %s; data %.1f MiB' % (gz, pr['removed'], pr['bytes'] / 1048576))
    return 0


# ---------------------------------------------------------------- retention
def file_day(name):
    try:
        return dt.date.fromisoformat(name[:10])
    except ValueError:
        return None


def du(data):
    total = 0
    for dp, _, fs in os.walk(data):
        for f in fs:
            try:
                total += os.lstat(os.path.join(dp, f)).st_size
            except OSError:
                pass
    return total


def prune(data, today, dry=False, cap=None):
    """Delete files past KEEP_DAYS (by the date in their name); then, while the directory is over the cap, the oldest
    samples, requests and reports in that order, down to 90% of it.  Today's and yesterday's raw samples always stay."""
    data, t = Path(data), dt.date.fromisoformat(today)
    cap = CAP_BYTES if cap is None else cap
    files, removed = [], []
    for cat in KEEP_DAYS:
        for p in sorted((data / cat).glob('*')) if (data / cat).is_dir() else []:
            d = file_day(p.name)
            if d is not None:
                files.append((cat, d, p))
    keep = []
    for cat, d, p in files:
        (removed if (t - d).days > KEEP_DAYS[cat] else keep).append((cat, d, p))
    size = {p: p.stat().st_size for _, _, p in files}
    total = du(data) - sum(size[p] for _, _, p in removed)
    if total > cap:
        order = {c: i for i, c in enumerate(KEEP_DAYS)}
        for cat, d, p in sorted(keep, key=lambda x: (order[x[0]], x[1], x[2].name)):
            if total <= 0.9 * cap:
                break
            if cat == 'samples' and (t - d).days <= 1:
                continue
            removed.append((cat, d, p))
            total -= size[p]
    if not dry:
        for _, _, p in removed:
            with contextlib.suppress(FileNotFoundError):
                p.unlink()
    return dict(removed=[p.name for _, _, p in removed], bytes=total)


# ---------------------------------------------------------------- status and cron
def last_line(p):
    try:
        with open(p, 'rb') as f:
            f.seek(max(0, f.seek(0, 2) - 65536))
            tail = f.read().splitlines()
        return json.loads(tail[-1]) if tail else None
    except (OSError, ValueError):
        return None


def cron_lines(script, data, default_data):
    log = shlex.quote(str(Path(data) / 'monitor.log'))
    py = '/usr/bin/nice -n 10 /usr/bin/python3 -I -B %s%s' % (shlex.quote(str(script)), '' if default_data else ' --data ' + shlex.quote(str(data)))
    lines = [BEGIN + ' (strata_monitor.py cron install/remove manages this block)',
             '* * * * * f=%s; [ -f "$f" ] && [ "$(wc -c < "$f")" -gt %d ] && mv -f "$f" "$f.1"; %s sample >> "$f" 2>&1' % (log, LOG_CAP, py),
             '17 0 * * * f=%s; %s daily >> "$f" 2>&1' % (log, py),
             END]
    if any('%' in x for x in lines):           # cron turns % into a newline
        raise SystemExit('cron: a path contains %%: %s' % lines)
    return lines


def cron(action, data, default_data):
    r = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
    lines = r.stdout.splitlines() if r.returncode == 0 else []
    kept, inside, block = [], False, []
    for x in lines:
        if x.startswith(BEGIN):
            inside = True
        if inside:
            block.append(x)
        else:
            kept.append(x)
        if inside and x.startswith(END):
            inside = False
    if action == 'show':
        print('\n'.join(block) if block else '(no strata_monitor block in the crontab)')
        return 0
    new = kept + (cron_lines(Path(__file__).resolve(), data, default_data) if action == 'install' else [])
    subprocess.run(['crontab', '-'], input='\n'.join(new) + '\n' if new else '', text=True, check=True)
    print('crontab %s:' % ('installed' if action == 'install' else 'block removed'))
    print('\n'.join(new) if new else '(empty)')
    return 0


def cmd_status(data):
    data = Path(data)
    raws = sorted((data / 'samples').glob('*.jsonl')) if (data / 'samples').is_dir() else []
    last = last_line(raws[-1]) if raws else None
    reps = sorted((data / 'reports').glob('*.json')) if (data / 'reports').is_dir() else []
    rep = load_json(reps[-1]) if reps else None
    try:
        r = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        cron_ok = r.returncode == 0 and BEGIN in r.stdout
    except OSError:
        cron_ok = None
    out = dict(now=iso(time.time()), data=str(data),
               last_sample=last and dict(t=last.get('t'), age_s=round(time.time() - last['ts']), mode=last.get('mode'), lab=last.get('lab'),
                                         host=last.get('host'), engine=last.get('engine'), gpu=last.get('gpu'),
                                         metrics=last.get('metrics'), log=last.get('log'), errors=last.get('errors')),
               disk=dict(bytes=du(data) if data.is_dir() else 0, cap=CAP_BYTES, day_raw_cap=DAY_RAW_CAP,
                         files={c: len(list((data / c).glob('*'))) if (data / c).is_dir() else 0 for c in KEEP_DAYS}),
               keep_days=KEEP_DAYS, cron_installed=cron_ok,
               last_report=rep and dict(date=rep.get('date'), error=rep.get('error'), requests=(rep.get('requests') or {}).get('attributed'),
                                        coverage=(rep.get('coverage') or {}).get('ratio'), warnings=rep.get('warnings')))
    print(json.dumps(out, indent=1))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data', help='data directory (default: data/ beside this script)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('sample')
    d = sub.add_parser('daily')
    d.add_argument('--date')
    d.add_argument('--force', action='store_true')
    p = sub.add_parser('prune')
    p.add_argument('--dry-run', action='store_true')
    sub.add_parser('status')
    c = sub.add_parser('cron')
    c.add_argument('action', choices=('show', 'install', 'remove'))
    a = ap.parse_args(argv)
    data = Path(a.data).resolve() if a.data else HERE / 'data'
    os.umask(0o022)
    if a.cmd == 'sample':
        return cmd_sample(data)
    if a.cmd == 'daily':
        return cmd_daily(data, a.date, a.force)
    if a.cmd == 'prune':
        print(json.dumps(prune(data, local_date(time.time()), a.dry_run), indent=1))
        return 0
    if a.cmd == 'status':
        return cmd_status(data)
    if a.cmd == 'cron':
        if a.action == 'install':
            for s in ('samples', 'requests', 'reports'):
                (data / s).mkdir(parents=True, exist_ok=True)
        return cron(a.action, data, a.data is None)
    return 2


if __name__ == '__main__':
    sys.exit(main())
