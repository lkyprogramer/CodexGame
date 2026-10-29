import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ocrbench.scoring import SCORER_VERSION, distance, score_page, summarize, text_metrics


def gold(text='你好', profile='printed_chinese'):
    return dict(page_id='p1', acceptance_rule_id='page-good-v1', GT_version='human-v1',
                scorer_version=SCORER_VERSION, unit_kind='page', required_tasks=['text'],
                required_text_groups=[dict(id='full', profile=profile, text=text)],
                required_output_units=['raw_text'], critical_assertions=[],
                GT_complete_for_required_tasks=True, provenance={'kind': 'human_verified'},
                applicability={k: False for k in ('text_blocks', 'table', 'formula', 'reading_order', 'style', 'resources')})


class ScoringTest(unittest.TestCase):
    def test_edit_and_unicode(self):
        self.assertEqual(distance('kitten', 'sitting'), 3)
        m = text_metrics('é 甲', 'e\u0301  甲')
        self.assertGreater(m['strict_CER'], 0)
        self.assertEqual(m['NFC_whitespace_CER'], 0)
        self.assertNotEqual(text_metrics('１', '1')['NFC_whitespace_CER'], 0)

    def test_complete_text_success(self):
        p = score_page({'page_id': 'p1', 'status': 'PASS', 'raw_text': '你好'}, gold())
        self.assertIs(p['is_good'], True)

    def test_failed_output_scores_deletions(self):
        p = score_page({'page_id': 'p1', 'status': 'FAIL', 'raw_text': '你好'}, gold())
        self.assertIs(p['is_good'], False)
        self.assertEqual(p['text_groups'][0]['strict_CER'], 1)

    def test_missing_gt_and_draft(self):
        p = {'page_id': 'p1', 'status': 'PASS', 'raw_text': '你好'}
        self.assertIsNone(score_page(p, None)['is_good'])
        g = gold(); g['provenance']['kind'] = 'pdf_extracted_draft'
        r = score_page(p, g)
        self.assertIsNone(r['is_good'])
        self.assertIsNone(summarize([r], 10)['units']['page']['primary_good_units_per_second'])

    def test_blank_hallucination_and_critical(self):
        p = {'page_id': 'p1', 'status': 'PASS', 'raw_text': '答案'}
        self.assertIs(score_page(p, gold(''))['is_good'], False)
        g = gold('答案'); g['critical_assertions'] = [dict(id='name', operation='contains', value='王')]
        self.assertIs(score_page(p, g)['is_good'], False)

    def test_structure_missing_not_fabricated(self):
        g = gold(); g['applicability']['table'] = True
        r = score_page({'page_id': 'p1', 'status': 'PASS', 'raw_text': '你好'}, g)
        self.assertIsNone(r['is_good'])
        self.assertEqual(r['structural_metrics']['table']['status'], 'UNAVAILABLE')
        g['required_output_units'].append('table_html')
        self.assertIs(score_page({'page_id': 'p1', 'status': 'PASS', 'raw_text': '你好'}, g)['is_good'], False)

    def test_corpus_average_not_page_acceptance(self):
        pages = []
        for i in range(100):
            g = gold('甲' * 100); g['page_id'] = str(i)
            p = dict(page_id=str(i), status='PASS', raw_text='甲' * (100 if i < 90 else 90))
            pages.append(score_page(p, g))
        r = summarize(pages, 100)['units']['page']
        self.assertEqual(r['micro_CER'], .01)
        self.assertEqual(r['good_count'], 90)
        self.assertEqual(r['primary_good_units_per_second'], .9)
        z = summarize([score_page({'page_id': 'p1', 'status': 'FAIL'}, gold())], 10, 1)['units']['page']
        self.assertEqual(z['primary_good_units_per_second'], 0)
        self.assertIsNone(z['J_per_good_unit'])
        self.assertEqual(z['energy_reason'], 'NO_GOOD_PAGES')

    def test_cli_fixed_gt_missing_prediction(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / 'pred.json').write_text(json.dumps({'pages': []}))
            (d / 'gt.json').write_text(json.dumps({'pages': [gold()]}))
            subprocess.run([sys.executable, '-m', 'ocrbench.scoring', '--predictions', str(d/'pred.json'), '--gt', str(d/'gt.json'), '--wall-seconds', '1', '--out', str(d/'out.json')], cwd=Path(__file__).resolve().parents[1], check=True)
            r = json.loads((d/'out.json').read_text())
            self.assertEqual(r['pages'][0]['text_groups'][0]['edit_count'], 2)
            self.assertEqual(r['units']['page']['submitted_count'], 1)

