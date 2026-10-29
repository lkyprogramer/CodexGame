"""P23 opt-in host-only HC cost trace on frozen P21 sources.

No new device work/sync/fold, math, dispatch, or scheduling operations. H2D
counters describe submitted expert bytes; only completed error-free requests
qualify them. Existing timer wait-copy intervals are diagnostic, not performance
samples or a sum-of-copies critical-path estimate.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re

SOURCE_SHA256 = {
    'src/prefill/prefill.cpp': 'f5e9137eea2781e09ca3e4e143586fab593d05be495e89d3ec69bdd99ea22b95',
    'src/program/generate.cpp': '00a29b0543d5562eb83a98e02a356032dcf1dc7bea4f43c7a7c115d938f222bd',
}
PATTERN = re.compile(r'\n/\* P23_COST_BEGIN ([a-z0-9_]+) \*/\n.*?\n/\* P23_COST_END \1 \*/\n', re.S)


def block(name, body):
    return '\n/* P23_COST_BEGIN ' + name + ' */\n' + body + '\n/* P23_COST_END ' + name + ' */\n'


def blocks(source):
    return [m.group() for m in PATTERN.finditer(source)]


def strip_cost(source):
    return PATTERN.sub('', source)


def once(source, anchor, extra, *, before=False):
    if source.count(anchor) != 1:
        raise ValueError('COST_ANCHOR_COUNT: ' + anchor[:100])
    return source.replace(anchor, extra + anchor if before else anchor + extra, 1)


def identity(name, source):
    if '/* P23_COST_BEGIN ' in source:
        raise ValueError('COST_ALREADY_PATCHED: ' + name)
    if hashlib.sha256(source.encode()).hexdigest() != SOURCE_SHA256[name]:
        raise ValueError('COST_SOURCE_IDENTITY: ' + name)


HELPERS = r'''#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <cstdint>
namespace {
inline bool lab_hc_cost_on() {
    static const bool on = [] { const char* e = std::getenv("STRATA_LAB_HC_COST"); return e && std::strcmp(e, "1") == 0; }();
    return on;
}
std::string lab_hc_cost_i32(const int32_t* p, size_t n) {
    if (!p) return "null";
    std::string out = "[";
    for (size_t i = 0; i < n; ++i) { if (i) out += ','; out += std::to_string(p[i]); }
    return out + ']';
}
std::string lab_hc_cost_cpu(const std::vector<char>& cpu, int64_t ne) {
    std::string out = "[";
    for (int64_t i = 0; i < ne; ++i) { if (i) out += ','; out += cpu.empty() ? "0" : std::to_string((int) cpu[(size_t) i]); }
    return out + ']';
}
template<class Pairs> std::string lab_hc_cost_pairs(const Pairs& pairs) {
    std::string out = "[";
    for (size_t i = 0; i < pairs.size(); ++i) {
        if (i) out += ',';
        out += '[' + std::to_string(pairs[i].first) + ',' + std::to_string(pairs[i].second) + ']';
    }
    return out + ']';
}
template<class Cache> void lab_hc_cost_cache(const char* mode, const Cache& cache,
                                            const std::vector<int32_t>& host_res, int64_t ne) {
    if (!lab_hc_cost_on()) return;
    std::string offsets = "[";
    for (int64_t s = 0; s <= cache.slots(); ++s) { if (s) offsets += ','; offsets += std::to_string(cache.slot_offset(s)); }
    offsets += ']';
    std::fprintf(stderr, "P23_CACHE {\"mode\":\"%s\",\"slots\":%lld,\"full_slots\":%lld,\"cache_bytes\":%lld,\"variable_offsets\":%s,\"n_expert\":%lld,\"slot_offsets\":%s,\"host_res\":%s}\n",
                 mode, (long long) cache.slots(), (long long) cache.full_slots(), (long long) cache.bytes(),
                 cache.slot_offsets() != nullptr ? "true" : "false", (long long) ne,
                 offsets.c_str(), lab_hc_cost_i32(host_res.data(), host_res.size()).c_str());
}
} // namespace'''


LAYER = r'''                        if (lab_hc_cost_on())
                            std::fprintf(stderr, "P23_LAYER {\"p0\":%lld,\"T\":%lld,\"layer\":%lld,\"use_mmq\":%s,\"fused_l\":%s,\"fused_nat\":%s,\"native\":%s,\"gu_type\":%d,\"d_type\":%d,\"blob_bytes\":%llu,\"stream_all\":%s,\"route_counts_available\":true,\"host_res\":%s,\"cnt\":%s,\"on_cpu\":%s,\"n_cpu\":%lld,\"rows_cpu\":%lld,\"n_stream\":%lld}\n",
                                (long long) p0, (long long) T, (long long) l, use_mmq ? "true" : "false",
                                fused_l ? "true" : "false", fused_nat ? "true" : "false", lay.native ? "true" : "false", mmq_gt, mmq_dt,
                                (unsigned long long) lay.blob_bytes(l), stream_all ? "true" : "false", lab_hc_cost_i32(m.host_res ? m.host_res + (size_t) l * m.g->n_expert : nullptr, (size_t) m.g->n_expert).c_str(),
                                lab_hc_cost_i32(m.cnt.data(), (size_t) m.g->n_expert).c_str(), lab_hc_cost_cpu(on_cpu, m.g->n_expert).c_str(),
                                (long long) n_cpu, (long long) rows_cpu, (long long) n_stream);'''

FUSED = r'''                    if (lab_hc_cost_on() && fused_l)
                        std::fprintf(stderr, "P23_LAYER {\"p0\":%lld,\"T\":%lld,\"layer\":%lld,\"use_mmq\":%s,\"fused_l\":true,\"fused_nat\":%s,\"native\":%s,\"gu_type\":%d,\"d_type\":%d,\"blob_bytes\":%llu,\"stream_all\":%s,\"route_counts_available\":false,\"host_res\":%s,\"cnt\":null,\"on_cpu\":null}\n",
                            (long long) p0, (long long) T, (long long) l, use_mmq ? "true" : "false", fused_nat ? "true" : "false",
                            lay.native ? "true" : "false", mmq_gt, mmq_dt, (unsigned long long) lay.blob_bytes(l), stream_all ? "true" : "false",
                            lab_hc_cost_i32(m.host_res ? m.host_res + (size_t) l * m.g->n_expert : nullptr, (size_t) m.g->n_expert).c_str());'''


def prefill(source):
    identity('src/prefill/prefill.cpp', source)
    source = once(source, '#include "strata/kernels/fused_gr.hpp"', block('helpers', HELPERS), before=True)
    start, end = source.index('bool Prefill::run_impl('), source.index('void Prefill::lm_release()')
    prefix, source, suffix = source[:start], source[start:end], source[end:]
    source = once(source, '        const bool stream_all = m.ring > STAGE && T >= stream_all_min() && m.src != nullptr;', block('chunk', r'''        if (lab_hc_cost_on())
            std::fprintf(stderr, "P23_CHUNK {\"p0\":%lld,\"T\":%lld,\"allocated_T\":%lld,\"LB\":%lld,\"LE\":%lld,\"n_expert\":%lld,\"K\":%lld,\"stream_all\":%s,\"ring\":%d}\n",
                         (long long) p0, (long long) T, (long long) m.T, (long long) LB, (long long) LE,
                         (long long) m.g->n_expert, (long long) K, stream_all ? "true" : "false", m.ring);'''))
    source = once(source, '        size_t issued = 0, consumed = 0;', block('counters', '''        // Main thread alone owns inline/staged counters; issuer alone writes issuer counters.
        // The issuer values are read only after its existing join, like iss_streamed.
        uint64_t cost_inline_bytes = 0, cost_inline_count = 0;
        uint64_t cost_issuer_bytes = 0, cost_issuer_count = 0;
        uint64_t cost_staged_bytes = 0, cost_staged_count = 0;'''))
    copies = [
        ('inline_pinned', '\n                    cudaMemcpyAsync(m.stage_dev[sl], en.blob, bytes, cudaMemcpyHostToDevice, m.copy);', 'inline', 'bytes'),
        ('inline_stager', '\n                    cudaMemcpyAsync(m.stage_dev[sl], hb, bytes, cudaMemcpyHostToDevice, m.copy);', 'inline', 'bytes'),
        ('issuer_pinned', '\n                        cudaMemcpyAsync(m.stage_dev[sl], en.blob, bytes, cudaMemcpyHostToDevice, m.copy);', 'issuer', 'bytes'),
        ('issuer_stager', '\n                        cudaMemcpyAsync(m.stage_dev[sl], hb, bytes, cudaMemcpyHostToDevice, m.copy);', 'issuer', 'bytes'),
        ('staged_pinned', '\n                                cudaMemcpyAsync(m.stage_dev[sl], b, (size_t) lay.blob_bytes(l), cudaMemcpyHostToDevice, m.copy);', 'staged', '(uint64_t) lay.blob_bytes(l)'),
        ('staged_stager', '\n                                cudaMemcpyAsync(m.stage_dev[sl], hb, (size_t) lay.blob_bytes(l), cudaMemcpyHostToDevice, m.copy);', 'staged', '(uint64_t) lay.blob_bytes(l)'),
    ]
    for name, anchor, writer, size in copies:
        source = once(source, anchor, block(name, '                        if (lab_hc_cost_on()) { cost_' + writer + '_bytes += ' + size + '; ++cost_' + writer + '_count; }'))
    source = once(source, '                    if (fused_l) {', block('fused', FUSED), before=True)
    source = once(source, '                        // multi-GPU: the rows of the experts the peer computes go last, as one block [rows_local, T*K)', block('ordinary', LAYER), before=True)
    source = once(source, '\n        stats_.tokens += T;', block('h2d', r'''        if (lab_hc_cost_on())
            std::fprintf(stderr, "P23_H2D {\"p0\":%lld,\"T\":%lld,\"inline_bytes\":%llu,\"inline_count\":%llu,\"issuer_bytes\":%llu,\"issuer_count\":%llu,\"staged_bytes\":%llu,\"staged_count\":%llu,\"bytes\":%llu,\"count\":%llu,\"submitted_only\":true}\n",
                         (long long) p0, (long long) T, (unsigned long long) cost_inline_bytes, (unsigned long long) cost_inline_count,
                         (unsigned long long) cost_issuer_bytes, (unsigned long long) cost_issuer_count,
                         (unsigned long long) cost_staged_bytes, (unsigned long long) cost_staged_count,
                         (unsigned long long) (cost_inline_bytes + cost_issuer_bytes + cost_staged_bytes),
                         (unsigned long long) (cost_inline_count + cost_issuer_count + cost_staged_count));'''), before=True)
    source = once(source, '    stats_.ms_total += ms_since(t_start);', block('complete', r'''    if (lab_hc_cost_on())
        std::fprintf(stderr, "P23_PREFILL_COMPLETE {\"pos0\":%lld,\"n\":%lld,\"compute_copy_sync_ok\":true,\"timing_enabled\":%s,\"diagnostic_only\":true}\n",
                     (long long) pos0, (long long) n, pt.on ? "true" : "false");'''), before=True)
    source = once(source, '    if (pt.on) {\n        pt.fold();', block('timing', r'''        if (lab_hc_cost_on())
            std::fprintf(stderr, "P23_TIMING {\"pos0\":%lld,\"n\":%lld,\"scope\":\"run_impl\",\"wait_copy_ms\":%.6f,\"host_group_ms\":%.6f,\"diagnostic_only\":true,\"copy_sum_is_critical_path\":false}\n",
                         (long long) pos0, (long long) n, pt.ms[kPfWaitCopy], pt.ms[kPfHostGroup]);'''))
    return prefix + source + suffix


def program(source):
    identity('src/program/generate.cpp', source)
    source = once(source, '#include "strata/core/logit_bias.hpp"', block('helpers', HELPERS), before=True)
    source = once(source, '        bool any_loan = borrow != nullptr;', block('cache_serve', '        lab_hc_cost_cache("serve", xcache, host_res, g.n_expert);'), before=True)
    source = once(source, '    bool kvg_started = false;   // the elastic K/V took this run\'s cells', block('cache_native', '    lab_hc_cost_cache("generate", xcache, host_res, g.n_expert);'), before=True)
    source = once(source, '                    p.lent_chunk = want_p;', block('loan_serve', r'''                    if (lab_hc_cost_on())
                        std::fprintf(stderr, "P23_LOAN {\"mode\":\"serve\",\"dev\":%d,\"tokens\":%lld,\"exact\":%lld,\"chunk\":%lld,\"first\":%d,\"slots\":%lld,\"borrow_slots\":%lld,\"borrow_bytes\":%llu,\"lent\":%s}\n",
                            p.dev, (long long) tokens, (long long) exact, (long long) want_p, first, (long long) p.cache->slots(),
                            (long long) (p.cache->slots() - first), (unsigned long long) part_bytes(p, first), lab_hc_cost_pairs(p.lent).c_str());'''))
    source = once(source, '''                borrow_bytes = xcache.slot_offsets() ? (uint64_t) (xcache.bytes() - (int64_t) xcache.slot_offsets()[first])
                                                     : (uint64_t) k * (uint64_t) blob;''', block('loan_native', r'''                if (lab_hc_cost_on())
                    std::fprintf(stderr, "P23_LOAN {\"mode\":\"generate\",\"first\":%d,\"slots\":%lld,\"borrow_slots\":%lld,\"borrow_bytes\":%llu,\"lent\":%s}\n",
                        first, (long long) xcache.slots(), (long long) k, (unsigned long long) borrow_bytes, lab_hc_cost_pairs(lent).c_str());'''))
    source = once(source, '            auto refill_issue = [&](PfPart& p, std::string& e) -> bool {', block('refill_counters', '''                uint64_t cost_refill_bytes = 0, cost_refill_count = 0, cost_refill_copies = 0;
                uint64_t cost_parts = 0, cost_queued = 0, cost_blocking = 0;'''))
    source = once(source, '                        if (!p.cache->fill_slot_queued_parts(slot, parts, np, e)) return false;', block('refill_parts', '''                        if (lab_hc_cost_on()) {
                            for (int z = 0; z < np; ++z) cost_refill_bytes += parts[z].n;
                            ++cost_refill_count; cost_refill_copies += (uint64_t) np; ++cost_parts;
                        }'''))
    anchor = '''                    if (!refill_blocking()) srcp->note_async_read(b, nullptr);   // #1237
                    host_res[(size_t) i] = slot;'''
    source = once(source, anchor, block('refill_blob', '''                    if (lab_hc_cost_on()) {
                        // Positive native layer nb fits its original profile-sized slot; fill_slot_* uses exactly nb.
                        cost_refill_bytes += (uint64_t) nb; ++cost_refill_count; ++cost_refill_copies;
                        if (refill_blocking()) ++cost_blocking; else ++cost_queued;
                    }'''))
    anchor = '''                return true;
            };
            auto refill_wait = [&](PfPart& p, std::string& e) -> bool {'''
    source = once(source, anchor, block('refill_issue_report', r'''                if (lab_hc_cost_on())
                    std::fprintf(stderr, "P23_REFILL_ISSUE {\"mode\":\"serve\",\"dev\":%d,\"chunk\":%lld,\"bytes\":%llu,\"count\":%llu,\"copy_calls\":%llu,\"parts_experts\":%llu,\"queued_experts\":%llu,\"blocking_experts\":%llu}\n",
                        p.dev, (long long) p.lent_chunk, (unsigned long long) cost_refill_bytes, (unsigned long long) cost_refill_count,
                        (unsigned long long) cost_refill_copies, (unsigned long long) cost_parts, (unsigned long long) cost_queued, (unsigned long long) cost_blocking);'''), before=True)
    source = once(source, '                if (!p.cache->sync_queued(e)) return false;', block('refill_sync', r'''                if (lab_hc_cost_on())
                    std::fprintf(stderr, "P23_REFILL_SYNC {\"mode\":\"serve\",\"dev\":%d,\"count\":%zu,\"sync_ok\":true}\n", p.dev, p.lent.size());'''))
    source = once(source, '                if (trace && n_parts > 0) {', block('refill_done', r'''                if (lab_hc_cost_on() && n_parts > 0)
                    std::fprintf(stderr, "P23_REFILL_DONE {\"mode\":\"serve\",\"count\":%lld,\"participants\":%lld,\"wall_ms\":%.6f,\"sync_ok\":true}\n",
                        (long long) n_lent, (long long) n_parts, std::chrono::duration<double, std::milli>(Clock::now() - t_rf).count());'''), before=True)
    source = once(source, '            const Clock::time_point tr = Clock::now();\n            for (const auto& [i, slot] : lent)', block('native_refill_counters', '            uint64_t cost_native_refill_bytes = 0, cost_native_refill_count = 0;'), before=True)
    source = once(source, '                if (!refill_blocking()) srcp->note_async_read(b, nullptr);   // #1237\n                host_res[(size_t) i] = slot;', block('native_refill_blob', '''                if (lab_hc_cost_on()) { cost_native_refill_bytes += (uint64_t) nb; ++cost_native_refill_count; }'''))
    anchor = '''            if (!xcache.sync_queued(err)) {
                std::fprintf(stderr, "strata generate: refilling the lent slots failed: %s\\n", err.c_str());
                return 1;
            }'''
    source = once(source, anchor, block('native_refill_report', r'''            if (lab_hc_cost_on()) {
                std::fprintf(stderr, "P23_REFILL_ISSUE {\"mode\":\"generate\",\"bytes\":%llu,\"count\":%llu,\"copy_calls\":%llu,\"parts_experts\":0,\"queued_experts\":%llu,\"blocking_experts\":%llu}\n",
                    (unsigned long long) cost_native_refill_bytes, (unsigned long long) cost_native_refill_count,
                    (unsigned long long) cost_native_refill_count, (unsigned long long) (refill_blocking() ? 0 : cost_native_refill_count),
                    (unsigned long long) (refill_blocking() ? cost_native_refill_count : 0));
                std::fprintf(stderr, "P23_REFILL_DONE {\"mode\":\"generate\",\"count\":%llu,\"wall_ms\":%.6f,\"sync_ok\":true}\n",
                    (unsigned long long) cost_native_refill_count, std::chrono::duration<double, std::milli>(Clock::now() - tr).count());
            }'''))
    return source


def transform(sources):
    for name in SOURCE_SHA256:
        identity(name, sources[name])
    return {'src/prefill/prefill.cpp': prefill(sources['src/prefill/prefill.cpp']),
            'src/program/generate.cpp': program(sources['src/program/generate.cpp'])}


def apply(tree, patch):
    tree, patch = Path(tree), Path(patch)
    if patch.exists():
        raise ValueError('COST_PATCH_OUTPUT_EXISTS')
    old = {name: (tree / name).read_text() for name in SOURCE_SHA256}
    new = transform(old)
    text = ''.join(''.join(difflib.unified_diff(old[name].splitlines(True), new[name].splitlines(True),
                   fromfile='a/' + name, tofile='b/' + name)) for name in SOURCE_SHA256)
    patch.write_text(text)
    for name, source in new.items():
        (tree / name).write_text(source)
    return {'files': {name: {'source_sha256': SOURCE_SHA256[name], 'patched_sha256': hashlib.sha256(new[name].encode()).hexdigest()}
                      for name in SOURCE_SHA256}, 'patch_sha256': hashlib.sha256(text.encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--patch', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(apply(args.tree, args.patch), indent=2))


if __name__ == '__main__':
    main()
