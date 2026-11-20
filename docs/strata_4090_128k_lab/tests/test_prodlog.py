import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'tools/prodlog.py'

T = ('strata decode timing: 40 windows, avg T 2.67, 2.02 tokens/window, 27.18 ms/window = adapt wait 0.05 + verify 25.37 '
     '(GPU-reach wait 7.32 + per-layer host 17.37 [plan 0.28 actq 0.30 jobs 0.10 CPU 16.54] + stage 0.11) + commit/emit 0.04 + '
     'draft 1.54 + adapt join 0.18 + other 0.00; per layer-window: CPU experts 3.42 (4.71 entries), VRAM hits 20.10, PCIe 0.20; 9.0 swaps/window')
LOG = [
    '[strata] 2026-11-20 06:45:02 engine started: /x/engine/strata --serve --pack p',
    'strata serve: conversation cache sized from the free RAM: 6144 MiB for up to 4 parked conversations',
    T,
    'strata serve: prompt 63 tokens = 0 reused + 63 read in 583 ms (108.1 tok/s), 81 generated in 1087 ms (74.5 tok/s), drafts accepted 41 of 67, 1 checkpoints',
    'strata serve: checkpoint pool: this request took 1 checkpoint ready from the pool and allocated 0 fresh',
    'strata serve: decode expert cache hit rate: 80.9% (38225 hits / 47274 lookups); 115 more read by the GPU over PCIe',
    'strata serve: conversation cache: parked 143 tokens in 29.1 ms; parked=1 bytes=238330044 evictions=0 snapshot_bytes=238330044 reused_kv_bytes=0',
    'strata serve: conversation cache: restored 143 tokens (live) in 3.2 ms; parked=0 bytes=0',
    'strata serve: prompt 20000 tokens = 143 reused + 12288 of 19857 read in 4000 ms (3072.0 tok/s), 0 generated in 0 ms (0.0 tok/s), drafts accepted 0 of 0, 2 checkpoints (cancelled)',
    'strata serve: conversation cache: evicted 2 parked conversations to admit this snapshot (900 MiB plus 4096 MiB floor)',
    'strata serve: conversation cache: skip parking (RAM floor after capture: 4096 MiB needed, 3000 MiB free)',
    '[strata] 2026-11-21 08:00:00 engine started: /x/engine/strata --serve',
    'strata serve: prompt 70000 tokens = 0 reused + 70000 read in 15000 ms (4666.7 tok/s), 512 generated in 4000 ms (128.0 tok/s), drafts accepted 300 of 400, 5 checkpoints',
]


class ProdLog(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('prodlog', MODULE)
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)

    def test_requests_and_attachment(self):
        r = self.m.parse(LOG)
        self.assertEqual([x['prompt'] for x in r], [63, 20000, 70000])
        self.assertEqual(len(r[0]['timing']), 1)                 # decode timing precedes its own summary
        self.assertEqual(r[0]['timing'][0]['cpu_entries'], 4.71)
        self.assertEqual(r[0]['hit_rate'], 80.9)                  # hit rate follows the summary
        self.assertTrue(r[0]['park']['stored'])                   # the park after request 1 is request 1's
        self.assertIsNone(r[0]['restored'])
        self.assertEqual(r[1]['restored'], {'tokens': 143, 'source': 'live', 'ms': 3.2})   # the restore before request 2 is request 2's

    def test_cancelled_read_counts_what_was_read(self):
        r = self.m.parse(LOG)[1]
        self.assertTrue(r['cancelled'])
        self.assertEqual((r['read'], r['read_planned']), (12288, 19857))
        self.assertEqual(r['evicted'], 2)
        self.assertTrue(any(n.startswith('skip parking') for n in r['conv_notes']))

    def test_epochs_and_since(self):
        r = self.m.parse(LOG)
        self.assertEqual([x['epoch'] for x in r], ['2026-11-20 06:45:02'] * 2 + ['2026-11-21 08:00:00'])
        self.assertEqual([x['prompt'] for x in self.m.parse(LOG, since='2026-11-21 00:00:00')], [70000])
        self.assertEqual(self.m.parse(LOG[:1] + LOG[2:5]), self.m.parse(LOG[:5]))   # unrelated lines change nothing

    def test_summary(self):
        s = self.m.summarize(self.m.parse(LOG))
        self.assertEqual(s['requests'], 3)
        self.assertEqual(s['cancelled'], 1)
        self.assertEqual(s['reused_tokens'], 143)
        self.assertAlmostEqual(s['reuse_ratio'], 143 / 90063, places=4)
        self.assertEqual(s['cold_reads_ge_8k'], {'count': 1, 'tokens': 70000, 'seconds': 15.0})
        self.assertEqual(s['partial_reuse_reads_ge_8k']['count'], 1)
        self.assertEqual(s['restores'], {'count': 1, 'live': 1, 'checkpoint': 0})
        self.assertEqual((s['parks'], s['park_skips'], s['evictions']), (1, 1, 2))
        self.assertEqual(set(s['by_prompt_bucket']), {'<4K', '4K-32K', '>=64K'})
        self.assertEqual(s['by_prompt_bucket']['>=64K']['decode_tok_s'], 128.0)
        self.assertIsNone(s['by_prompt_bucket']['4K-32K']['decode_tok_s'])   # nothing generated: no rate, not zero

    def test_empty(self):
        s = self.m.summarize([])
        self.assertEqual((s['requests'], s['reuse_ratio'], s['by_prompt_bucket']), (0, None, {}))


if __name__ == '__main__':
    unittest.main()