class StructureTest(unittest.TestCase):
    def test_table_text_structure_and_spans(self):
        from ocrbench.scoring import table_metrics
        a = '<table><tr><td colspan="2">甲乙</td></tr></table>'
        b = '<table><tr><td>甲</td><td>乙</td></tr></table>'
        self.assertEqual(table_metrics(a, a)['TEDS'], 1.)
        self.assertLess(table_metrics(a, b)['TEDS_struct'], 1.)
        self.assertGreater(table_metrics(a, b)['cell_CER'], 0.)
        c = '<table><tr><td colspan="2">甲丙</td></tr></table>'
        m = table_metrics(a, c)
        self.assertEqual(m['TEDS_struct'], 1.)
        self.assertLess(m['TEDS'], 1.)
        self.assertEqual(m['cell_CER'], .5)
        self.assertFalse(table_metrics(a, '<table>')['HTML_valid'])

    def test_bound_matching_recall_order_and_missing_table(self):
        from ocrbench.scoring import structural_scores, prediction_digest
        p = {'page_id': 'p1', 'status': 'PASS', 'raw_text': '甲乙', 'ordered_blocks': [
            {'raw_text': '乙'}, {'raw_text': '甲'}]}
        g = gold('甲乙')
        g['applicability'].update(text_blocks=True, reading_order=True, table=True)
        g['structure_GT'] = {'text_blocks': [{'id':'a','critical':True},{'id':'b'},{'id':'missing'}],
            'reading_order':[{'before':'a','after':'b','severe':True}],
            'table':[{'id':'t','html':'<table><tr><td>字</td></tr></table>'}]}
        g['assessment'] = {'kind':'human_verified_correspondence', 'prediction_sha256':prediction_digest(p),
                           'matches':{'a':1,'b':0,'t':None,'missing':None}}
        r = structural_scores(p,g)
        self.assertEqual(r['text_blocks']['recall'], 2/3)
        self.assertEqual(r['reading_order']['pair_accuracy'], 0.)
        self.assertEqual(r['table']['TEDS'], 0.)
        self.assertIs(score_page(p,g)['is_good'], False)
        p['raw_text'] = 'changed'
        self.assertEqual(structural_scores(p,g)['table']['status'], 'UNAVAILABLE')

    def test_rowspan_and_extra_predicted_table(self):
        from ocrbench.scoring import table_metrics, structural_scores, prediction_digest
        html = '<table><tr><th rowspan="2">A</th><td>B</td></tr><tr><td>C</td></tr></table>'
        self.assertEqual(table_metrics(html, html)['cell_CER'], 0)
        p = {'ordered_blocks': [{'table_html': html}, {'table_html': html}]}
        g = gold(); g['applicability']['table'] = True
        g['structure_GT'] = {'table': [{'id':'t','html':html}]}
        g['assessment'] = {'kind':'human_verified_correspondence', 'prediction_sha256':prediction_digest(p), 'matches':{'t':0}}
        metrics = structural_scores(p,g)['table']
        self.assertEqual(metrics['TEDS'], 1.)
        self.assertEqual(metrics['unmatched_predicted_table_indices'], [1])
        self.assertFalse(metrics['passes'])

    def test_invalid_matching_rejected_and_resources_complete(self):
        from ocrbench.scoring import structural_scores, prediction_digest
        p = {'ordered_blocks':[{'raw_text':'A'}]}
        g = gold(); g['applicability']['resources'] = True
        g['structure_GT'] = {'resources':[{'id':'r'}]}
        g['assessment'] = {'kind':'human_verified_correspondence','prediction_sha256':prediction_digest(p),
                           'matches':{'a':0,'b':0}}
        with self.assertRaises(ValueError):
            structural_scores(p,g)
        g['assessment']['matches'] = {}
        g['assessment']['resources_assertions'] = [{'id':'r','passes':True}]
        self.assertTrue(structural_scores(p,g)['resources']['passes'])
        g['assessment']['resources_assertions'] = [{'id':'wrong','passes':True}]
        self.assertEqual(structural_scores(p,g)['resources']['status'], 'UNAVAILABLE')

    def test_empty_versions_and_global_GT_gate(self):
        prediction = {'page_id':'p1','status':'PASS','raw_text':'你好'}
        for field in ('GT_version','acceptance_rule_id','scorer_version'):
            for value in (None, '', '  ', 1):
                g=gold();g[field]=value
                result=score_page(prediction,g)
                self.assertIsNone(result['is_good'])
                self.assertFalse(result['GT_complete'])
        valid=score_page(prediction,gold())
        unknown=score_page({'page_id':'extra','status':'PASS','raw_text':'extra'},None)
        result=summarize([valid,unknown],1)
        self.assertFalse(result['full_workload_GT_complete'])
        self.assertIsNone(result['units']['page']['primary_good_units_per_second'])
        self.assertEqual(result['units']['page']['diagnostic_known_good_units_per_second'],1)


