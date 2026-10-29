#!/usr/bin/env python3
"""Freeze 6 real-source x 8 deterministic image variants, without reading OCR output."""
from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
import math
import os
from pathlib import Path

import fitz
import PIL
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps, features


SELECTION = [
    ('PAPER-016-p001', 'chinese_exam', ['Q01', 'Q10']),
    ('PAPER-005-p001', 'math_formula', ['Q05', 'Q07']),
    ('PDF-002-p002', 'technical_pdf', ['Q03', 'Q07']),
    ('LOCAL-ESSAY-001', 'real_handwritten_essay', ['Q13', 'Q21']),
    ('PUBLIC-docunet-photo-1', 'real_document_photo', ['Q15', 'Q16']),
    ('LOCAL-SEALCROP-0', 'real_seal_crop', ['Q22']),
]
OPERATIONS = ['resolution_low', 'resolution_high', 'rotate90', 'skew_plus5',
              'jpeg_q35', 'gaussian_sigma1', 'contrast_055', 'occlusion_lower_right_15pct_area']


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pixels(image: Image.Image) -> str:
    return hashlib.sha256(image.tobytes()).hexdigest()


def write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def load_image(source: Path, case: dict, dpi: int = 300) -> Image.Image:
    if case['kind'] == 'pdf':
        with fitz.open(source) as doc:
            pix = doc[case['page_index']].get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72),
                                                    colorspace=fitz.csRGB, alpha=False)
        return Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    with Image.open(source) as original:
        return ImageOps.exif_transpose(original).convert('RGB')


