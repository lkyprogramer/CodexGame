import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from lab.core import run


class ProcessTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'posix', 'owned process group test is POSIX only')
    def test_timeout_ends_owned_children_and_keeps_partial_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / 'child-survived'
            log = Path(tmp) / 'timeout.log'
            child = 'import time,pathlib; time.sleep(3); pathlib.Path(%r).write_text("bad")' % str(marker)
            parent = ('import subprocess,sys,time; '
                      'subprocess.Popen([sys.executable,"-c",%r],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); '
                      'print("STARTED",flush=True); time.sleep(10)' % child)
            with self.assertRaises(subprocess.TimeoutExpired):
                run([sys.executable, '-c', parent], timeout=1, log=log)
            time.sleep(3.3)
            self.assertFalse(marker.exists(), 'timeout must stop descendants started by this owned command')
            self.assertTrue(log.exists(), 'partial command output must survive a timeout')
            self.assertIn('STARTED', log.read_text())
