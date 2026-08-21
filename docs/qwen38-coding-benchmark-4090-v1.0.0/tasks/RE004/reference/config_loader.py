import json
from pathlib import Path
from defaults import DEFAULTS
_KEYS=set(DEFAULTS)
def _bool(v):
 if isinstance(v,bool):return v
 if isinstance(v,str):
  x=v.strip().lower()
  if x in {'true','1','yes'}:return True
  if x in {'false','0','no'}:return False
 raise ValueError('invalid bool')
def _convert(k,v):
 if k=='host':
  if not isinstance(v,str) or not v.strip():raise ValueError('invalid host')
  return v.strip()
 if k in {'port','workers'}:
  if isinstance(v,bool):raise ValueError('invalid int')
  try:n=int(v)
  except (TypeError,ValueError) as e:raise ValueError('invalid int') from e
  if str(v).strip()!=str(n) and not isinstance(v,int):raise ValueError('non-canonical int')
  if k=='port' and not 1<=n<=65535:raise ValueError('port range')
  if k=='workers' and not 1<=n<=128:raise ValueError('workers range')
  return n
 if k=='debug':return _bool(v)
 if k=='tags':
  if isinstance(v,str):items=[x.strip() for x in v.split(',') if x.strip()]
  elif isinstance(v,list) and all(isinstance(x,str) and x.strip() for x in v):items=[x.strip() for x in v]
  else:raise ValueError('invalid tags')
  return items
 raise ValueError('unknown key')
def _validated(source):
 if not isinstance(source,dict):raise ValueError('config source must be object')
 unknown=set(source)-_KEYS
 if unknown:raise ValueError('unknown keys: '+','.join(sorted(unknown)))
 return {k:_convert(k,v) for k,v in source.items()}
def load_config(path,env,cli):
 result=dict(DEFAULTS)
 if path:
  try:data=json.loads(Path(path).read_text(encoding='utf-8'))
  except Exception as e:raise ValueError('invalid config file') from e
  result.update(_validated(data))
 env_data={k[4:].lower():v for k,v in dict(env).items() if k.startswith('APP_')}
 result.update(_validated(env_data));result.update(_validated(dict(cli)))
 return {k:_convert(k,v) for k,v in result.items()}
