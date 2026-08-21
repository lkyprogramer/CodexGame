from .defaults import DEFAULTS
def resolve(file_cfg,env_cfg,cli_cfg):
 return {k:cli_cfg.get(k) or env_cfg.get(k) or file_cfg.get(k) or v for k,v in DEFAULTS.items()}
