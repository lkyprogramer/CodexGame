"""Exercise the actual Guard class without importing campaign/remote dependencies."""
import ast
import contextlib
from pathlib import Path
import signal
import subprocess
import threading
import time
import unittest
from unittest.mock import Mock


SOURCE = Path(__file__).resolve().parents[1] / 'tools/v027/run_reference_logits.py'
GUARD = next(node for node in ast.parse(SOURCE.read_text()).body if isinstance(node, ast.ClassDef) and node.name == 'Guard')


class ReferenceGuardTests(unittest.TestCase):
    def guard(self, status, inventory, error):
        namespace = dict(Path=Path, time=time, threading=threading, contextlib=contextlib,
                         signal=signal, subprocess=subprocess, os=Mock(), dump=Mock(),
                         gpu_inventory=Mock(side_effect=inventory), available_mib=Mock(return_value=8192),
                         validate_gpu_ownership=Mock(side_effect=error))
        # Compile only the real class to keep tests local and independent of the
        # campaign imports. No process, thread or GPU query is actually started.
        exec(compile(ast.Module(body=[GUARD], type_ignores=[]), str(SOURCE), 'exec'), namespace)
        proc = Mock(pid=123, poll=Mock(side_effect=status))
        guard = namespace['Guard']({}, Path('/tmp'), proc, '/tmp/owned-engine', 60)
        guard.stop = Mock(wait=Mock(side_effect=[False, True]))
        guard.terminate = Mock()
        return guard, namespace

    @staticmethod
    def gpu(pids):
        return {'compute_processes': pids, 'temperature_c': 45}

    def test_exited_owner_and_fresh_empty_gpu_is_normal(self):
        guard, ns = self.guard([None, 0], [self.gpu(['123']), self.gpu([])], FileNotFoundError('/proc/123/exe'))
        guard.loop()
        self.assertIsNone(guard.reason)
        guard.terminate.assert_not_called()
        self.assertEqual(ns['gpu_inventory'].call_count, 2)
        self.assertEqual(ns['gpu_inventory'].call_args_list[1].args, ('0',))
        ns['validate_gpu_ownership'].assert_called_once_with(['123'], 123, guard.exe)

    def test_exited_owner_and_fresh_stale_owner_gpu_row_is_normal(self):
        guard, ns = self.guard([None, 0],
                               [self.gpu(['123']), self.gpu(['123, [No data], 3002'])],
                               FileNotFoundError('/proc/123/exe'))
        guard.loop()
        self.assertIsNone(guard.reason)
        guard.terminate.assert_not_called()
        self.assertEqual(ns['gpu_inventory'].call_count, 2)

    def test_exited_owner_with_stale_owner_and_foreign_gpu_pid_preserves_failure(self):
        guard, ns = self.guard([None, 0],
                               [self.gpu(['123']), self.gpu(['123, [No data], 3002', '456, foreign, 1000'])],
                               FileNotFoundError('/proc/123/exe'))
        guard.loop()
        self.assertEqual(guard.reason, '/proc/123/exe')
        guard.terminate.assert_called_once_with()
        self.assertEqual(ns['gpu_inventory'].call_count, 2)

    def test_still_running_owner_preserves_failure(self):
        guard, ns = self.guard([None, None], [self.gpu(['123'])], FileNotFoundError('/proc/123/exe'))
        guard.loop()
        self.assertEqual(guard.reason, '/proc/123/exe')
        guard.terminate.assert_called_once_with()
        self.assertEqual(ns['gpu_inventory'].call_count, 1)

    def test_exited_owner_with_foreign_gpu_pid_preserves_failure(self):
        guard, ns = self.guard([None, 0], [self.gpu(['123']), self.gpu(['456'])], FileNotFoundError('/proc/123/exe'))
        guard.loop()
        self.assertEqual(guard.reason, '/proc/123/exe')
        guard.terminate.assert_called_once_with()
        self.assertEqual(ns['gpu_inventory'].call_count, 2)

    def test_other_ownership_exception_preserves_failure(self):
        guard, ns = self.guard([None], [self.gpu(['123'])], RuntimeError('GPU_OWNER_MISMATCH'))
        guard.loop()
        self.assertEqual(guard.reason, 'GPU_OWNER_MISMATCH')
        guard.terminate.assert_called_once_with()
        self.assertEqual(ns['gpu_inventory'].call_count, 1)

    def test_finish_joins_monitor_before_shutdown(self):
        guard, ns = self.guard([], [], None)
        order = []
        guard.stop.set = Mock(side_effect=lambda: order.append('stop'))
        guard.thread = Mock(join=Mock(side_effect=lambda **_: order.append('join')),
                            is_alive=Mock(return_value=False))
        guard.finish()
        self.assertEqual(order, ['stop', 'join'])
        guard.terminate.assert_not_called()
        ns['gpu_inventory'].assert_not_called()

    def test_finish_rejects_a_monitor_that_did_not_stop(self):
        guard, _ = self.guard([], [], None)
        guard.thread = Mock(is_alive=Mock(return_value=True))
        with self.assertRaisesRegex(RuntimeError, 'GUARD_MONITOR_NOT_STOPPED'):
            guard.finish()

    def test_finish_preserves_an_existing_guard_failure(self):
        guard, _ = self.guard([], [], None)
        guard.thread = Mock(is_alive=Mock(return_value=False))
        guard.reason = 'GPU_OWNER_MISMATCH'
        with self.assertRaisesRegex(RuntimeError, 'GPU_OWNER_MISMATCH'):
            guard.finish()
        self.assertEqual(guard.reason, 'GPU_OWNER_MISMATCH')

    def test_native_protocol_stops_monitor_before_quit(self):
        import queue
        import tempfile
        from types import SimpleNamespace

        native = next(node for node in ast.parse(SOURCE.read_text()).body
                      if isinstance(node, ast.FunctionDef) and node.name == 'run_native')
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            events = []

            class ProtocolGuard:
                reason = None
                def __init__(self, *_): pass
                def __enter__(self): return self
                def __exit__(self, *_): pass
                def finish(self): events.append('monitor-stopped')

            @contextlib.contextmanager
            def memory(*_):
                yield SimpleNamespace(stage=None)

            def write(command):
                if command.startswith('GEN '):
                    (folder / 'first.0').write_bytes(bytes(248320 * 4))
                elif command.startswith('SAVE '):
                    (folder / 'session.bin').write_bytes(b'abc')
                elif command == 'QUIT\n':
                    self.assertEqual(events, ['monitor-stopped'])
                    events.append('quit')

            proc = Mock(returncode=0, pid=123,
                        stdout=['READY 131072\n', 'T 1\n', 'DONE\n', 'SAVED 4095 3 1\n'])
            proc.stdin.write.side_effect = write
            class PumpThread:
                def __init__(self, target, **_): self.target = target
                def start(self): self.target()
                def join(self, **_): pass

            ns = dict(Path=Path, queue=queue, threading=SimpleNamespace(Thread=PumpThread),
                      subprocess=SimpleNamespace(Popen=Mock(return_value=proc), PIPE=subprocess.PIPE),
                      make_run_config=Mock(return_value={'exe': 'fixture', 'cwd': tmp, 'args': [], 'env': {}}),
                      clean_env=lambda: {}, dump=Mock(), Guard=ProtocolGuard, MemorySampler=memory,
                      read_ids=lambda path: [], fnv_ids=lambda _: 'fixture', WIDTH=248320)
            exec(compile(ast.Module(body=[native], type_ignores=[]), str(SOURCE), 'exec'), ns)
            case = {'name': 'fixture', 'tokens': {'path': 'tokens'}, 'prefix': {'path': 'prefix'}}
            ns['run_native']({'deployed_repo': tmp}, folder, [case], save_session=True)
            self.assertEqual(events, ['monitor-stopped', 'quit'])
            proc.wait.assert_called_once_with(timeout=60)


if __name__ == '__main__':
    unittest.main()
