from .config import resolve
def build(args,env,file_cfg):return resolve(file_cfg,env,vars(args))
