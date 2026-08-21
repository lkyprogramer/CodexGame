import hashlib
from .model import FlagConfig
def is_enabled(user_id,config,overrides=None):
 if not isinstance(user_id,str) or not user_id or not isinstance(config,FlagConfig) or not config.name or not config.salt or isinstance(config.basis_points,bool) or not 0<=config.basis_points<=10000:raise ValueError('invalid input')
 if overrides is None:overrides={}
 if not isinstance(overrides,dict) or any(not isinstance(k,str) or not isinstance(v,bool) for k,v in overrides.items()):raise ValueError('invalid overrides')
 if user_id in overrides:return overrides[user_id]
 raw=f'{config.salt}:{config.name}:{user_id}'.encode('utf-8');bucket=int.from_bytes(hashlib.sha256(raw).digest()[:8],'big')%10000
 return bucket<config.basis_points
