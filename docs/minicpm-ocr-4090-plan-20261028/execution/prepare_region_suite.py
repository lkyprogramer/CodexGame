#!/usr/bin/env python3
"""Build independent R0 crops and draft references, without OCR candidate access."""
import argparse, hashlib, json, math, os, unicodedata, re
from pathlib import Path
from PIL import Image, ImageDraw
import fitz


def digest(data): return hashlib.sha256(data).hexdigest()
def load(p): return json.loads(p.read_text())
def save(p,d): p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path('/private/tmp/ocr-ai-judge-20261029'));ap.add_argument('--corpus',type=Path,default=Path('/private/tmp/ocr-corpus-execution-20261028'));args=ap.parse_args()
    os.umask(0o077);out=args.root/'r0-300';(out/'inputs').mkdir(parents=True,exist_ok=True);(out/'contact-sheets').mkdir(exist_ok=True)
    refs=args.root/'references';source=args.corpus/'inputs';entries=[];references=[];pixel_seen={};gaps=[]
    def add(ident,im,page,bbox,group,ref,task='text',extra=None):
        im=im.convert('RGB');ph=digest(im.tobytes())
        if ph in pixel_seen:gaps.append({'id':ident,'status':'DUPLICATE_PIXELS','duplicate_of':pixel_seen[ph]});return
        pixel_seen[ph]=ident;dest=out/'inputs'/(ident+'.png');im.save(dest)
        family=next((x['source_family_id']for x in load(args.corpus/'manifest.json')['pages']if x['page_id']==page or x['document_id']==page),page)
        entry={'page_id':ident,'document_id':page,'source_family_id':family,'path':str(dest.relative_to(out)),'kind':'image','unit_kind':'crop','region_task':task,'task':task,'scene_tags':[group],'split':'diagnostic_reference','original_case_id':page,'original_bbox_xyxy':bbox,'expected_pixel_hash':ph,'sha256':digest(dest.read_bytes()),'dimensions':list(im.size),'bytes':dest.stat().st_size,'output_task_cap':8192 if task=='table' else 2048 if task in ['seal','formula'] else 4096}
        if extra:entry.update(extra)
        entries.append(entry);references.append({'page_id':ident,'source_case':page,'provenance':{'kind':'ai_visual_reference' if group!='printed_pdf' and group!='icdar' else 'source_text_draft','candidate_outputs_seen':False,'human_verified':False},'status':'DRAFT_PARENT_JUDGE_APPROVAL_REQUIRED','GT_complete_for_required_tasks':False,'reference':ref,'unit_kind':'crop'})
    # Approximate reference y-values are snapped to original grid horizontal borders.
    for i in range(1,5):
        d=load(refs/f'essay-{i:03d}.json');ind=load(refs/'essay-004-independent.json')if i==4 else d
        im=Image.open(source/f'LOCAL-ESSAY-{i:03d}.png').convert('RGB');gray=im.convert('L');groups=[]
        for y in range(im.height):
            h=gray.crop((100,y,1450,y+1)).histogram()
            if sum(h[:170])>1350*.65:
                if not groups or y>groups[-1][-1]+1:groups.append([y])
                else:groups[-1].append(y)
        cells=[(a[-1],b[0])for a,b in zip(groups,groups[1:])if 65<b[0]-a[-1]<115]
        for n,line in enumerate(ind['lines']):
            approx=line['y_range_approx'];center=sum(approx)/2;top,bottom=min(cells,key=lambda c:abs(sum(c)/2-center))
            if i==1 and n==34: top,bottom=4121,4214
            if abs((top+bottom)/2-center)>45:gaps.append({'id':f'ESSAY-{i}-{n+1}','status':'GRID_SNAP_DISTANCE','approx':approx});continue
            box=[45,max(0,top),1505,min(im.height,bottom+2)]
            original_line_text=line['text'];resolved_text=original_line_text
            decisions=[u for u in d.get('uncertainties',[]) if str(u.get('line_id')).lstrip('L0')==str(line.get('line_id')).lstrip('L0') and u.get('resolved')]
            for u in decisions:
                decision=u.get('root_decision',u.get('decision'))
                if decision is None:continue
                if u.get('rendered'):resolved_text=resolved_text.replace(u['rendered'],decision)
                for marker in re.findall(r'〔[^〕]+〕',resolved_text):
                    if any(c in marker for c in u.get('candidates',[]) if c):resolved_text=resolved_text.replace(marker,decision)
            final_doc=re.sub(r'\s+','',d.get('reference_text',''))
            for marker in re.findall(r'〔[^〕]+〕',resolved_text):
                pos=resolved_text.index(marker);before=resolved_text[max(0,pos-3):pos];after=resolved_text[pos+len(marker):pos+len(marker)+3]
                possible=[x.rstrip('？?') for x in marker[1:-1].split('/')]
                hits=[x for x in possible if before+x+after in final_doc]
                if len(hits)==1:resolved_text=resolved_text.replace(marker,hits[0])
            rootline=d['lines'][n] if n<len(d['lines'])else{}
            add(f'R0-HW-{i:03d}-{n+1:03d}',im.crop(box),d['page_id'],box,'handwrite',{'line_reference':line,'reference_text':resolved_text,'raw_line_reference':original_line_text,'unresolved_marker_present':bool(re.search(r'〔[^〕]+〕',resolved_text)),'root_adjudicated_line':rootline,'document_uncertainties':d.get('uncertainties',[]),'independent_document_uncertainties':ind.get('uncertainties',[]),'root_final_document_reference':d.get('reference_text'),'reference_must_apply_root_decisions_not_literal_uncertainty_markers':True},extra={'approx_bbox_y':approx,'grid_border_y':[top,bottom]})
    for r in load(refs/'names-seals.json')['records']:
        if r['page_id'].startswith(('LOCAL-HN-','LOCAL-SEALCROP-')):
            im=Image.open(r['source_image_path']);add('R0-'+r['page_id'],im,r['page_id'],[0,0,*im.size],'name'if r['page_id'].startswith('LOCAL-HN')else 'seal',r,'text'if r['page_id'].startswith('LOCAL-HN')else 'seal')
    old=load(args.corpus/'region-manifest.json')['pages'];oldgt={x['page_id']:x for x in load(args.corpus/'region-gt-draft.json')['pages']}
    for r in old:add('R0-'+r['page_id'],Image.open(args.corpus/r['path']),r['document_id'],r['original_bbox'],'icdar',oldgt[r['page_id']])
    struct=load(refs/'print-structures.json')['rois'];chosen=[r for r in struct if r['kind']in ['formula_options','question_formula_options','chemical_formula_options','nuclear_formula_options','graph_and_options','table']]
    for r in chosen:add('R0-STRUCT-'+r['roi_id'],Image.open(r['crop_path']),r['page_id'],r['bbox'],'table'if r['kind']=='table'else 'formula',r,'table'if r['kind']=='table'else 'formula')
    # Fixed 107 rows spread over all 49 original PDF pages, independent of outputs.
    totalpage=0; printed_extras=[]
    for docnum in range(1,4):
        docid=f'PDF-{docnum:03d}';pdf=fitz.open(source/(docid+'.pdf'))
        for pi,page in enumerate(pdf):
            want=4 if totalpage<5 else 3 if totalpage<9 else 2;totalpage+=1;candidates=[]
            for b in page.get_text('dict')['blocks']:
                for line in b.get('lines',[]):
                    txt=''.join(s['text']for s in line['spans']).strip()
                    if not 25<=len(txt)<=190 or '\ufffd'in txt or any(c in txt for c in '∑∫√≤≥≈±→←∈∂πλμσδβγθ')or not all(c.isprintable()for c in txt):continue
                    if any('math'in s['font'].lower()or 'symbol'in s['font'].lower()for s in line['spans']):continue
                    if sum(c.isalpha()for c in txt)<len(txt)*.4:continue
                    if txt.startswith(('“','”','\"')) or '......' in txt or any('courier'in z['font'].lower()for z in line['spans']):continue
                    candidates.append((line['bbox'],txt))
            if len(candidates)<want:gaps.append({'page':f'{docid}-p{pi+1:03d}','status':'INSUFFICIENT_PLAIN_TEXT_LINES','available':len(candidates)})
            pix=page.get_pixmap(dpi=300,colorspace=fitz.csRGB,alpha=False);im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
            selected=[]
            for n in range(min(want,len(candidates))):
                idx=round((n+1)*(len(candidates)-1)/(want+1));selected.append(idx);bbox,txt=candidates[idx]
                box=[max(0,math.floor(bbox[0]*300/72)-5),max(0,math.floor(bbox[1]*300/72)-3),min(im.width,math.ceil(bbox[2]*300/72)+5),min(im.height,math.ceil(bbox[3]*300/72)+3)]
                add(f'R0-PRINT-{docnum:03d}-{pi+1:03d}-{n+1:02d}',im.crop(box),f'{docid}-p{pi+1:03d}',box,'printed_pdf',{'text_layer_raw':txt,'text_nfkc':unicodedata.normalize('NFKC',txt),'normalization':'NFKC reference only; source pixels unchanged','visual_review':'CONTACT_SHEET_PENDING'},extra={'source_full_page_pixel_hash':digest(pix.samples),'source_pdf_sha256':digest((source/(docid+'.pdf')).read_bytes())})
            for idx,(bb,tt) in enumerate(candidates):
                if idx not in selected:printed_extras.append((docnum,pi,idx,bb,tt))
    # Redistribute absent plain-text cover/code rows across eligible originals.
    need=107-sum('printed_pdf'in x['scene_tags']for x in entries)
    step=max(1,len(printed_extras)//max(1,need))
    for docnum,pi,idx,bb,txt in printed_extras[::step]:
        if sum('printed_pdf'in x['scene_tags']for x in entries)>=107:break
        docid=f'PDF-{docnum:03d}';pdf=fitz.open(source/(docid+'.pdf'));pix=pdf[pi].get_pixmap(dpi=300,colorspace=fitz.csRGB,alpha=False);im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
        box=[max(0,math.floor(bb[0]*300/72)-5),max(0,math.floor(bb[1]*300/72)-3),min(im.width,math.ceil(bb[2]*300/72)+5),min(im.height,math.ceil(bb[3]*300/72)+3)]
        add(f'R0-PRINT-{docnum:03d}-{pi+1:03d}-X{idx:03d}',im.crop(box),f'{docid}-p{pi+1:03d}',box,'printed_pdf',{'text_layer_raw':txt,'text_nfkc':unicodedata.normalize('NFKC',txt),'normalization':'NFKC reference only; source pixels unchanged','visual_review':'CONTACT_SHEET_PENDING'},extra={'source_full_page_pixel_hash':digest(pix.samples)})
    # Drop fragments from neighbouring text lines caused by oversized PDF font boxes.
    for e in entries:
        if 'printed_pdf'not in e['scene_tags']:continue
        path=out/e['path'];im=Image.open(path).convert('RGB');gray=im.convert('L');ys=[]
        for y in range(im.height):
            if sum(gray.crop((0,y,im.width,y+1)).histogram()[:180])>=8:ys.append(y)
        runs=[]
        for y in ys:
            if not runs or y>runs[-1][-1]+4:runs.append([y])
            else:runs[-1].append(y)
        if runs:
            main=max(runs,key=lambda r:sum(sum(gray.crop((0,y,im.width,y+1)).histogram()[:180])for y in r));top=max(0,main[0]-9);bottom=min(im.height,main[-1]+7)
            crop=im.crop((0,top,im.width,bottom));crop.save(path);e['original_bbox_xyxy'][1]+=top;e['original_bbox_xyxy'][3]=e['original_bbox_xyxy'][1]+crop.height;e.update(expected_pixel_hash=digest(crop.tobytes()),sha256=digest(path.read_bytes()),dimensions=list(crop.size),bytes=path.stat().st_size,pdf_line_vertical_trim=[top,bottom])
    save(out/'manifest.json',{'version':'r0-fixed-independent-v1','target':300,'actual':len(entries),'pages':entries,'candidate_outputs_seen':False});save(out/'references-draft.json',{'records':references,'status':'NOT_HUMAN_GOLD_PARENT_REVIEW_REQUIRED'});save(out/'gaps.json',gaps)
    # Every output crop appears, uncropped, in a contact sheet. Original PNG authoritative.
    for group in ['handwrite','name','seal','icdar','formula','table','printed_pdf']:
        items=[x for x in entries if group in x['scene_tags']]
        per=10 if group in ['formula','table']else 14
        for start in range(0,len(items),per):
            chunk=items[start:start+per];thumbs=[]
            for x in chunk:
                im=Image.open(out/x['path']);im.thumbnail((1460,350 if group in ['formula','table']else 125));thumbs.append((x,im.copy()))
            sheet=Image.new('RGB',(1500,sum(im.height+35 for _,im in thumbs)), 'white');draw=ImageDraw.Draw(sheet);y=0
            for x,im in thumbs:draw.text((5,y),x['page_id'],fill='black');sheet.paste(im,(5,y+25));y+=im.height+35
            sheet.save(out/'contact-sheets'/f'{group}-{start//per+1:02d}.png')
    save(out/'summary.json',{'target':300,'actual':len(entries),'groups':{g:sum(g in e['scene_tags']for e in entries)for g in ['handwrite','name','seal','icdar','formula','table','printed_pdf']},'unique_pixel_hashes':len(pixel_seen),'input_bytes':sum(e['bytes']for e in entries),'independent_writers_added':0,'formal_human_gold':False,'gaps':len(gaps),'contact_sheet_count':len(list((out/'contact-sheets').glob('*.png')))})
    print(json.dumps(load(out/'summary.json'),indent=2))
if __name__=='__main__':main()
