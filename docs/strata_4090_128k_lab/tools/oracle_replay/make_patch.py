"""Generate P14's single-target same-process FFN diagnostic (no build/run).

Only p0=0,T=4090,layer=3,half=1 is replayed. HC executes once. Timing,
adaptive-share state and on_routes side effects are diagnostic; full final
logits are not an oracle. Byte outputs are retained even if they differ.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path

RELATIVE = Path('src/prefill/prefill.cpp')
SOURCE_SHA256 = '9deeead6286f8a1d47a6e8e77a41f2100f73cf66f5485dba057680d582293fd5'
HEADER = Path(__file__).with_name('replay_probe.hpp')
MARKER = '// P14_REPLAY single-target loop'


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('REPLAY_ANCHOR_COUNT: ' + old[:100])
    return source.replace(old, new, 1)


BEGIN = r'''
                    // P14_REPLAY single-target loop: HC read above and HC write below run once.
                    auto& replay = strata_lab_replay::probe();
                    const bool replay_target = replay.dir && !replay.hit && p0 == 0 && T == 4090 && l == 3 && half == 1;
                    if (replay_target) {
                        replay.hit = true;
                        strata_lab_replay::require(!stream_all && !m.pp && !ps_on &&
                            !std::getenv("STRATA_DBG_FEAT") && !std::getenv("STRATA_DBG_ROUTE_OVERRIDE"),
                            "unsupported target path/debug routing");
                    }
                    for (int replay_pass = 0; replay_pass < (replay_target ? 2 : 1); ++replay_pass) {
                    int replay_h_kind = 0; // 0 unused; 1 fp32 H; 2 fp16 Hh
                    auto replay_gpu = [&](const std::string& field, const void* ptr, size_t bytes, bool guard) {
                        if (!replay_target) return;
                        strata_lab_replay::require(cudaStreamSynchronize(m.cs) == cudaSuccess, "compute sync: " + field);
                        replay.raw(replay_pass, field, bytes, guard, [&](size_t off, void* dst, size_t n) {
                            strata_lab_replay::require(cudaMemcpy(dst, (const char*) ptr + off, n, cudaMemcpyDeviceToHost) == cudaSuccess,
                                                      "readback: " + field);
                        });
                    };
                    if (replay_target) {
                        strata_lab_replay::require(cudaStreamSynchronize(m.cs) == cudaSuccess &&
                                                  cudaStreamSynchronize(m.copy) == cudaSuccess, "pass boundary sync");
                        if (replay.neg("input", replay_pass)) {
                            unsigned char b;
                            strata_lab_replay::require(cudaMemcpy(&b, m.mixed, 1, cudaMemcpyDeviceToHost) == cudaSuccess, "negative read");
                            b ^= 1;
                            strata_lab_replay::require(cudaMemcpy(m.mixed, &b, 1, cudaMemcpyHostToDevice) == cudaSuccess, "negative write");
                        }
                        const int64_t geometry[] = {p0, T, l, half, N, D, HC, K, m.g->n_expert};
                        replay.host(replay_pass, "geometry", geometry, sizeof geometry);
                        replay_gpu("R", m.R, (size_t) T * D * 4, true);
                        replay_gpu("inj", m.inj, (size_t) T * HC * 4, true);
                        replay_gpu("mixed", m.mixed, (size_t) T * N * 4, true);
                        replay_gpu("mixed_h", m.mixed_h, (size_t) T * N * 2, true);
                        replay_gpu("mixed_bf", m.mixed_bf, (size_t) T * N * 2, true);
                        const int low = m.mixed_bf_lo != nullptr;
                        replay.host(replay_pass, "mixed_bf_lo_present", &low, sizeof low);
                        if (low) replay_gpu("mixed_bf_lo", m.mixed_bf_lo, (size_t) T * N * 2, true);
                        // Dm has no live reader here: HC read finished; original FFN has not begun.
                        strata_lab_replay::require(cudaMemsetAsync(m.Dm, replay_pass ? 0x5a : 0xa5,
                            (size_t) T * K * N * 4, m.cs) == cudaSuccess, "Dm poison");
                    }
'''

DISPATCH = r'''
                        if (replay_target && replay_pass == 1) {
                            strata_lab_replay::require(cpu_maybe, "CPU path became unavailable");
                            on_cpu = replay.cpu;
                            cpu_blob.assign((size_t) m.g->n_expert, nullptr);
                            n_cpu = 0; rows_cpu = 0; n_stream = 0;
                            if (replay.neg("dispatch", replay_pass)) {
                                strata_lab_replay::require(!on_cpu.empty(), "negative dispatch has no CPU map");
                                on_cpu[0] ^= 1;
                            }
                            for (int32_t e = 0; e < m.g->n_expert; ++e) {
                                const bool resident = m.host_res && m.cache && m.host_res[(size_t) l * m.g->n_expert + e] >= 0;
                                if (m.cnt[(size_t) e] > 0 && !resident) ++n_stream;
                                if (on_cpu.empty() || !on_cpu[(size_t) e]) continue;
                                strata_lab_replay::require(!resident && m.cnt[(size_t) e] > 0 &&
                                    m.cnt[(size_t) e] <= strata::kernels::cpu::MAXT &&
                                    (m.src->pinned(l, e) || !m.src->transient(l, e)), "invalid replay CPU expert");
                                const uint8_t* b = m.src->blob_stable(l, e);
                                strata_lab_replay::require(b && b == replay.blobs[(size_t) e], "CPU blob identity changed");
                                cpu_blob[(size_t) e] = b;
                                rows_cpu += m.cnt[(size_t) e]; ++n_cpu;
                            }
                        } else '''

SELECTION = r'''
                        if (replay_target) {
                            const int dispatch_resident_present = m.host_res && m.cache;
                            replay.host(replay_pass, "dispatch_resident_present", &dispatch_resident_present, sizeof dispatch_resident_present);
                            if (dispatch_resident_present) replay.host(replay_pass, "dispatch_host_res",
                                m.host_res + (size_t) l * m.g->n_expert, (size_t) m.g->n_expert * sizeof(*m.host_res));
                            if (replay_pass == 0) {
                                replay.cpu = on_cpu; replay.blobs = cpu_blob; replay.arm = cpu_arm;
                                replay.rows = rows_cpu; replay.count = n_cpu; replay.streamed = n_stream;
                            }
                            replay.vec(replay_pass, "on_cpu", on_cpu);
                            const int64_t choice[] = {cpu_arm, n_cpu, rows_cpu, n_stream};
                            replay.host(replay_pass, "cpu_selection", choice, sizeof choice);
                            strata_lab_replay::require(rows_cpu == replay.rows && n_cpu == replay.count &&
                                n_stream == replay.streamed, "CPU dispatch geometry changed");
                            for (size_t e = 0; e < on_cpu.size(); ++e) if (on_cpu[e])
                                replay.host(replay_pass, "cpu_blob_" + std::to_string(e), cpu_blob[e], (size_t) lay.blob_bytes(l));
                            std::fprintf(stderr, "P14_REPLAY pass=%d p0=0 T=4090 layer=3 half=1 cpu_arm=%d cpu_count=%lld cpu_rows=%lld cpu_ids=",
                                         replay_pass, int(cpu_arm), (long long) n_cpu, (long long) rows_cpu);
                            for (size_t e = 0; e < on_cpu.size(); ++e) if (on_cpu[e]) std::fprintf(stderr, "%zu,", e);
                            std::fprintf(stderr, " path=%s diagnostic_adaptive_side_effects=1 final_logits_oracle=0\n", replay.dir);
                        }
'''

MAPPING = r'''
                        if (replay_target) {
                            if (replay.neg("mapping", replay_pass)) std::swap(slot_h[0], slot_h[1]);
                            replay.mapping(ids_h, slot_h, src_h, m.cnt, m.off, order, on_cpu, T * K, K, rows_cpu);
                            replay.vec(replay_pass, "cnt", m.cnt);
                            replay.vec(replay_pass, "off", m.off);
                            replay.vec(replay_pass, "order", order);
                            replay.host(replay_pass, "slot", slot_h, (size_t) T * K * 4);
                            replay.host(replay_pass, "src", src_h, (size_t) T * K * 4);
                        }
'''

END = r'''
                    if (replay_target) {
                        strata_lab_replay::require(cudaStreamSynchronize(m.cs) == cudaSuccess &&
                            cudaStreamSynchronize(m.copy) == cudaSuccess, "completed pass sync");
                        replay_gpu("GU", m.GU, (size_t) (T * K - rows_cpu) * 1280 * 4, false);
                        replay.host(replay_pass, "H_kind", &replay_h_kind, sizeof replay_h_kind);
                        if (replay_h_kind == 1) replay_gpu("H", m.H, (size_t) (T * K - rows_cpu) * 640 * 4, false);
                        if (replay_h_kind == 2) replay_gpu("Hh", m.Hh, (size_t) (T * K - rows_cpu) * 640 * 2, false);
                        if (rows_cpu) replay.host(replay_pass, "cpu_rows", m.cpu_rows, (size_t) rows_cpu * N * 4, false);
                        replay_gpu("Dm", m.Dm, (size_t) T * K * N * 4, false);
                        replay_gpu("shared", m.shared, (size_t) T * N * 4, false);
                        replay_gpu("sg", m.sg, (size_t) T * 4, false);
                        replay_gpu("bo", m.bo, (size_t) T * N * 4, false);
                        if (replay_pass == 1) {
                            replay.complete = true;
                            std::fprintf(stderr, "P14_REPLAY COMPLETE two_same_process_FFN_passes final_logits_oracle=0 path=%s\n", replay.dir);
                        }
                    }
                    } // P14_REPLAY pass: original futures/stager/scopes are destroyed each time.
'''


def transform(source: str) -> str:
    if MARKER in source:
        raise ValueError('REPLAY_ALREADY_PATCHED')
    if hashlib.sha256(source.encode()).hexdigest() != SOURCE_SHA256:
        raise ValueError('REPLAY_SOURCE_IDENTITY')
    source = replace_once(source, '#include "strata/kernels/fused_gr.hpp"', HEADER.read_text() + '\n#include "strata/kernels/fused_gr.hpp"')
    moe = '                    // ======================= MoE ======================='
    source = replace_once(source, moe, moe + BEGIN)
    route = '                    route(m.logits, m.ids, m.w, T, m.g->n_expert, m.cs);'
    source = replace_once(source, route, route + '''
                    if (replay_target) {
                        replay_gpu("ids", m.ids, (size_t) T * K * 4, true);
                        replay_gpu("w", m.w, (size_t) T * K * 4, true);
                        const int resident_present = m.host_res && m.cache;
                        replay.host(replay_pass, "resident_present", &resident_present, sizeof resident_present);
                        if (resident_present) replay.host(replay_pass, "host_res", m.host_res + (size_t) l * m.g->n_expert,
                                                          (size_t) m.g->n_expert * sizeof(*m.host_res));
                    }''')
    anchor = '                    size_t n_order = 0;'
    source = replace_once(source, anchor, '''                    if (replay_target) {
                        strata_lab_replay::require(!fused_l, "fused target unsupported");
                        const int64_t path[] = {use_mmq, lay.native, mmq_gt, mmq_dt, had_gu, had_d, had_block, MMQ_GROUP,
                            m.f16_io, m.fused_bufs, m.ring};
                        replay.host(replay_pass, "compute_geometry", path, sizeof path);
                        if (lay.native) {
                            const auto& f = lay.fmt[(size_t) l];
                            const int64_t fmt[] = {f.gu_type, f.d_type, (int64_t) f.gu_row, (int64_t) f.d_row,
                                (int64_t) f.up_off, (int64_t) f.down_off, (int64_t) f.tail_off, f.n_embd, f.n_ff};
                            replay.host(replay_pass, "native_geometry", fmt, sizeof fmt);
                        }
                    }
''' + anchor)
    anchor = '                        if (cpu_maybe && cpu_arm) {'
    source = replace_once(source, anchor, '''                        if (replay_target && replay_pass == 1) cpu_arm = replay.arm;
''' + anchor)
    anchor = '                        if (cpu_maybe) {\n                            std::vector<std::pair<int32_t, int32_t>> cand;'
    source = replace_once(source, anchor, DISPATCH + anchor.lstrip())
    anchor = '                        // multi-GPU: the rows of the experts the peer computes go last, as one block [rows_local, T*K)'
    source = replace_once(source, anchor, SELECTION + anchor)
    anchor = '                        if (grp_mapped) {\n                            copy_i32(m.slot_dev, m.grp_dev + m.grp_tk, T * K, m.cs);'
    source = replace_once(source, anchor, MAPPING + anchor)
    anchor = '                        const size_t mmq_gub = use_mmq ? mmq::matrix_bytes(mmq_gt, 1280, N) : 0;'
    source = replace_once(source, anchor, '''                        if (replay_target) replay_h_kind = !use_mmq || wmma_l ? 2 : 1;
''' + anchor)
    anchor = '                        ws::Layer wl;'
    source = replace_once(source, anchor, '''                        if (replay_target) {
                            const int64_t group_geometry[] = {wmma_l, (int64_t) mmq_gub, (int64_t) mmq_db, rows_local};
                            replay.host(replay_pass, "group_geometry", group_geometry, sizeof group_geometry);
                        }
''' + anchor)
    anchor = '                            // STRATA_MMQ_WS=1 (moe_ws.hpp, GP100):'
    source = replace_once(source, anchor, '''                            if (replay_target) replay.vec(replay_pass, "bounds", m.bounds_host);
''' + anchor)
    anchor = '                            mmq::swiglu_quant(m.GU, m.Hq, T * K, !lay.native, m.cs);'
    source = replace_once(source, anchor, '''                            if (replay_target) replay_h_kind = 0; // swiglu_quant initializes Hq, not H
''' + anchor)
    anchor = '                }\n                pt.mark(kPfHcWrite, cs);'
    source = replace_once(source, anchor, END + anchor)
    return source


def apply(tree: Path, patch: Path) -> dict:
    if patch.exists():
        raise ValueError('REPLAY_PATCH_OUTPUT_EXISTS')
    path = tree / RELATIVE
    old = path.read_text()
    new = transform(old)
    diff = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                     fromfile='a/' + str(RELATIVE), tofile='b/' + str(RELATIVE)))
    patch.write_text(diff)
    path.write_text(new)
    return {'source_sha256': SOURCE_SHA256, 'patched_sha256': hashlib.sha256(new.encode()).hexdigest(),
            'patch_sha256': hashlib.sha256(diff.encode()).hexdigest(), 'target': {'p0': 0, 'T': 4090, 'layer': 3, 'half': 1}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--patch', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(apply(args.tree, args.patch), indent=2))


if __name__ == '__main__':
    main()
