import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'tools/v027/trace_ada.py'
spec = importlib.util.spec_from_file_location('trace_ada_test', SOURCE)
trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace)


class MarkersTest(unittest.TestCase):
    def test_output_boundaries_use_parser_classification(self):
        lines = [b'data: {"choices":[{"delta":{"role":"assistant"}}]}',
                 b'data: {"progress":1}',
                 b'data: {"choices":[{"delta":{"reasoning_content":"r"}}]}',
                 b'data: {"choices":[{"delta":{"content":"x"}}]}',
                 b'data: {"usage":{"completion_tokens":2}}', b'data: [DONE]']
        marks = []
        marker = type('Marker', (), {'mark': lambda _, name: marks.append(name)})()
        original = trace.http.parse_sse
        with trace.output_markers(marker, 'case'):
            response = trace.http.parse_sse(lines)
        self.assertIs(trace.http.parse_sse, original)
        self.assertEqual(marks, ['P11_OUTPUT/case', 'P11_FIRST/case', 'P11_OUTPUT/case'])
        self.assertEqual((response['reasoning'], response['text'], response['done']), ('r', 'x', True))
        self.assertEqual(response['usage']['completion_tokens'], 2)

    def test_restore_and_malformed_stream_preserved(self):
        original = trace.http.parse_sse
        marker = type('Marker', (), {'mark': lambda *_: None})()
        with trace.output_markers(marker, 'bad'):
            result = trace.http.parse_sse([b'data: {bad'])
            self.assertIn('JSONDecodeError', result['error'])
        self.assertIs(trace.http.parse_sse, original)
        with self.assertRaisesRegex(RuntimeError, 'probe'):
            with trace.output_markers(marker, 'exception'):
                raise RuntimeError('probe')
        self.assertIs(trace.http.parse_sse, original)


if __name__ == '__main__':
    unittest.main()
