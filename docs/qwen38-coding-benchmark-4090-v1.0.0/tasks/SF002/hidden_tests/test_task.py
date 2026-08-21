import unittest
from duration import parse_duration

class DurationTests(unittest.TestCase):
    def test_valid_combinations(self):
        self.assertEqual(parse_duration("1h30m"), 5_400_000)
        self.assertEqual(parse_duration("2m5s250ms"), 125_250)
        self.assertEqual(parse_duration("1d2h3m4s5ms"), 93_784_005)
    def test_single_millisecond(self):
        self.assertEqual(parse_duration("500ms"), 500)
    def test_zero_component_allowed_when_total_positive(self):
        self.assertEqual(parse_duration("1h0m5s"), 3_605_000)
    def test_rejects_bad_order_and_duplicates(self):
        for value in ("30m1h", "1h1h", "1ms1s"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError): parse_duration(value)
    def test_rejects_syntax_noise(self):
        for value in (" 1h", "1h ", "1.5h", "1hour", "1h+2m", ""):
            with self.subTest(value=value):
                with self.assertRaises(ValueError): parse_duration(value)
    def test_rejects_zero_and_non_string(self):
        with self.assertRaises(ValueError): parse_duration("0s")
        with self.assertRaises(ValueError): parse_duration(60)

if __name__ == '__main__': unittest.main()
