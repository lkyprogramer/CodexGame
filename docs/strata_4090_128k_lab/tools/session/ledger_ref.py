import copy, math, threading
class Ledger:
    def __init__(self):
        self._lock = threading.RLock(); self._s = {'bal': {}, 'lim': {}, 'hist': {}, 'bps': 0}; self._undo = []
    def _save(self): self._undo.append(copy.deepcopy(self._s))
    def add(self, account, amount):
        with self._lock:
            self._save(); s = self._s
            s['bal'][account] = s['bal'].get(account, 0) + amount; s['hist'].setdefault(account, []).append(('add', amount))
    def balance(self, account):
        with self._lock: return self._s['bal'].get(account, 0)
    def transfer(self, src, dst, amount):
        with self._lock:
            if not isinstance(amount, int) or amount <= 0: raise ValueError('amount')
            s = self._s; fee = math.ceil(amount * s['bps'] / 10000)
            if s['bal'].get(src, 0) - amount - fee < -s['lim'].get(src, 0): raise ValueError('funds')
            self._save()
            s['bal'][src] = s['bal'].get(src, 0) - amount - fee; s['bal'][dst] = s['bal'].get(dst, 0) + amount
            h = s['hist'].setdefault(src, []); h.append(('transfer_out', amount))
            if fee: h.append(('fee', fee))
            s['hist'].setdefault(dst, []).append(('transfer_in', amount))
    def history(self, account):
        with self._lock: return list(self._s['hist'].get(account, []))
    def set_limit(self, account, limit):
        with self._lock:
            if not isinstance(limit, int) or limit < 0: raise ValueError('limit')
            self._save(); self._s['lim'][account] = limit
    def snapshot(self):
        with self._lock: return copy.deepcopy(self._s)
    def restore(self, snap):
        with self._lock: self._save(); self._s = copy.deepcopy(snap)
    def set_fee_bps(self, bps):
        with self._lock:
            if not isinstance(bps, int) or not 0 <= bps <= 10000: raise ValueError('bps')
            self._save(); self._s['bps'] = bps
    def undo(self):
        with self._lock:
            if not self._undo: raise IndexError('nothing')
            self._s = self._undo.pop()
