#!/usr/bin/env python3
"""Generate an isolated synthetic OCR control profile, never human ground truth."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import fitz
import pymupdf._mupdf as mupdf_binary
from PIL import Image
import PIL


STATUS = 'programmatic_reference_pending_AI_approval'
FAMILY = 'synthetic-control-20261029-v1'
WIDTH, HEIGHT = 540, 720


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def prepare(out: Path) -> dict:
    # Refuse accidental replacement of frozen evidence.
    out.mkdir(parents=True, exist_ok=False)
    os.chmod(out, 0o700)
    (out / 'inputs').mkdir()
    (out / 'renders').mkdir()
    font = fitz.Font('cjk')
    pages, references = [], []
    layouts = []
    table_html = ('<table><tr><th rowspan="2">编号</th><th colspan="2">季度金额</th>'
                  '<th rowspan="2">合计</th></tr><tr><th>一季度</th><th>二季度</th></tr>'
                  '<tr><td>0012</td><td>12.50</td><td>7.50</td><td>20.00</td></tr>'
                  '<tr><td>0034</td><td>0.00</td><td>108.08</td><td>108.08</td></tr></table>')

    for number, scene in enumerate(['mixed_fields', 'merged_table', 'formula_chemistry',
                                   'two_column', 'vertical', 'rotated_90', 'blank', 'grid_only'], 1):
        pid = f'CONTROL-{number:02d}'
        doc = fitz.open()
        page = doc.new_page(width=WIDTH, height=HEIGHT)
        page.insert_font(fontname='control', fontbuffer=font.buffer)
        strings, regions = [], []

        def text(x: float, y: float, value: str, size: float = 16, rotate: int = 0) -> None:
            missing = [c for c in value if not c.isspace() and not font.has_glyph(ord(c))]
            if missing:
                raise ValueError(f'Missing font glyphs: {missing!r}')
            page.insert_text((x, y), value, fontsize=size, fontname='control', rotate=rotate)
            strings.append(value)

        reference = {'page_id': pid, 'scene': scene, 'status': STATUS,
                     'source_kind': 'synthetic_control', 'source_family_id': FAMILY,
                     'expected_text': '', 'key_fields': {}, 'table_html': None,
                     'formula_latex': [], 'reading_order': [], 'regions': regions}
        if scene == 'mixed_fields':
            values = ['中英数字与标点核验', 'Sample: OCR-Control / Rev.01',
                      '订单号：000127-A09', '日期：2026-10-29', '金额：￥1,028.50',
                      '比例：12.5%  温度：23℃', '电话：010-00123456',
                      '标点：“完成”；（复核）！A/B，C.D：E？',
                      'code = "000042"', 'if total <= 10: return "A_09"']
            for index, value in enumerate(values):
                text(42, 65 + index * 42, value, 16 if index else 21)
            reference['key_fields'] = {'订单号': '000127-A09', '日期': '2026-10-29',
                                       '金额': '￥1,028.50', '电话': '010-00123456',
                                       'code': '000042', 'return_literal': 'A_09'}
        elif scene == 'merged_table':
            text(42, 65, '合并单元格与数值', 21)
            xs, ys = [42, 156, 270, 384, 498], [120, 170, 220, 280, 340]
            page.draw_rect(fitz.Rect(xs[0], ys[0], xs[-1], ys[-1]))
            for x in [xs[1], xs[3]]:
                page.draw_line((x, ys[0]), (x, ys[-1]))
            page.draw_line((xs[2], ys[1]), (xs[2], ys[-1]))
            page.draw_line((xs[1], ys[1]), (xs[3], ys[1]))
            for y in ys[2:-1]:
                page.draw_line((xs[0], y), (xs[-1], y))
            for x, y, value in [(72, 180, '编号'), (230, 151, '季度金额'), (414, 180, '合计'),
                                (185, 202, '一季度'), (299, 202, '二季度')]:
                text(x, y, value, 15)
            for row, values in enumerate([['0012', '12.50', '7.50', '20.00'],
                                          ['0034', '0.00', '108.08', '108.08']]):
                for col, value in enumerate(values):
                    text(xs[col] + 22, 257 + row * 60, value, 16)
            reference['table_html'] = table_html
            regions.append({'kind': 'table', 'bbox_points': [42, 120, 498, 340]})
        elif scene == 'formula_chemistry':
            text(42, 65, '分数、上下标与化学式', 21)
            text(75, 151, 'a + b', 22)
            page.draw_line((62, 163), (151, 163), width=1.2)
            text(98, 191, '2', 22)
            text(175, 175, '= c', 22)
            # Explicit baseline offsets create actual super/subscript geometry.
            for x, y, val, size in [(65, 280, 'x', 24), (80, 267, '2', 14),
                                     (104, 280, '+ y', 24), (143, 267, '2', 14),
                                     (170, 280, '= z', 24), (207, 267, '2', 14),
                                     (65, 380, 'H', 24), (83, 388, '2', 14),
                                     (94, 380, 'O + CO', 24), (186, 388, '2', 14),
                                     (216, 380, '→ H', 24), (266, 388, '2', 14),
                                     (278, 380, 'CO', 24), (312, 388, '3', 14)]:
                text(x, y, val, size)
            reference['formula_latex'] = [r'\frac{a+b}{2}=c', r'x^2+y^2=z^2', r'H_2O+CO_2\rightarrow H_2CO_3']
            reference['expected_formula_plain'] = ['(a+b)/2=c', 'x²+y²=z²', 'H₂O+CO₂→H₂CO₃']
            reference['reading_order'] = ['title', 'fraction', 'squared_equation', 'chemical_equation']
        elif scene == 'two_column':
            text(42, 38, '控制文档 / 研究简报', 12)
            text(42, 85, '双栏阅读顺序', 21)
            blocks = [('L1', 42, 150, ['左栏第一段。编号001。', '种子先发芽，再长叶。']),
                      ('L2', 42, 270, ['左栏第二段。编号002。', '请先读完左栏，再读右栏。']),
                      ('R1', 294, 150, ['右栏第一段。编号003。', '河水流入湖泊。']),
                      ('R2', 294, 270, ['右栏第二段。编号004。', '全文到此结束。'])]
            for ident, x, y, lines in blocks:
                for index, line in enumerate(lines):
                    text(x, y + index * 32, line, 14)
                regions.append({'id': ident, 'kind': 'paragraph', 'bbox_points': [x, y - 20, x + 210, y + 36]})
            text(234, 684, '第 1 页 / 共 1 页', 11)
            reference['reading_order'] = ['header', 'title', 'L1', 'L2', 'R1', 'R2', 'footer']
        elif scene == 'vertical':
            # Right column first; upright glyphs rather than rotated Chinese letters.
            columns = ['春风吹过山川', '明月照见江河', '编号零零七号']
            for x, column in zip([400, 300, 200], columns):
                for index, char in enumerate(column):
                    text(x, 125 + index * 38, char, 26)
            reference['expected_text'] = '\n'.join(columns)
            reference['reading_order'] = ['right_column', 'middle_column', 'left_column']
        elif scene == 'rotated_90':
            for x, value in [(180, '旋转测试 编号0009'), (240, 'Rotation 90 degrees'), (300, 'Value: 001.25')]:
                text(x, 610, value, 22, rotate=90)
            reference['expected_text'] = '旋转测试 编号0009\nRotation 90 degrees\nValue: 001.25'
            reference['key_fields'] = {'编号': '0009', 'Value': '001.25'}
            reference['orientation_degrees'] = 90
        elif scene == 'grid_only':
            for x in range(60, 481, 60):
                page.draw_line((x, 120), (x, 540), color=(0.45, 0.45, 0.45))
            for y in range(120, 541, 60):
                page.draw_line((60, y), (480, y), color=(0.45, 0.45, 0.45))
            reference['expected_no_text'] = True
            reference['negative_target'] = 'no_hallucinated_cell_text_or_numbers'
        else:
            reference['expected_no_text'] = True
            reference['negative_target'] = 'no_hallucinated_text_or_structure'
        if not reference['expected_text']:
            reference['expected_text'] = '\n'.join(strings)
        # Check actual rendered text boxes in the PDF, not just nominal insertion points.
        text_boxes = [list(span['bbox']) for block in page.get_text('dict')['blocks']
                      if 'lines' in block for line in block['lines'] for span in line['spans']]
        if any(not page.rect.contains(fitz.Rect(box)) for box in text_boxes):
            raise ValueError(f'Text bbox outside page: {pid}')
        pdf = out / 'inputs' / f'{pid}.pdf'
        doc.save(pdf, garbage=4, deflate=True, no_new_id=True)
        doc.close()
        with fitz.open(pdf) as rendered:
            pix = rendered[0].get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72), colorspace=fitz.csRGB, alpha=False)
        image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
        png = out / 'renders' / f'{pid}.png'
        image.save(png, dpi=(300, 300))
        pixel_hash = hashlib.sha256(image.tobytes()).hexdigest()
        kind = 'image' if scene in ('vertical', 'rotated_90') else 'pdf'
        source = png if kind == 'image' else pdf
        case = {'page_id': pid, 'document_id': pid, 'path': str(source.relative_to(out)),
                'kind': kind, 'page_index': 0, 'unit_kind': 'page', 'source_family_id': FAMILY,
                'source_kind': 'synthetic_control', 'split': 'control', 'scene_tags': [scene],
                'expected_pixel_hash': pixel_hash, 'GT_status': STATUS}
        pages.append(case)
        reference.update(input_pixel_hash=pixel_hash, source_sha256=sha(source),
                         source_path=case['path'], pdf_sha256=sha(pdf),
                         png_path=str(png.relative_to(out)), png_sha256=sha(png),
                         crop_bbox_pixels=[0, 0, image.width, image.height],
                         crop_bbox_points=[0, 0, WIDTH, HEIGHT], rgb_dimensions=list(image.size),
                         text_bboxes_points=text_boxes)
        references.append(reference)
        layouts.append(image.resize((270, 360)))

    contact = Image.new('RGB', (1080, 720), 'white')
    for index, preview in enumerate(layouts):
        contact.paste(preview, ((index % 4) * 270, (index // 4) * 360))
    contact.save(out / 'contact-sheet.png')
    manifest = {'profile_id': FAMILY, 'source_kind': 'synthetic_control',
                'scope': 'independent_control_only_excluded_from_original_420_denominator', 'pages': pages}
    write(out / 'manifest.json', manifest)
    write(out / 'gt-reference.json', {'status': STATUS, 'provenance': 'preset_generation_program',
          'human_GT': False, 'pages': references})
    write(out / 'profile.json', {'profile_id': FAMILY, 'source_family_id': FAMILY,
          'source_kind': 'synthetic_control', 'quality_denominator': 'independent_controls_only',
          'original_420_denominator_contribution': 0,
          'renderer': {'name': 'PyMuPDF', 'version': fitz.VersionBind, 'mupdf_version': fitz.VersionFitz,
                       'binary_sha256': sha(Path(mupdf_binary.__file__)),
                       'dpi': 300, 'color_mode': 'RGB', 'alpha': False, 'pillow_version': PIL.__version__},
          'font': {'selector': 'fitz.Font(cjk)', 'name': font.name,
                   'sha256': hashlib.sha256(font.buffer).hexdigest(), 'embedded': True},
          'generator_sha256': sha(Path(__file__)), 'visual_QA': 'pending_independent_AI_approval',
          'limitations': ['synthetic typeset only; no handwriting or seal generalization',
                         'formula reference uses explicit LaTex plus baseline geometry',
                         'image cases share their generated PDF pixel lineage; never count as independent source families']})

    faults = out / 'faults'
    faults.mkdir()
    (faults / 'broken.pdf').write_bytes(b'%PDF-1.7\nINTENTIONALLY_TRUNCATED_CONTROL\n')
    (faults / 'broken.png').write_bytes(b'\x89PNG\r\n\x1a\nINTENTIONALLY_TRUNCATED_CONTROL')
    with fitz.open(out / 'inputs' / 'CONTROL-01.pdf') as doc:
        doc.save(faults / 'password.pdf', encryption=fitz.PDF_ENCRYPT_AES_256,
                 owner_pw='control-owner-only', user_pw='control-input-password')
    write(out / 'fault-manifest.json', {'profile_id': FAMILY + '-F01', 'separate_from_quality': True,
          'pages': [{'page_id': ident, 'document_id': ident, 'path': f'faults/{name}',
                     'kind': kind, 'page_index': 0, 'unit_kind': 'page', 'source_family_id': FAMILY,
                     'source_kind': 'synthetic_control', 'split': 'control', 'scene_tags': ['F01', tag],
                     'source_sha256': sha(faults / name), 'expected': 'explicit_input_failure_no_OCR_success'}
                    for ident, name, kind, tag in [('F01-BAD-PDF', 'broken.pdf', 'pdf', 'corrupt_pdf'),
                                                  ('F01-BAD-PNG', 'broken.png', 'image', 'corrupt_image'),
                                                  ('F01-PASSWORD', 'password.pdf', 'pdf', 'password_pdf')]]})
    return manifest


def prepare_chart(out: Path) -> dict:
    """Append one chart lineage without touching the original eight frozen units."""
    baseline_paths = [out / name for name in ('manifest.json', 'gt-reference.json', 'profile.json')]
    baseline_paths += [out / folder / f'CONTROL-{i:02d}.{suffix}'
                       for i in range(1, 9) for folder, suffix in [('inputs', 'pdf'), ('renders', 'png')]]
    baseline = {str(path.relative_to(out)): sha(path) for path in baseline_paths}
    # A dedicated directory makes an interrupted append visible and prevents replacement.
    chart_dir = out / 'chart-v2'
    chart_dir.mkdir(exist_ok=False)
    font = fitz.Font('cjk')
    doc = fitz.open()
    page = doc.new_page(width=WIDTH, height=HEIGHT)
    page.insert_font(fontname='control', fontbuffer=font.buffer)
    labels = []

    def text(x: float, y: float, value: str, size: float = 15) -> None:
        if any(not font.has_glyph(ord(c)) for c in value if not c.isspace()):
            raise ValueError('Chart label contains an unsupported glyph')
        page.insert_text((x, y), value, fontname='control', fontsize=size)
        labels.append(value)

    points = [{'x': x, 'y': y} for x, y in zip(['一月', '二月', '三月', '四月', '五月'], [12, 18, 15, 24, 21])]
    text(154, 80, '2026年月度产量', 22)
    text(48, 126, '产量（吨）', 16)
    # One y unit is exactly ten PDF points. Five labeled bars share the same zero.
    left, top, right, bottom = 100, 170, 480, 470
    for value in range(0, 31, 5):
        y = bottom - value * 10
        page.draw_line((left, y), (right, y), color=(0.8, 0.8, 0.8), width=0.5)
        text(68 if value >= 10 else 77, y + 5, str(value), 13)
    page.draw_line((left, top), (left, bottom), width=1.2)
    page.draw_line((left, bottom), (right, bottom), width=1.2)
    for index, point in enumerate(points):
        center = 138 + index * 76
        bar_top = bottom - point['y'] * 10
        page.draw_rect(fitz.Rect(center - 23, bar_top, center + 23, bottom),
                       color=(0.08, 0.30, 0.58), fill=(0.18, 0.47, 0.76))
        text(center - 10, bar_top - 10, str(point['y']), 15)
        text(center - 16, 498, point['x'], 16)
    text(270, 548, '月份', 17)
    bboxes = [list(span['bbox']) for block in page.get_text('dict')['blocks'] if 'lines' in block
              for line in block['lines'] for span in line['spans']]
    crop_points = fitz.Rect(40, 35, 510, 580)
    if any(not crop_points.contains(fitz.Rect(box)) for box in bboxes):
        raise ValueError('Chart text bbox outside exported chart crop')
    pdf = chart_dir / 'CONTROL-09.pdf'
    doc.save(pdf, garbage=4, deflate=True, no_new_id=True)
    doc.close()
    with fitz.open(pdf) as doc:
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72), colorspace=fitz.csRGB, alpha=False)
    image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    png = chart_dir / 'CONTROL-09.png'
    image.save(png, dpi=(300, 300))
    # Crop existing page pixels; avoid a second rasterization with a shifted pixel grid.
    crop_bbox = [166, 145, 2125, 2417]
    cropped = image.crop(tuple(crop_bbox))
    crop_png = chart_dir / 'CONTROL-09-chart-crop.png'
    cropped.save(crop_png, dpi=(300, 300))
    common = {'document_id': 'CONTROL-09', 'source_family_id': FAMILY, 'source_kind': 'synthetic_control',
              'split': 'control', 'scene_tags': ['bar_chart', 'chinese_chart_labels', 'known_data_points'],
              'GT_status': STATUS, 'page_index': 0}
    page_case = {**common, 'page_id': 'CONTROL-09', 'kind': 'pdf', 'unit_kind': 'page',
                 'path': str(pdf.relative_to(out)), 'expected_pixel_hash': hashlib.sha256(image.tobytes()).hexdigest()}
    crop_case = {**common, 'page_id': 'CONTROL-09-CHART', 'kind': 'image', 'unit_kind': 'crop',
                 'task': 'chart', 'original_bbox': crop_bbox, 'path': str(crop_png.relative_to(out)),
                 'expected_pixel_hash': hashlib.sha256(cropped.tobytes()).hexdigest()}
    manifest = {'profile_id': FAMILY + '-chart-v2', 'source_kind': 'synthetic_control', 'pages': [page_case]}
    write(out / 'chart-manifest.json', manifest)
    write(out / 'chart-region-manifest.json', {'profile_id': FAMILY + '-chart-v2-R0',
          'scope': 'same_chart_lineage_native_chart_task_only_not_an_additional_quality_page', 'pages': [crop_case]})
    write(chart_dir / 'gt-chart-reference.json', {
          'status': STATUS, 'human_GT': False, 'source_kind': 'synthetic_control',
          'source_family_id': FAMILY, 'page_id': 'CONTROL-09', 'chart_crop_page_id': 'CONTROL-09-CHART',
          'chart': {'type': 'bar', 'title': '2026年月度产量',
                    'x_axis': {'label': '月份', 'type': 'category', 'categories': [p['x'] for p in points]},
                    'y_axis': {'label': '产量', 'unit': '吨', 'min': 0, 'max': 30, 'ticks': list(range(0, 31, 5))},
                    'series': [{'name': '产量', 'unit': '吨', 'points': points}]},
          'expected_labeltext': labels, 'source_sha256': sha(pdf), 'png_sha256': sha(png),
          'input_pixel_hash': page_case['expected_pixel_hash'], 'rgb_dimensions': list(image.size),
          'chart_crop': {'path': crop_case['path'], 'sha256': sha(crop_png),
                         'input_pixel_hash': crop_case['expected_pixel_hash'], 'bbox_pixels': crop_bbox,
                         'rgb_dimensions': list(cropped.size), 'coordinate_system': 'full_page_RGB300DPI_pixels'},
          'text_bboxes_points': bboxes})
    if any(sha(out / path) != digest for path, digest in baseline.items()):
        raise RuntimeError('Original eight-page control corpus changed during chart append')
    write(out / 'profile-chart-v2.json', {'profile_id': FAMILY + '-chart-v2',
          'source_kind': 'synthetic_control', 'source_family_id': FAMILY,
          'base_profile_path': 'profile.json', 'base_profile_sha256': baseline['profile.json'],
          'base_manifest_path': 'manifest.json', 'additional_quality_manifest': 'chart-manifest.json',
          'native_chart_R0_manifest': 'chart-region-manifest.json',
          'reference_path': 'chart-v2/gt-chart-reference.json', 'additional_quality_pages': 1,
          'combined_control_quality_pages': 9, 'original_420_denominator_contribution': 0,
          'original_eight_unchanged_sha256': baseline, 'generator_sha256': sha(Path(__file__)),
          'font_sha256': hashlib.sha256(font.buffer).hexdigest(),
          'renderer': {'pymupdf': fitz.VersionBind, 'mupdf': fitz.VersionFitz,
                       'binary_sha256': sha(Path(mupdf_binary.__file__)), 'dpi': 300, 'mode': 'RGB'},
          'visual_QA': 'pending_independent_AI_approval',
          'limitations': ['single synthetic bar chart; no real chart generalization',
                         'full page and chart crop represent one chart, not independent samples']})
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('/private/tmp/ocr-ai-judge-20261029/controls'))
    parser.add_argument('--append-chart', action='store_true', help='Append chart-v2 to an existing frozen corpus')
    args = parser.parse_args()
    os.umask(0o077)
    manifest = prepare_chart(args.out.resolve()) if args.append_chart else prepare(args.out.resolve())
    print(json.dumps({'output': str(args.out.resolve()), 'quality_units': len(manifest['pages']),
                      'fault_units': 0 if args.append_chart else 3, 'reference_status': STATUS}))


if __name__ == '__main__':
    main()
