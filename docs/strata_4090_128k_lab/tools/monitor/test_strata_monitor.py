import gzip
import importlib.util
import json
import shutil
import tempfile
import time
import unittest
import datetime as dt
from pathlib import Path

MODULE = Path(__file__).resolve().parent / 'strata_monitor.py'
UNIT = 'openclaw-qwen38-next.service'
CID = 'ab' * 32
TIMING = ('strata decode timing: 40 windows, avg T 2.67, 2.02 tokens/window, 27.18 ms/window = adapt wait 0.05 + verify 25.37 '
          '(GPU-reach wait 7.32 + per-layer host 17.37 [plan 0.28 actq 0.30 jobs 0.10 CPU 16.54] + stage 0.11) + commit/emit 0.04 + '
          'draft 1.54 + adapt join 0.18 + other 0.00; per layer-window: CPU experts 3.42 (4.71 entries), VRAM hits 20.10, PCIe 0.20; 9.0 swaps/window')
HIT = 'strata serve: decode expert cache hit rate: 80.9% (38225 hits / 47274 lookups); 115 more read by the GPU over PCIe'


def summary(prompt, gen=100, dms=1000, cancelled=False):
    return ('strata serve: prompt %d tokens = 0 reused + %d read in 500 ms (100.0 tok/s), %d generated in %d ms (100.0 tok/s), '
            'drafts accepted 50 of 80, 1 checkpoints%s' % (prompt, prompt, gen, dms, ' (cancelled)' if cancelled else ''))


def w(p, text):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def at(y, mo, d, h, mi, s=0):
    return time.mktime((y, mo, d, h, mi, s, 0, 0, -1))


