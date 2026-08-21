import unittest
from datetime import date
from scheduler.monthly import next_monthly
class Tests(unittest.TestCase):
 def test_clamp_and_same_month(self):self.assertEqual(next_monthly(date(2026,1,10),31),date(2026,1,31));self.assertEqual(next_monthly(date(2026,1,31),31),date(2026,2,28))
 def test_leap_and_year(self):self.assertEqual(next_monthly(date(2028,1,31),31),date(2028,2,29));self.assertEqual(next_monthly(date(2026,12,31),31),date(2027,1,31))
 def test_day_30_after_clamped_day(self):self.assertEqual(next_monthly(date(2026,2,28),30),date(2026,3,30))
 def test_invalid(self):
  for d in (0,32,True):
   with self.assertRaises(ValueError):next_monthly(date.today(),d)
if __name__=='__main__':unittest.main()
