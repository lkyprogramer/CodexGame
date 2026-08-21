import codecs
class Utf8ChunkDecoder:
    def __init__(self):self._decoder=codecs.getincrementaldecoder('utf-8')('strict');self._finished=False
    def feed(self,data,final=False):
        if self._finished:raise RuntimeError('decoder already finalized')
        if not isinstance(data,(bytes,bytearray,memoryview)):raise TypeError('data must be bytes-like')
        result=self._decoder.decode(bytes(data),final=bool(final))
        if final:self._finished=True
        return result
