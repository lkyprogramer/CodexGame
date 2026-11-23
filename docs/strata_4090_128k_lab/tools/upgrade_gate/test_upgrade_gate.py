"""CPU-only checks of upgrade_gate.py's arm helpers (--arg, the config stand-in, per-window figures); no GPU, no 4090 paths.

    python3 -B -m unittest test_upgrade_gate      (from this directory)
"""
import json, tempfile, unittest
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


if __name__ == '__main__':
    unittest.main()
