import threading, unittest
from cache import LruTtlCache
class Clock:
    def __init__(self): self.now=0.0
    def __call__(self): return self.now
class Tests(unittest.TestCase):
    def test_validation(self):
        for args in ((0,1),(1,0),(-1,1)):
            with self.assertRaises(ValueError): LruTtlCache(*args)
    def test_ttl_and_refresh(self):
        c=Clock(); x=LruTtlCache(2,10,c); x.put('a',1); c.now=9; self.assertEqual(x.get('a'),1); c.now=10; self.assertIsNone(x.get('a')); self.assertEqual(len(x),0)
        x.put('a',2); c.now=15; x.put('a',3); c.now=24.9; self.assertEqual(x.get('a'),3)
    def test_lru(self):
        c=Clock(); x=LruTtlCache(2,100,c); x.put('a',1); x.put('b',2); x.get('a'); x.put('c',3); self.assertIsNone(x.get('b')); self.assertEqual(x.get('a'),1)
    def test_expired_not_considered_for_capacity(self):
        c=Clock(); x=LruTtlCache(2,5,c); x.put('a',1); x.put('b',2); c.now=6; x.put('c',3); self.assertEqual(len(x),1)
    def test_thread_safety(self):
        c=Clock(); x=LruTtlCache(8,100,c); errors=[]
        def worker(n):
            try:
                for i in range(500): x.put((n,i%16),i); x.get((n,i%16))
            except Exception as e: errors.append(e)
        ts=[threading.Thread(target=worker,args=(i,)) for i in range(8)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertFalse(errors); self.assertLessEqual(len(x),8)
if __name__=='__main__': unittest.main()
