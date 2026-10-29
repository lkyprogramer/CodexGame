"""Apply the isolated P13 HC-region layout probe to the frozen v0.2.7 source."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path


RELATIVE = Path('src/prefill/prefill.cpp')


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('HC_ANCHOR_COUNT: ' + old[:100])
    return source.replace(old, new, 1)


FLAGS = '''// P13 lab-only: same arithmetic and streams, with HC temporaries in the shared region.
inline bool lab_hc_region() {
    static const bool v = [] { const char* e = std::getenv("STRATA_LAB_HC_REGION"); return e && e[0] == '1'; }();
    return v;
}
inline bool lab_hc_keep_loan() {
    static const bool v = [] { const char* e = std::getenv("STRATA_LAB_HC_KEEP_LOAN"); return e && e[0] == '1'; }();
    return lab_hc_region() && v;
}

'''

SIZE = '''// Same padded allocation sequence as the HC suballocator in carve. The region owns these bytes once.
uint64_t lab_hc_set_bytes(size_t T, bool f16_io) {
    Alloc a; a.count_only = true; bool ok = true;
    a.take<uint16_t>(T * (D + (hc_pad() ? XN_PAD : 0)), ok);
    a.take<float>(T * LR, ok); a.take<uint16_t>(T * LR, ok); a.take<float>(T * D, ok);
    if (bf16x2_hc(f16_io)) { a.take<uint16_t>(T * D, ok); a.take<uint16_t>(T * LR, ok); }
    return a.used;
}

'''

CARVE_OLD = '''    m.xn16 = o.take<uint16_t>(T * (D + (hc_pad() ? XN_PAD : 0)), ok); m.lo = o.take<float>(T * LR, ok); m.lo16 = o.take<uint16_t>(T * LR, ok);
    m.gated = o.take<float>(T * D, ok); m.inj = o.take<float>(T * HC, ok);'''
CARVE_NEW = '''    if (!lab_hc_region()) {
        m.xn16 = o.take<uint16_t>(T * (D + (hc_pad() ? XN_PAD : 0)), ok); m.lo = o.take<float>(T * LR, ok); m.lo16 = o.take<uint16_t>(T * LR, ok);
        m.gated = o.take<float>(T * D, ok);
    }
    m.inj = o.take<float>(T * HC, ok);'''
LOW_OLD = '''    if (bf16x2_hc(m.f16_io)) { m.xn16_lo = o.take<uint16_t>(T * D, ok); m.lo16_lo = o.take<uint16_t>(T * LR, ok); }'''
LOW_NEW = '''    if (!lab_hc_region() && bf16x2_hc(m.f16_io)) { m.xn16_lo = o.take<uint16_t>(T * D, ok); m.lo16_lo = o.take<uint16_t>(T * LR, ok); }'''
REGION_OLD = '''        const uint64_t region = std::max({gdn_set_bytes(T), qsa_set_bytes(T, m.cap, m.max_blocks, m.sel_batch,
                                                                           m.attn_batch, s), moe_set_bytes(T, m.g->n_expert, fz)});'''
REGION_NEW = '''        const uint64_t region = std::max({gdn_set_bytes(T), qsa_set_bytes(T, m.cap, m.max_blocks, m.sel_batch,
                                                                           m.attn_batch, s), moe_set_bytes(T, m.g->n_expert, fz),
                                         lab_hc_region() ? lab_hc_set_bytes(T, m.f16_io) : uint64_t(0)});'''
HC_SUBALLOC = '''        if (lab_hc_region()) {
            Alloc h;
            h.base = base; h.cap = region; h.owned = &m.owned;
            m.xn16 = h.take<uint16_t>(T * (D + (hc_pad() ? XN_PAD : 0)), ok);
            m.lo = h.take<float>(T * LR, ok); m.lo16 = h.take<uint16_t>(T * LR, ok);
            m.gated = h.take<float>(T * D, ok);
            if (bf16x2_hc(m.f16_io)) { m.xn16_lo = h.take<uint16_t>(T * D, ok); m.lo16_lo = h.take<uint16_t>(T * LR, ok); }
        }
'''

COUNT_OLD = '''    o.take<uint16_t>(T * (D + (hc_pad() ? XN_PAD : 0)), ok); f(T * LR); o.take<uint16_t>(T * LR, ok);
    f(T * D); f(T * HC); f(T * N); o.take<uint16_t>(T * N, ok); o.take<uint16_t>(T * N, ok);'''
COUNT_NEW = '''    if (!lab_hc_region() || lab_hc_keep_loan()) {
        o.take<uint16_t>(T * (D + (hc_pad() ? XN_PAD : 0)), ok); f(T * LR); o.take<uint16_t>(T * LR, ok);
        f(T * D);
    }
    f(T * HC); f(T * N); o.take<uint16_t>(T * N, ok); o.take<uint16_t>(T * N, ok);'''
COUNT_LOW_OLD = '''    if (bf16x2_hc(f16_io)) { o.take<uint16_t>(T * D, ok); o.take<uint16_t>(T * LR, ok); }'''
COUNT_LOW_NEW = '''    if ((!lab_hc_region() || lab_hc_keep_loan()) && bf16x2_hc(f16_io)) { o.take<uint16_t>(T * D, ok); o.take<uint16_t>(T * LR, ok); }'''
COUNT_REGION_OLD = '''    o.take<uint8_t>((size_t) std::max({gdn_set_bytes(T), qsa_set_bytes(T, cap, max_blocks, 256, 32, s),
                                       moe_set_bytes(T, g.n_expert, fused_layout(T, src))}), ok);'''
COUNT_REGION_NEW = '''    o.take<uint8_t>((size_t) std::max({gdn_set_bytes(T), qsa_set_bytes(T, cap, max_blocks, 256, 32, s),
                                       moe_set_bytes(T, g.n_expert, fused_layout(T, src)),
                                       lab_hc_region() ? lab_hc_set_bytes(T, f16_io) : uint64_t(0)}), ok);'''

MANIFEST = '''    // Qualification only: one record per carve/relayout, never in the half/layer loop.
    if (const char* manifest = std::getenv("STRATA_LAB_HC_MANIFEST"); manifest && manifest[0] == '1') {
        const auto off = [&](const void* p) -> long long {
            return p && o.base ? (long long) ((uintptr_t) p - (uintptr_t) o.base) : -1ll;
        };
        const uint64_t counted = bytes_needed_impl(g, ss, (int64_t) T, false, m.src != nullptr);
        std::fprintf(stderr, "P13_HC_ALLOCATION {\\"variant\\":\\"%s\\",\\"T\\":%llu,\\"borrow_cap\\":%llu,"
            "\\"carve_used\\":%llu,\\"bytes_needed\\":%llu,\\"region_bytes\\":%llu,\\"hc_set_bytes\\":%llu,"
            "\\"gdn_set_bytes\\":%llu,\\"qsa_set_bytes\\":%llu,\\"moe_set_bytes\\":%llu,"
            "\\"f16_io\\":%d,\\"bf16x2_hc\\":%d,\\"hc_pad\\":%d,\\"fused_layout\\":%d,"
            "\\"offsets\\":{\\"region\\":%lld,\\"xn16\\":%lld,\\"lo\\":%lld,\\"lo16\\":%lld,\\"gated\\":%lld,"
            "\\"inj\\":%lld,\\"mixed\\":%lld,\\"mixed_bf\\":%lld,\\"mixed_h\\":%lld,\\"ple_emb\\":%lld}}\\n",
            lab_hc_region() ? (lab_hc_keep_loan() ? "B" : "C") : "A", (unsigned long long) T,
            (unsigned long long) o.cap, (unsigned long long) o.used, (unsigned long long) counted,
            (unsigned long long) m.region_bytes, (unsigned long long) lab_hc_set_bytes(T, m.f16_io),
            (unsigned long long) gdn_set_bytes(T),
            (unsigned long long) qsa_set_bytes(T, m.cap, m.max_blocks, m.sel_batch, m.attn_batch, s),
            (unsigned long long) moe_set_bytes(T, m.g->n_expert, m.fused_bufs),
            (int) m.f16_io, (int) bf16x2_hc(m.f16_io), (int) hc_pad(), (int) m.fused_bufs,
            off(m.region), off(m.xn16), off(m.lo), off(m.lo16), off(m.gated), off(m.inj),
            off(m.mixed), off(m.mixed_bf), off(m.mixed_h), off(m.ple_emb));
    }
'''


def transform(source):
    if 'STRATA_LAB_HC_REGION' in source:
        raise ValueError('HC_ALREADY_PATCHED')
    source = replace_once(source, 'double ms_since(Clock::time_point t)', FLAGS + 'double ms_since(Clock::time_point t)')
    source = replace_once(source, 'uint64_t gdn_set_bytes(size_t T) {', SIZE + 'uint64_t gdn_set_bytes(size_t T) {')
    source = replace_once(source, CARVE_OLD, CARVE_NEW)
    source = replace_once(source, LOW_OLD, LOW_NEW)
    source = replace_once(source, REGION_OLD, REGION_NEW)
    source = replace_once(source, '        m.region_bytes = region;\n', '        m.region_bytes = region;\n' + HC_SUBALLOC)
    source = replace_once(source, COUNT_OLD, COUNT_NEW)
    source = replace_once(source, COUNT_LOW_OLD, COUNT_LOW_NEW)
    source = replace_once(source, COUNT_REGION_OLD, COUNT_REGION_NEW)
    source = replace_once(source, '    m.T = (int64_t) T;\n    return ok;\n', MANIFEST + '    m.T = (int64_t) T;\n    return ok;\n')
    return source


def apply(tree, patch_path):
    tree, patch_path = Path(tree), Path(patch_path)
    path = tree / RELATIVE
    original = path.read_text()
    changed = transform(original)
    if patch_path.exists():
        raise ValueError('HC_PATCH_OUTPUT_EXISTS')
    patch = ''.join(difflib.unified_diff(original.splitlines(keepends=True), changed.splitlines(keepends=True),
                                      fromfile='a/' + str(RELATIVE), tofile='b/' + str(RELATIVE)))
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path.write_text(patch)
    path.write_text(changed)
    return {'file': str(RELATIVE), 'before_sha256': hashlib.sha256(original.encode()).hexdigest(),
            'after_sha256': hashlib.sha256(changed.encode()).hexdigest(),
            'patch_sha256': hashlib.sha256(patch.encode()).hexdigest()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tree', type=Path)
    parser.add_argument('patch', type=Path)
    args = parser.parse_args()
    print(json.dumps(apply(args.tree, args.patch)))
