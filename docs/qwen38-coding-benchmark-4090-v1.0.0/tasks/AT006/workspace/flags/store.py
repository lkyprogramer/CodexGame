class Store:
 def __init__(self,data):self.data=data;self.reads=0
 def get(self,tenant,name):self.reads+=1;return self.data[(tenant,name)]
