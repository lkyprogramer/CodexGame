import base64,json,unittest
from datetime import datetime,timezone,timedelta,date
from platform.serialization.event import serialize_event
class Tests(unittest.TestCase):
 def test_canonical_and_no_mutation(self):
  e={'z':'你','a':datetime(2026,1,2,3,4,5,678900,tzinfo=timezone(timedelta(hours=8))),'b':b'hi','d':date(2026,1,2)};before=dict(e);raw=serialize_event(e);self.assertEqual(e,before);self.assertEqual(raw,b'{"a":"2026-01-01T19:04:05.678Z","b":{"$bytes":"aGk="},"d":"2026-01-02","z":"\xe4\xbd\xa0"}');self.assertEqual(raw,serialize_event(e))
 def test_invalid(self):
  for e in ({'x':float('nan')},{'x':datetime.now()},{1:'x'},{'x':object()}):
   with self.subTest(e=e):
    with self.assertRaises(ValueError):serialize_event(e)
  x=[];x.append(x)
  with self.assertRaises(ValueError):serialize_event({'x':x})
if __name__=='__main__':unittest.main()
