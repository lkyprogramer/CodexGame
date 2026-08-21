from datetime import date
def next_monthly(after,day):
 month=after.month+1;year=after.year
 if month==13:month=1;year+=1
 return date(year,month,day)
