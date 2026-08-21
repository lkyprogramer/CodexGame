from app.config import resolve
out=resolve({'debug':True},{},{'debug':False})
assert out['debug'] is False,out
print('PUBLIC OK')
