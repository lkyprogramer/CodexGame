import inspect
import json
import time
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from lab import http


class StreamTimingTests(unittest.TestCase):
    def test_reasoning_visible_and_tool_arrival_are_separate(self):
        clock = [100.0]
        records = [(101, {'reasoning_content': 'thinking'}),
                   (103, {'content': 'visible'}),
                   (104, {'tool_calls': [{'index': 0, 'id': 'a', 'function': {'name': 'f', 'arguments': '{}'}}]})]
        def lines():
            for at, delta in records:
                clock[0] = at
                yield 'data: ' + json.dumps({'choices': [{'delta': delta}]})
            clock[0] = 105
            yield 'data: [DONE]'
        with patch('lab.http.time.perf_counter', lambda: clock[0]):
            result = http.parse_sse(lines(), started=100)
        self.assertEqual(result.get('first_reasoning_s'), 1)
        self.assertEqual(result.get('first_visible_s'), 3)
        self.assertEqual(result.get('first_tool_s'), 4)
        self.assertEqual(result.get('first_tool_arguments_s'), 4)
        self.assertEqual(result['first_s'], 1)
        self.assertEqual(result.get('output_event_gaps_s'), [2, 1])
        metrics = http.measurements(result)
        self.assertEqual(metrics.get('visible_ttft_s'), 3)
        self.assertIsNone(metrics['generated_tokens'])
        self.assertIsNone(metrics.get('token_itl_ms'))

    def test_empty_role_delta_does_not_become_first_output(self):
        clock = [100.0]
        def lines():
            yield 'data: {"choices":[{"delta":{"role":"assistant"}}]}'
            clock[0] = 102
            yield 'data: {"choices":[{"delta":{"content":"x"}}]}'
            yield 'data: [DONE]'
        with patch('lab.http.time.perf_counter', lambda: clock[0]):
            result = http.parse_sse(lines(), started=100)
        self.assertEqual(result.get('output_event_times_s'), [2])


class SlowHandler(BaseHTTPRequestHandler):
    mode = 'slow'
    def log_message(self, *_):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers['Content-Length']))
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.end_headers()
        try:
            if self.mode == 'heartbeat':
                for _ in range(30):
                    self.wfile.write(b': ping\n\n'); self.wfile.flush(); time.sleep(.01)
            elif self.mode == 'partial':
                for _ in range(30):
                    self.wfile.write(b' '); self.wfile.flush(); time.sleep(.01)
            else:
                time.sleep(.08)
                self.wfile.write(b'data: {"choices":[{"delta":{"content":"OK"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n')
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


class StreamingDeadlineTests(unittest.TestCase):
    def call(self, mode, **options):
        self.assertIn('idle_timeout_s', inspect.signature(http.chat).parameters,
                      'Long prefill needs an explicit idle timeout separate from absolute deadline')
        handler = type('Handler', (SlowHandler,), {'mode': mode})
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            return http.chat(f'http://127.0.0.1:{server.server_port}', {'messages': [], 'max_tokens': 4}, **options)
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_slow_prefill_succeeds_with_larger_idle_budget(self):
        result = self.call('slow', timeout=.5, idle_timeout_s=.25)
        self.assertIsNone(result['error'])
        self.assertEqual(result['text'], 'OK')

    def test_idle_timeout_is_enforced_independently(self):
        result = self.call('slow', timeout=.5, idle_timeout_s=.02)
        self.assertTrue(result['error'])
        self.assertLess(result['total_s'], .2)

    def test_heartbeats_do_not_extend_absolute_deadline(self):
        result = self.call('heartbeat', timeout=.06, idle_timeout_s=.04)
        self.assertIn('Absolute', result['error'])
        self.assertLess(result['total_s'], .2)

    def test_partial_sse_line_cannot_bypass_absolute_deadline(self):
        result = self.call('partial', timeout=.06, idle_timeout_s=.04)
        self.assertIn('Absolute', result['error'])
        self.assertLess(result['total_s'], .2)
