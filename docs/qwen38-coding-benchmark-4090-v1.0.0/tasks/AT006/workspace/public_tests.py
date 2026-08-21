from flags.store import Store
from flags.service import FlagService
s=FlagService(Store({('a','x'):True,('b','x'):False}))
assert s.enabled('a','x') is True
assert s.enabled('b','x') is False
print('PUBLIC OK')
