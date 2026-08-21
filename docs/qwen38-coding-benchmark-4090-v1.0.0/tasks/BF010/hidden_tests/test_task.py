import unittest
from utf8_stream import Utf8ChunkDecoder
class Tests(unittest.TestCase):
    def test_split_multibyte(self):
        raw='A你🙂B'.encode();d=Utf8ChunkDecoder();parts=[raw[:2],raw[2:5],raw[5:7],raw[7:]];self.assertEqual(''.join(d.feed(p,final=i==len(parts)-1) for i,p in enumerate(parts)),'A你🙂B')
    def test_empty_final(self):
        d=Utf8ChunkDecoder();self.assertEqual(d.feed(b'abc'),'abc');self.assertEqual(d.feed(b'',final=True),'');
        with self.assertRaises(RuntimeError):d.feed(b'x')
    def test_incomplete_and_invalid(self):
        d=Utf8ChunkDecoder();d.feed(bytes([0xE4]))
        with self.assertRaises(UnicodeDecodeError):d.feed(b'',final=True)
        with self.assertRaises(UnicodeDecodeError):Utf8ChunkDecoder().feed(bytes([0xFF]),final=True)
    def test_bytes_like_and_type(self):
        self.assertEqual(Utf8ChunkDecoder().feed(memoryview(b'ok'),final=True),'ok')
        with self.assertRaises(TypeError):Utf8ChunkDecoder().feed('x')
if __name__=='__main__':unittest.main()
