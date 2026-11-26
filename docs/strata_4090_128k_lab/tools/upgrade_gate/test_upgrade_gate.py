"""CPU-only checks of upgrade_gate.py's arm helpers (--arg, the config stand-in, per-window figures, the long-context
replay and its verdicts, sampling defaults, the approximate-routing screen and verdict); no GPU, no 4090 paths.

    python3 -B -m unittest test_upgrade_gate      (from this directory)
"""
import gzip, json, tempfile, time, unittest
from pathlib import Path

import upgrade_gate as ug

# two requests as a v0.2.17 serve engine prints them (b2 arm log, trimmed): the first stops at the 4096-token thinking
# budget and the server continues it in a second engine request; then a second attempt, and one after a restart
LOG = """strata engine started: x
strata decode timing: 2048 windows, avg T 2.49, 2.00 tokens/window, 14.84 ms/window = adapt wait 0.06 + verify 13.48 (GPU-reach wait 8.11 + per-layer host 4.73 [plan 0.17 actq 0.15 jobs 0.04 CPU 4.19] + stage 0.02) + commit/emit 0.02 + draft 1.12 + adapt join 0.15 + other 0.00; per layer-window: CPU experts 1.13 (1.38 entries), VRAM hits 22.21, PCIe 0.14; 15.7 swaps/window
strata decode adapt overlap: 511 windows took swaps still landing, a layer waited 298.16 ms in all so far
strata serve: prompt 1241 tokens = 0 reused + 1241 read in 1644 ms (754.9 tok/s), 4096 generated in 30383 ms (134.8 tok/s), drafts accepted 2048 of 3048, 1 checkpoints
strata decode timing: 99 windows, avg T 3.84, 3.41 tokens/window, 26.02 ms/window = adapt wait 0.05 + verify 24.13 (GPU-reach wait 8.26 + per-layer host 15.23 [plan 0.33 actq 0.36 jobs 0.11 CPU 14.39] + stage 0.02) + commit/emit 0.03 + draft 1.58 + adapt join 0.22 + other 0.00; per layer-window: CPU experts 3.92 (5.12 entries), VRAM hits 28.93, PCIe 1.02; 23.3 swaps/window
strata decode adapt overlap: 535 windows took swaps still landing, a layer waited 300.00 ms in all so far
strata serve: prompt 5355 tokens = 5336 reused + 19 read in 122 ms (156.4 tok/s), 338 generated in 2576 ms (131.2 tok/s), drafts accepted 239 of 281, 1 checkpoints
strata decode timing: 1229 windows, avg T 2.55, 2.06 tokens/window, 15.87 ms/window = adapt wait 0.05 + verify 14.49 (GPU-reach wait 8.04 + per-layer host 5.82 [plan 0.18 actq 0.16 jobs 0.04 CPU 5.26] + stage 0.02) + commit/emit 0.02 + draft 1.13 + adapt join 0.17 + other 0.00; per layer-window: CPU experts 1.44 (1.82 entries), VRAM hits 22.04, PCIe 0.25; 16.3 swaps/window
strata serve: prompt 2153 tokens = 1236 reused + 917 read in 1050 ms (873.1 tok/s), 2535 generated in 19500 ms (130.0 tok/s), drafts accepted 1000 of 1500, 1 checkpoints
strata engine started: y
strata decode adapt overlap: 10 windows took swaps still landing, a layer waited 5.00 ms in all so far
strata serve: prompt 40000 tokens = 0 reused + 40000 read in 9000 ms (4444.4 tok/s), 10 generated in 100 ms (100.0 tok/s), drafts accepted 0 of 0, 1 checkpoints
"""
ROWS = [dict(task_id='ex:a', attempts=[dict(completion_tokens=4452), dict(completion_tokens=2535)]),
        dict(task_id='ex:b', attempts=[dict(completion_tokens=10)])]


