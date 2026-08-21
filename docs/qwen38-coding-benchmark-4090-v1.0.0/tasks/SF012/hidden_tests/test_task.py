import os, tempfile, unittest
from pathlib import Path
from safe_path import safe_join
class Tests(unittest.TestCase):
    def test_normal_and_missing_tail(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); expected=(root/'a'/'b.txt').resolve(); self.assertEqual(safe_join(root,'a/b.txt'),expected)
    def test_rejects_common_attacks(self):
        with tempfile.TemporaryDirectory() as d:
            for p in ('', '../x', 'a/../../x', '/tmp/x', r'C:\temp\x', 'C:/temp/x', r'a\..\x', 'bad' + chr(0) + 'name'):
                with self.subTest(p=p):
                    with self.assertRaises(ValueError): safe_join(d,p)
    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
            root=Path(d); link=root/'link'
            try: link.symlink_to(Path(outside),target_is_directory=True)
            except (OSError,NotImplementedError): self.skipTest('symlink unsupported')
            with self.assertRaises(ValueError): safe_join(root,'link/new.txt')
    def test_bad_root(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): safe_join(Path(d)/'missing','a')
if __name__=='__main__': unittest.main()
