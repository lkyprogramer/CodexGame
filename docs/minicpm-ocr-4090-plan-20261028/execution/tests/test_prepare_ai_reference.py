import tempfile
import hashlib
import json
from io import BytesIO
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from prepare_ai_reference import draft, check_original_identity, reconstruct_page, generate_full_pages
from ocrbench.scoring import score_page


class ReferenceDraftTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'input.png'
        Image.new('RGB',(8,4),'white').save(self.path)
    def tearDown(self): self.temp.cleanup()

    def test_clear_text_stays_DRAFT_and_cannot_be_accepted_by_scorer(self):
        p=draft('x',self.path,{'text_layer_raw':'text','text_nfkc':'WRONG'},[],'f',category='printed_line')
        self.assertEqual(p['required_text_groups'][0]['text'],'text')
        self.assertTrue(p['proposed_approval']['exact_text_eligible'])
        self.assertFalse(p['GT_complete_for_required_tasks'])
        self.assertEqual(p['reference_provenance']['review_status'],'pending_root_approval')
        result=score_page({'page_id':'x','status':'PASS','raw_text':'text','input_pixel_hash':p['image_identity']['input_pixel_hash']},p)
        self.assertIsNone(result['is_good'])
        self.assertFalse(result['text_reference_verified'])

    def test_only_explicit_resolved_root_line_decision_replaces_marker(self):
        ref={'root_adjudicated_line':{'text':'〔圆/园〕满'},'line_reference':{'line_id':'L03'},
             'document_uncertainties':[{'line_id':3,'resolved':True,'root_decision':'圆'}]}
        p=draft('x',self.path,ref,[],'f',category='handwriting_line')
        self.assertEqual(p['required_text_groups'][0]['text'],'圆满')
        self.assertEqual(len(p['reference_transforms']),1)
        self.assertTrue(p['proposed_approval']['exact_text_eligible'])
        ref['document_uncertainties'][0]['resolved']=False
        p=draft('x',self.path,ref,[],'f',category='handwriting_line')
        self.assertFalse(p['proposed_approval']['exact_text_eligible'])

    def test_partial_full_essay_and_formula_are_not_exact(self):
        p=draft('x',self.path,{'reference_text':'body'},[],'f',unit='long_image',category='essay_full')
        self.assertFalse(p['proposed_approval']['exact_text_eligible'])
        f=draft('x',self.path,{'reference_text':'A=x²','formula_latex':['x^2']},[],'f',category='formula')
        self.assertFalse(f['proposed_approval']['complete_required_reference_eligible'])
        self.assertTrue(f['applicability']['formula'])
        self.assertIn('FORMULA_RENDER_AND_SEMANTIC_VALIDATION_PENDING',f['proposed_approval']['reasons'])

    def test_complete_table_reference_has_no_fabricated_model_matching(self):
        p=draft('x',self.path,{'table_html':'<table><tr><td>A</td></tr></table>'},[],'f',category='table')
        self.assertTrue(p['proposed_approval']['complete_required_reference_eligible'])
        self.assertEqual(p['required_tasks'],['table'])
        self.assertNotIn('assessment',p)
        self.assertFalse(p['GT_complete_for_required_tasks'])

    def test_changed_source_reference_hash_rejected(self):
        item=draft('x',self.path,{'reference_text':'A'},[],'f')
        with self.assertRaises(ValueError):
            check_original_identity({'source_image_sha256':'f'*64},item)
        check_original_identity({'source_image_sha256':item['image_identity']['source_image_sha256']},item)


class FullPageDraftTest(unittest.TestCase):
    def fixture(self,base,page_id):
        full=Image.new('RGB',(4,4),'white');tiles=[]
        for number,bbox in enumerate([(0,0,4,3),(0,1,4,4)]):
            path=base/f'{page_id}-{number}.png';image=full.crop(bbox);image.save(path)
            tiles.append({'path':str(path),'bbox_xyxy':bbox,'dimensions':list(image.size),
                'file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'pixel_sha256':hashlib.sha256(image.tobytes()).hexdigest()})
        return {'page_id':page_id,'document_id':page_id,'source_family_id':'fixture',
                'dimensions':[4,4],'pixel_sha256':hashlib.sha256(full.tobytes()).hexdigest(),
                'tiles':tiles,'kind':'pdf','source_asset_sha256':'d'*64}

    def test_reconstruction_matches_pixels_and_real_PNG_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);case=self.fixture(base,'p')
            encoded,pixels=reconstruct_page(case,base)
            with Image.open(BytesIO(encoded)) as image:
                self.assertEqual(hashlib.sha256(image.convert('RGB').tobytes()).hexdigest(),pixels)
            case['tiles'][1]['bbox_xyxy']=[0,2,4,4]
            with self.assertRaises(ValueError):reconstruct_page(case,base)

    def test_full_page_draft_separates_text_coverage_from_structure(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);(base/'references').mkdir();(base/'full-page-audit').mkdir()
            cases=[self.fixture(base,f'p{i}') for i in range(3)]
            (base/'full-page-audit/manifest.json').write_text(json.dumps({'pages':cases}))
            names=['full-audit-pdf1-pdf3.json','full-audit-pdf2.json','full-audit-papers.json']
            for i,name in enumerate(names):
                ref={'page_id':f'p{i}','input_pixel_hash':cases[i]['pixel_sha256'],
                    'reference_text':'checked text' if i<2 else None,
                    'reference_text_complete_for_visible_text':i<2,'candidate_outputs_read':False}
                (base/'references'/name).write_text(json.dumps({'pages':[ref],'candidate_outputs_read':False}))
            out=base/'out';summary=generate_full_pages(base,out)
            self.assertEqual(summary['linear_text_candidates'],2)
            self.assertEqual(summary['partial_reference_pages'],1)
            rows=json.loads((out/'full-page-gt-draft.json').read_text())['pages']
            for row in rows:
                self.assertFalse(row['GT_complete_for_required_tasks'])
                self.assertTrue(row['applicability']['reading_order'])
                self.assertNotIn('source_sha256',row['reference_provenance'])
                self.assertNotEqual(row['reference_provenance']['source_image_sha256'],'d'*64)
                self.assertEqual(row['reference_provenance']['review_status'],'pending_root_approval')
            approved=rows[0]
            approved['reference_provenance'].update(kind='ai_verified',judge_id='root',review_status='accepted')
            scored=score_page({'page_id':'p0','status':'PASS','raw_text':'checked text','ordered_blocks':[],
                               'input_pixel_hash':cases[0]['pixel_sha256']},approved)
            self.assertTrue(scored['text_reference_verified'])
            self.assertIsNone(scored['is_good'])


if __name__=='__main__':unittest.main()
