"""Validate the generated control assets against the runner's real input boundary."""
import hashlib
import json
import os
from pathlib import Path
import unittest

from ocrbench.core import _decode_page, load_manifest
from prepare_controls import FAMILY, STATUS, prepare, sha


class ControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(os.environ.get('OCR_CONTROL_ROOT', '/private/tmp/ocr-ai-judge-20261029/controls'))
        cls.manifest = json.loads((cls.root / 'manifest.json').read_text())
        cls.references = {p['page_id']: p for p in json.loads((cls.root / 'gt-reference.json').read_text())['pages']}

    def test_runner_input_pixels_and_reference_lineage(self):
        self.assertEqual(len(self.manifest['pages']), 8)
        self.assertEqual(len(load_manifest(self.root / 'manifest.json')), 8)
        for case in self.manifest['pages']:
            with self.subTest(page_id=case['page_id']):
                self.assertEqual(case['split'], 'control')
                self.assertEqual(case['source_family_id'], FAMILY)
                self.assertEqual(case['source_kind'], 'synthetic_control')
                self.assertEqual(case['GT_status'], STATUS)
                source = self.root / case['path']
                image, _ = _decode_page({**case, 'path': str(source)})
                reference = self.references[case['page_id']]
                digest = hashlib.sha256(image.tobytes()).hexdigest()
                self.assertEqual(digest, case['expected_pixel_hash'])
                self.assertEqual(digest, reference['input_pixel_hash'])
                self.assertEqual(sha(source), reference['source_sha256'])
                self.assertEqual(sha(self.root / reference['png_path']), reference['png_sha256'])
                self.assertEqual(reference['crop_bbox_pixels'], [0, 0, *image.size])
                self.assertEqual(image.mode, 'RGB')
                if case['page_id'] == 'CONTROL-07':
                    self.assertEqual(image.getextrema(), ((255, 255),) * 3)
                elif case['page_id'] == 'CONTROL-08':
                    self.assertNotEqual(image.getextrema(), ((255, 255),) * 3)

    def test_f01_inputs_fail_explicitly_at_runner_decode(self):
        manifest = json.loads((self.root / 'fault-manifest.json').read_text())
        self.assertEqual(len(manifest['pages']), 3)
        for case in manifest['pages']:
            with self.subTest(page_id=case['page_id']):
                with self.assertRaises((RuntimeError, ValueError, OSError)):
                    _decode_page({**case, 'path': str(self.root / case['path'])})

    def test_frozen_generation_refuses_overwrite(self):
        before = sha(self.root / 'manifest.json')
        with self.assertRaises(FileExistsError):
            prepare(self.root)
        self.assertEqual(sha(self.root / 'manifest.json'), before)

    def test_chart_append_pixels_and_original_eight_unchanged(self):
        profile = json.loads((self.root / 'profile-chart-v2.json').read_text())
        for path, digest in profile['original_eight_unchanged_sha256'].items():
            self.assertEqual(sha(self.root / path), digest, path)
        reference = json.loads((self.root / 'chart-v2/gt-chart-reference.json').read_text())
        self.assertEqual([p['y'] for p in reference['chart']['series'][0]['points']], [12, 18, 15, 24, 21])
        self.assertEqual(reference['chart']['y_axis']['unit'], '吨')
        page = load_manifest(self.root / 'chart-manifest.json')[0]
        crop = load_manifest(self.root / 'chart-region-manifest.json')[0]
        page_image, _ = _decode_page(page)
        crop_image, _ = _decode_page(crop)
        self.assertEqual(hashlib.sha256(page_image.tobytes()).hexdigest(), page['expected_pixel_hash'])
        self.assertEqual(hashlib.sha256(crop_image.tobytes()).hexdigest(), crop['expected_pixel_hash'])
        self.assertEqual(page_image.crop(tuple(reference['chart_crop']['bbox_pixels'])).tobytes(), crop_image.tobytes())
        self.assertEqual(crop['task'], 'chart')


if __name__ == '__main__':
    unittest.main()
