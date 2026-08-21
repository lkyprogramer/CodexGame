import unittest
from expiring_lru import ExpiringLru
class Clock:
    def __init__(self):self.t=0
    def __call__(self):return self.t
class Tests(unittest.TestCase):
    def test_expired_does_not_evict_live(self):
        c=Clock();x=ExpiringLru(2,10,c);x.put('old',1);c.t=5;x.put('hot',2);x.get('hot');c.t=11;x.put('new',3);self.assertIsNone(x.get('old'));self.assertEqual(x.get('hot'),2);self.assertEqual(x.get('new'),3)
    def test_refresh_and_boundary(self):
        c=Clock();x=ExpiringLru(1,5,c);x.put('a',1);c.t=4;x.put('a',2);c.t=9;self.assertIsNone(x.get('a'));self.assertEqual(len(x),0)
    def test_lru(self):
        c=Clock();x=ExpiringLru(2,100,c);x.put('a',1);x.put('b',2);x.get('a');x.put('c',3);self.assertIsNone(x.get('b'))
    def test_validation(self):
        with self.assertRaises(ValueError):ExpiringLru(0,1,lambda:0)
if __name__=='__main__':unittest.main()
