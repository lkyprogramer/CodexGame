"""Prepare private AI-reference DRAFTS only; never reads candidate OCR outputs or approves GT."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from PIL import Image
from ocrbench.scoring import SCORER_VERSION

VERSION = 'ai-reference-import-draft-v1'
MARKERS = ('□', '〔', '〕', '无法辨认', '不可辨')
STRUCTURES = ('text_blocks','table','formula','reading_order','style','resources')


def load(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def image_identity(path):
    with Image.open(path) as image:
        rgb=image.convert('RGB')
        return {'source_image_sha256':sha(path),'input_pixel_hash':hashlib.sha256(rgb.tobytes()).hexdigest(),
                'width':rgb.width,'height':rgb.height}


def uncertainty_list(reference):
    result=[]
    for key in ('uncertainties','document_uncertainties'):
        for value in reference.get(key,[]):
            item=dict(value)
            item['resolved']=item.get('resolved') is True
            item['affects_required_tasks']=item.get('affects_required_tasks',True)
            result.append(item)
    return result


def draft(page_id, image, reference, evidence, family, unit='crop', category='generic', whole_image=True):
    identity=image_identity(image)
    text=reference.get('reference_text')
    uncertain=uncertainty_list(reference)
    reasons=[]
    transforms=[]
    profile='printed_chinese'
    if category=='handwriting_line':
        text=reference.get('root_adjudicated_line',reference.get('line_reference',{})).get('text',text)
        line_id=reference.get('line_reference',{}).get('line_id')
        def same_line(value):
            left=re.findall(r'\d+',str(value));right=re.findall(r'\d+',str(line_id))
            return bool(left and right and int(left[-1])==int(right[-1]))
        uncertain=[u for u in uncertain if not u.get('line_id') or same_line(u['line_id'])]
        # Only replace literal uncertainty markup by an explicit already-resolved root decision.
        decisions={u.get('root_decision') for u in uncertain if u.get('resolved') is True and isinstance(u.get('root_decision'),str)}
        def replace_marker(match):
            choices={part.strip().rstrip('?？') for part in match.group(1).split('/')}
            matching=decisions & choices
            if len(matching)==1:
                replacement=next(iter(matching));transforms.append({'original':match.group(0),'replacement':replacement,'basis':'EXPLICIT_RESOLVED_ROOT_LINE_DECISION'})
                return replacement
            return match.group(0)
        if isinstance(text,str):text=re.sub(r'〔([^〕]+)〕',replace_marker,text)
        profile='handwritten'
    elif category=='printed_line':
        text=reference.get('text_layer_raw')  # No NFKC folding or semantic repairs.
        profile='technical_zh_en' if text and any('\u4e00'<=c<='\u9fff' for c in text) else 'printed_english'
    elif category=='dataset_text':
        groups=reference.get('required_text_groups',[])
        text=groups[0].get('text') if len(groups)==1 else None
        profile='printed_english'
    elif category=='name':
        profile='handwritten_name'
    elif category=='essay_full':
        profile='handwritten';whole_image=False
        reasons.append('FULL_IMAGE_PRINTED_HEADER_OR_EDGE_GLYPHS_NOT_FULLY_TRANSCRIBED')
    elif category=='seal':
        profile='seal_text'
        coverage=reference.get('coverage','')
        if isinstance(coverage,str) and ('partial' in coverage.lower() or '全文' in coverage):
            whole_image=False
    table=reference.get('table_html')
    if any(not u['resolved'] and u['affects_required_tasks'] for u in uncertain):
        reasons.append('UNRESOLVED_REQUIRED_REFERENCE')
    if text is not None and any(marker in text for marker in MARKERS):
        reasons.append('UNRESOLVED_LITERAL_MARKER_IN_REFERENCE')
    if not whole_image:
        reasons.append('REFERENCE_DOES_NOT_COVER_WHOLE_INPUT')
    text_eligible=isinstance(text,str) and whole_image and not reasons
    if category in ('formula','graph_options','partial_structure'):
        text_eligible=False
        reasons.append('STRUCTURAL_OR_PARTIAL_REFERENCE_NOT_FULL_EXACT_TEXT')
    applicable={key:False for key in STRUCTURES}
    tasks=['text'];outputs=['raw_text'];structure={}
    if table:
        applicable['table']=True;tasks=['table'];outputs=['ordered_blocks']
        structure['table']=[{'id':'table-0','html':table,'critical_assertions':[]}]
        text_eligible=False
    if category=='formula':
        applicable['formula']=True;tasks=['formula'];outputs=['ordered_blocks']
        formulas=reference.get('formula_latex',[])
        if isinstance(formulas,str):formulas=[formulas]
        structure['formula']=[{'id':f'formula-{i}','latex':value} for i,value in enumerate(formulas)]
        reasons.append('FORMULA_RENDER_AND_SEMANTIC_VALIDATION_PENDING')
    if category=='graph_options':
        applicable['reading_order']=True;tasks=['text','reading_order'];reasons.append('GRAPH_RELATIONS_AND_OPTIONS_REQUIRE_SEPARATE_GT')
    proposed_complete=bool(text_eligible or (table and whole_image and not reasons))
    provenance={'kind':'ai_reference_draft','judge_id':'root-review-pending',
        'review_status':'pending_root_approval','review_evidence':evidence,
        'source_image_sha256':identity['source_image_sha256'],'input_pixel_hash':identity['input_pixel_hash']}
    return {'page_id':page_id,'source_family_id':family,'unit_kind':unit,
        'acceptance_rule_id':'page-good-ai-v1','GT_version':VERSION,'scorer_version':SCORER_VERSION,
        'required_tasks':tasks,'required_output_units':outputs,
        'required_text_groups':[{'id':'full','profile':profile,'text':text,'prediction_field':'raw_text'}] if isinstance(text,str) and not table else [],
        'critical_assertions':[],'applicability':applicable,'structure_GT':structure,
        'uncertainties':uncertain,'reference_provenance':provenance,
        'GT_complete_for_required_tasks':False,'status':'DRAFT_ROOT_APPROVAL_REQUIRED',
        'proposed_approval':{'exact_text_eligible':text_eligible,'complete_required_reference_eligible':proposed_complete,
            'category':category,'reasons':reasons,'decision':'PENDING',
            'approval_requires':'Root accepts independent source-only reference and evidence; no automatic candidate-assisted edits'},
        'reference_transforms':transforms,'source_image_path':str(image),'image_identity':identity}



def check_original_identity(reference, item):
    expected_file = reference.get('source_image_sha256') or reference.get('image_sha256') or reference.get('crop_png_sha256') or reference.get('png_sha256')
    expected_pixels = reference.get('crop_pixel_sha256') or reference.get('input_pixel_hash')
    actual = item['image_identity']
    if expected_file and expected_file != actual['source_image_sha256']:
        raise ValueError('reference source image file changed: ' + item['page_id'])
    if expected_pixels and expected_pixels != actual['input_pixel_hash']:
        raise ValueError('reference source pixels changed: ' + item['page_id'])

def generate(base, output):
    base,output=Path(base),Path(output)
    output.mkdir(parents=True,exist_ok=True);os.chmod(output,0o700)
    evidence_cache={}
    def evidence(path):
        path=Path(path)
        if path not in evidence_cache:evidence_cache[path]={'path':str(path),'sha256':sha(path)}
        return evidence_cache[path]
    manifest_path=base/'r0-300/manifest.json';reference_path=base/'r0-300/references-draft.json'
    manifest=load(manifest_path)['pages'];records=load(reference_path)['records']
    mapping={r['page_id']:r for r in records}
    if len(mapping)!=len(records) or len({p['page_id'] for p in manifest})!=len(manifest):raise ValueError('duplicate R0 IDs')
    if set(mapping)!={p['page_id'] for p in manifest}:raise ValueError('R0 manifest/reference mismatch')
    groups={'r0':[],'references':[],'controls':[]}
    for page in manifest:
        ref=mapping[page['page_id']]['reference'];pid=page['page_id']
        if pid.startswith('R0-HW-'):category='handwriting_line'
        elif pid.startswith('R0-PRINT-'):category='printed_line'
        elif 'required_text_groups'in ref:category='dataset_text'
        elif ref.get('table_html'):category='table'
        elif 'graph'in ref.get('kind',''):category='graph_options'
        elif 'formula'in ref.get('kind',''):category='formula'
        elif '-HN-'in pid:category='name'
        elif 'SEALCROP'in pid:category='seal'
        else:category='partial_structure'
        image=base/'r0-300'/page['path']
        item=draft(pid,image,ref,[evidence(manifest_path),evidence(reference_path)],page['source_family_id'],category=category)
        if item['image_identity']['input_pixel_hash']!=page['expected_pixel_hash'] or item['image_identity']['source_image_sha256']!=page['sha256']:
            raise ValueError('R0 input integrity mismatch: '+pid)
        groups['r0'].append(item)
    for number in range(1,5):
        path=base/f'references/essay-{number:03d}.json';ref=load(path)
        # Independent originals are explicitly named by the source-only review workspace.
        image=Path('/private/tmp/ocr-corpus-execution-20261028/inputs')/f'LOCAL-ESSAY-{number:03d}.png'
        item=draft(ref['page_id'],image,ref,[evidence(path)],ref['page_id'],unit='long_image',category='essay_full')
        check_original_identity(ref,item);groups['references'].append(item)
    path=base/'references/names-seals.json'
    for ref in load(path)['records']:
        image=Path(ref['source_image_path']);pid=ref['page_id']
        whole=ref.get('exact_crop_bbox_xyxy')==[0,0,*ref['dimensions']]
        category='name' if '-HN-'in pid else 'seal'
        item=draft(pid,image,ref,[evidence(path)],pid,unit='crop' if whole else 'page',category=category,whole_image=whole)
        check_original_identity(ref,item);groups['references'].append(item)
    path=base/'references/print-structures.json'
    for ref in load(path)['rois']:
        category='table' if ref.get('table_html') else 'graph_options' if 'graph'in ref['kind'] else 'formula' if 'formula'in ref['kind'] else 'partial_structure'
        item=draft('ROI-'+ref['roi_id'],Path(ref['crop_path']),ref,[evidence(path)],ref['page_id'],category=category)
        check_original_identity(ref,item);groups['references'].append(item)
    path=base/'controls/gt-reference.json'
    for ref in load(path)['pages']:
        content=dict(ref,reference_text=ref.get('expected_text',''))
        category='formula' if ref.get('formula_latex') else 'table' if ref.get('table_html') else 'generic'
        # Controls with reading-order/style/image/graph tasks retain those coverage requirements.
        if not ref.get('formula_latex') and (ref.get('reading_order') or ref['scene'] in ('style_marks','figure_text','flowchart','chart')):
            category='partial_structure'
        item=draft(ref['page_id'],base/'controls'/ref['png_path'],content,[evidence(path)],ref['source_family_id'],unit='page',category=category)
        check_original_identity(ref,item)
        item['reference_provenance']['source_sha256']=ref['source_sha256']
        if ref.get('table_html'):
            item['required_tasks'].insert(0,'text')
            item['required_output_units'].append('raw_text')
            item['required_text_groups']=[{'id':'full','profile':'technical_zh_en','text':ref['expected_text'],'prediction_field':'raw_text'}]
            item['proposed_approval']['complete_required_reference_eligible']=False
            item['proposed_approval']['reasons'].append('FULL_CONTROL_TITLE_AND_TABLE_TEXT_CHANNEL_REVIEW_REQUIRED')
        groups['controls'].append(item)
    summary={'version':VERSION,'status':'DRAFT_ONLY_NO_ACCEPTANCE','groups':{}}
    approvals=[]
    for group,items in groups.items():
        target=output/(group+'-gt-draft.json')
        target.write_text(json.dumps({'version':VERSION,'status':'DRAFT_ROOT_APPROVAL_REQUIRED','pages':items},ensure_ascii=False,indent=2)+'\n');os.chmod(target,0o600)
        summary['groups'][group]={'count':len(items),'exact_text_candidates':sum(p['proposed_approval']['exact_text_eligible'] for p in items),
            'complete_reference_candidates':sum(p['proposed_approval']['complete_required_reference_eligible'] for p in items),
            'categories':dict(Counter(p['proposed_approval']['category'] for p in items)),
            'gaps':dict(Counter(reason for p in items for reason in p['proposed_approval']['reasons']))}
        for item in items:
            approvals.append({'group':group,'page_id':item['page_id'],'input_pixel_hash':item['image_identity']['input_pixel_hash'],
                'draft_sha256':hashlib.sha256(json.dumps(item,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
                **item['proposed_approval']})
    for name,value in [('summary.json',summary),('approval-template.json',{'version':VERSION,'status':'PENDING','judge_id':None,'approvals':approvals})]:
        path=output/name;path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');os.chmod(path,0o600)
    return summary



def reconstruct_page(case, tile_base):
    """Reconstruct exact RGB from verified review tiles; reject gaps or mismatched overlaps."""
    from io import BytesIO
    from PIL import ImageChops
    width,height=case['dimensions']
    result=Image.new('RGB',(width,height));coverage=Image.new('L',(width,height))
    previous=[]
    for tile in case['tiles']:
        path=Path(tile['path'])
        if not path.is_absolute():path=Path(tile_base)/path
        if sha(path)!=tile['file_sha256']:raise ValueError('review tile file changed: '+case['page_id'])
        with Image.open(path) as image:
            rgb=image.convert('RGB')
            if hashlib.sha256(rgb.tobytes()).hexdigest()!=tile['pixel_sha256']:
                raise ValueError('review tile pixels changed: '+case['page_id'])
            x0,y0,x1,y1=tile['bbox_xyxy']
            if not(0<=x0<x1<=width and 0<=y0<y1<=height) or rgb.size!=(x1-x0,y1-y0):
                raise ValueError('review tile geometry mismatch: '+case['page_id'])
            for a,b,c,d in previous:
                left,top,right,bottom=max(a,x0),max(b,y0),min(c,x1),min(d,y1)
                if left<right and top<bottom:
                    before=result.crop((left,top,right,bottom))
                    after=rgb.crop((left-x0,top-y0,right-x0,bottom-y0))
                    if ImageChops.difference(before,after).getbbox():
                        raise ValueError('review tile overlap mismatch: '+case['page_id'])
            result.paste(rgb,(x0,y0));coverage.paste(255,(x0,y0,x1,y1));previous.append((x0,y0,x1,y1))
    if coverage.getextrema()!=(255,255):raise ValueError('review tile coverage gap: '+case['page_id'])
    pixel_hash=hashlib.sha256(result.tobytes()).hexdigest()
    if pixel_hash!=case['pixel_sha256']:raise ValueError('reconstructed page pixel mismatch: '+case['page_id'])
    encoded=BytesIO();result.save(encoded,format='PNG');value=encoded.getvalue()
    return value,pixel_hash


def generate_full_pages(base,output):
    base,output=Path(base),Path(output)
    output.mkdir(parents=True,exist_ok=True);os.chmod(output,0o700)
    images=output/'reconstructed';images.mkdir(exist_ok=True);os.chmod(images,0o700)
    manifest_path=base/'full-page-audit/manifest.json'
    cases=load(manifest_path)['pages'];case_map={case['page_id']:case for case in cases}
    if len(case_map)!=len(cases):raise ValueError('duplicate full-page manifest IDs')
    sources=('full-audit-pdf1-pdf3.json','full-audit-pdf2.json','full-audit-papers.json')
    references=[]
    for name in sources:
        path=base/'references'/name;document=load(path)
        if document.get('candidate_outputs_read') or document.get('model_outputs_read'):
            raise ValueError('reference was exposed to candidate OCR')
        for reference in document['pages']:references.append((reference,path,document.get('judge_id')))
    if len({r['page_id'] for r,_,_ in references})!=len(references) or {r['page_id'] for r,_,_ in references}!=set(case_map):
        raise ValueError('full-page reference/manifest identity mismatch')
    pages=[]
    evidence_manifest={'path':str(manifest_path),'sha256':sha(manifest_path)}
    file_evidence={}
    for ref,path,independent_judge in references:
        case=case_map[ref['page_id']]
        if ref.get('candidate_outputs_read') or ref.get('candidate_outputs_seen'):
            raise ValueError('reference page was exposed to candidate OCR')
        encoded,pixels=reconstruct_page(case,base/'full-page-audit')
        if ref.get('input_pixel_hash')!=pixels:raise ValueError('audit reference pixel identity mismatch')
        image=images/(case['page_id']+'.png');image.write_bytes(encoded);os.chmod(image,0o600)
        file_evidence.setdefault(path,{'path':str(path),'sha256':sha(path)})
        text=ref.get('reference_text')
        linear=(ref.get('reference_text_complete_for_visible_text') is True or
                ref.get('exact_linear_reference_eligible') is True or
                ref.get('full_visible_text_exact_candidate') is True)
        linear=linear and isinstance(text,str)
        uncertainty=[dict(u) for u in ref.get('uncertainties',[])]
        if not linear:
            uncertainty.append({'resolved':False,'affects_required_tasks':True,
                'kind':'PARTIAL_REFERENCE_COVERAGE','note':'Full exact linear reference not independently approved; diagnostic only'})
        applicable={key:None for key in STRUCTURES}
        applicable.update(text_blocks=True,reading_order=True)
        tasks=['text','text_blocks','reading_order']
        for task,flag in [('table','table_present'),('formula','formula_present')]:
            if isinstance(ref.get(flag),bool):
                applicable[task]=ref[flag]
                if ref[flag]:tasks.append(task)
        row={'page_id':case['page_id'],'document_id':case['document_id'],
            'source_family_id':case['source_family_id'],'unit_kind':'page',
            'acceptance_rule_id':'page-good-ai-v1','GT_version':VERSION+'-fullpage',
            'scorer_version':SCORER_VERSION,'required_tasks':tasks,
            'required_output_units':['raw_text','ordered_blocks'],'critical_assertions':[],
            'required_text_groups':[{'id':'full_visible_text','profile':'printed_english' if case['document_id']=='PDF-001' else 'technical_zh_en','text':text,'prediction_field':'raw_text'}] if isinstance(text,str) else [],
            'applicability':applicable,'structure_GT':{},'uncertainties':uncertainty,
            'reference_provenance':{'kind':'ai_reference_draft','judge_id':'root-review-pending',
                'independent_source_judge_id':ref.get('judge_id',independent_judge),
                'source_image_sha256':hashlib.sha256(encoded).hexdigest(),'input_pixel_hash':pixels,
                'review_status':'pending_root_approval','review_evidence':[file_evidence[path],evidence_manifest]},
            'source_image_path':str(image),
            'original_source_asset_metadata':{'path':case.get('source_path'),
                'sha256':case.get('source_asset_sha256'),'kind':case.get('kind')},
            'GT_complete_for_required_tasks':False,'status':'DRAFT_ROOT_APPROVAL_REQUIRED',
            'reference_text_scope':'COMPLETE_LINEAR_TEXT_CANDIDATE' if linear else 'PARTIAL_DIAGNOSTIC_ONLY',
            'proposed_approval':{'decision':'PENDING','complete_text_reference_eligible':linear,
                'complete_page_all_tasks_eligible':False,
                'scope':'Independent source-only AI audit; structural matching/coverage/order not fully annotated',
                'root_view_claim':'Independent agents viewed source tiles; no claim root transcribed all105 pages'},
            'source_review_notes':ref.get('notes',ref.get('issues',ref.get('gaps',[])))}
        pages.append(row)
    summary={'version':VERSION+'-fullpage','status':'DRAFT_ONLY_NO_ACCEPTANCE','pages':len(pages),
        'linear_text_candidates':sum(p['proposed_approval']['complete_text_reference_eligible'] for p in pages),
        'partial_reference_pages':sum(not p['proposed_approval']['complete_text_reference_eligible'] for p in pages),
        'complete_page_all_tasks':0,'accepted':0,'reconstructed_verified_tiles':sum(len(c['tiles']) for c in cases)}
    approvals=[{'page_id':p['page_id'],'decision':'PENDING',
        'input_pixel_hash':p['reference_provenance']['input_pixel_hash'],
        'draft_sha256':hashlib.sha256(json.dumps(p,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
        'complete_text_reference_eligible':p['proposed_approval']['complete_text_reference_eligible'],
        'complete_page_all_tasks_eligible':False} for p in pages]
    for name,value in [('full-page-gt-draft.json',{'version':VERSION+'-fullpage','pages':pages}),
                       ('full-page-approval-template.json',{'status':'PENDING','judge_id':None,'approvals':approvals}),
                       ('full-page-summary.json',summary)]:
        target=output/name;target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');os.chmod(target,0o600)
    return summary

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--full-page-only',action='store_true')
    args=parser.parse_args()
    action=generate_full_pages if args.full_page_only else generate
    print(json.dumps(action(args.base,args.out),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