class ArgSpecs(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(ug.parse_arg_specs(['adapt-every=2', '--adapt-decay=0.92', 'no-hit-poke']),
                         [('--adapt-every', '2'), ('--adapt-decay', '0.92'), ('--no-hit-poke', None)])
        for bad in (['expert-profile-save=/tmp/x'], ['port=1'], ['Bad_Flag=1'], ['adapt-every=']):
            with self.assertRaises(ug.Stop): ug.parse_arg_specs(bad)
        with self.assertRaises(ug.Stop): ug.parse_arg_specs(['expert-profile=/no/such/file.bin'])

    def test_apply_replaces_or_appends(self):
        a = ['--expert-profile', '/p/a.bin', '--spec', '4', '--kv-grow']
        b = ug.apply_arg_specs(a, [('--expert-profile', '/p/b.bin'), ('--adapt-every', '2'), ('--no-hit-poke', None)])
        self.assertEqual(b, ['--expert-profile', '/p/b.bin', '--spec', '4', '--kv-grow', '--adapt-every', '2', '--no-hit-poke'])
        self.assertEqual(a[1], '/p/a.bin')                                   # a copy, the config is not touched
        with self.assertRaises(ug.Stop): ug.apply_arg_specs(a, [('--spec', None)])          # already there
        with self.assertRaises(ug.Stop): ug.apply_arg_specs(a, [('--kv-grow', '1')])        # bare flag given a value

    def test_arm_suffix(self):
        self.assertEqual(ug.arm_suffix({'STRATA_VERIFY_DEVICE_HITS': '0', 'STRATA_ADAPT_LAG': '1'}, []), '-adapt_lag1-verify_device_hits0')
        self.assertEqual(ug.arm_suffix({}, [('--adapt-decay', '0.92'), ('--expert-profile', '/d/expert-profile-learned-20261121.bin')]),
                         '-adaptdecay092-expertprofileexpertprofilelearned20261121')

    def test_arm_tree(self):
        t = ug._ArmTree('/home/x/tree'); t.config = Path('/w/configs/arm.json')
        self.assertEqual(str(t), '/home/x/tree')
        self.assertEqual('cd "%s"' % t, 'cd "/home/x/tree"')
        self.assertEqual(t / 'strata-iq3_xxs.json', Path('/w/configs/arm.json'))
        self.assertEqual(t / 'python', Path('/home/x/tree/python'))
        self.assertEqual(ug._ArmTree('/home/x/tree') / 'strata-iq3_xxs.json', Path('/home/x/tree/strata-iq3_xxs.json'))


class PerWindow(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.log = Path(self.d.name) / 'engine.log'; self.log.write_text(LOG)

    def tearDown(self): self.d.cleanup()

    def test_requests_and_alignment(self):
        reqs, waited = ug.engine_requests(self.log)
        self.assertEqual([r['generated'] for r in reqs], [4096, 338, 2535, 10])
        self.assertEqual([len(r['timing']) for r in reqs], [1, 1, 1, 0])
        self.assertEqual(waited, 305.0)                                      # last cumulative value of each engine run
        mine, bad = ug.task_requests(reqs, ROWS[:1], 4096)                   # attempt 1 = two engine requests
        self.assertEqual((len(mine), bad), (3, 0))
        mine, bad = ug.task_requests(reqs, ROWS, 4096)
        self.assertEqual((len(mine), bad), (4, 0))
        _, bad = ug.task_requests(reqs, [dict(attempts=[dict(completion_tokens=4000)])], 4096)
        self.assertEqual(bad, 1)

    def test_window_stats(self):
        reqs, _ = ug.engine_requests(self.log)
        st = ug.window_stats(reqs)
        w = 2048 + 99 + 1229
        self.assertEqual(st['all']['windows'], w)
        self.assertAlmostEqual(st['all']['ms_win'], round((2048 * 14.84 + 99 * 26.02 + 1229 * 15.87) / w, 3))
        self.assertAlmostEqual(st['all']['cpu_entries'], round((2048 * 1.38 + 99 * 5.12 + 1229 * 1.82) / w, 3))
        self.assertAlmostEqual(st['all']['swaps'], round((2048 * 15.7 + 99 * 23.3 + 1229 * 16.3) / w, 3))
        self.assertEqual(st['<4K']['requests'], 2); self.assertEqual(st['4K-32K']['requests'], 1); self.assertEqual(st['32K-64K']['requests'], 1)
        self.assertEqual(st['4K-32K']['reach'], 8.26)
        self.assertEqual(st['all']['accept'], round((2048 + 239 + 1000) / (3048 + 281 + 1500), 3))
        self.assertEqual(st['>=64K'], dict(requests=0, windows=0, **{k: None for k in ug.DT_FIELDS}, generated=0, decode_tok_s=None, accept=None))


class Replay(unittest.TestCase):
    def test_pisim_tools(self):
        src = "import os\nTOOLS = [\n {'type': 'function', 'function': {'name': 'read'}},\n]\ndef f(): pass\n"
        self.assertEqual(ug.pisim_tools(src), [{'type': 'function', 'function': {'name': 'read'}}])
        with self.assertRaises(ug.Stop): ug.pisim_tools('X = 1\n')

    def test_build_and_bodies(self):
        A = [dict(role='system', content='sa'), dict(role='user', content='u1'), dict(role='assistant', content='a1', tool_calls=[1]),
             dict(role='tool', content='t1'), dict(role='assistant', content='a2')]
        B = [dict(role='system', content='sb'), dict(role='user', content='u2'), dict(role='assistant', content='b1')]
        doc = ug.build_replay(A, B, ['T'], 'm', 16384, 100)
        self.assertEqual([m['content'] for m in doc['messages']], ['sa', 'u1', 'a1', 't1', 'a2', 'u2', 'b1'])   # B's system dropped
        self.assertEqual(doc['cuts'], [2, 4, 6])
        bodies = list(ug.replay_bodies(doc))
        self.assertEqual([len(b['messages']) for b in bodies], [2, 4, 6])
        self.assertEqual([b['seed'] for b in bodies], [100, 101, 102])
        self.assertEqual(bodies[2]['messages'][-1], dict(role='user', content='u2'))   # recorded history, ends before b1
        self.assertTrue(all(b['tools'] == ['T'] and b['max_tokens'] == 16384 and b['stream'] is False for b in bodies))
        with self.assertRaises(ug.Stop): ug.build_replay(A[1:], B, [], 'm', 1, 0)

    def test_started_args_and_flags(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'engine.log'
            p.write_text('[strata] 2026-11-23 engine started: /x/strata --serve --spec 4 --adapt-every 2\nother\n')
            argv = ug.started_args(p)
        self.assertEqual(argv, ['--serve', '--spec', '4', '--adapt-every', '2'])
        flags = {'--adapt-every'}
        self.assertTrue(ug.flags_ok(argv, [('--adapt-every', '2')], flags))
        self.assertFalse(ug.flags_ok(argv, [('--adapt-every', '4')], flags))
        self.assertFalse(ug.flags_ok(argv, [], flags))                       # a control run must not carry it
        self.assertTrue(ug.flags_ok(['--serve', '--spec', '4'], [], flags))
        self.assertFalse(ug.flags_ok(None, [], flags))

    def test_verdict(self):
        def runs(c0a, l1a, l1b, c0b, tw=(2.0, 2.0, 2.0, 2.0), tps=(130, 140, 140, 130), valid=True):
            return {n: dict(ms_win=m, tok_win=t, decode_tok_s=s, valid=valid) for n, m, t, s in zip(('C0a', 'L1a', 'L1b', 'C0b'), (c0a, l1a, l1b, c0b), tw, tps)}
        v = ug.replay_verdict(runs(18.0, 16.8, 16.9, 18.1))
        self.assertEqual(v['verdict'], 'PASS'); self.assertAlmostEqual(v['aa'], round(0.1 / 18.05, 4)); self.assertEqual(v['bar'], 0.04)
        self.assertEqual(ug.replay_verdict(runs(18.0, 17.6, 17.5, 18.0))['verdict'], 'NO_PASS')            # only 2.5% faster
        v = ug.replay_verdict(runs(18.0, 16.0, 17.95, 17.0))                                               # AA 5.7%
        self.assertEqual(v['verdict'], 'NOISY')
        v = ug.replay_verdict(runs(18.0, 16.0, 17.2, 17.4))      # AA 3.4% -> bar 6.8%; mean 16.6 vs 17.7 is -6.2%
        self.assertEqual(v['verdict'], 'NO_PASS'); self.assertFalse(v['checks']['faster_by_bar'])
        v = ug.replay_verdict(runs(18.0, 16.5, 18.05, 18.1))     # one L run not below both C runs
        self.assertFalse(v['checks']['both_l_below_both_c']); self.assertEqual(v['verdict'], 'NO_PASS')
        v = ug.replay_verdict(runs(18.0, 16.8, 16.9, 18.1, tw=(2.0, 2.2, 2.2, 2.0)))
        self.assertEqual(v['verdict'], 'INCONCLUSIVE')
        self.assertEqual(ug.replay_verdict(runs(18.0, 16.8, 16.9, 18.1, tps=(130, 120, 120, 130)))['verdict'], 'NO_PASS')
        self.assertEqual(ug.replay_verdict(runs(18.0, 16.8, 16.9, 18.1, valid=False))['verdict'], 'INVALID')
        self.assertEqual(ug.replay_verdict({k: v for k, v in runs(1, 1, 1, 1).items() if k != 'C0b'})['verdict'], 'INCOMPLETE')


class Sampling(unittest.TestCase):
    def test_parse_and_suffix(self):
        self.assertEqual(ug.parse_sampling(['temperature=0.6', 'top_k=20']), dict(temperature=0.6, top_k=20))
        self.assertEqual(ug.sampling_suffix(dict(temperature=0.6)), '-temperature06')
        self.assertEqual(ug.sampling_suffix(dict(top_p=0.9, temperature=0.8)), '-temperature08-topp09')
        self.assertEqual(ug.sampling_suffix({}), '')
        for bad in (['temp=0.6'], ['temperature'], ['temperature=x'], ['top_p=1.5'], ['temperature=-1']):
            with self.assertRaises(ug.Stop): ug.parse_sampling(bad)

    def test_loop_signs(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'server-stdout.txt'
            p.write_text('[strata] the reply repeated one token (\'a\') 256 times\nok\n[strata] the thinking repeated the same passages (coverage=0.9)\n')
            self.assertEqual(ug.loop_signs(p, ['stop', 'length', 'tool_calls', 'length']), dict(finish_length=2, repeat_notices=2))
        self.assertEqual(ug.loop_signs(Path('/nonexistent/x'), []), dict(finish_length=0, repeat_notices=0))

    def test_verdict(self):
        ctl = lambda t, ms=17.5: dict(ms_win=ms, decode_tok_s=t, finish_length=0, repeat_notices=0, valid=True)
        controls = [ctl(144.6), ctl(145.7), ctl(145.0)]; ref = dict(ms_win=17.565, decode_tok_s=145.15)
        cand = lambda t, temp, fl=0: dict(ms_win=17.5, decode_tok_s=t, finish_length=fl, repeat_notices=0, valid=True, temperature=temp)
        smk = lambda t, e: dict(decode_tok_s=t, e2e=e, finish_length=0, repeat_notices=0, errors=0, valid=True)
        sref = dict(decode_tok_s=135.3, e2e=130.6)
        v = ug.sampling_verdict(controls, ref, {'T06': cand(165.0, 0.6), 'T08': cand(156.0, 0.8)}, sref, {'T06': smk(150, 140), 'T08': smk(145, 136)})
        self.assertEqual(v['arms']['T06']['verdict'], 'PASS'); self.assertEqual(v['arms']['T08']['verdict'], 'PASS')
        self.assertEqual(v['stage2'], 'T06')                       # 13.8% vs 7.5%: faster by >= 3 points
        v = ug.sampling_verdict(controls, ref, {'T06': cand(158.0, 0.6), 'T08': cand(156.0, 0.8)}, sref, {'T06': smk(150, 140), 'T08': smk(145, 136)})
        self.assertEqual(v['stage2'], 'T08')                       # within 3 points: the one closest to the card
        v = ug.sampling_verdict(controls, ref, {'T06': cand(165.0, 0.6, fl=3), 'T08': cand(150.0, 0.8)}, sref, {'T06': smk(150, 140), 'T08': smk(145, 136)})
        self.assertFalse(v['arms']['T06']['checks']['replay_loops_ok']); self.assertEqual(v['arms']['T08']['verdict'], 'NO_PASS')
        self.assertEqual(v['verdict'], 'NO_GAIN'); self.assertIsNone(v['stage2'])
        v = ug.sampling_verdict(controls, ref, {'T06': cand(165.0, 0.6)}, sref, {'T06': smk(130, 140)})
        self.assertFalse(v['arms']['T06']['checks']['smoke_decode_not_slower'])
        self.assertEqual(ug.sampling_verdict(controls[:2] + [ctl(140.0)], ref, {}, sref, {})['verdict'], 'STOP_ENV')
        self.assertEqual(ug.sampling_verdict(controls, ref, {'T06': cand(165.0, 0.6)}, sref, {})['arms']['T06']['verdict'], 'INVALID')
        wide = [ctl(140.0), ctl(150.0), ctl(145.0)]                # AA 6.9% -> bar 13.8%
        self.assertEqual(ug.sampling_verdict(wide, ref, {'T06': cand(160.0, 0.6)}, sref, {'T06': smk(150, 140)})['arms']['T06']['verdict'], 'NO_PASS')



class Approx(unittest.TestCase):
    def test_arm_env(self):
        self.assertEqual(ug.arm_env({}), {'STRATA_ROUTE_TAIL_SKIP': '7'})
        self.assertEqual(ug.arm_env({'STRATA_ROUTE_TAIL_SKIP': 5, 'STRATA_ROUTE_PRIOR': 0.5}),
                         {'STRATA_ROUTE_TAIL_SKIP': '5', 'STRATA_ROUTE_PRIOR': '0.5'})      # the arm's own rank wins
        for bad in ({'STRATA_ROUTE_RESIDENT': '1'}, {'STRATA_STAGE_PIN': '1'}):
            with self.assertRaises(ug.Stop): ug.arm_env(bad)

    def test_scoring_seconds(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'x.console.txt'
            p.write_text('engine: /x --serve\ncode: 999 positions, 9.9 s\ndocs: 999 positions, 7.8 s\nagent: 999 positions, 9.8 s\n')
            self.assertEqual(ug.scoring_seconds(p), 27.5)
            self.assertIsNone(ug.scoring_seconds(Path(d) / 'missing.txt'))

    def test_kl_screen(self):
        r = lambda kl, ag, top1=0.93: {'all': dict(kl=kl, top1=top1), 'agent': dict(kl=ag, top1=top1)}
        spec = dict(screen=dict(kl_all_max=0.10, kl_agent_max=0.25), identity_run='ts7')
        cmp = {'ts7': dict(exact=r(0.047, 0.136), b2=r(0.0, 0.0, 1.0)), 'ts5': dict(exact=r(0.074, 0.186), b2=r(0.03, 0.06)),
               'p10': dict(exact=r(0.09, 0.27), b2=r(0.05, 0.12)), 'p20': dict(exact=r(0.12, 0.2), b2=r(0.08, 0.1))}
        v = ug.kl_screen(cmp, spec)
        self.assertEqual(v['verdict'], 'SCREENED')
        self.assertEqual({n: x['screen'] for n, x in v['runs'].items()}, dict(ts7='IDENTITY', ts5='PASS', p10='FAIL', p20='FAIL'))
        cmp['ts7']['b2'] = r(0.0001, 0.0, 0.999)                  # the yardstick moved: nothing can be judged
        self.assertEqual(ug.kl_screen(cmp, spec)['verdict'], 'INVALID')

    def test_verdict(self):
        run = lambda t, ms=17.5, tw=2.4, fl=0, rep=0, co=None, ok=True: dict(valid=ok, ms_win=ms, tok_win=tw, decode_tok_s=t, finish_length=fl,
                                                                         repeat_notices=rep, cotenant_cpu=co)
        fresh = dict(C0a=run(140.0), C0b=run(141.4))              # AA 1.0% -> bar 4%
        kl = dict(TS5=dict(kl_all=0.074), P10=dict(kl_all=0.06), TS6=dict(kl_all=0.06), P05=dict(kl_all=0.03))
        cands = dict(TS5=run(158.0, ms=16.0), P10=run(152.0), TS6=run(150.0), P05=run(143.0))
        v = ug.approx_verdict(fresh, cands, kl, reused=[run(145.15)])
        self.assertEqual((v['bar'], v['verdict']), (0.04, 'STAGE3'))
        self.assertEqual({n: a['verdict'] for n, a in v['arms'].items()}, dict(TS5='PASS', P10='PASS', TS6='PASS', P05='NO_PASS'))
        self.assertEqual(v['stage3'], ['TS5', 'P10'])             # 12.4% vs 7.9%: the fastest goes first
        self.assertEqual(v['drift_vs_reused'], round(140.7 / 145.15 - 1, 4))
        cands['P10'] = run(157.0)                                  # within 3 points of TS5 with lower KL: it goes first
        self.assertEqual(ug.approx_verdict(fresh, cands, kl)['stage3'], ['P10', 'TS5'])
        cands['P10'] = run(157.0, fl=2)                            # more length stops than any control + 1
        v = ug.approx_verdict(fresh, cands, kl)
        self.assertFalse(v['arms']['P10']['checks']['loops_ok']); self.assertEqual(v['stage3'], ['TS5', 'TS6'])
        self.assertEqual(ug.approx_verdict(dict(C0a=run(140.0), C0b=run(150.0)), dict(TS5=run(158.0)), kl)['verdict'], 'NO_GAIN')   # bar 13.8%
        self.assertEqual(ug.approx_verdict(fresh, dict(TS5=run(158.0, ok=False)), kl), dict(verdict='INVALID', invalid=['TS5']))
        self.assertEqual(ug.approx_verdict(fresh, dict(TS5=run(158.0, co=1.5)), kl), dict(verdict='CONTENDED', rerun=['TS5']))
        self.assertEqual(ug.approx_verdict(fresh, {}, kl)['verdict'], 'NO_GAIN')

    def test_cotenant_cpu(self):
        with tempfile.TemporaryDirectory() as d:
            t0 = time.mktime((2026, 11, 24, 1, 0, 0, 0, 0, -1)); day = time.strftime('%Y-%m-%d', time.localtime(t0))
            s = lambda ts, a, b: json.dumps(dict(ts=ts, docker={'x': dict(cpu=a), 'y': dict(cpu=b)}))
            lines = [s(t0 - 60, 9.0, 9.0), s(t0 + 60, 0.5, 0.1), s(t0 + 120, 1.0, None), s(t0 + 400, 9.0, 9.0)]
            with gzip.open(Path(d) / (day + '.jsonl.gz'), 'wt') as f: f.write('\n'.join(lines) + '\n')
            self.assertEqual(ug.cotenant_cpu(t0, t0 + 100, d), 0.8)     # the samples at +60 and +120 (0.6 and 1.0)
            self.assertIsNone(ug.cotenant_cpu(t0 + 1000, t0 + 1100, d))
            self.assertIsNone(ug.cotenant_cpu(None, t0, d))


class ProbeBuild(unittest.TestCase):
    def test_cli_guards(self):
        import sys
        bad = [['prepare', 'v0.2.17', '--patch', 'x.patch'],                     # a patched build needs its own label
               ['prepare', 'v0.2.17', '--label', 'xp', '--patch', 'x.patch'],     # the label is the tag plus a suffix
               ['prepare', 'v0.2.17', '--label', 'v0.2.17'],
               ['probe', 'lab-x', '--label', 'v0.2.17-xp'],                       # --label/--patch/--target: prepare only
               ['replay', 'lab-x', '--eval', '--tree-label', 'v0.2.17-xp']]       # replay names its tree in the prereg
        old = sys.argv
        try:
            for argv in bad:
                sys.argv = ['upgrade_gate.py'] + argv
                with self.assertRaises(SystemExit, msg=argv): ug.main()
        finally:
            sys.argv = old

    def test_run_tree(self):
        with tempfile.TemporaryDirectory() as d:
            P, X = Path(d) / 'strata-0.2.17', Path(d) / 'strata-0.2.17-xp'
            def cfg(t, save):
                return dict(exe=str(t / 'engine/strata'), port=1, log=str(t / 'a.log'),
                            args=['--expert-profile', str(t / 'data/p.bin'), '--expert-profile-save', save, '--spec', '6'])
            for t in (P, X):
                (t / 'engine').mkdir(parents=True); (t / 'engine/strata').write_text(t.name)
            prod = cfg(P, str(P / 'learned.bin'))
            (X / 'strata-iq3_xxs.json').write_text(json.dumps(dict(cfg(X, '/elsewhere.bin'), port=2)))
            prep = dict(status='READY', tree=str(X), engine_sha256=ug.sha(X / 'engine/strata'))
            saved = ug.b2_production_tree, ug.load
            ug.b2_production_tree = lambda force=False: (P, prod)
            ug.load = lambda lb, name: prep if (lb, name) == ('v0.2.17-xp', 'PREPARE.json') else None
            try:
                self.assertEqual(ug.run_tree(None), (P, prod))
                t, c = ug.run_tree('v0.2.17-xp')
                self.assertEqual((t, c['exe']), (X, str(X / 'engine/strata')))
                with self.assertRaises(ug.Stop): ug.run_tree('v0.2.17-other')             # no prepare
                prep['status'] = 'STOPPED'
                with self.assertRaises(ug.Stop): ug.run_tree('v0.2.17-xp')                # not READY
                prep.update(status='READY', engine_sha256='0' * 64)
                with self.assertRaises(ug.Stop): ug.run_tree('v0.2.17-xp')                # engine replaced
                prep['engine_sha256'] = ug.sha(X / 'engine/strata')
                c2 = json.loads((X / 'strata-iq3_xxs.json').read_text()); c2['args'][-1] = '8'
                (X / 'strata-iq3_xxs.json').write_text(json.dumps(c2))
                with self.assertRaises(ug.Stop): ug.run_tree('v0.2.17-xp')                # config drifted from production
            finally:
                ug.b2_production_tree, ug.load = saved


if __name__ == '__main__':
    unittest.main()
