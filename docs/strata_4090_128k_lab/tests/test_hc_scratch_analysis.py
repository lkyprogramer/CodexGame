import importlib.util
from pathlib import Path
import struct
import unittest

PATH = Path(__file__).resolve().parents[1] / 'tools/hc_scratch/analyze.py'
SPEC = importlib.util.spec_from_file_location('hc_analysis', PATH)
hc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hc)


class HcAnalysisTests(unittest.TestCase):
    def test_signed_zero_is_a_bit_difference_even_when_float_equal(self):
        row = hc.float_comparison(struct.pack('<ff', 0, 1), struct.pack('<ff', -0.0, 1))
        self.assertFalse(row['bitwise_equal'])
        self.assertEqual(row['different_f32_bits'], 1)
        self.assertEqual(row['max_abs'], 0)

    def test_incomplete_or_nonfinite_rows_are_not_a_pass(self):
        with self.assertRaises(ValueError):
            hc.float_comparison(b'', b'')
        with self.assertRaises(ValueError):
            hc.float_comparison(struct.pack('<f', float('nan')), struct.pack('<f', 0))

    def test_first_difference_requires_identical_checkpoint_coverage(self):
        a = [dict(chunk_p0=0, T=4095, layer=0, half=0, stage='enter', field='R', bytes=4, fnv1a64='one')]
        b = [{**a[0], 'fnv1a64': 'two'}]
        self.assertEqual(hc.first_checkpoint_difference(a, b)['index'], 0)
        with self.assertRaisesRegex(ValueError, 'COVERAGE_MISMATCH'):
            hc.first_checkpoint_difference(a, [{**b[0], 'layer': 1}])


if __name__ == '__main__':
    unittest.main()
