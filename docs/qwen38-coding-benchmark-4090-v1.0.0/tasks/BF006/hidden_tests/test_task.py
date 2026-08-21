import unittest
from named_sql import compile_named
class Tests(unittest.TestCase):
    def test_basic_and_duplicate(self):
        self.assertEqual(compile_named('a=:x OR b=:x AND c=:y',{'x':1,'y':2}),('a=? OR b=? AND c=?',[1,1,2]))
    def test_ignored_regions(self):
        sql="select ':no', \"a:no\", x::text -- :line\nfrom t /* :block */ where id=:id"
        expected="select ':no', \"a:no\", x::text -- :line\nfrom t /* :block */ where id=?"
        self.assertEqual(compile_named(sql,{'id':7}),(expected,[7]))
    def test_escaped_quotes(self):
        self.assertEqual(compile_named("select 'it''s :x', :real",{'real':3}),("select 'it''s :x', ?",[3]))
    def test_name_rules(self):
        self.assertEqual(compile_named('x=:_a1 and y=:2',{'_a1':4}),('x=? and y=:2',[4]))
    def test_errors(self):
        with self.assertRaises(KeyError):compile_named('x=:missing',{})
        for sql in ("select ':x",'select "x:bad','select /* bad'):
            with self.subTest(sql=sql):
                with self.assertRaises(ValueError):compile_named(sql,{})
if __name__=='__main__':unittest.main()