class AIReferenceTest(unittest.TestCase):
    def reference(self):
        g=gold();g['acceptance_rule_id']='page-good-ai-v1';g.pop('provenance')
        g['reference_provenance']={'kind':'ai_verified','judge_id':'root-blind',
            'source_image_sha256':'a'*64,'input_pixel_hash':'b'*64,'source_sha256':'c'*64,
            'review_status':'accepted','review_evidence':[{'path':'private/review.json','sha256':'d'*64}]}
        return g

    def prediction(self):
        return {'page_id':'p1','status':'PASS','raw_text':'你好', 'input_pixel_hash':'b'*64,'source_sha256':'c'*64}

    def test_AI_reference_separate_rule_and_pdf_image_identity(self):
        result=score_page(self.prediction(),self.reference())
        self.assertTrue(result['is_good'])
        self.assertEqual(result['reference_kind'],'AI_JUDGED')
        # Original PDF bytes intentionally differ from rendered judge image bytes.
        self.assertEqual(summarize([result],1)['reference_kinds'],['AI_JUDGED'])
        g=self.reference();g['acceptance_rule_id']='page-good-v1'
        self.assertIsNone(score_page(self.prediction(),g)['is_good'])
        self.assertTrue(score_page({'page_id':'p1','status':'PASS','raw_text':'你好'},gold())['is_good'])

    def test_AI_missing_review_provenance(self):
        for field in ('judge_id','source_image_sha256','review_status','review_evidence'):
            g=self.reference();g['reference_provenance'].pop(field)
            r=score_page(self.prediction(),g)
            self.assertIsNone(r['is_good'])
            self.assertFalse(r['GT_complete'])

    def test_AI_unresolved_uncertainty_and_pixel_mismatch(self):
        g=self.reference();g['uncertainties']=[{'resolved':False,'affects_required_tasks':True}]
        self.assertIsNone(score_page(self.prediction(),g)['is_good'])
        g['uncertainties'][0]['resolved']=True
        self.assertTrue(score_page(self.prediction(),g)['is_good'])
        g['reference_provenance']['input_pixel_hash']='e'*64
        self.assertFalse(score_page(self.prediction(),g)['is_good'])

    def test_AI_requires_actual_input_pixel_binding(self):
        g=self.reference();g['reference_provenance'].pop('input_pixel_hash')
        p=self.prediction();p['input_pixel_hash']='f'*64
        r=score_page(p,g)
        self.assertIsNone(r['is_good'])
        self.assertFalse(r['text_reference_verified'])
        g=self.reference();g['acceptance_rule_id']='page-good-v1';g['provenance']={'kind':'human_verified'}
        r=score_page(self.prediction(),g)
        self.assertIsNone(r['is_good'])
        self.assertFalse(r['text_reference_verified'])

    def test_unresolved_reference_excluded_from_CER_but_structure_gap_not_text(self):
        g=self.reference();g['uncertainties']=[{'resolved':False,'affects_required_tasks':True}]
        p=self.prediction();p['raw_text']='错误'
        r=score_page(p,g)
        stats=summarize([r],1)['units']['page']
        self.assertIsNone(stats['micro_CER'])
        self.assertEqual(stats['gt_characters'],0)
        self.assertEqual(stats['text_reference_verified_units'],0)
        self.assertEqual(stats['unverified_text_diagnostics'][0]['strict_CER'],1)
        g=self.reference();g['applicability']['formula']=True
        r=score_page(self.prediction(),g)
        self.assertIsNone(r['is_good'])
        self.assertTrue(r['text_reference_verified'])
        self.assertEqual(summarize([r],1)['units']['page']['micro_CER'],0)

    def test_human_AI_reference_metrics_are_stratified(self):
        a=score_page(self.prediction(),self.reference())
        h=score_page({'page_id':'p1','status':'PASS','raw_text':'你好'},gold())
        report=summarize([a,h],1)
        self.assertIsNone(report['units']['page']['micro_CER'])
        self.assertIsNone(report['units']['page']['primary_good_units_per_second'])
        self.assertEqual(report['reference_strata']['AI_JUDGED']['units']['page']['micro_CER'],0)
        self.assertEqual(report['reference_strata']['HUMAN_VERIFIED']['units']['page']['micro_CER'],0)


