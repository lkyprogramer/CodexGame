import json, shutil, subprocess, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('javac') and shutil.which('java'),'JDK is not installed')
class JavaOracleTests(unittest.TestCase):
    def test_all_trusted_reference_programs(self):
        for task in json.loads((ROOT/'fixtures/java/tasks.json').read_text()):
            with self.subTest(task=task['id']), tempfile.TemporaryDirectory() as t:
                d=ROOT/'fixtures/java'/task['id']
                r=subprocess.run(['javac','--release','8','-encoding','UTF-8','-d',t,str(d/'reference/Solution.java'),str(d/'Harness.java')],capture_output=True,text=True,timeout=30)
                self.assertEqual(r.returncode,0,r.stderr)
                r=subprocess.run(['java','-cp',t,'Harness'],capture_output=True,text=True,timeout=30)
                self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stdout.strip(),'ALL_OK')
