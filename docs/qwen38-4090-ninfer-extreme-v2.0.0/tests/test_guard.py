import unittest
from tools.remote_guard import ProductionLease,wait_gpu_free,HEALTH_PORTS
class GuardTests(unittest.TestCase):
    def test_health_requires_native_and_compat_ports(self):
        self.assertEqual(set(HEALTH_PORTS),{18343,18030})
    def test_gpu_free_polls_until_released(self):
        seq=iter([['1509'],['1509'],['24000']]);t=[0.];slept=[]
        free=wait_gpu_free(query=lambda:next(seq),poll_sec=30,sleep=lambda s:(slept.append(s),t.__setitem__(0,t[0]+s)),clock=lambda:t[0])
        self.assertEqual(free,24000);self.assertEqual(len(slept),2)
    def test_gpu_free_gives_up_after_poll_window(self):
        t=[0.]
        with self.assertRaises(RuntimeError):
            wait_gpu_free(query=lambda:['1509'],poll_sec=30,sleep=lambda s:t.__setitem__(0,t[0]+s),clock=lambda:t[0])
    def test_gpu_free_rejects_multi_gpu_output(self):
        with self.assertRaises(RuntimeError):wait_gpu_free(query=lambda:['24000','24000'],poll_sec=0,sleep=lambda s:None,clock=lambda:0.)
    def test_explicit_approval(self):
        calls=[];g=ProductionLease(lambda:True,lambda:calls.append('stop'),lambda:calls.append('start'))
        with self.assertRaises(RuntimeError):g.acquire(False)
        self.assertEqual(calls,[])
    def test_restore_active(self):
        calls=[];g=ProductionLease(lambda:True,lambda:calls.append('stop'),lambda:calls.append('start'));g.acquire(True);g.restore();self.assertEqual(calls,['stop','start'])
    def test_keep_inactive(self):
        calls=[];g=ProductionLease(lambda:False,lambda:calls.append('stop'),lambda:calls.append('start'));g.acquire(True);g.restore();self.assertEqual(calls,[])
    def test_stop_error_still_restores(self):
        calls=[]
        def fail():raise RuntimeError('stop maybe happened')
        g=ProductionLease(lambda:True,fail,lambda:calls.append('start'))
        with self.assertRaises(RuntimeError):g.acquire(True)
        g.restore();self.assertEqual(calls,['start'])
    def test_no_acquire_no_restore(self):
        calls=[];g=ProductionLease(lambda:True,lambda:None,lambda:calls.append('start'));g.restore();self.assertEqual(calls,[])
if __name__=='__main__':unittest.main()
