"""Compare effective logical state in frozen Strata v0.2.7 SAVE format v1.

SAVE has no draft computed extent. The caller must establish draft_tokens from
execution evidence; without it main state is compared but the result is BLOCKED.
This does not inspect resident maps, PLE token scratch or MTP execution batches.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import mmap
from pathlib import Path
import struct

MASK = (1 << 64) - 1
P1, P2, P3, P4, P5 = (0x9E3779B185EBCA87, 0xC2B2AE3D27D4EB4F,
                      0x165667B19E3779F9, 0x85EBCA77C2B2AE63, 0x27D4EB2F165667C5)
CHUNK = 1 << 20
STATE_PARTS = ('gdn', 'ple', 'tails', 'dead', 'block_pos')
KV_PARTS = ('k', 'v', 'k_scale', 'v_scale', 'pooled')
# Frozen include/strata/kernels/ngram.hpp: NG_HIST=9, NG_HC_DIM=10240.
PLE_BYTES = 9 * 10240 * 4


def require(ok, why):
    if not ok:
        raise ValueError(why)


def rotl(x, r):
    x &= MASK
    return ((x << r) | (x >> (64 - r))) & MASK


def round1(acc, word):
    return rotl((acc + word * P2) & MASK, 31) * P1 & MASK


def session_hash64(data, start=0, end=None):
    """Exact custom SessionHasher; it is not standard xxHash64 (file.cpp:820)."""
    end = len(data) if end is None else end
    lanes = [(P1 + P2) & MASK, P2, 0, (-P1) & MASK]
    cursor = start
    while cursor + 32 <= end:
        words = struct.unpack_from('<4Q', data, cursor)
        for i in range(4):
            lanes[i] = round1(lanes[i], words[i])
        cursor += 32
    h = sum(rotl(lane, r) for lane, r in zip(lanes, (1, 7, 12, 18))) & MASK
    for lane in lanes:
        h = ((h ^ round1(0, lane)) * P1 + P4) & MASK
    h = (h + end - start) & MASK
    while cursor + 8 <= end:
        h = (rotl(h ^ round1(0, struct.unpack_from('<Q', data, cursor)[0]), 27) * P1 + P4) & MASK
        cursor += 8
    while cursor < end:
        h = rotl(h ^ (data[cursor] * P5 & MASK), 11) * P1 & MASK
        cursor += 1
    h ^= h >> 33
    h = h * P2 & MASK
    h ^= h >> 29
    h = h * P3 & MASK
    return (h ^ (h >> 32)) & MASK


@dataclass(frozen=True)
class Span:
    offset: int
    size: int


class Session:
    def __init__(self, path):
        self.path = Path(path)
        self.file = self.path.open('rb')
        self.data = None
        try:
            require(self.path.stat().st_size >= 80, 'session below minimum length')
            self.data = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
            self._parse()
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.data is not None:
            self.data.close()
        self.file.close()

    def take(self, size):
        require(0 <= size <= self.limit - self.at, 'payload ends early')
        result = Span(self.at, size)
        self.at += size
        return result

    def number(self, signed=False):
        span = self.take(8)
        return struct.unpack_from('<q' if signed else '<Q', self.data, span.offset)[0]

    def vector(self, element=1):
        count = self.number()
        require(count <= (self.limit - self.at) // element, 'element count exceeds payload')
        return self.take(count * element)

    def checkpoint(self, name):
        fields = {name + '.ids': self.vector(4), name + '.images': self.vector(16)}
        for part in STATE_PARTS:
            fields[name + '.' + part] = self.vector()
        used = self.take(8)
        return fields, used

    def _parse(self):
        data = self.data
        require(data[:8] == b'STRSESS\x01', 'wrong session magic')
        version, header = struct.unpack_from('<II', data, 8)
        model, config, payload, r0, r1, checksum = struct.unpack_from('<6Q', data, 16)
        require(version == 1 and header == 64 and r0 == r1 == 0, 'unsupported session header')
        require(checksum == session_hash64(data, 0, 56), 'header checksum mismatch')
        require(payload == len(data) - 80, 'session file length mismatch')
        require(data[-8:] == b'STRSEND\x01', 'wrong session end marker')
        require(struct.unpack_from('<Q', data, len(data) - 16)[0] == session_hash64(data, 64, 64 + payload),
                'payload checksum mismatch')
        self.identity = (model, config)
        self.at, self.limit = 64, 64 + payload
        self.fields = {'identity': Span(16, 16), 'geometry': self.take(18 * 8), 'layer_range': self.take(16),
                       'cvec': self.take(8)}
        self.geometry = struct.unpack_from('<18q', data, self.fields['geometry'].offset)
        require(all(g > 0 for g in self.geometry), 'invalid model geometry')
        require(self.geometry[1] >= self.geometry[2] and self.geometry[1] % self.geometry[2] == 0,
                'unsupported QSA layer geometry')
        self.layer_range = struct.unpack_from('<2q', data, self.fields['layer_range'].offset)
        require(self.layer_range == (0, self.geometry[1]), 'only whole-model sessions are supported')
        require(struct.unpack_from('<Q', data, self.fields['cvec'].offset)[0] in (0, 1), 'invalid cvec flag')
        live, used = self.checkpoint('live')
        self.fields.update(live)
        self.checkpoints = [('live', live)]
        self.excluded = [('live.used', used, 'checkpoint LRU metadata')]
        self.tokens = live['live.ids'].size // 4
        require(0 < self.tokens <= 131072, 'invalid live token count')
        self._validate_checkpoint(live, 'live')
        checkpoints = self.number()
        require(checkpoints <= (self.limit - self.at) // 72, 'checkpoint count exceeds payload')
        self.checkpoint_count = checkpoints
        for i in range(checkpoints):
            name = f'checkpoint[{i}]'
            fields, used = self.checkpoint(name)
            self._validate_checkpoint(fields, name)
            ids = fields[name + '.ids']
            require(ids.size <= live['live.ids'].size and
                    data[ids.offset:ids.offset + ids.size] == data[live['live.ids'].offset:live['live.ids'].offset + ids.size],
                    'checkpoint is not a live token prefix')
            self.fields.update(fields)
            self.checkpoints.append((name, fields))
            self.excluded.append((name + '.used', used, 'checkpoint LRU metadata'))
        nkv = self.number()
        layers, interval = self.geometry[1:3]
        require(layers % interval == 0 and nkv == layers // interval + 1, 'expected main QSA layers plus MTP layer')
        self.kv = []
        for i in range(nkv):
            header_span = self.take(7 * 8)
            geometry = struct.unpack_from('<7q', data, header_span.offset)
            fmt, cells, heads, dim, page, pooled, idx = geometry
            require(fmt in (1, 17), 'only INT8 KV format is supported')
            require(heads == self.geometry[10] and dim == self.geometry[11] and dim % 64 == 0 and
                    page > 0 and cells == (self.tokens + page - 1) // page * page and idx == self.geometry[13],
                    'invalid KV geometry or extent')
            draft = i == nkv - 1
            require((pooled == 0) if draft else (pooled == self.tokens // self.idx_block + 1), 'invalid pooled extent')
            parts = [self.vector() for _ in KV_PARTS]
            expected = (cells * heads * dim, cells * heads * dim,
                        cells * heads * (dim // 64 * 2), cells * heads * (dim // 64 * 2), pooled * idx * 4)
            require(tuple(p.size for p in parts) == expected, 'KV part length differs from geometry')
            self.fields[f'kv[{i}].geometry'] = header_span
            self.kv.append((geometry, parts))
        require(self.at == self.limit, 'unparsed session payload bytes')

    def _validate_checkpoint(self, fields, name):
        g = self.geometry
        nqsa = g[1] // g[2]
        ngdn = g[1] - nqsa
        expected_gdn = ngdn * (g[3] * g[5] * g[3] + g[7] * (g[6] - 1)) * 4
        require(fields[name + '.gdn'].size == expected_gdn, 'invalid GDN state length')
        require(fields[name + '.ple'].size == PLE_BYTES, 'invalid frozen PLE history length')
        require(fields[name + '.dead'].size == nqsa * g[13] * 4 and
                fields[name + '.block_pos'].size == nqsa * 4, 'invalid indexer state length')
        tail_unit = nqsa * g[13] * 4
        require(fields[name + '.tails'].size % tail_unit == 0, 'invalid indexer tail length')
        idx_block = fields[name + '.tails'].size // tail_unit + 1
        require(idx_block == 4, 'frozen indexer block size must be 4')
        if hasattr(self, 'idx_block'):
            require(idx_block == self.idx_block, 'inconsistent indexer tail length')
        else:
            self.idx_block = idx_block
        ids = fields[name + '.ids']
        require(ids.size > 0 and all(v[0] >= 0 for v in struct.iter_unpack('<i',
                self.data[ids.offset:ids.offset + ids.size])), 'invalid checkpoint token IDs')
        images = fields[name + '.images']
        previous = -1
        for start, _ in struct.iter_unpack('<qQ', self.data[images.offset:images.offset + images.size]):
            require(previous < start < ids.size // 4, 'invalid image keys')
            previous = start


def _compare_ranges(a, b, name, ranges):
    result = {'field': name, 'bytes': 0, 'different_bytes': 0, 'first_byte': None,
              'first_file_offsets': None, 'bitwise_equal': True}
    for left, right, size in ranges:
        for off in range(0, size, CHUNK):
            n = min(CHUNK, size - off)
            x, y = a.data[left + off:left + off + n], b.data[right + off:right + off + n]
            if x != y:
                if result['first_byte'] is None:
                    first = next(i for i, pair in enumerate(zip(x, y)) if pair[0] != pair[1])
                    result['first_byte'] = result['bytes'] + first
                    result['first_file_offsets'] = [left + off + first, right + off + first]
                result['different_bytes'] += sum(u != v for u, v in zip(x, y))
                result['bitwise_equal'] = False
            result['bytes'] += n
    return result


def compare(left, right, draft_tokens=None, draft_ranges=None):
    result = {'status': 'FAIL', 'scope': 'logical_saved_state', 'left': str(left), 'right': str(right),
              'fields': [], 'excluded': [], 'issues': [], 'total_compared_bytes': 0,
              'total_excluded_bytes': 0, 'first_different_field': None,
              'limitations': ['SAVE omits resident maps, PLE token scratch and actual MTP execution batches',
                             'draft validity is supplied by the caller, not inferred from SAVE'],
              'caller_supplied_draft_tokens': draft_tokens, 'caller_supplied_draft_ranges': draft_ranges}
    sessions = []
    try:
        a = Session(left)
        sessions.append(a)
        b = Session(right)
        sessions.append(b)
        require(a.identity == b.identity, 'model/config identity mismatch')
        require(a.geometry == b.geometry and a.layer_range == b.layer_range, 'session geometry mismatch')
        require(a.tokens == b.tokens and a.checkpoint_count == b.checkpoint_count, 'live/checkpoint count mismatch')
        require(a.fields.keys() == b.fields.keys(), 'session field set mismatch')
        require(draft_tokens is None or type(draft_tokens) is int and 0 <= draft_tokens <= a.tokens,
                'invalid caller supplied draft extent')
        require(draft_ranges is None or draft_tokens is None, 'supply draft tokens or ranges, not both')
        if draft_ranges is None and draft_tokens is not None:
            draft_ranges = [(0, draft_tokens)] if draft_tokens else []
        if draft_ranges is not None:
            previous = 0
            for start, end in draft_ranges:
                require(type(start) is int and type(end) is int and previous <= start < end <= a.tokens,
                        'invalid caller supplied draft ranges')
                previous = end
        result['live_tokens'] = a.tokens
        result['kv_layers'] = len(a.kv)
        result['checksums_verified'] = True
        for name, span in a.fields.items():
            other = b.fields[name]
            require(span.size == other.size, 'state field length mismatch: ' + name)
            if name.endswith('.tails'):
                prefix = name[:-6]
                n = a.fields[prefix + '.ids'].size // 4
                active = n % a.idx_block * a.geometry[13] * 4
                stride = (a.idx_block - 1) * a.geometry[13] * 4
                ranges = [(span.offset + off, other.offset + off, active) for off in range(0, span.size, stride)]
                excluded = span.size - sum(r[2] for r in ranges)
                if excluded:
                    result['excluded'].append({'field': name, 'bytes': excluded,
                                              'reason': 'indexer tail slots overwritten before the next reduction'})
            else:
                ranges = [(span.offset, other.offset, span.size)]
            result['fields'].append(_compare_ranges(a, b, name, ranges))
        for (name, span, reason), (_, other, _) in zip(a.excluded, b.excluded):
            require(span.size == other.size, 'excluded metadata size mismatch')
            result['excluded'].append({'field': name, 'bytes': span.size, 'reason': reason})
        for i, ((geometry, parts), (other_geometry, other_parts)) in enumerate(zip(a.kv, b.kv)):
            require(geometry == other_geometry, f'KV geometry mismatch: {i}')
            _, cells, heads, dim, page, _, _ = geometry
            draft = i == len(a.kv) - 1
            valid = draft_ranges if draft else [(0, a.tokens)]
            for part, span, other, width in zip(KV_PARTS, parts, other_parts, (dim, dim, dim // 64 * 2, dim // 64 * 2, 0)):
                name = f'kv[{i}].{part}'
                require(span.size == other.size, 'KV part size mismatch: ' + name)
                if part == 'pooled':
                    ranges = [(span.offset, other.offset, span.size)]
                    excluded = 0
                elif valid is None:
                    ranges = []
                    excluded = span.size
                else:
                    ranges = []
                    for start, end in valid:
                        for pg in range(start // page, (end + page - 1) // page):
                            lo, hi = max(start, pg * page) - pg * page, min(end, (pg + 1) * page) - pg * page
                            for head in range(heads):
                                off = ((pg * heads + head) * page + lo) * width
                                ranges.append((span.offset + off, other.offset + off, (hi - lo) * width))
                    excluded = span.size - sum(end - start for start, end in valid) * heads * width
                result['fields'].append(_compare_ranges(a, b, name, ranges))
                if excluded:
                    result['excluded'].append({'field': name, 'bytes': excluded,
                        'reason': 'draft computed extent not supplied' if valid is None else
                                  'cells beyond caller supplied draft extent' if draft else 'stale last-page cells'})
        for field in result['fields']:
            result['total_compared_bytes'] += field['bytes']
            if not field['bitwise_equal'] and result['first_different_field'] is None:
                result['first_different_field'] = field['field']
        result['total_excluded_bytes'] = sum(f['bytes'] for f in result['excluded'])
        if result['first_different_field']:
            result['issues'].append('effective saved-state bytes differ')
        if not result['issues']:
            result['status'] = 'BLOCKED' if draft_ranges is None else 'PASS'
            if draft_ranges is None:
                result['issues'].append('SAVE does not establish the MTP computed extent')
    except (OSError, ValueError, TypeError, struct.error) as exc:
        result['issues'].append(str(exc))
    finally:
        for session in sessions:
            session.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('left', type=Path)
    parser.add_argument('right', type=Path)
    parser.add_argument('--draft-tokens', type=int,
                        help='computed MTP extent established by separate execution evidence')
    parser.add_argument('--draft-ranges', type=Path,
                        help='JSON object with ranges [[start,end],...] established by separate execution evidence')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    ranges = json.loads(args.draft_ranges.read_text())['ranges'] if args.draft_ranges else None
    result = compare(args.left, args.right, args.draft_tokens, ranges)
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    print(text if not args.output else json.dumps({k: result[k] for k in ('status', 'issues', 'first_different_field')}))
    raise SystemExit(0 if result['status'] == 'PASS' else 2)


if __name__ == '__main__':
    main()
