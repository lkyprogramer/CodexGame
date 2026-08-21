from plugin import Spec
class PluginRegistry:
 def __init__(self):self.specs={};self.instances={}
 def register(self,name,factory,dependencies=()):
  if not isinstance(name,str) or not name.strip() or not callable(factory):raise ValueError('invalid plugin')
  name=name.strip()
  if name in self.specs:raise ValueError('duplicate plugin')
  deps=tuple(dependencies)
  if any(not isinstance(x,str) or not x.strip() for x in deps) or len(set(deps))!=len(deps):raise ValueError('invalid dependencies')
  self.specs[name]=Spec(name,factory,tuple(x.strip() for x in deps))
 def resolve_order(self):
  missing=sorted({d for s in self.specs.values() for d in s.dependencies if d not in self.specs})
  if missing:raise ValueError('missing dependencies: '+', '.join(missing))
  remaining=set(self.specs);order=[]
  while remaining:
   ready=sorted(n for n in remaining if not (set(self.specs[n].dependencies)&remaining))
   if not ready:raise ValueError('cycle or blocked: '+', '.join(sorted(remaining)))
   order.extend(ready);remaining.difference_update(ready)
  return order
 def start_all(self):
  order=self.resolve_order();started=dict(self.instances)
  for name in order:
   if name in started:continue
   try:started[name]=self.specs[name].factory()
   except Exception:
    self.instances={k:v for k,v in started.items() if k in self.instances}
    raise
  self.instances=started;return dict(started)
