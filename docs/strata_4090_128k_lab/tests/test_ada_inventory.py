import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / 'tools/v027/ada_inventory.py'
spec = importlib.util.spec_from_file_location('ada_inventory_tested', PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class AdaInventoryTests(unittest.TestCase):
    def test_cpp_comments_and_trailing_commas(self):
        source = 'constexpr X foo[] = { // hi\n{12, {{0,1,2,4,0}, {1,1,1,1,1}, {0,0,0,0,0}}}, };'
        self.assertEqual(m.parse_table(source, 'foo')[12][0], [0, 1, 2, 4, 0])
        with self.assertRaisesRegex(ValueError, 'TABLE_NOT_FOUND'):
            m.parse_table(source, 'bar')

    def test_duplicate_table_type_rejected(self):
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_TYPE'):
            m.parse_table('x foo[]={{1,{0}},{1,{1}}};', 'foo')

    def test_class_boundaries(self):
        self.assertEqual([m.row_class(x) for x in [512,2047,2048,4095,4096,8191,8192,12287,12288,248320]],
                         [0,0,1,1,2,2,3,3,4,4])

    def test_one_and_wide_routes(self):
        table={11:[[4]*5]*3}; single={11:[0,0,1,1,1]}
        self.assertEqual(m.rows_for(table,single,11,1,6144),1)
        self.assertEqual(m.rows_for(table,{},11,1,6144),0)
        self.assertEqual(m.rows_for(table,single,11,5,6144),0)
        self.assertEqual(m.rows_for(table,single,21,3,6144),0)

    def test_old_zero_candidate_is_reused(self):
        self.assertEqual(m.classification(1,0,0),'changed_but_old_candidate_reused')
        self.assertEqual(m.classification(1,1,0),'unchanged')
        self.assertEqual(m.classification(2,1,4),'changed_not_covered_by_old_override')

    def test_bad_or_duplicate_override_rejected(self):
        with self.assertRaisesRegex(ValueError,'INVALID_OVERRIDE'):
            m.parse_old_override('STRATA_MMVQ_IL_ROWS=12:2:0,0,0,0,3')
        with self.assertRaisesRegex(ValueError,'DUPLICATE_OVERRIDE'):
            m.parse_old_override('STRATA_MMVQ_IL_ROWS=12:2:0,0,0,0,0;12:2:1,1,1,1,1')


if __name__ == '__main__':
    unittest.main()
