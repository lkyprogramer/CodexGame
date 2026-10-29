import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('oracle_session_compare', ROOT / 'tools/oracle_replay/compare_session.py')
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)
GEOMETRY = (64, 4, 2, 1, 1, 1, 2, 1, 1, 4, 2, 64, 1, 2, 4, 8, 8, 2)


def fixture(path, *, used=0, checkpoint=True, fmt=1, model=11, ple_size=probe.PLE_BYTES, tails_size=48):
    payload = bytearray(struct.pack('<18q2qQ', *GEOMETRY, 0, 4, 0))
    offsets = {}

    def vec(name, value, count=None):
        payload.extend(struct.pack('<Q', len(value) if count is None else count))
        offsets[name] = 64 + len(payload)
        payload.extend(value)

    def ckpt(name, tokens):
        vec(name + '.ids', struct.pack('<' + str(tokens) + 'i', *range(1, tokens + 1)), tokens)
        vec(name + '.images', b'', 0)
        for part, size in (('gdn', 16), ('ple', ple_size), ('tails', tails_size), ('dead', 16), ('block_pos', 8)):
            vec(name + '.' + part, bytes((i * 3 + 1) % 256 for i in range(size)))
        offsets[name + '.used'] = 64 + len(payload)
        payload.extend(struct.pack('<Q', used))

    ckpt('live', 5)
    payload.extend(struct.pack('<Q', int(checkpoint)))
    if checkpoint:
        ckpt('checkpoint[0]', 2)
    payload.extend(struct.pack('<Q', 3))
    for i in range(3):
        pooled = 0 if i == 2 else 2
        offsets[f'kv[{i}].geometry'] = 64 + len(payload)
        payload.extend(struct.pack('<7q', fmt, 8, 2, 64, 4, pooled, 2))
        for part, size in (('k', 1024), ('v', 1024), ('k_scale', 32), ('v_scale', 32), ('pooled', pooled * 8)):
            vec(f'kv[{i}].{part}', bytes((j * 5 + i) % 256 for j in range(size)))
    header = bytearray(struct.pack('<8sII6Q', b'STRSESS\x01', 1, 64, model, 22, len(payload), 0, 0, 0))
    struct.pack_into('<Q', header, 56, probe.session_hash64(header, 0, 56))
    path.write_bytes(header + payload + struct.pack('<Q8s', probe.session_hash64(payload), b'STRSEND\x01'))
    return offsets


def change(path, offset, *, fix_checksum=True):
    data = bytearray(path.read_bytes())
    data[offset] ^= 1
    if fix_checksum:
        struct.pack_into('<Q', data, len(data) - 16, probe.session_hash64(data, 64, len(data) - 16))
    path.write_bytes(data)


class SessionCompareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.a, self.b = (Path(self.temp.name) / n for n in ('a.session', 'b.session'))
        self.offsets = fixture(self.a)
        fixture(self.b)

    def test_custom_checksum_matches_independently_compiled_cpp_vectors(self):
        # Frozen SessionHasher rounds compiled with the host C++ compiler, not XXH64.
        data = bytes((i * 17 + 3) & 255 for i in range(1025))
        expected = {0: 0x3fdf455f9dcf1e62, 1: 0x3bf0057bb82bae76, 7: 0x4d2b1ae6ca9dc9ab,
                    8: 0x406215aaae58560a, 15: 0x8efc403c723d021e, 31: 0xdb7c95a6d888dcee,
                    32: 0x0facd3340ff96628, 33: 0x851a6ea9cbe767ab, 56: 0xe31c0cf34c77f373,
                    64: 0x342fc0c8324c6c58, 1025: 0x5d5df9d3654e2989}
        for size, value in expected.items():
            self.assertEqual(probe.session_hash64(data, 0, size), value)

    def test_equal_effective_state_and_lru_metadata(self):
        fixture(self.b, used=999)
        result = probe.compare(self.a, self.b, draft_tokens=4)
        self.assertEqual(result['status'], 'PASS', result['issues'])
        self.assertTrue(result['checksums_verified'])
        self.assertGreater(result['total_compared_bytes'], 100)
        self.assertTrue(any(f['field'] == 'live.used' for f in result['excluded']))

    def test_stale_cells_are_excluded_for_each_page_and_head(self):
        # Last page layout is head0 cells4..7, then head1 cells4..7.
        for name, width in (('k', 64), ('v_scale', 2)):
            change(self.b, self.offsets['kv[0].' + name] + (4 * 2 + 1 * 4 + 1) * width)
        result = probe.compare(self.a, self.b, draft_tokens=4)
        self.assertEqual(result['status'], 'PASS', result['issues'])
        excluded = next(f for f in result['excluded'] if f['field'] == 'kv[0].k')
        self.assertEqual(excluded['bytes'], 3 * 2 * 64)

    def test_effective_cell_in_second_head_of_last_page_is_compared(self):
        change(self.b, self.offsets['kv[0].k'] + (4 * 2 + 1 * 4) * 64 + 9)
        result = probe.compare(self.a, self.b, draft_tokens=4)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['first_different_field'], 'kv[0].k')
        self.assertEqual(next(f for f in result['fields'] if f['field'] == 'kv[0].k')['different_bytes'], 1)

    def test_gdn_and_ple_changes_are_not_ignored(self):
        for name in ('live.gdn', 'live.ple'):
            fixture(self.b)
            change(self.b, self.offsets[name])
            result = probe.compare(self.a, self.b, draft_tokens=4)
            self.assertEqual(result['status'], 'FAIL')
            self.assertEqual(result['first_different_field'], name)

    def test_indexer_tail_uses_each_checkpoints_own_token_extent(self):
        # live L=5 => one active row; checkpoint L=2 => two active rows.
        change(self.b, self.offsets['live.tails'] + 8)
        change(self.b, self.offsets['checkpoint[0].tails'] + 16)
        self.assertEqual(probe.compare(self.a, self.b, draft_tokens=4)['status'], 'PASS')
        change(self.b, self.offsets['checkpoint[0].tails'] + 8)
        result = probe.compare(self.a, self.b, draft_tokens=4)
        self.assertEqual(result['first_different_field'], 'checkpoint[0].tails')

    def test_equal_but_wrong_tail_geometry_is_refused(self):
        fixture(self.a, tails_size=64)  # infers block=5, with still self-consistent live pooled_rows=2
        fixture(self.b, tails_size=64)
        result = probe.compare(self.a, self.b, draft_tokens=4)
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('frozen indexer block size must be 4', result['issues'])

    def test_draft_validity_is_required_and_can_be_disjoint(self):
        self.assertEqual(probe.compare(self.a, self.b)['status'], 'BLOCKED')
        change(self.b, self.offsets['kv[2].k'])  # skipped prefix, not an assumed valid cell
        result = probe.compare(self.a, self.b, draft_ranges=[(1, 3), (4, 5)])
        self.assertEqual(result['status'], 'PASS', result['issues'])
        change(self.b, self.offsets['kv[2].k'] + 64)
        result = probe.compare(self.a, self.b, draft_ranges=[(1, 3), (4, 5)])
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['first_different_field'], 'kv[2].k')

    def test_invalid_or_overlapping_draft_ranges_are_refused(self):
        for ranges in ([(-1, 3)], [(0, 6)], [(0, 3), (2, 4)], [(2, 2)]):
            result = probe.compare(self.a, self.b, draft_ranges=ranges)
            self.assertEqual(result['status'], 'FAIL')
            self.assertIn('invalid caller supplied draft ranges', result['issues'])

    def test_format_identity_and_dimensions_are_refused(self):
        fixture(self.b, fmt=0)
        self.assertIn('only INT8 KV format is supported', probe.compare(self.a, self.b, 4)['issues'])
        fixture(self.b, model=12)
        self.assertIn('model/config identity mismatch', probe.compare(self.a, self.b, 4)['issues'])
        fixture(self.b)
        change(self.b, self.offsets['kv[0].geometry'] + 8)  # cells no longer page-ceil(L)
        self.assertIn('invalid KV geometry or extent', probe.compare(self.a, self.b, 4)['issues'])
        fixture(self.b, ple_size=16)
        self.assertIn('invalid frozen PLE history length', probe.compare(self.a, self.b, 4)['issues'])
        fixture(self.b)
        change(self.b, 64 + 2 * 8)  # qsa_interval no longer divides the layer count
        self.assertIn('unsupported QSA layer geometry', probe.compare(self.a, self.b, 4)['issues'])

    def test_payload_header_and_truncation_corruption_fail_closed(self):
        change(self.b, self.offsets['live.gdn'], fix_checksum=False)
        self.assertIn('payload checksum mismatch', probe.compare(self.a, self.b, 4)['issues'])
        fixture(self.b)
        change(self.b, 16, fix_checksum=False)
        self.assertIn('header checksum mismatch', probe.compare(self.a, self.b, 4)['issues'])
        fixture(self.b)
        self.b.write_bytes(self.b.read_bytes()[:-1])
        self.assertIn('session file length mismatch', probe.compare(self.a, self.b, 4)['issues'])

    def test_field_comparison_crosses_chunk_boundary(self):
        previous = probe.CHUNK
        self.addCleanup(setattr, probe, 'CHUNK', previous)
        probe.CHUNK = 7
        change(self.b, self.offsets['live.gdn'] + 9)
        result = probe.compare(self.a, self.b, 4)
        field = next(f for f in result['fields'] if f['field'] == 'live.gdn')
        self.assertEqual(field['first_byte'], 9)
        self.assertEqual(field['different_bytes'], 1)


if __name__ == '__main__':
    unittest.main()
