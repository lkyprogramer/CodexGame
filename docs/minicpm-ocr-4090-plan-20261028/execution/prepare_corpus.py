#!/usr/bin/env python3
"""Prepare anonymized fixed inputs. Does not promote source text to human gold."""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    path.chmod(0o600)


def page_count(path):
    result = subprocess.run(['pdfinfo', str(path)], capture_output=True, text=True, check=True)
    return int(next(line.split(':', 1)[1] for line in result.stdout.splitlines() if line.startswith('Pages:')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--convert-word', action='store_true')
    ap.add_argument('--word-fontconfig', type=Path)
    ap.add_argument('--rerender-word', action='store_true')
    args = ap.parse_args()
    os.umask(0o077)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for name in ['inputs', 'annotations-draft', 'conversion-logs']:
        (out / name).mkdir(exist_ok=True)
    load = lambda n: json.loads((args.plan / n).read_text())
    primary, local, public = map(load, ['corpus-inventory.json', 'local-supplement-candidates.json', 'public-source-manifest.json'])
    sizes = {x['bytes'] for x in local['candidates']}
    sources = {}
    for root in [Path(local['root']), Path('/Users/luo/Downloads/作文')]:
        for folder, _, files in os.walk(root):
            for name in files:
                p = Path(folder) / name
                if p.is_file() and p.stat().st_size in sizes:
                    sources.setdefault(sha(p), p)
    pages, admissions, private_map, seen = [], [], {}, {}

    def add(ident, source, expected_sha, family, tags, annotation=None, word=False):
        entry = {'document_id': ident, 'source_family_id': family or ident, 'scene_tags': tags,
                 'GT_status': 'UNSCORED_REQUIRES_INDEPENDENT_REVIEW', 'formal_quality_admitted': False}
        if not source or not source.is_file():
            entry['status'] = 'MISSING_SOURCE'
            admissions.append(entry)
            return
        digest = sha(source)
        if digest != expected_sha:
            entry.update(status='HASH_MISMATCH', observed_sha256=digest)
            admissions.append(entry)
            return
        private_map[ident] = str(source)
        entry.update(source_sha256=digest, source_bytes=source.stat().st_size)
        if digest in seen:
            entry.update(status='EXACT_DUPLICATE', duplicate_of=seen[digest])
            admissions.append(entry)
            return
        seen[digest] = ident
        dest = out / 'inputs' / (ident + source.suffix.lower())
        shutil.copyfile(source, dest)
        entry['source_relative_path'] = str(dest.relative_to(out))
        if word:
            if args.rerender_word and dest.with_suffix('.pdf').is_file():
                evidence = out / 'rejected-word-render-fonts-v1'
                evidence.mkdir(exist_ok=True)
                saved = evidence / dest.with_suffix('.pdf').name
                if not saved.exists():
                    shutil.copyfile(dest.with_suffix('.pdf'), saved)
                dest.with_suffix('.pdf').unlink()
            entry['render_status'] = 'NOT_RENDERED'
            soffice = shutil.which('soffice')
            if args.convert_word and soffice and not dest.with_suffix('.pdf').is_file():
                proc = subprocess.run([soffice, '-env:UserInstallation=file://' + str(out / 'lo-profile'), '--headless', '--convert-to', 'pdf', '--outdir', str(out / 'inputs'), str(dest)], capture_output=True, text=True, timeout=180, env={**os.environ, **({'FONTCONFIG_FILE':str(args.word_fontconfig.resolve())} if args.word_fontconfig else {})})
                (out / 'conversion-logs' / (ident + '.log')).write_text(proc.stdout + proc.stderr)
                rendered = dest.with_suffix('.pdf')
                if proc.returncode == 0 and rendered.is_file():
                    dest = rendered
                    entry['render_status'] = 'CONVERTED_VISUAL_FONT_FORMULA_QA_PENDING'
                    entry['rendered_sha256'] = sha(dest)
                else:
                    entry['status'] = 'CONVERSION_FAILED'
                    admissions.append(entry)
                    return
            elif dest.with_suffix('.pdf').is_file():
                dest = dest.with_suffix('.pdf')
                entry['render_status'] = 'CONVERTED_VISUAL_FONT_FORMULA_QA_PENDING'
                entry['rendered_sha256'] = sha(dest)
            else:
                entry['status'] = 'GAP_WORD_RENDERER'
                admissions.append(entry)
                return
        if dest.suffix == '.pdf':
            count = page_count(dest)
            for i in range(count):
                pid = f'{ident}-p{i+1:03d}'
                pages.append({'page_id': pid, 'document_id': ident, 'source_family_id': family or ident, 'path': str(dest.relative_to(out)), 'kind': 'pdf', 'unit_kind': 'page', 'page_index': i, 'scene_tags': tags, 'split': 'development' if int(hashlib.sha256((family or ident).encode()).hexdigest(), 16) % 5 == 0 else 'evaluation_diagnostic', 'GT_status': entry['GT_status'], 'render_QA_required': word})
                text = subprocess.run(['pdftotext', '-f', str(i+1), '-l', str(i+1), '-layout', str(dest), '-'], capture_output=True, text=True, check=True).stdout
                write(out / 'annotations-draft' / (pid + '.json'), {'page_id': pid, 'status': 'DRAFT_NOT_HUMAN_GOLD', 'provenance': 'PDF_TEXT_LAYER', 'text': text})
        else:
            from PIL import Image, ImageOps
            with Image.open(dest) as image:
                image = ImageOps.exif_transpose(image).convert('RGB')
                rgb_hash = hashlib.sha256(image.tobytes()).hexdigest()
                geometry = list(image.size)
            pages.append({'page_id': ident, 'document_id': ident, 'source_family_id': family or ident, 'path': str(dest.relative_to(out)), 'kind': 'image', 'scene_tags': tags, 'split': 'evaluation_diagnostic', 'GT_status': entry['GT_status'], 'unit_kind': 'crop' if 'name_crop' in str(tags) or 'seal_crop' in str(tags) else 'long_image' if 'essay' in str(tags) else 'scene_image' if 'incidental_scene_text_photo' in tags else 'page', 'expected_pixel_hash': rgb_hash, 'rgb_dimensions': geometry})
            count = 1
        if annotation and Path(annotation).is_file():
            shutil.copyfile(annotation, out / 'annotations-draft' / (ident + '-source' + Path(annotation).suffix))
        entry.update(status='ADMITTED_EXECUTION_DIAGNOSTIC', input_units=count)
        admissions.append(entry)

    docs = [x for x in primary['files'] if x['extension'] == '.docx']
    for i, x in enumerate(docs, 1):
        add(f'PAPER-{i:03d}', Path(x['path']), x['sha256'], x['proposed_source_family_id'], ['exam_paper', 'word_converted', 'formula_QA_pending'], word=True)
    for i, x in enumerate(primary['pdfs'], 1):
        add(f'PDF-{i:03d}', Path(x['path']), x['sha256'], f'technical-pdf-{i}', ['technical_pdf', 'english' if i == 1 else 'chinese_mixed'])
    for x in local['candidates']:
        add(x['anon_id'], sources.get(x['sha256']), x['sha256'], x.get('document_family_id'), [x['scene_candidate']])
    for x in public['downloaded_candidates']:
        add('PUBLIC-' + x['sample_id'], Path(x['local_path']), x['sha256'], x['source_family_id'], x['scene_tags'], x.get('annotation_local_path'))
    # Existing dataset labels remain independent drafts until image-level review.
    region_pages, region_gt = [], []
    from PIL import Image
    gt_root = Path(local['root']) / 'icdar2015/text_localization/ch4_test_images_gt'
    for ident, source_name in private_map.items():
        if not ident.startswith('LOCAL-IC15-'):
            continue
        source = Path(source_name)
        label = gt_root / ('gt_' + source.stem + '.txt')
        if not label.is_file():
            continue
        shutil.copyfile(label, out / 'annotations-draft' / (ident + '-dataset.txt'))
        with Image.open(source) as im:
            rgb = im.convert('RGB')
            for index, line in enumerate(label.read_text(encoding='utf-8-sig').splitlines()):
                fields = line.split(',', 8)
                if len(fields) != 9 or fields[8].strip() == '###':
                    continue
                points = [int(v) for v in fields[:8]]
                box = (max(0,min(points[0::2])), max(0,min(points[1::2])), min(rgb.width,max(points[0::2])), min(rgb.height,max(points[1::2])))
                if box[2] <= box[0] or box[3] <= box[1]:
                    continue
                crop_id = ident + '-r' + str(index+1).zfill(3)
                crop = rgb.crop(box)
                relative = 'inputs/' + crop_id + '.png'
                crop.save(out / relative)
                region_pages.append({'page_id':crop_id,'document_id':ident,'source_family_id':ident,'path':relative,'kind':'image','unit_kind':'crop','task':'text','scene_tags':['scene_text_crop'],'split':'evaluation_diagnostic','expected_pixel_hash':hashlib.sha256(crop.tobytes()).hexdigest(),'original_bbox':box})
                region_gt.append({'page_id':crop_id,'acceptance_rule_id':'page-good-v1','GT_version':'dataset-reference-v1','scorer_version':'ocrbench-scoring-v1','unit_kind':'crop','GT_complete_for_required_tasks':False,'required_tasks':['text'],'required_output_units':['text'],'required_text_groups':[{'id':'full','profile':'printed_english','text':fields[8],'prediction_field':'raw_text'}],'critical_assertions':[],'provenance':{'kind':'draft','source':'ICDAR2015_TEST_DATASET_LABEL','review':'crop context and transcription not independently revalidated'},'applicability':{'text_blocks':False,'table':False,'formula':False,'reading_order':False,'style':False,'resources':False}})
    write(out / 'region-manifest.json', {'pages':region_pages,'track':'R0_DATASET_REFERENCE_DIAGNOSTIC'})
    write(out / 'region-gt-draft.json', {'pages':region_gt})
    active_page_ids = {x['page_id'] for x in pages}
    for obsolete in (out / 'annotations-draft').glob('PAPER-*.json'):
        if obsolete.stem not in active_page_ids:
            obsolete.unlink()
    write(out / 'manifest.json', {'version': 'corpus-execution-v1', 'root_relative_paths': True, 'quality_status': 'DIAGNOSTIC_NOT_FORMAL_GOLD', 'pages': pages})
    # Fixed-configuration smoke keeps all prior split labels unchanged.
    selected_ids = ['PAPER-005-p001', 'PDF-001-p002', 'PDF-001-p003', 'PDF-002-p004', 'PDF-003-p005',
                    'LOCAL-HN-01-01', 'LOCAL-ESSAY-001', 'LOCAL-ESSAY-002',
                    'LOCAL-ESSAY-003', 'LOCAL-ESSAY-004']
    smoke = [x for x in pages if x['page_id'] in selected_ids]
    for tag in ['document_with_red_seals','official_document_seal_candidate','isolated_seal_crop','scanned_or_camera_form','curved_page','english_handwriting']:
        candidate = next((x for x in pages if tag in x['scene_tags']), None)
        if candidate and candidate not in smoke:
            smoke.append(candidate)
    write(out / 'smoke-manifest.json', {'purpose':'FROZEN_PARAMETER_DIAGNOSTIC_NOT_TUNING','split_labels_unchanged':True,'pages':smoke})
    dev = []
    for x in pages:
        if x['split'] == 'development' and not any(z['source_family_id']==x['source_family_id'] for z in dev):
            dev.append(x)
    write(out / 'development-manifest.json', {'purpose':'DEVELOPMENT_EXISTING_FAMILIES_ONLY','pages':dev[:12]})
    gt = []
    for x in pages:
        draft_path = out / 'annotations-draft' / (x['page_id'] + '.json')
        text = json.loads(draft_path.read_text())['text'] if draft_path.is_file() else ''
        gt.append({'page_id':x['page_id'],'acceptance_rule_id':'page-good-v1','GT_version':'source-draft-v1','scorer_version':'ocrbench-scoring-v1','unit_kind':x.get('unit_kind','page'),'GT_complete_for_required_tasks':False,'required_tasks':['text'],'required_output_units':['text'],'required_text_groups':[{'id':'full','profile':'handwriting' if 'essay' in str(x['scene_tags']) else 'printed_english' if 'english' in x['scene_tags'] else 'printed_chinese','text':text,'prediction_field':'raw_text'}],'critical_assertions':[],'provenance':{'kind':'draft','source':'PDF_TEXT_LAYER' if draft_path.is_file() else 'EMPTY_REVIEW_TEMPLATE','review':'NOT_HUMAN_VERIFIED'},'applicability':{'text_blocks':None,'table':None,'formula':None,'reading_order':None,'style':None,'resources':None}})
    write(out / 'gt-draft.json', {'pages':gt,'warning':'DRAFT_NOT_FORMAL_GOLD_NOT_FOR_GOOD_PAGE_WINNER'})
    review = out / 'blind-review'
    review.mkdir(exist_ok=True)
    for index, x in enumerate(z for z in pages if 'LOCAL-ESSAY-' in z['page_id']):
        blind_id = 'WRITING-' + str(index+1).zfill(3)
        folder = review / blind_id
        folder.mkdir(exist_ok=True)
        shutil.copyfile(out / x['path'], folder / 'original.png')
        segments = []
        with Image.open(out / x['path']) as im:
            for n, y in enumerate(range(0,im.height,1000)):
                box = [0,max(0,y-80),im.width,min(im.height,y+1080)]
                tile = 'section-' + str(n+1).zfill(2) + '.png'
                im.crop(box).save(folder / tile)
                segments.append({'section_id':str(n+1),'image':tile,'bbox_xyxy':box,'transcription':'','uncertain_spans':[],'line_regions':[],'overlap_context_only':True})
        write(folder / 'annotation-template.json', {'blind_source_id':blind_id,'annotator_id':'','reviewer_id':'','text':'','blank_grid_regions':[],'corrections':[],'unreadable_regions':[],'sections':segments,'status':'EMPTY_NOT_GOLD','instructions':'Annotate visible original spelling, punctuation, deletions and uncertainty; overlap tiles are navigation only, not independent pages. Reconcile all sections against original before completing full text.'})
    write(out / 'essay-review-key-private.json', {f'WRITING-{i+1:03d}':x['page_id'] for i,x in enumerate(z for z in pages if 'LOCAL-ESSAY-' in z['page_id'])})
    review.joinpath('README.txt').write_text('Blind transcription pack. No model predictions or source filenames included. Assign independent annotator/reviewer identities, transcribe original visible ink, preserve punctuation and uncertainty; distinguish blank cells from unreadable ink. Tiles overlap for context and do not add pages or writers. Full-image reconciliation is mandatory. Templates are empty and are not gold.\n')
    tag_map = {'Q01':['chinese_mixed','exam_paper'],'Q02':['english','printed_english'],'Q03':['technical_pdf'],'Q04':['technical_pdf','exam_paper'],'Q05':['formula_QA_pending','formula'],'Q06':['formula_QA_pending'],'Q07':['tables','scanned_or_camera_form'],'Q08':['technical_pdf'],'Q09':['double_column','exam_paper'],'Q10':['technical_pdf','exam_paper'],'Q11':['image_labels','exam_paper'],'Q12':['plots'],'Q13':['handwritten_name_crop','english_handwriting','longform_chinese_handwritten_essay_answer_region'],'Q14':[],'Q15':[],'Q16':['official_document_seal_candidate','curved_page','shadows','real_photo'],'Q17':['technical_pdf','official_document_seal_candidate'],'Q18':['technical_pdf','exam_paper'],'Q19':['handwritten_name_crop','scanned_or_camera_form'],'Q20':['exam_paper'],'Q21':['longform_chinese_handwritten_essay_answer_region'],'Q22':['document_with_red_seals','isolated_seal_crop','official_document_seal_candidate']}
    coverage=[]
    for q, tags in tag_map.items():
        matches=[x for x in pages if set(tags)&set(x['scene_tags'])]
        coverage.append({'scene_id':q,'candidate_page_ids':[x['page_id'] for x in matches],'candidate_input_units':len(matches),'source_documents':len({x['document_id'] for x in matches}),'mapping_status':'CANDIDATE_ONLY_NOT_VISUAL_OR_GT_ACCEPTANCE','test_status':'NOT_RUN','gold_status':'GAP','notes':'Source tags nominate candidates only; require actual output and visual/GT checks. Q08 needs adjacent-pair annotation; Q06 chemistry/physics selection and Q20 style regions need explicit review.'})
    write(out / 'scene-coverage-map.json', coverage)
    unit_counts = dict(collections.Counter(x['unit_kind'] for x in pages))
    write(out / 'unit-coverage.json', {'version':'unit-coverage-v1','input_units':len(pages),'unit_kind_counts':unit_counts,'R0_diagnostic_crop_units':len(region_pages),'original_source_documents':len(admissions),'writers_verified':0,'physical_pages_verified':None,'unit_semantics':{'page':'one PDF logical page or full document/page image input; not proof of physical A4 sheet','long_image':'one original tall essay answer-region image, physical page boundaries unknown','crop':'one isolated name/seal/diagnostic region; never a page or writer','scene_image':'one incidental street-scene image; not a document page'},'essay_ids':[x['page_id'] for x in pages if x['unit_kind']=='long_image'],'physical_page_or_writer_counts_increased_by_crops':False})
    write(out / 'admission.json', admissions)
    write(out / 'private-source-map.json', private_map)
    report = {'candidates': len(admissions), 'status_counts': dict(collections.Counter(x['status'] for x in admissions)), 'execution_input_units': len(pages), 'source_families': len({x['source_family_id'] for x in pages}), 'scene_input_unit_counts': dict(collections.Counter(t for x in pages for t in x['scene_tags'])), 'formal_human_gold_units': 0, 'word_render_counts': dict(collections.Counter(x.get('render_status') for x in admissions if 'render_status' in x)), 'total_packaged_bytes': sum(p.stat().st_size for p in out.rglob('*') if p.is_file()), 'private_source_map_not_for_repository': True}
    write(out / 'summary.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
