class Utf8ChunkDecoder:
    def feed(self,data,final=False):return data.decode('utf-8')
