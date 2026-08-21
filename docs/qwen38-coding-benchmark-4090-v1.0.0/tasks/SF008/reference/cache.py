import time
import threading
from collections import OrderedDict

class LruTtlCache:
    def __init__(self, max_size, ttl_seconds, clock=time.monotonic):
        if max_size <= 0 or ttl_seconds <= 0:
            raise ValueError("max_size and ttl_seconds must be positive")
        self.max_size = int(max_size)
        self.ttl_seconds = float(ttl_seconds)
        self.clock = clock
        self._data = OrderedDict()
        self._lock = threading.RLock()

    def _purge_expired(self, now):
        expired = [key for key, (_, expires) in self._data.items() if expires <= now]
        for key in expired:
            self._data.pop(key, None)

    def put(self, key, value):
        now = self.clock()
        with self._lock:
            self._purge_expired(now)
            self._data.pop(key, None)
            self._data[key] = (value, now + self.ttl_seconds)
            while len(self._data) > self.max_size:
                self._data.popitem(last=False)

    def get(self, key, default=None):
        now = self.clock()
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return default
            value, expires = item
            if expires <= now:
                self._data.pop(key, None)
                return default
            self._data.move_to_end(key)
            return value

    def __len__(self):
        now = self.clock()
        with self._lock:
            self._purge_expired(now)
            return len(self._data)
