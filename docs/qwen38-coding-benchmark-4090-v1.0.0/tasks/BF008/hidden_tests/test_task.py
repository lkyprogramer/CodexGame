import io,os,stat,tempfile,unittest,zipfile
from pathlib import Path
from zip_extract import safe_extract
def make_zip(path,entries):
    with zipfile.ZipFile(path,'w') as z:
        for name,data,mode in entries:
            info=zipfile.ZipInfo(name);info.external_attr=mode<<16;z.writestr(info,data)
class Tests(unittest.TestCase):
    def test_valid(self):
        with tempfile.TemporaryDirectory() as d:
            z=Path(d)/'a.zip';out=Path(d)/'out';make_zip(z,[('a/b.txt',b'ok',stat.S_IFREG|0o644),('empty/',b'',stat.S_IFDIR|0o755)]);safe_extract(z,out);self.assertEqual((out/'a/b.txt').read_bytes(),b'ok');self.assertTrue((out/'empty').is_dir())
    def test_attacks_are_atomic(self):
        attacks=['../escape','/abs','C:/evil',r'a\..\evil']
        for name in attacks:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
                z=Path(d)/'a.zip';out=Path(d)/'out';make_zip(z,[('good.txt',b'x',stat.S_IFREG|0o644),(name,b'bad',stat.S_IFREG|0o644)])
                with self.assertRaises(ValueError):safe_extract(z,out)
                self.assertFalse((out/'good.txt').exists())
    def test_symlink_and_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            z=Path(d)/'s.zip';make_zip(z,[('link',b'target',stat.S_IFLNK|0o777)])
            with self.assertRaises(ValueError):safe_extract(z,Path(d)/'out')
        with tempfile.TemporaryDirectory() as d:
            z=Path(d)/'d.zip';make_zip(z,[('a/../b',b'1',stat.S_IFREG|0o644),('b',b'2',stat.S_IFREG|0o644)])
            with self.assertRaises(ValueError):safe_extract(z,Path(d)/'out')
if __name__=='__main__':unittest.main()
