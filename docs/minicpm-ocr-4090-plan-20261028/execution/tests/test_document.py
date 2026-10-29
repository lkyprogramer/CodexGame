import json
import tempfile
import time
import unittest
from pathlib import Path

from ocrbench.document import assemble_document


class DocumentTests(unittest.TestCase):
    def test_preserves_pages_relocates_known_assets_and_emits_all_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cases = []
            for index in range(2):
                page_id = f'p{index}'
                page = root/'pages'/page_id
                (page/'images').mkdir(parents=True)
                (page/'images/a.png').write_bytes(b'asset')
                record = {'page_id': page_id, 'document_id': 'd', 'status': 'PASS',
                          'text': f'text-{index}', 'raw_text': f'raw-{index}',
                          'markdown': '![img](images/a.png)',
                          'ordered_blocks': [{'image_reference': 'images/a.png'}]}
                (page/'result.json').write_text(json.dumps(record))
                (page/'markdown.md').write_text(record['markdown'])
                cases.append({'page_id': page_id, 'document_id': 'd', 'kind': 'image', 'path': 'unused'})
            result = assemble_document('d', cases, root, time.monotonic()+10)
            self.assertEqual(result['status'], 'PASS')
            md = (root/'documents/d/document.md').read_text()
            self.assertIn('../../pages/p0/images/a.png', md)
            self.assertIn('../../pages/p1/images/a.png', md)
            self.assertLess(md.index('page_id: p0'), md.index('page_id: p1'))
            self.assertEqual(len(result['resources']), 2)
            self.assertTrue(all((root/p).is_file() for p in result['outputs'].values()))
            self.assertIn('\f', (root/'documents/d/document.txt').read_text())

    def test_failed_page_missing_md_and_deadline_cannot_be_complete_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            page = root/'pages/p'
            page.mkdir(parents=True)
            (page/'result.json').write_text(json.dumps({'page_id': 'p', 'document_id': 'd', 'status': 'FAIL', 'ordered_blocks': []}))
            result = assemble_document('d', [{'page_id': 'p', 'document_id': 'd', 'kind': 'image', 'path': 'unused'}], root, 0)
            self.assertEqual(result['status'], 'FAIL')
            self.assertIn('DOCUMENT_DEADLINE_DURING_ASSEMBLY', result['errors'])
            self.assertIn('p:MISSING_PAGE_MARKDOWN', result['errors'])

    def test_table_embedded_assets_are_relocated_without_changing_cells(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            page = root/'pages/p'
            (page/'images').mkdir(parents=True)
            (page/'images/plot.jpg').write_bytes(b'plot')
            markdown = '<table><tr><td><img src=images/plot.jpg />图中字</td></tr></table>'
            record = {'page_id': 'p', 'document_id': 'd', 'status': 'PASS',
                      'text': '图中字', 'raw_text': '图中字', 'markdown': markdown,
                      'ordered_blocks': [{'block_type': 'table', 'embedded_images': [
                          {'image_reference': 'images/plot.jpg'}]}]}
            (page/'result.json').write_text(json.dumps(record))
            (page/'markdown.md').write_text(markdown)
            result = assemble_document('d', [{'page_id': 'p', 'document_id': 'd', 'kind': 'image', 'path': 'unused'}], root, time.monotonic()+10)
            exported = (root/'documents/d/document.md').read_text()
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(len(result['resources']), 1)
            self.assertIn('src="../../pages/p/images/plot.jpg"', exported)
            self.assertIn('图中字</td>', exported)


if __name__ == '__main__':
    unittest.main()
