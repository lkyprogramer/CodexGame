import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / 'tools/v027/trace_dequant.py'
spec = importlib.util.spec_from_file_location('p10_trace_tested', PATH)
trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace)


class MarkerTests(unittest.TestCase):
    def test_first_marker_uses_existing_nonempty_sse_classification(self):
        class Marker:
            def __init__(self): self.names = []
            def mark(self, name): self.names.append(name)
        marker = Marker()
        lines = [b'data: {"choices":[{"delta":{"role":"assistant"}}]}\n',
                 b'data: {"prompt_progress":{"processed":16384}}\n',
                 b'data: {"choices":[{"delta":{"content":"x"}}]}\n',
                 b'data: {"choices":[{"delta":{"content":"y"}}]}\n', b'data: [DONE]\n']
        expected = trace.http.parse_sse(iter(lines))
        original = trace.http.parse_sse
        with trace.first_output_marker(marker, 'case'):
            actual = trace.http.parse_sse(iter(lines))
        self.assertEqual(actual['text'], expected['text'])
        self.assertTrue(actual['done'])
        self.assertEqual(marker.names, ['P10_FIRST/case'])
        self.assertIs(trace.http.parse_sse, original)

    def test_parser_restored_if_observation_scope_fails(self):
        original = trace.http.parse_sse
        with self.assertRaisesRegex(RuntimeError, 'probe'):
            with trace.first_output_marker(None, 'case'):
                raise RuntimeError('probe')
        self.assertIs(trace.http.parse_sse, original)


if __name__ == '__main__':
    unittest.main()
