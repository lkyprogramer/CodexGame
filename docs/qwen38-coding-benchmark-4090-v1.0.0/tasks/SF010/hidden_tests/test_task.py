import unittest
from json_pointer import json_pointer_get
class Tests(unittest.TestCase):
    def setUp(self): self.doc={'a/b':{'~key':[10,20]},'':7,'arr':['x']}
    def test_root(self): self.assertIs(json_pointer_get(self.doc,''),self.doc)
    def test_escapes(self): self.assertEqual(json_pointer_get(self.doc,'/a~1b/~0key/1'),20)
    def test_empty_key(self): self.assertEqual(json_pointer_get(self.doc,'/'),7)
    def test_default(self): self.assertEqual(json_pointer_get(self.doc,'/missing',99),99)
    def test_missing(self):
        with self.assertRaises(KeyError): json_pointer_get(self.doc,'/arr/2')
    def test_invalid(self):
        for p in ('arr/0','/a~2b','/arr/-','/arr/00','/arr/x'):
            with self.subTest(p=p):
                with self.assertRaises(ValueError): json_pointer_get(self.doc,p)
if __name__=='__main__': unittest.main()
