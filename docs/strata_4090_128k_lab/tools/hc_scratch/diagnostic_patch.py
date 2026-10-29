"""Add opt-in P13 first-difference and adaptive-path diagnostics to the HC probe tree.

These synchronous readbacks perturb timing. Never enable them for performance samples.
FNV hashes locate a candidate difference; only retained raw byte comparisons prove equality.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path

from make_patch import RELATIVE, replace_once


HELPERS = r'''// P13 diagnosis only. Per-field m.cs readback deliberately synchronizes; not performance evidence.
inline bool lab_hc_diag_on(int64_t layer) {
    static const char* dir = std::getenv("STRATA_LAB_HC_DIAG_DIR");
    return dir && dir[0] && layer >= 0 && layer <= 8;
}
uint64_t lab_hc_diag_hash(const void* data, size_t n) {
    const auto* p = static_cast<const uint8_t*>(data);
    uint64_t h = 14695981039346656037ull;
    for (size_t i = 0; i < n; ++i) { h ^= p[i]; h *= 1099511628211ull; }
    return h;
}
bool lab_hc_diag_device(int64_t p0, int64_t T, int64_t layer, int half, const char* stage,
                        const char* field, const void* dev, size_t bytes, cudaStream_t stream, std::string& err) {
    if (!lab_hc_diag_on(layer)) return true;
    std::vector<uint8_t> host(bytes);
    cudaError_t rc = cudaMemcpyAsync(host.data(), dev, bytes, cudaMemcpyDeviceToHost, stream);
    if (rc == cudaSuccess) rc = cudaStreamSynchronize(stream);
    if (rc != cudaSuccess) { err = std::string("P13 diagnostic readback: ") + cudaGetErrorString(rc); return false; }
    bool dumped = false;
    static const char* select = std::getenv("STRATA_LAB_HC_DIAG_DUMP");
    int dl = -1, dh = -1; char ds[32] = {};
    if (select && std::sscanf(select, "%d:%d:%31s", &dl, &dh, ds) == 3 &&
        dl == layer && dh == half && (std::strcmp(ds, "all") == 0 || std::strcmp(ds, stage) == 0)) {
        const std::string name = "p" + std::to_string(p0) + "-T" + std::to_string(T) + "-l" +
            std::to_string(layer) + "-h" + std::to_string(half) + "-" + stage + "-" + field + ".bin";
        const std::string path = std::string(std::getenv("STRATA_LAB_HC_DIAG_DIR")) + "/" + name;
        std::FILE* f = std::fopen(path.c_str(), "wb");
        if (!f) { err = "P13 diagnostic dump open: " + name; return false; }
        const bool wrote = std::fwrite(host.data(), 1, host.size(), f) == host.size();
        const bool closed = std::fclose(f) == 0;
        if (!wrote || !closed) { err = "P13 diagnostic dump write: " + name; return false; }
        dumped = true;
    }
    std::fprintf(stderr, "P13_HC_DIAG {\"chunk_p0\":%lld,\"T\":%lld,\"layer\":%lld,\"half\":%d,"
        "\"stage\":\"%s\",\"field\":\"%s\",\"bytes\":%llu,\"fnv1a64\":\"%016llx\","
        "\"hash_is_bytewise_proof\":false,\"dumped\":%s}\n", (long long) p0, (long long) T,
        (long long) layer, half, stage, field, (unsigned long long) bytes,
        (unsigned long long) lab_hc_diag_hash(host.data(), host.size()), dumped ? "true" : "false");
    return true;
}
void lab_hc_diag_cpu(int64_t p0, int64_t T, int64_t layer, int64_t ne, const int32_t* resident,
                     const std::vector<char>& on_cpu, bool maybe, bool arm, int set, bool cold, bool gate,
                     double share, size_t take, size_t candidates, int64_t nstream, int64_t ncpu, int64_t rows,
                     double cpu_c_ms, double cpu_g_ms, int nratio) {
    if (!lab_hc_diag_on(layer)) return;
    std::string ids = "[";
    bool first = true;
    for (size_t e = 0; e < on_cpu.size(); ++e) if (on_cpu[e]) {
        if (!first) ids += ',';
        ids += std::to_string(e); first = false;
    }
    ids += ']';
    std::fprintf(stderr, "P13_HC_CPU {\"chunk_p0\":%lld,\"T\":%lld,\"layer\":%lld,\"half\":1,"
        "\"host_res_present\":%s,\"host_res_fnv1a64\":\"%016llx\",\"host_res_bytes\":%llu,"
        "\"on_cpu\":%s,\"cpu_maybe\":%s,\"cpu_arm\":%s,\"cpu_set\":%d,\"cpu_cold\":%s,\"cpu_gate\":%s,"
        "\"share\":%.17g,\"take\":%llu,\"candidates\":%llu,\"nstream\":%lld,\"ncpu\":%lld,\"rows_cpu\":%lld,"
        "\"cpu_c_ms\":%.17g,\"cpu_g_ms\":%.17g,\"nratio\":%d,\"hash_is_bytewise_proof\":false}\n",
        (long long) p0, (long long) T, (long long) layer, resident ? "true" : "false",
        (unsigned long long) (resident ? lab_hc_diag_hash(resident, (size_t) ne * sizeof(int32_t)) : 0),
        (unsigned long long) (resident ? (size_t) ne * sizeof(int32_t) : 0), ids.c_str(), maybe ? "true" : "false",
        arm ? "true" : "false", set, cold ? "true" : "false", gate ? "true" : "false", share,
        (unsigned long long) take, (unsigned long long) candidates, (long long) nstream,
        (long long) ncpu, (long long) rows, cpu_c_ms, cpu_g_ms, nratio);
}

'''

ENTER = '''                if (!lab_hc_diag_device(p0, T, l, half, "enter", "R", m.R, (size_t) T * D * sizeof(float), m.cs, err)) return false;
'''
HC_DONE = '''                if (!lab_hc_diag_device(p0, T, l, half, "hc", "mixed", m.mixed, (size_t) T * N * sizeof(float), m.cs, err) ||
                    !lab_hc_diag_device(p0, T, l, half, "hc", "inj", m.inj, (size_t) T * HC * sizeof(float), m.cs, err) ||
                    !lab_hc_diag_device(p0, T, l, half, "hc", "lo16", m.lo16, (size_t) T * LR * sizeof(uint16_t), m.cs, err)) return false;
'''
EXIT = '''                if (!lab_hc_diag_device(p0, T, l, half, "exit", "R", m.R, (size_t) T * D * sizeof(float), m.cs, err)) return false;
'''

SORT_OLD = '''                        if (detail::mmq_resident_sort_eligible((sort_all || sort_full) && on_peer.empty(), use_mmq, lay.native,
                                m.cache != nullptr, m.host_res ? m.host_res + (size_t) l * m.g->n_expert : nullptr,
                                m.g->n_expert, stream_all, !stream_all || seq_start[(size_t) l] == seq_start[(size_t) l + 1]))
                            detail::mmq_resident_sort_rows(ids_h, T * K, (int32_t) K, m.cnt, m.off, order, slot_h, src_h,
                                                           detail::mmq_resident_sort_span(order.size(), MMQ_GROUP, sort_full));'''
SORT_NEW = '''                        bool lab_hc_sort_taken = false;
                        if (detail::mmq_resident_sort_eligible((sort_all || sort_full) && on_peer.empty(), use_mmq, lay.native,
                                m.cache != nullptr, m.host_res ? m.host_res + (size_t) l * m.g->n_expert : nullptr,
                                m.g->n_expert, stream_all, !stream_all || seq_start[(size_t) l] == seq_start[(size_t) l + 1])) {
                            lab_hc_sort_taken = true;
                            detail::mmq_resident_sort_rows(ids_h, T * K, (int32_t) K, m.cnt, m.off, order, slot_h, src_h,
                                                           detail::mmq_resident_sort_span(order.size(), MMQ_GROUP, sort_full));
                        }
                        if (lab_hc_diag_on(l))
                            std::fprintf(stderr, "P13_HC_SORT {\\"chunk_p0\\":%lld,\\"T\\":%lld,\\"layer\\":%lld,\\"half\\":1,"
                                "\\"sort_all\\":%s,\\"sort_full\\":%s,\\"sort_taken\\":%s}\\n", (long long) p0, (long long) T,
                                (long long) l, sort_all ? "true" : "false", sort_full ? "true" : "false", lab_hc_sort_taken ? "true" : "false");'''


def transform(source):
    if 'STRATA_LAB_HC_DIAG_DIR' in source:
        raise ValueError('HC_DIAGNOSTIC_ALREADY_PATCHED')
    if 'STRATA_LAB_HC_REGION' not in source:
        raise ValueError('HC_REGION_PATCH_REQUIRED_FIRST')
    source = replace_once(source, 'double ms_since(Clock::time_point t)', HELPERS + 'double ms_since(Clock::time_point t)')
    source = replace_once(source, '                // ---- the hyper-connection read of this half\n', ENTER + '                // ---- the hyper-connection read of this half\n')
    source = replace_once(source, '\n                if (wd_q8.data) {   // the HC GEMMs that read the scratch are enqueued: the next user waits for them\n', '\n' + HC_DONE + '                if (wd_q8.data) {   // the HC GEMMs that read the scratch are enqueued: the next user waits for them\n')
    end = '''#endif
            }
        }
        if (!ple_land()) return false;   // a stage that ends before layer 1: the rows land anyway, the next gather starts'''
    source = replace_once(source, end, '#endif\n' + EXIT + end[len('#endif\n'):])
    take = '''                            const size_t take = std::min(cand.size(), (size_t) std::llround(share * (double) nstream));
                            n_stream = nstream;'''
    source = replace_once(source, take, take + '''
                            lab_hc_share = share; lab_hc_take = take; lab_hc_candidates = cand.size();''')
    candidate = '''                        if (cpu_maybe) {
                            std::vector<std::pair<int32_t, int32_t>> cand;   // (tokens, expert)'''
    source = replace_once(source, candidate, '''                        double lab_hc_share = 0.0;
                        size_t lab_hc_take = 0, lab_hc_candidates = 0;
''' + candidate)
    cpu_end = '''                        // multi-GPU: the rows of the experts the peer computes go last, as one block [rows_local, T*K)'''
    source = replace_once(source, cpu_end, '''                        lab_hc_diag_cpu(p0, T, l, m.g->n_expert,
                            m.host_res ? m.host_res + (size_t) l * m.g->n_expert : nullptr, on_cpu,
                            cpu_maybe, cpu_arm, cpu_set, cpu_cold, m.cpu_gate, lab_hc_share,
                            lab_hc_take, lab_hc_candidates, n_stream, n_cpu, rows_cpu, m.cpu_c_ms, m.cpu_g_ms, m.cpu_nratio);
''' + cpu_end)
    source = replace_once(source, SORT_OLD, SORT_NEW)
    direct = '''                        const bool direct = use_mmq && lay.native && m.cache && mmq_plan().direct[(size_t) l] && !wmma_l;'''
    source = replace_once(source, direct, direct + '''
                        if (lab_hc_diag_on(l))
                            std::fprintf(stderr, "P13_HC_DIRECT {\\"chunk_p0\\":%lld,\\"T\\":%lld,\\"layer\\":%lld,\\"half\\":1,"
                                "\\"direct\\":%s,\\"plan_direct\\":%s,\\"use_mmq\\":%s,\\"wmma_l\\":%s}\\n",
                                (long long) p0, (long long) T, (long long) l, direct ? "true" : "false",
                                (use_mmq && mmq_plan().direct[(size_t) l]) ? "true" : "false", use_mmq ? "true" : "false", wmma_l ? "true" : "false");''')
    fused = '''                    bool cpu_cold = false;                // auto: one-time costs in the window (no reading)'''
    source = replace_once(source, fused, fused + '''
                    if (lab_hc_diag_on(l))
                        std::fprintf(stderr, "P13_HC_MOE {\\"chunk_p0\\":%lld,\\"T\\":%lld,\\"layer\\":%lld,\\"half\\":1,"
                            "\\"fused_l\\":%s,\\"stream_all\\":%s,\\"use_mmq\\":%s}\\n", (long long) p0,
                            (long long) T, (long long) l, fused_l ? "true" : "false", stream_all ? "true" : "false", use_mmq ? "true" : "false");''')
    return source


def apply(tree, patch_path):
    tree, patch_path = Path(tree), Path(patch_path)
    source_path = tree / RELATIVE
    original = source_path.read_text()
    changed = transform(original)
    if patch_path.exists():
        raise ValueError('HC_DIAGNOSTIC_PATCH_OUTPUT_EXISTS')
    patch = ''.join(difflib.unified_diff(original.splitlines(keepends=True), changed.splitlines(keepends=True),
                                      fromfile='a/' + str(RELATIVE), tofile='b/' + str(RELATIVE)))
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path.write_text(patch)
    source_path.write_text(changed)
    return {'file': str(RELATIVE), 'before_sha256': hashlib.sha256(original.encode()).hexdigest(),
            'after_sha256': hashlib.sha256(changed.encode()).hexdigest(),
            'patch_sha256': hashlib.sha256(patch.encode()).hexdigest(), 'performance_samples_allowed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tree', type=Path)
    parser.add_argument('patch', type=Path)
    args = parser.parse_args()
    print(json.dumps(apply(args.tree, args.patch)))
