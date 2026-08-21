import json,tempfile,unittest
from pathlib import Path
from config_loader import load_config
class Tests(unittest.TestCase):
 def test_precedence_and_conversion(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'c.json';p.write_text(json.dumps({'host':'file','port':1000,'debug':False,'tags':['a']}));src={'port':'3000'};out=load_config(p,{'APP_PORT':'2000','APP_DEBUG':'yes','OTHER':'x'},src);self.assertEqual(out,{'host':'file','port':3000,'debug':True,'workers':4,'tags':['a']});self.assertEqual(src,{'port':'3000'})
 def test_tags_and_bool(self):self.assertEqual(load_config(None,{'APP_TAGS':' a, b ,,c ','APP_DEBUG':'0'},{} )['tags'],['a','b','c'])
 def test_errors(self):
  cases=[(None,{'APP_UNKNOWN':'x'},{}),(None,{}, {'port':0}),(None,{}, {'workers':129}),(None,{}, {'debug':'maybe'}),(None,{}, {'tags':[1]})]
  for args in cases:
   with self.subTest(args=args):
    with self.assertRaises(ValueError):load_config(*args)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x';p.write_text('[]')
   with self.assertRaises(ValueError):load_config(p,{}, {})
if __name__=='__main__':unittest.main()
