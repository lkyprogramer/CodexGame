import math, unittest
from intervals import merge_intervals

class Tests(unittest.TestCase):
    def test_overlap(self): self.assertEqual(merge_intervals([(5,7),(1,4),(3,6)]), [(1,7)])
    def test_touching_default_separate(self): self.assertEqual(merge_intervals([(1,2),(2,3)]), [(1,2),(2,3)])
    def test_touching_enabled(self): self.assertEqual(merge_intervals([(1,2),(2,3)], merge_touching=True), [(1,3)])
    def test_points_and_nested(self): self.assertEqual(merge_intervals([(1,5),(2,3),(8,8)]), [(1,5),(8,8)])
    def test_input_unchanged(self):
        source=[[2,3],[1,2]]; merge_intervals(source); self.assertEqual(source, [[2,3],[1,2]])
    def test_invalid(self):
        values = [[(3,2)], [(True,2)], [(1,math.inf)], [(1,2,3)], ["12"]]
        for value in values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError): merge_intervals(value)
if __name__ == '__main__': unittest.main()