class TableScoreViewTest(unittest.TestCase):
    def test_presentation_wrappers_and_image_supplement_are_symmetric(self):
        from ocrbench.scoring import table_metrics
        plain='<table><tr><td>测量值</td></tr></table>'
        product='<table><tr><td><img src="assets/cell.png"/><br/><span data-ocr-supplement="true"><strong>测量值</strong></span></td></tr></table>'
        m=table_metrics(plain,product)
        self.assertEqual(m['score_view_version'],'table-score-view-v1')
        self.assertEqual(m['TEDS'],1)
        self.assertEqual(m['TEDS_struct'],1)
        self.assertEqual(m['cell_CER'],0)
        self.assertLess(m['raw_HTML_TEDS'],1)
        self.assertTrue(m['resource_validation_required'])
        self.assertEqual(table_metrics(product,plain)['TEDS'],1)

    def test_visible_missing_text_span_and_semantic_math_still_fail(self):
        from ocrbench.scoring import table_metrics
        plain='<table><tr><td>测量值</td></tr></table>'
        img='<table><tr><td><img src="测量值.png"/></td></tr></table>'
        self.assertEqual(table_metrics(plain,img)['cell_CER'],1)
        span='<table><tr><td colspan="2">测量值</td></tr></table>'
        self.assertLess(table_metrics(plain,span)['TEDS_struct'],1)
        math='<table><tr><td><math><msup><mi>x</mi><mn>2</mn></msup></math></td></tr></table>'
        flat='<table><tr><td>x2</td></tr></table>'
        self.assertLess(table_metrics(math,flat)['TEDS'],1)
        sup='<table><tr><td>x<sup>2</sup></td></tr></table>'
        self.assertLess(table_metrics(sup,flat)['TEDS'],1)

    def test_br_separates_text_without_merging_words_and_resource_gate(self):
        from ocrbench.scoring import table_metrics, structural_scores, prediction_digest
        gt='<table><tr><td>甲\n乙</td></tr></table>'
        product='<table><tr><td>甲<br/>乙<img src="a.png"/></td></tr></table>'
        self.assertEqual(table_metrics(gt,product)['cell_CER'],0)
        self.assertGreater(table_metrics('<table><tr><td>甲乙</td></tr></table>',product)['cell_CER'],0)
        p={'ordered_blocks':[{'table_html':product}]}
        g=gold();g['applicability']['table']=True
        g['structure_GT']={'table':[{'id':'t','html':gt}]}
        g['assessment']={'kind':'human_verified_correspondence','prediction_sha256':prediction_digest(p),'matches':{'t':0}}
        r=structural_scores(p,g)
        self.assertTrue(r['table']['passes'])
        self.assertEqual(r['resources']['status'],'UNAVAILABLE')

    def test_HTML_unquoted_border_optional_cell_endings_and_truncation(self):
        from ocrbench.scoring import table_metrics
        gt='<table><tr><td>甲</td><td>乙</td></tr></table>'
        pred='<table border=1><tr><td>甲<td>乙</table>'
        m=table_metrics(gt,pred)
        self.assertTrue(m['HTML_valid'])
        self.assertEqual(m['TEDS'],1)
        self.assertEqual(m['cell_CER'],0)
        self.assertEqual(m['html_parser_version'],'html5lib-1.1-strict-fragment-v1')
        self.assertFalse(table_metrics(gt,'<table border=1><tr><td>甲<td>乙')['HTML_valid'])
        self.assertFalse(table_metrics(gt,'<table><tr><td>甲</td></tr>')['HTML_valid'])

    def test_HTML_MathML_namespace_survives_canonical_serialization(self):
        from ocrbench.scoring import table_metrics
        gt='<table><tr><td colspan=2><math><msup><mi>x</mi><mn>2</mn></msup></math></td></tr></table>'
        pred='<table border=1><tr><td colspan=2><span><math><msup><mi>x</mi><mn>2</mn></msup></math></span></table>'
        m=table_metrics(gt,pred)
        self.assertEqual(m['TEDS'],1)
        self.assertIn('<msup>',m['prediction_score_view'])
        self.assertIn('colspan="2"',m['prediction_score_view'])
        flat='<table><tr><td colspan=2>x2</table>'
        self.assertLess(table_metrics(gt,flat)['TEDS'],1)
        comment='<table><tr><td colspan=2><!--display note--><math><msup><mi>x</mi><mn>2</mn></msup></math></td></tr></table>'
        self.assertEqual(table_metrics(gt,comment)['TEDS'],1)

    def test_table_outside_comment_tail_cannot_hide_visible_text(self):
        from ocrbench.scoring import table_metrics
        table='<table><tr><td>A</td></tr></table>'
        self.assertFalse(table_metrics(table,table+'<!--note-->extra')['HTML_valid'])
        self.assertFalse(table_metrics(table,'<!--note-->extra'+table)['HTML_valid'])
        self.assertEqual(table_metrics(table,'<!--note-->'+table+'<!--note-->')['TEDS'],1)
        inside='<table><tr><td><!--note-->A</td></tr></table>'
        self.assertEqual(table_metrics(table,inside)['cell_CER'],0)


if __name__ == '__main__':
    unittest.main()
