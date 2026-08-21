from plugin import Spec
class PluginRegistry:
 def __init__(self):self.specs={};self.instances={}
 def register(self,name,factory,dependencies=()):self.specs[name]=Spec(name,factory,tuple(dependencies))
 def resolve_order(self):return list(self.specs)
 def start_all(self):
  for n in self.resolve_order():self.instances[n]=self.specs[n].factory()
  return self.instances
