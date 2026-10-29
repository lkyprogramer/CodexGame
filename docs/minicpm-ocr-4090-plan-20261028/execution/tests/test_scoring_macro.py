import unittest

from ocrbench.scoring import SCORER_VERSION, score_page, summarize


def score(pid, family, edits=0, groups=1, *, partial=False, verified=True, status='PASS', predicted_family=None):
    gt = {'page_id':pid, 'source_family_id':family, 'acceptance_rule_id':'page-good-v1',
          'GT_version':'human-fixture-v1' if verified else '', 'scorer_version':SCORER_VERSION,
          'unit_kind':'page', 'required_tasks':['text'], 'critical_assertions':[],
          'required_output_units':['raw_text'], 'GT_complete_for_required_tasks':not partial,
          'required_text_groups':[{'id':str(i), 'profile':'printed_chinese', 'text':'甲'*100,
                                   'prediction_field':'raw_text'} for i in range(groups)],
          'provenance':{'kind':'human_verified'}, 'applicability':{}}
    pred = {'page_id':pid, 'status':status, 'raw_text':'甲'*(100-edits)+'乙'*edits}
    if predicted_family is not None:
        pred['source_family_id'] = predicted_family
    return score_page(pred, gt)


def aggregate(rows):
    return summarize(rows, 1)['units']['page']


class ScoringMacroTest(unittest.TestCase):
    def test_groups_first_collapse_to_unit_before_family(self):
        result = aggregate([score('p1', 'A', groups=2), score('p2', 'A', edits=10)])
        self.assertAlmostEqual(result['unit_macro_CER'], .05)
        self.assertAlmostEqual(result['family_macro_CER'], .05)
        self.assertAlmostEqual(result['macro_CER'], .05)
        self.assertAlmostEqual(result['text_group_macro_CER_diagnostic'], .1/3)
        self.assertAlmostEqual(result['micro_CER'], 10/300)
        self.assertEqual(result['macro_unit_count'], 2)
        # Within one unit, unequal group lengths also use character weighting.
        row = score('within-unit', 'A', groups=2)
        row['text_groups'][0].update(gt_characters=10, edit_count=1, strict_CER=.1)
        row['text_groups'][1].update(gt_characters=90, edit_count=0, strict_CER=0)
        weighted = aggregate([row])
        self.assertAlmostEqual(weighted['unit_macro_CER'], .01)
        self.assertAlmostEqual(weighted['text_group_macro_CER_diagnostic'], .05)

    def test_family_balance_is_not_page_or_character_weighting(self):
        result = aggregate([score('a1', 'A'), score('a2', 'A'), score('b1', 'B', edits=100)])
        self.assertAlmostEqual(result['unit_macro_CER'], 1/3)
        self.assertAlmostEqual(result['macro_CER'], .5)
        self.assertEqual(result['macro_family_count'], 2)
        self.assertEqual(result['family_macro_components']['A']['unit_count'], 2)

    def test_missing_family_never_falls_back_to_page_mean(self):
        result = aggregate([score('known', 'A'), score('unknown', None, edits=10)])
        self.assertAlmostEqual(result['unit_macro_CER'], .05)
        self.assertIsNone(result['macro_CER'])
        self.assertIsNone(result['family_macro_CER'])
        self.assertEqual(result['family_macro_status'], 'UNAVAILABLE_UNKNOWN_SOURCE_FAMILY')
        self.assertEqual(result['macro_unknown_family_unit_count'], 1)
        self.assertEqual(result['source_family_coverage']['submitted']['unknown_family_units'], 1)

    def test_family_sources_are_explicit_and_conflict_is_visible(self):
        matched = score('p1', 'A', predicted_family='A')
        self.assertEqual(matched['source_family_id'], 'A')
        self.assertEqual(matched['source_family_status'], 'REFERENCE_AND_PREDICTION_MATCH')
        prediction_only = score('p2', None, predicted_family='B')
        self.assertEqual(prediction_only['source_family_id'], 'B')
        self.assertEqual(prediction_only['source_family_status'], 'PREDICTION_ONLY')
        conflict = score('p3', 'A', predicted_family='B')
        self.assertIsNone(conflict['source_family_id'])
        self.assertEqual(conflict['source_family_status'], 'CONFLICT')
        result = aggregate([conflict])
        self.assertIsNone(result['macro_CER'])
        self.assertEqual(result['micro_CER'], 0)  # Family conflict changes aggregation eligibility, not text edits.

    def test_partial_structure_keeps_verified_text_but_draft_is_excluded(self):
        partial = score('partial', 'A', edits=10, partial=True)
        self.assertTrue(partial['text_reference_verified'])
        self.assertFalse(partial['GT_complete'])
        result = aggregate([partial, score('draft', 'B', edits=100, verified=False)])
        self.assertAlmostEqual(result['macro_CER'], .1)
        self.assertEqual(result['macro_unit_count'], 1)
        self.assertEqual(result['text_reference_verified_units'], 1)
        self.assertEqual(result['source_family_coverage']['submitted']['unit_count'], 2)
        self.assertIsNone(result['primary_good_units_per_second'])

    def test_failed_prediction_stays_empty_and_blank_only_has_no_CER(self):
        failed = score('failed', 'A', status='FAIL')
        result = aggregate([failed])
        self.assertEqual(result['macro_CER'], 1)
        self.assertEqual(result['unit_macro_CER'], 1)
        self.assertEqual(result['micro_CER'], 1)
        blank_gt = {'page_id':'blank', 'source_family_id':'B', 'acceptance_rule_id':'page-good-v1',
                    'GT_version':'human-fixture-v1', 'scorer_version':SCORER_VERSION, 'unit_kind':'page',
                    'required_tasks':['text'], 'required_text_groups':[{'id':'blank', 'profile':'printed_chinese', 'text':''}],
                    'required_output_units':['raw_text'], 'critical_assertions':[], 'GT_complete_for_required_tasks':True,
                    'provenance':{'kind':'human_verified'}, 'applicability':{}}
        blank = score_page({'page_id':'blank', 'status':'PASS', 'raw_text':'幻觉'}, blank_gt)
        only_blank = aggregate([blank])
        self.assertIsNone(only_blank['macro_CER'])
        self.assertIsNone(only_blank['unit_macro_CER'])
        self.assertEqual(only_blank['verified_blank_only_units'], 1)
        self.assertEqual(only_blank['edit_count'], 2)
        self.assertEqual(only_blank['family_macro_status'], 'UNAVAILABLE_NO_NONEMPTY_VERIFIED_REFERENCE')


if __name__ == '__main__':
    unittest.main()