def prepare(manifest_path: Path, out: Path) -> None:
    data = json.loads(manifest_path.read_text())
    pages = data if isinstance(data, list) else data['pages']
    indexed = {case['page_id']: case for case in pages}
    missing = [pid for pid, _, _ in SELECTION if pid not in indexed]
    if missing:
        raise ValueError(f'GAP: selected source pages absent from main manifest: {missing}')
    out.mkdir(parents=True, exist_ok=False)
    os.chmod(out, 0o700)
    for name in ['inputs', 'baselines', 'contact-sheets']:
        (out / name).mkdir()
    versions = {'pymupdf': fitz.VersionBind, 'mupdf': fitz.VersionFitz,
                'pillow': PIL.__version__, 'jpeg_codec': features.version_codec('jpg')}
    records, originals = [], []
    for group, (pid, scene, matrix_ids) in enumerate(SELECTION, 1):
        case = indexed[pid]
        source = Path(case['path'])
        if not source.is_absolute():
            source = manifest_path.parent / source
        source_hash = sha(source)
        base = load_image(source, case)
        base_hash = pixels(base)
        if case.get('expected_pixel_hash') and case['expected_pixel_hash'] != base_hash:
            raise ValueError(f'Frozen source pixels mismatch: {pid}')
        baseline_path = out / 'baselines' / f'{pid}.png'
        base.save(baseline_path)
        lineage = {'original_page_id': pid, 'original_document_id': case['document_id'],
                   'source_family_id': case['source_family_id'], 'source_path': str(source.resolve()),
                   'source_kind': case['kind'], 'source_sha256': source_hash,
                   'source_page_index': case.get('page_index'), 'original_split': case.get('split'),
                   'baseline_dpi': 300 if case['kind'] == 'pdf' else None,
                   'baseline_rgb_dimensions': list(base.size), 'baseline_input_pixel_hash': base_hash,
                   'baseline_path': str(baseline_path.relative_to(out)), 'baseline_png_sha256': sha(baseline_path),
                   'scene': scene, 'matrix_ids': matrix_ids}
        originals.append(lineage)
        preview_images = [('original', base.copy())]
        for operation in OPERATIONS:
            params = {'operation': operation, 'applied_to': 'original_normalized_RGB_not_chained',
                      'versions': versions}
            if operation in ('resolution_low', 'resolution_high'):
                target = 200 if operation == 'resolution_low' else 400
                if case['kind'] == 'pdf':
                    image = load_image(source, case, target)
                    params.update(method='native_PDF_rasterization', dpi=target,
                                  colorspace='RGB', alpha=False, matrix_scale=target / 72)
                else:
                    numerator = 2 if target == 200 else 4
                    size = tuple(max(1, round(value * numerator / 3)) for value in base.size)
                    image = base.resize(size, Image.Resampling.LANCZOS)
                    params.update(method='pixel_resample_not_physical_DPI', physical_dpi=None,
                                  scale_fraction=f'{numerator}/3', size_rounding='Python_round_half_even',
                                  resampling='Pillow_LANCZOS')
            elif operation == 'rotate90':
                image = base.transpose(Image.Transpose.ROTATE_90)
                params.update(angle_degrees_counterclockwise=90, method='Pillow_TRANSPOSE_ROTATE_90',
                              expand=True, interpolation='none_exact_pixel_permutation')
            elif operation == 'skew_plus5':
                image = base.rotate(5, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=(255, 255, 255))
                params.update(angle_degrees_counterclockwise=5, resampling='Pillow_BICUBIC', expand=True,
                              center_pixels=[base.width / 2, base.height / 2], fill_rgb=[255, 255, 255])
            elif operation == 'jpeg_q35':
                memory = BytesIO()
                base.save(memory, format='JPEG', quality=35, subsampling=2, optimize=False, progressive=False)
                encoded_jpeg = memory.getvalue()
                with Image.open(BytesIO(encoded_jpeg)) as jpeg:
                    image = jpeg.convert('RGB')
                params.update(quality=35, subsampling='4:2:0', subsampling_code=2,
                              optimize=False, progressive=False, method='Pillow_JPEG_encode_decode')
            elif operation == 'gaussian_sigma1':
                image = base.filter(ImageFilter.GaussianBlur(radius=1))
                params.update(method='Pillow_GaussianBlur', sigma_pixels=1, radius_argument=1)
            elif operation == 'contrast_055':
                image = ImageEnhance.Contrast(base).enhance(0.55)
                params.update(method='Pillow_ImageEnhance_Contrast', factor=0.55,
                              pivot='Pillow_grayscale_image_mean')
            else:
                image = base.copy()
                fraction = math.sqrt(0.15)
                bbox = [math.floor(base.width * (1 - fraction)), math.floor(base.height * (1 - fraction)),
                        base.width, base.height]
                ImageDraw.Draw(image).rectangle((bbox[0], bbox[1], bbox[2] - 1, bbox[3] - 1), fill=(128, 128, 128))
                params.update(method='solid_rectangle_mask', target_page_area_fraction=0.15,
                              placement='lower_right', bbox_pixels_half_open=bbox, fill_rgb=[128, 128, 128],
                              actual_page_area_fraction=((bbox[2] - bbox[0]) * (bbox[3] - bbox[1])) / (base.width * base.height),
                              recognition_scope='visible_unmasked_content_only',
                              hidden_text_recognition_required=False)
            variant_id = f'ROBUST-{group:02d}-{operation}'
            destination = out / 'inputs' / (variant_id + ('.jpg' if operation == 'jpeg_q35' else '.png'))
            if operation == 'jpeg_q35':
                destination.write_bytes(encoded_jpeg)
            else:
                image.save(destination)
            with Image.open(destination) as actual:
                actual = actual.convert('RGB')
                assert pixels(actual) == pixels(image), variant_id
            records.append({'page_id': variant_id, 'document_id': f'ROBUST-{group:02d}-{operation}',
                            'path': str(destination.relative_to(out)), 'kind': 'image',
                            'unit_kind': case.get('unit_kind', 'page'),
                            'source_family_id': case['source_family_id'], 'origin_kind': 'real_source_deterministic_degradation',
                            'split': 'robustness_diagnostic', 'scene_tags': [scene, operation, *matrix_ids],
                            'expected_pixel_hash': pixels(image), 'rgb_dimensions': list(image.size),
                            'file_sha256': sha(destination), 'source_lineage': lineage, 'operation': params,
                            'GT_status': 'reference_transfer_pending_root_AI_visible_content_review',
                            'reference_transfer_complete': False,
                            'occluded_content_is_scored': False if operation.startswith('occlusion') else None})
            preview_images.append((operation, image))
        # One original plus exactly eight independent variants. Never include these thumbnails in quality counts.
        sheet = Image.new('RGB', (1350, 1872), '#e8e8e8')
        draw = ImageDraw.Draw(sheet)
        for index, (label, image) in enumerate(preview_images):
            thumbnail = ImageOps.contain(image, (440, 590), Image.Resampling.LANCZOS)
            x, y = (index % 3) * 450, (index // 3) * 624
            draw.text((x + 7, y + 5), label, fill='black')
            sheet.paste(thumbnail, (x + (450 - thumbnail.width) // 2, y + 27))
        sheet.save(out / 'contact-sheets' / f'{group:02d}-{scene}.png')
        if sha(source) != source_hash:
            raise RuntimeError(f'Source changed while deriving variants: {pid}')
    assert len(records) == 48
    assert len({x['source_family_id'] for x in records}) == 6
    write(out / 'manifest.json', {'profile_id': 'robustness48-20261029-v2', 'pages': records})
    write(out / 'profile.json', {'profile_id': 'robustness48-20261029-v2', 'source_kind': 'real_source_deterministic_degradation',
          'selected_originals': originals, 'original_count': 6, 'variant_count': 48, 'variants_per_original': 8,
          'new_independent_source_families': 0, 'original_420_denominator_contribution': 0,
          'main_manifest_path': str(manifest_path.resolve()), 'main_manifest_sha256': sha(manifest_path),
          'generator_sha256': sha(Path(__file__)), 'versions': versions,
          'operations': OPERATIONS, 'reference_transfer_complete': False, 'root_AI_approval': 'pending',
          'visual_QA': 'pending_generator_contact_sheet_inspection', 'gaps': [],
          'limitations': ['six selected real pages are not coverage of all Q01-Q22',
                         'synthetic degradation of real inputs is not additional real acquisition evidence',
                         'image resampling has no physical DPI interpretation',
                         'resolution_high is not degradation; report as resolution sensitivity',
                         'lower-right 15 percent means target image AREA, not 15 percent per edge',
                         'occlusion may cover existing whitespace; require only visible unmasked text',
                         'do not automatically transfer complete references or require hidden text recognition',
                         'variants and originals retain the same existing source family and must remain grouped']})
    print(json.dumps({'out': str(out), 'originals': 6, 'variants': 48, 'source_families': 6}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    prepare(args.manifest.resolve(), args.out.resolve())
