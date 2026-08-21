class MemoryStore:
 def __init__(self):self.processed=set()
 def contains(self,event_id):return event_id in self.processed
 def add(self,event_id):self.processed.add(event_id)
