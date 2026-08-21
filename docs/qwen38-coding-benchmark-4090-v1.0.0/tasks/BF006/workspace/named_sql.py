import re
def compile_named(sql,params):
    names=re.findall(r':(\w+)',sql)
    return re.sub(r':\w+','?',sql),[params[n] for n in names]
