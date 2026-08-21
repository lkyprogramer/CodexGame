from .defaults import DEFAULTS

def resolve(file_cfg,env_cfg,cli_cfg):
 result=dict(DEFAULTS)
 for source in (file_cfg,env_cfg,cli_cfg):
  if source is None:continue
  unknown=set(source)-set(DEFAULTS)
  if unknown:raise ValueError('unknown config: '+','.join(sorted(unknown)))
  for key,value in source.items():
   if value is not None:result[key]=value
 return result
