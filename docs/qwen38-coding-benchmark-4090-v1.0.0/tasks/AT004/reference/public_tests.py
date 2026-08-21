from datetime import date
from scheduler.monthly import next_monthly
assert next_monthly(date(2026,1,31),31)==date(2026,2,28)
print('PUBLIC OK')
