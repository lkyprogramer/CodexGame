import calendar
from datetime import date

def next_monthly(after,day):
 if not isinstance(after,date) or isinstance(after,type) or not isinstance(day,int) or isinstance(day,bool) or not 1<=day<=31:raise ValueError('invalid input')
 year,month=after.year,after.month
 candidate=date(year,month,min(day,calendar.monthrange(year,month)[1]))
 if candidate<=after:
  month+=1
  if month==13:year+=1;month=1
  candidate=date(year,month,min(day,calendar.monthrange(year,month)[1]))
 return candidate
