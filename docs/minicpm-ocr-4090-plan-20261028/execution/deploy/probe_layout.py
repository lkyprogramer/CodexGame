"""Real CPU layout smoke; no recognition or quality score is produced."""
import json
import pathlib
import time

from PIL import Image
from minicpmvocr.layouts import create_layout_detector

config = {'provider': 'ppdoclayout3_paddlex', 'model_name': 'PP-DocLayoutV3',
          'model_dir': '/models/PP-DocLayoutV3_infer', 'device': 'cpu',
          'threshold': .3, 'nms': True, 'skip_vlm_labels': [],
          'use_ocr_for_image_block': True, 'use_chart_recognition': True,
          'use_seal_recognition': True}
started = time.monotonic()
detector = create_layout_detector(config)
detector.validate_config(config)
detector.start()
initialized = time.monotonic()
with Image.open('/work/deploy/ocr-probe-dev-photo.png') as opened:
    image = opened.convert('RGB')
    detections = detector.detect([image])
    assert len(detections) == 1
    crops = detector.crop(image, detections[0])
result = {'status': 'PASS', 'provider': detector.describe(),
          'initialization_seconds': initialized-started,
          'inference_seconds': time.monotonic()-initialized,
          'CPU_build_interference': True, 'quality_evidence': False,
          'detections': detections[0], 'crop_count': len(crops),
          'folded_crop_count': sum(c.get('image') is None for c in crops),
          'labels': [c['label'] for c in crops]}
pathlib.Path('/work/evidence/mini-layout-probe-r1.json').write_text(json.dumps(result, indent=2))
print(json.dumps({k:v for k,v in result.items() if k != 'detections'}))
