import json
from defaults import DEFAULTS
def load_config(path,env,cli):
 c=DEFAULTS
 if path:c.update(json.load(open(path)))
 c.update(cli)
 return c
