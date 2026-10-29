"""Process RSS parsing and partial cgroup snapshots; no Docker or GPU is used."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location('sample_resources', Path(__file__).parents[1] / 'deploy/sample_resources.py')
sampler = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sampler)

STATUS = '''Name:\tocr-worker
State:\tS (sleeping)
Uid:\t1234\t1234\t1234\t1234
VmHWM:\t30 kB
VmRSS:\t20 kB
RssAnon:\t12 kB
RssFile:\t7 kB
RssShmem:\t1 kB
'''


class ProcessRssTest(unittest.TestCase):
    def test_parser_keeps_only_name_and_byte_values(self):
        self.assertEqual(sampler.parse_process_status(STATUS), {
            'name': 'ocr-worker', 'rss_bytes': 20 * 1024, 'hwm_bytes': 30 * 1024,
            'anon_bytes': 12 * 1024, 'file_bytes': 7 * 1024, 'shmem_bytes': 1024,
        })

    def test_missing_and_invalid_memory_are_unavailable_not_zero(self):
        for text in (STATUS.replace('VmRSS:\t20 kB\n', ''), STATUS.replace('20 kB', '20 MB')):
            with self.subTest(text=text), self.assertRaises(ValueError):
                sampler.parse_process_status(text)

    def snapshot(self, pids):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        cgroup, proc = root / 'cgroup', root / 'proc'
        cgroup.mkdir()
        proc.mkdir()
        (cgroup / 'cgroup.procs').write_text('\n'.join(str(pid) for pid in pids))
        return cgroup, proc

    def status(self, proc, pid):
        (proc / str(pid)).mkdir()
        (proc / str(pid) / 'status').write_text(STATUS)

    def test_complete_snapshot_sums_process_rss_with_explicit_shared_counting(self):
        cgroup, proc = self.snapshot([11, 12])
        self.status(proc, 11)
        self.status(proc, 12)
        row = sampler.read_process_rss(cgroup, proc)
        self.assertEqual(row['process_rss_status'], 'AVAILABLE')
        self.assertEqual(row['sum_rss_bytes_including_shared'], 40 * 1024)
        self.assertEqual([item['pid'] for item in row['process_rss']], [11, 12])
        self.assertIn('more than once', row['process_rss_note'])

    def test_exited_pid_keeps_readable_entries_but_has_no_partial_total(self):
        cgroup, proc = self.snapshot([11, 12])
        self.status(proc, 11)
        row = sampler.read_process_rss(cgroup, proc)
        self.assertEqual(row['process_rss_status'], 'PARTIAL')
        self.assertIsNone(row['sum_rss_bytes_including_shared'])
        self.assertEqual(row['process_rss'][0]['rss_bytes'], 20 * 1024)
        self.assertEqual(row['process_rss'][1]['status'], 'UNAVAILABLE')
        self.assertIn('FileNotFoundError', row['process_rss'][1]['error'])

    def test_unreadable_pid_is_not_treated_as_zero_rss(self):
        cgroup, proc = self.snapshot([11, 12])
        self.status(proc, 11)
        self.status(proc, 12)
        read_text = Path.read_text

        def read(path, *args, **kwargs):
            if path == proc / '12/status':
                raise PermissionError('status unreadable')
            return read_text(path, *args, **kwargs)

        with patch.object(Path, 'read_text', read):
            row = sampler.read_process_rss(cgroup, proc)
        self.assertEqual(row['process_rss_status'], 'PARTIAL')
        self.assertIsNone(row['sum_rss_bytes_including_shared'])
        self.assertIn('PermissionError', row['process_rss'][1]['error'])

    def test_unreadable_pid_list_is_unknown_and_known_empty_list_is_zero(self):
        cgroup, proc = self.snapshot([])
        row = sampler.read_process_rss(cgroup, proc)
        self.assertEqual(row['process_rss_status'], 'AVAILABLE')
        self.assertEqual(row['sum_rss_bytes_including_shared'], 0)
        (cgroup / 'cgroup.procs').unlink()
        row = sampler.read_process_rss(cgroup, proc)
        self.assertEqual(row['process_rss_status'], 'UNAVAILABLE')
        self.assertIsNone(row['sum_rss_bytes_including_shared'])
        self.assertIn('FileNotFoundError', row['process_rss_error'])


if __name__ == '__main__':
    unittest.main()