class Fake:
    """/proc and cgroup files of a host running the production unit (server + engine) and one docker co-tenant."""

    def __init__(self, tmp):
        self.root, self.log, self.cfg = Path(tmp) / 'root', Path(tmp) / 'engine.log', Path(tmp) / 'run.json'
        w(self.cfg, json.dumps(dict(log=str(self.log), port=18343, host='127.0.0.1', gpu=0)))
        w(self.log, '[strata] 2026-11-20 06:45:02 engine started: /x/engine/strata --serve\n')
        self.t = dict(cpu=[1000, 0, 500, 100000, 100], unit=10_000_000, engine=(100, 50), majflt=10, docker=5_000_000,
                      psi=1000, unit_psi=2000, io=(0, 0), avail_kb=8_000_000)
        self.on = True
        self.write()

    def append(self, *lines):
        with open(self.log, 'a') as f:
            f.write(''.join(x + '\n' for x in lines))

    def write(self):
        t, r = self.t, self.root
        w(r / 'proc/stat', 'cpu  %d %d %d %d %d 0 0 0 0 0\ncpu0 1 1 1 1 1 0 0 0 0 0\ncpu1 1 1 1 1 1 0 0 0 0 0\nintr 0\n' % tuple(t['cpu']))
        w(r / 'proc/meminfo', 'MemTotal: 65000000 kB\nMemAvailable: %d kB\nSwapTotal: 1048576 kB\nSwapFree: 262144 kB\n'
                              'AnonHugePages: 38000000 kB\n' % t['avail_kb'])
        w(r / 'proc/loadavg', '0.50 0.40 0.30 1/100 123\n')
        for res in ('cpu', 'memory', 'io'):
            w(r / 'proc/pressure' / res, 'some avg10=0.00 avg60=0.00 avg300=0.00 total=%d\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=%d\n'
              % (t['psi'], t['psi'] // 2))
        u = r / 'sys/fs/cgroup/system.slice' / UNIT
        w(u / 'cgroup.procs', '100\n101\n' if self.on else '')
        w(u / 'cpu.stat', 'usage_usec %d\nuser_usec 1\nsystem_usec 1\n' % t['unit'])
        w(u / 'memory.current', '%d\n' % (50 << 30))
        w(u / 'memory.swap.current', '%d\n' % (600 << 20))
        for res in ('cpu', 'memory', 'io'):
            w(u / ('%s.pressure' % res), 'some avg10=0.00 avg60=0.00 avg300=0.00 total=%d\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=%d\n'
              % (t['unit_psi'], t['unit_psi']))
        w(u / 'io.stat', '259:0 rbytes=%d wbytes=%d rios=1 wios=1 dbytes=0 dios=0\n' % t['io'])
        if self.on:
            w(r / 'proc/100/cmdline', '\0'.join(['/t/python/bin/python3.12', '-B', '/t/terminal/serve/server.py', '--engine', 'strata',
                                                 '--config', str(self.cfg), '--port', '18343']) + '\0')
            w(r / 'proc/101/cmdline', '/t/engine/strata\0--serve\0--pack\0/p\0')
            f = ['S', '100', '101', '101', '0', '-1', '4194560', '1000', '0', str(t['majflt']), '0', str(t['engine'][0]), str(t['engine'][1]),
                 '0', '0', '20', '0', '45', '0', '777'] + ['0'] * 32
            w(r / 'proc/101/stat', '101 (strata host) ' + ' '.join(f) + '\n')
            w(r / 'proc/101/status', 'Name:\tstrata-host\nVmRSS:\t 2097152 kB\nRssAnon:\t1048576 kB\nVmSwap:\t  10240 kB\nThreads:\t45\n')
        else:
            for p in ('100', '101'):
                shutil.rmtree(r / 'proc' / p, ignore_errors=True)
        d = r / 'sys/fs/cgroup/system.slice' / ('docker-%s.scope' % CID)
        w(d / 'cgroup.procs', '200\n')
        w(d / 'cpu.stat', 'usage_usec %d\n' % t['docker'])
        w(d / 'memory.current', '%d\n' % (3 << 30))
        w(r / 'proc/200/comm', 'gunicorn\n')
        w(r / 'proc/200/cmdline', 'gunicorn\0--workers=4\0')

    def tick(self, seconds=60, docker_cores=1.0):
        """One interval: 2 CPUs, 0.8 cores busy and 0.2 in iowait; unit and engine 0.5 cores; 7 major faults."""
        n = int(100 * seconds)                 # 100 ticks/s per CPU, 2 CPUs
        c = self.t['cpu']
        c[0] += int(0.8 * n)
        c[3] += int(1.0 * n)
        c[4] += int(0.2 * n)
        self.t['unit'] += int(0.5 * seconds * 1e6)
        u, s = self.t['engine']
        self.t['engine'] = (u + int(0.5 * seconds * 100), s)
        self.t['majflt'] += 7
        self.t['docker'] += int(docker_cores * seconds * 1e6)
        self.t['psi'] += int(0.1 * seconds * 1e6)
        self.t['unit_psi'] += int(0.01 * seconds * 1e6)
        self.t['io'] = (self.t['io'][0] + int(seconds * 1048576), self.t['io'][1])
        self.write()


class Stub:
    def __init__(self, reasons=0x4, fail=False):
        self.gpu_calls, self.metrics_calls, self.reasons, self.fail, self.requests = [], [], reasons, fail, 0

    def gpu(self, index=0):
        self.gpu_calls.append(index)
        if self.fail:
            raise RuntimeError('nvidia-smi rc=9')
        return dict(temp=40, util=10, power_w=50.0, reasons=self.reasons, mem_used_mib=23000)

    def metrics(self, host, port):
        self.metrics_calls.append((host, port))
        return dict(state='idle', queued=0, totals=dict(since=1.0, requests=self.requests), conv={}, requests_kept=0)


class Monitor(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('strata_monitor', MODULE)
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)
        self.tmp = tempfile.mkdtemp()
        self.data = Path(self.tmp) / 'data'
        self.f = Fake(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sample(self, ts, stub):
        self.m.cmd_sample(self.data, self.f.root, ts, stub.gpu, stub.metrics)
        return self.m.load_samples(self.data, self.m.local_date(ts))[-1]

    def test_rates_appear_from_the_second_sample(self):
        st, t0 = Stub(), at(2026, 11, 20, 12, 0)
        s0 = self.sample(t0, st)
        self.assertEqual((s0['mode'], s0['dt'], s0['host']['cpu'], s0['engine']['pid']), ('prod', None, None, 101))
        self.assertEqual(s0['log'], dict(path=str(self.f.log), ino=self.f.log.stat().st_ino, size=self.f.log.stat().st_size, live=True))
        self.assertEqual((s0['host']['avail_mib'], s0['host']['swap_used_mib'], s0['engine']['swap_mib']), (7812, 768, 10))
        self.f.tick()
        s1 = self.sample(t0 + 60, st)
        self.assertEqual(s1['dt'], 60)
        self.assertEqual((s1['host']['cpu'], s1['host']['iowait']), (0.8, 0.2))
        self.assertEqual((s1['unit']['cpu'], s1['engine']['cpu'], s1['engine']['majflt']), (0.5, 0.5, 7))
        self.assertEqual(s1['docker'][CID[:12]], dict(name='gunicorn', cpu=1.0, mem_mib=3072))
        self.assertEqual((s1['host']['psi']['mem_some'], s1['host']['psi']['mem_full'], s1['unit']['psi']['mem_full']), (0.1, 0.05, 0.01))
        self.assertEqual(s1['unit']['read_mib_s'], 1.0)
        self.assertEqual((len(st.gpu_calls), st.metrics_calls[-1]), (2, ('127.0.0.1', 18343)))
        self.assertNotIn('errors', s1)

    def test_lab_run_skips_gpu_and_metrics(self):
        w(self.f.root / 'proc/300/cmdline', 'python3\0-B\0/d/upgrade_gate.py\0kl\0')
        w(self.f.root / 'proc/400/cmdline', '/y/engine/strata\0--serve\0')
        w(self.f.root / 'proc/500/cmdline', 'rg\0upgrade_gate.py\0')               # not a lab run
        st = Stub()
        s = self.sample(at(2026, 11, 20, 12, 0), st)
        self.assertEqual((s['mode'], s['lab'], s['gpu'], s['metrics']), ('lab', ['engine:400', 'upgrade_gate.py'], None, None))
        self.assertEqual((st.gpu_calls, st.metrics_calls), ([], []))
        self.assertEqual(s['engine']['pid'], 101)                                    # production figures still recorded

    def test_down_keeps_the_log_offset(self):
        st, t0 = Stub(), at(2026, 11, 20, 12, 0)
        self.sample(t0, st)
        self.f.on = False
        self.f.write()
        self.f.append('[strata] 2026-11-20 12:01:00 engine started: /x/engine/strata --serve')
        s = self.sample(t0 + 60, st)
        self.assertEqual((s['mode'], s['unit'], s['engine'], s['metrics']), ('down', None, None, None))
        self.assertEqual((s['log']['size'], s['log']['live']), (self.f.log.stat().st_size, False))
        self.assertEqual(len(st.metrics_calls), 1)

    def test_a_failing_source_is_recorded(self):
        s = self.sample(at(2026, 11, 20, 12, 0), Stub(fail=True))
        self.assertIsNone(s['gpu'])
        self.assertTrue(s['errors'][0].startswith('gpu: RuntimeError'))
        self.assertEqual(json.loads((self.data / 'state.json').read_text())['errors'], ['gpu'])
        self.assertEqual(s['engine']['pid'], 101)

    def test_day_raw_cap(self):
        self.m.DAY_RAW_CAP = 10
        t0 = at(2026, 11, 20, 12, 0)
        self.sample(t0, Stub())
        self.m.cmd_sample(self.data, self.f.root, t0 + 60, Stub().gpu, Stub().metrics)
        self.assertEqual(len(self.m.load_samples(self.data, '2026-11-20')), 1)
        self.assertEqual(json.loads((self.data / 'state.json').read_text())['ts'], t0 + 60)

    def test_daily_dates_requests_by_sample_interval(self):
        st = Stub()
        t_prev = at(2026, 11, 19, 23, 59, 30)
        self.sample(t_prev, st)
        ts = [at(2026, 11, 20, 0, m, 30) for m in range(3)]
        lines = [(TIMING, summary(40000), HIT), (summary(500, gen=80),), (summary(20000, gen=0, dms=0, cancelled=True),)]
        for t, ls in zip(ts, lines):
            self.f.append(*ls)
            self.f.tick()
            st.requests += 1
            self.sample(t, st)
        self.m.cmd_daily(self.data, now=at(2026, 11, 21, 0, 17))
        rows = [json.loads(x) for x in gzip.open(self.data / 'requests/2026-11-20.jsonl.gz', 'rt')]
        self.assertEqual([r['prompt'] for r in rows], [40000, 500, 20000])
        self.assertEqual([r['ts'] for r in rows], [round(t, 1) for t in ts])
        self.assertEqual(rows[0]['t_after'], self.m.iso(t_prev))                     # the bridge from the day before
        self.assertEqual((len(rows[0]['timing']), rows[0]['hit_rate'], rows[2]['cancelled']), (1, 80.9, True))
        # request B (1.5 s) ran in (00:00:28.5, 00:01:30]: the 00:01:30 sample, and 1.5 s of the 00:00:30 one
        self.assertEqual((rows[1]['ctx']['samples'], rows[1]['ctx']['cotenant_cpu_mean'], rows[1]['ctx']['engine_majflt']), (2, 1.0, 14))
        rep = json.loads((self.data / 'reports/2026-11-20.json').read_text())
        self.assertEqual((rep['requests']['attributed'], rep['coverage']['samples'], rep['coverage']['expected']), (3, 3, 1440))
        self.assertEqual(rep['requests']['metrics_totals']['requests'], 3)
        self.assertEqual(rep['requests']['summary']['requests'], 3)
        self.assertTrue(any(x.startswith('coverage') for x in rep['warnings']))
        self.assertEqual(rep['docker'][CID[:12]]['busy_minutes'], 3)
        self.assertEqual(json.loads((self.data / 'reports/2026-11-19.json').read_text())['requests']['attributed'], 0)
        names = sorted(p.name for p in (self.data / 'samples').iterdir())
        self.assertEqual(names, ['2026-11-19.jsonl.gz', '2026-11-20.jsonl.gz'])
        before = (self.data / 'reports/2026-11-20.json').stat().st_mtime_ns
        self.m.cmd_daily(self.data, now=at(2026, 11, 21, 0, 18))                     # idempotent
        self.assertEqual((self.data / 'reports/2026-11-20.json').stat().st_mtime_ns, before)
        with self.assertRaises(SystemExit):
            self.m.cmd_daily(self.data, date='2026-11-21', now=at(2026, 11, 21, 0, 18))

    def test_warnings_from_samples(self):
        self.f.t['avail_kb'] = 2_000_000
        self.f.write()
        st = Stub(reasons=0x40 | 0x1)
        t0 = at(2026, 11, 20, 12, 0)
        self.sample(t0, st)
        self.f.tick()
        self.sample(t0 + 60, st)
        self.m.cmd_daily(self.data, now=at(2026, 11, 21, 1, 0))
        rep = json.loads((self.data / 'reports/2026-11-20.json').read_text())
        self.assertEqual(rep['gpu']['reason_minutes_prod'], {'idle': 2, 'hw_thermal': 2})
        txt = ' | '.join(rep['warnings'])
        self.assertIn('MemAvailable min 1953 MiB < 3072', txt)
        self.assertIn("'hw_thermal': 2", txt)
        self.assertNotIn('idle', txt.split('production minutes:')[1].split('|')[0])

    def test_decode_drop_against_trailing_reports(self):
        rep = dict(coverage=dict(ratio=1.0, samples=1440, expected=1440), host=dict(avail_mib_min=9000, swap_free_frac_min=0.5),
                   gpu=dict(temp_max=60, reason_minutes_prod={}), unit=dict(psi_s=dict(mem_full=0.0)), engine=dict(runs=1),
                   requests=dict(log={}, metrics_totals=dict(requests=12), attributed=12,
                                 summary=dict(by_prompt_bucket={'>=64K': dict(decode_tok_s=50.0, requests=12)})), sample_errors={})
        self.assertEqual(self.m.warnings(rep, {'>=64K': 100.0}), ['decode >=64K median 50.0 tok/s < 0.85 x trailing 100.0 (12 requests)'])
        self.assertEqual(self.m.warnings(rep, {'>=64K': 55.0}), [])
        rep['requests']['metrics_totals']['requests'] = 20
        self.assertEqual(self.m.warnings(rep, {}), ['requests: 12 dated from the log, 20 counted by /metrics'])

    def test_intervals_bridge_gaps_and_stop_at_switches(self):
        L = lambda p, i, n: dict(path=p, ino=i, size=n)
        seq = [dict(ts=1, log=L('a', 1, 10)), dict(ts=2, log=L('a', 1, 30)), dict(ts=3, log=None), dict(ts=4, log=L('a', 1, 50)),
               dict(ts=5, log=L('b', 2, 5)), dict(ts=6, log=L('b', 2, 9)), dict(ts=7, log=L('b', 2, 3)), dict(ts=8, log=L('b', 2, 3))]
        ivs, sw, sh = self.m.intervals(seq)
        self.assertEqual([(k[0], lo, hi, a, b) for k, lo, hi, a, b in ivs], [('a', 10, 30, 1, 2), ('a', 30, 50, 2, 4), ('b', 5, 9, 5, 6)])
        self.assertEqual((sw, sh), (1, 1))

    def test_prune_by_age_then_cap(self):
        today = dt.date(2026, 11, 20)
        day = lambda n: (today - dt.timedelta(days=n)).isoformat()
        for cat, n, ext in (('samples', 31, '.jsonl.gz'), ('samples', 30, '.jsonl.gz'), ('requests', 181, '.jsonl.gz'),
                            ('requests', 180, '.jsonl.gz'), ('reports', 181, '.json'), ('reports', 2, '.json')):
            w(self.data / cat / (day(n) + ext), 'x')
        w(self.data / 'state.json', '{}')
        r = self.m.prune(self.data, today.isoformat())
        self.assertEqual(sorted(r['removed']), sorted([day(31) + '.jsonl.gz', day(181) + '.jsonl.gz', day(181) + '.json']))
        self.assertTrue((self.data / 'samples' / (day(30) + '.jsonl.gz')).exists())
        for n, ext in ((5, '.jsonl.gz'), (4, '.jsonl.gz'), (1, '.jsonl'), (0, '.jsonl')):
            w(self.data / 'samples' / (day(n) + ext), 'y' * 600)
        dry = self.m.prune(self.data, today.isoformat(), dry=True, cap=1000)
        self.assertTrue((self.data / 'samples' / (day(30) + '.jsonl.gz')).exists())
        r = self.m.prune(self.data, today.isoformat(), cap=1000)
        self.assertEqual(r['removed'], dry['removed'])
        self.assertEqual(r['removed'][:3], [day(30) + '.jsonl.gz', day(5) + '.jsonl.gz', day(4) + '.jsonl.gz'])
        self.assertTrue((self.data / 'samples' / (day(1) + '.jsonl')).exists() and (self.data / 'samples' / (day(0) + '.jsonl')).exists())

    def test_cron_lines(self):
        lines = self.m.cron_lines(Path('/d/monitor/strata_monitor.py'), Path('/d/monitor/data'), True)
        self.assertEqual((lines[0].split(' (')[0], lines[-1]), (self.m.BEGIN, self.m.END))
        self.assertTrue(lines[1].startswith('* * * * * ') and ' sample >> "$f" 2>&1' in lines[1] and '-gt 1048576' in lines[1])
        self.assertTrue(lines[2].startswith('17 0 * * * ') and lines[2].endswith(' daily >> "$f" 2>&1'))
        self.assertFalse(any('%' in x or '--data' in x for x in lines))
        self.assertIn('--data /x', self.m.cron_lines(Path('/d/s.py'), Path('/x'), False)[1])

    def test_parsers(self):
        g = self.m.parse_gpu('37, 0, 0, 23428, 11.15, 210, 405, 1, 16, 0x0000000000000001, [N/A]')
        self.assertEqual((g['temp'], g['power_w'], g['reasons'], g['fan'], g['pcie_width']), (37, 11.15, 1, None, 16))
        self.assertEqual(self.m.psi('some avg10=0.00 avg60=0.00 avg300=0.00 total=538172\nfull avg10=0.00 total=537850\n'),
                         {'some': 538172, 'full': 537850})
        self.assertEqual(self.m.io_stat('259:0 rbytes=10 wbytes=20 rios=1\n8:0 rbytes=1 wbytes=2\n'), dict(r=11, w=22))
        self.assertEqual(self.m.pid_stat('7 (a) b) S ' + ' '.join(str(i) for i in range(4, 60)))['majflt'], 12)
        d = dict(live=dict(state='busy', queued=1, phase='decode'), totals=dict(since=5.0, requests=3, extra=1),
                 conversation_cache=dict(parked=1, evictions=2), requests_kept=3, requests=[{'x': 1}])
        s = self.m.metrics_subset(d)
        self.assertEqual((s['state'], s['totals']['requests'], s['totals']['decode_ms'], s['conv']['evictions']), ('busy', 3, None, 2))
        self.assertNotIn('extra', s['totals'])


if __name__ == '__main__':
    unittest.main()
