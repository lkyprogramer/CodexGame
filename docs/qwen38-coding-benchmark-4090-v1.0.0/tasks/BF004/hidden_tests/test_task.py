import unittest
from retrying import retry
class Transient(Exception):pass
class Tests(unittest.TestCase):
    def test_success_after_retries(self):
        calls=[];delays=[]
        def action():
            calls.append(1)
            if len(calls)<3:raise Transient('x')
            return 7
        self.assertEqual(retry(action,2,Transient,delays.append,0.25),7);self.assertEqual(delays,[0.25,0.5]);self.assertEqual(len(calls),3)
    def test_exhausted_preserves_exception(self):
        err=Transient('last')
        with self.assertRaises(Transient) as ctx:retry(lambda:(_ for _ in ()).throw(err),1,Transient,lambda _:None)
        self.assertIs(ctx.exception,err)
    def test_non_retryable_and_base_exception(self):
        delays=[]
        with self.assertRaises(ValueError):retry(lambda:(_ for _ in ()).throw(ValueError('no')),3,Transient,delays.append)
        self.assertEqual(delays,[])
        with self.assertRaises(KeyboardInterrupt):retry(lambda:(_ for _ in ()).throw(KeyboardInterrupt()),3,Exception,delays.append)
    def test_zero_retries_still_calls_once(self):
        calls=[]
        with self.assertRaises(Transient):retry(lambda:(calls.append(1),(_ for _ in ()).throw(Transient()))[1],0,Transient,lambda _:None)
        self.assertEqual(len(calls),1)
    def test_validation(self):
        for retries in (-1,True):
            with self.assertRaises(ValueError):retry(lambda:1,retries,Exception,lambda _:None)
if __name__=='__main__':unittest.main()
