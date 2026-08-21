import unittest
from dag import topological_layers
class Tests(unittest.TestCase):
    def test_layers(self):
        graph={'deploy':{'test'},'test':{'build'},'lint':set(),'build':set()}
        self.assertEqual(topological_layers(graph), [['build','lint'],['test'],['deploy']])
    def test_disconnected(self): self.assertEqual(topological_layers({'b':set(),'a':set()}), [['a','b']])
    def test_unknown(self):
        with self.assertRaisesRegex(ValueError,'missing'): topological_layers({'a':{'missing'}})
    def test_cycle_lists_nodes(self):
        with self.assertRaises(ValueError) as ctx: topological_layers({'a':{'b'},'b':{'a'},'c':{'a'}})
        self.assertIn('a',str(ctx.exception)); self.assertIn('b',str(ctx.exception)); self.assertIn('c',str(ctx.exception))
    def test_input_unchanged(self):
        graph={'a':set(),'b':{'a'}}; before={k:set(v) for k,v in graph.items()}; topological_layers(graph); self.assertEqual(graph,before)
if __name__=='__main__': unittest.main()
