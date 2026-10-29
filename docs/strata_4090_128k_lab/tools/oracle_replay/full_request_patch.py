"""Generate P15 complete-request diagnostic from the frozen original P13 source.

Every FFN executes once. Capture records natural CPU dispatch; replay restores
only CPU arm/selection, and compares actual routing/grouping/MMQ geometry.
This changes diagnostic timing, not weights, router results, or model math.
No SAVE/state export, build, or remote action is performed by this generator.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path

RELATIVE = Path('src/prefill/prefill.cpp')
SOURCE_SHA256 = '9deeead6286f8a1d47a6e8e77a41f2100f73cf66f5485dba057680d582293fd5'
HEADER = Path(__file__).with_name('full_request_probe.hpp')
MARKER = '// P15_ORACLE complete-request diagnostic'


def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('FULL_ORACLE_ANCHOR_COUNT: ' + old[:100])
    return source.replace(old, new, 1)


CHUNK = r'''
        // P15_ORACLE complete-request diagnostic: one original computation per half.
        auto& oracle = strata_lab_full_oracle::probe();
        const strata_lab_full_oracle::Key oracle_chunk{p0, T, -1, -1};
        auto oracle_gpu = [&](const strata_lab_full_oracle::Key& key, const std::string& field,
                              const void* ptr, size_t bytes) {
            if (!oracle.dir) return;
            strata_lab_full_oracle::require(cudaStreamSynchronize(m.cs) == cudaSuccess, "compute sync " + key.str() + "/" + field);
            oracle.raw(key, field, bytes, [&](size_t off, void* dst, size_t n) {
                strata_lab_full_oracle::require(cudaMemcpy(dst, (const char*) ptr + off, n, cudaMemcpyDeviceToHost) == cudaSuccess,
                                               "readback " + key.str() + "/" + field);
            });
        };
        // Pack only initialized row payload; padding is not numerical evidence.
        auto oracle_rows = [&](const strata_lab_full_oracle::Key& key, const std::string& field,
                               const void* ptr, size_t row_bytes, size_t stride_bytes) {
            if (!oracle.dir) return;
            strata_lab_full_oracle::require(cudaStreamSynchronize(m.cs) == cudaSuccess, "row sync " + field);
            oracle.raw(key, field, (size_t) T * row_bytes, [&](size_t off, void* dst, size_t n) {
                while (n) {
                    const size_t row = off / row_bytes, col = off % row_bytes;
                    const size_t take = std::min(n, row_bytes - col);
                    strata_lab_full_oracle::require(cudaMemcpy(dst, (const char*) ptr + row * stride_bytes + col,
                        take, cudaMemcpyDeviceToHost) == cudaSuccess, "row readback " + key.str() + "/" + field);
                    dst = (char*) dst + take; off += take; n -= take;
                }
            });
        };
        if (oracle.dir) {
            strata_lab_full_oracle::require(!oracle.chunk_open && !m.pp && !next_ && !hand_in_ && LB == 0 && LE == g.n_layers,
                                           "single-device full-stage path required");
            strata_lab_full_oracle::require(!std::getenv("STRATA_DBG_FEAT") && !std::getenv("STRATA_DBG_ROUTE_OVERRIDE") &&
                                           cpu_share_env() != 0.0, "debug routing or disabled CPU share");
            oracle.chunk_open = true;
            const int64_t shape[] = {p0, T, N, D, HC, LR, K, g.n_expert, LB, LE};
            oracle.host(oracle_chunk, "chunk_begin", shape, sizeof shape);
        }
'''

HALF = r'''
                const strata_lab_full_oracle::Key oracle_key{p0, T, l, half};
                const bool oracle_large = oracle.dir && p0 == 0 && T == 4090 && l == 3 && half == 1;
                const bool oracle_handoff = oracle.dir && p0 == 0 && T == 4090 && l == 4 && half == 0;
                if (oracle_large) oracle_gpu(oracle_key, "hc_entry_R", m.R, (size_t) T * D * 4);
'''

NORM = r'''
                const bool oracle_norm_reused = normed;
                if (oracle_handoff) {
                    const int64_t cache[] = {normed, ldx, xf16, gr_unfused(), m.xn16_lo != nullptr};
                    oracle.host(oracle_key, "normed_handoff", cache, sizeof cache);
                    if (normed) {
                        oracle_gpu(oracle_key, "cached_grs", m.grs, (size_t) T * HC * 4);
                        oracle_rows(oracle_key, "cached_xn16", m.xn16, (size_t) D * 2, (size_t) ldx * 2);
                        if (m.xn16_lo) oracle_gpu(oracle_key, "cached_xn16_lo", m.xn16_lo, (size_t) T * D * 2);
                    }
                }
'''

INITIAL = r'''
    auto& initial_oracle = strata_lab_full_oracle::probe();
    if (initial_oracle.dir) {
        strata_lab_full_oracle::require(pos0 == 0 && !initial_oracle.initial_seen,
                                       "initial state covers one cold run_impl at pos0=0 only");
        initial_oracle.initial_seen = true;
        strata_lab_full_oracle::require(ss.gdn_alloc >= 0 && (ss.gdn_alloc == 0 || ss.gdn_state), "invalid initial GDN carve");
        strata_lab_full_oracle::require(cudaDeviceSynchronize() == cudaSuccess, "initial state device sync");
        const strata_lab_full_oracle::Key key{pos0, n, -2, -1};
        const int64_t shape[] = {pos0, n, ss.gdn_ord0, ss.gdn_alloc, ss.qsa_ord0, ss.qsa_alloc,
            (int64_t) gdn_floats, ss.ple_hist != nullptr, strata::kernels::NG_HIST, strata::kernels::NG_HC_DIM};
        initial_oracle.host(key, "initial_geometry", shape, sizeof shape);
        const int32_t ple[] = {ss.ple_prev[0], ss.ple_prev[1], ss.ple_token};
        initial_oracle.host(key, "initial_ple_tokens", ple, sizeof ple);
        const int64_t kv_prefix = 0; // pos0=0: no initialized KV prefix is read by this request.
        initial_oracle.host(key, "initial_kv_prefix_tokens", &kv_prefix, sizeof kv_prefix);
        auto initial_gpu = [&](const std::string& field, const void* ptr, size_t bytes) {
            initial_oracle.raw(key, field, bytes, [&](size_t off, void* dst, size_t take) {
                strata_lab_full_oracle::require(cudaMemcpy(dst, (const char*) ptr + off, take,
                    cudaMemcpyDeviceToHost) == cudaSuccess, "initial readback " + field);
            });
        };
        initial_gpu("initial_gdn_state", ss.gdn_state, (size_t) ss.gdn_alloc * gdn_floats * sizeof(float));
        if (ss.ple_hist) initial_gpu("initial_ple_hist", ss.ple_hist,
            (size_t) strata::kernels::NG_HIST * strata::kernels::NG_HC_DIM * sizeof(float));
    }
'''

HC = r'''
                if (oracle_large) {
                    const int64_t path[] = {oracle_norm_reused, gr_unfused(), ldx, xf16, hcd, hdown, upmixed,
                                           m.xn16_lo != nullptr, m.lo16_lo != nullptr, m.mixed_bf_lo != nullptr};
                    oracle.host(oracle_key, "hc_path", path, sizeof path);
                    if (!gr_unfused()) oracle_gpu(oracle_key, "hc_grs", m.grs, (size_t) T * HC * 4);
                    else oracle_gpu(oracle_key, "hc_xn", m.xn, (size_t) T * D * 4);
                    oracle_rows(oracle_key, "hc_xn16", m.xn16, (size_t) D * 2, (size_t) ldx * 2);
                    if (m.xn16_lo) oracle_gpu(oracle_key, "hc_xn16_lo", m.xn16_lo, (size_t) T * D * 2);
                    oracle_gpu(oracle_key, "hc_lo", m.lo, (size_t) T * LR * 4);
                    oracle_gpu(oracle_key, "hc_lo16", m.lo16, (size_t) T * LR * 2);
                    if (m.lo16_lo) oracle_gpu(oracle_key, "hc_lo16_lo", m.lo16_lo, (size_t) T * LR * 2);
                    if (!upmixed) oracle_gpu(oracle_key, "hc_gated", m.gated, (size_t) T * D * 4);
                    oracle_gpu(oracle_key, "hc_mixed", m.mixed, (size_t) T * N * 4);
                    oracle_gpu(oracle_key, "hc_mixed_h", m.mixed_h, (size_t) T * N * 2);
                    oracle_gpu(oracle_key, "hc_mixed_bf", m.mixed_bf, (size_t) T * N * 2);
                    if (m.mixed_bf_lo) oracle_gpu(oracle_key, "hc_mixed_bf_lo", m.mixed_bf_lo, (size_t) T * N * 2);
                    oracle_gpu(oracle_key, "hc_inj", m.inj, (size_t) T * HC * 4);
                }
'''

REBUILD = r'''
                        if (oracle.dir && oracle.ref) {
                            on_cpu = oracle.load<char>(oracle_key, "on_cpu", (size_t) m.g->n_expert);
                            strata_lab_full_oracle::require(on_cpu.empty() || on_cpu.size() == (size_t) m.g->n_expert,
                                                           "CPU map size " + oracle_key.str());
                            cpu_blob.assign(on_cpu.size(), nullptr);
                            n_cpu = 0; rows_cpu = 0; n_stream = 0;
                            for (int32_t e = 0; e < m.g->n_expert; ++e) {
                                const int32_t c = m.cnt[(size_t) e];
                                const bool resident = m.host_res && m.cache && m.host_res[(size_t) l * m.g->n_expert + e] >= 0;
                                if (cpu_maybe && c > 0 && !resident) ++n_stream;
                                if (on_cpu.empty() || !on_cpu[(size_t) e]) continue;
                                strata_lab_full_oracle::require(on_cpu[(size_t) e] == 1 && cpu_maybe && cpu_arm &&
                                    !resident && c > 0 && c <= strata::kernels::cpu::MAXT &&
                                    (m.src->pinned(l, e) || !m.src->transient(l, e)), "invalid replay CPU expert " + oracle_key.str());
                                const uint8_t* b = m.src->blob_stable(l, e);
                                strata_lab_full_oracle::require(b != nullptr, "stable CPU blob missing " + oracle_key.str());
                                cpu_blob[(size_t) e] = b; rows_cpu += c; ++n_cpu;
                            }
                        } else '''



def transform(source):
    if MARKER in source:
        raise ValueError('FULL_ORACLE_ALREADY_PATCHED')
    if hashlib.sha256(source.encode()).hexdigest() != SOURCE_SHA256:
        raise ValueError('FULL_ORACLE_SOURCE_IDENTITY')
    source = once(source, '#include "strata/kernels/fused_gr.hpp"', HEADER.read_text() + '\n#include "strata/kernels/fused_gr.hpp"')
    anchor = '''    for (int64_t b0 = r0; b0 < n; b0 += B) {
        const int64_t nb = std::min(B, n - b0), c0 = cell0 + b0;'''
    source = once(source, anchor, anchor + r'''
        if (std::getenv("STRATA_LAB_ORACLE_DIR"))
            std::fprintf(stderr, "P14_FULL_MTP_BATCH {\"cell0\":%lld,\"n\":%lld,\"r0\":%lld,\"B\":%lld,\"b0\":%lld,\"nb\":%lld,\"c0\":%lld,\"q8\":%d,\"kv_mode\":%d,\"n_slots\":%lld}\n",
                         (long long) cell0, (long long) n, (long long) r0, (long long) B, (long long) b0,
                         (long long) nb, (long long) c0, int(q8), int(st.kv_mode), (long long) st.n_slots);
''')
    start = source.index('bool Prefill::run_impl(')
    end = source.index('void Prefill::lm_release()', start)
    prefix, source, suffix = source[:start], source[start:end], source[end:]
    anchor = '''    const uint64_t gdn_floats = (uint64_t) g.ssm_state_size * g.ssm_v_heads * g.ssm_state_size +
                                (uint64_t) g.ssm_conv_channels * (g.ssm_d_conv - 1);'''
    source = once(source, anchor, anchor + INITIAL)
    anchor = '        const int64_t T = std::min(C, n - c0), p0 = pos0 + c0;'
    source = once(source, anchor, anchor + CHUNK)
    anchor = '                // ---- the hyper-connection read of this half\n'
    source = once(source, anchor, HALF + anchor)
    anchor = '                if (gr_unfused()) gr_norm(m.R, (const float*) wn->data, EPS, m.xn, m.xn16, T, m.cs, m.xn16_lo, xf16);'
    source = once(source, anchor, NORM + anchor)
    anchor = '                if (wd_q8.data) {   // the HC GEMMs that read the scratch are enqueued: the next user waits for them'
    source = once(source, anchor, HC + anchor)
    anchor = '                    // ======================= MoE ======================='
    source = once(source, anchor, anchor + '''
                    if (oracle.dir) {
                        strata_lab_full_oracle::require(!stream_all && !ps_on && !m.pp, "streamed/peer FFN unsupported " + oracle_key.str());
                        ++oracle.ffn;
                    }
''')
    anchor = '                    route(m.logits, m.ids, m.w, T, m.g->n_expert, m.cs);'
    source = once(source, anchor, anchor + '''
                    if (oracle.dir) {
                        oracle_gpu(oracle_key, "ids", m.ids, (size_t) T * K * 4);
                        oracle_gpu(oracle_key, "w", m.w, (size_t) T * K * 4);
                    }
''')
    anchor = '                    size_t n_order = 0;'
    source = once(source, anchor, '''                    if (oracle.dir) {
                        strata_lab_full_oracle::require(!fused_l, "fused FFN unsupported " + oracle_key.str());
                        const int64_t shape[] = {use_mmq, lay.native, mmq_gt, mmq_dt, had_gu, had_d, had_block,
                                                MMQ_GROUP, m.f16_io, m.fused_bufs, m.ring};
                        oracle.host(oracle_key, "mmq_geometry", shape, sizeof shape);
                        if (lay.native) {
                            const auto& f = lay.fmt[(size_t) l];
                            const int64_t format[] = {f.gu_type, f.d_type, (int64_t) f.gu_row, (int64_t) f.d_row,
                                (int64_t) f.up_off, (int64_t) f.down_off, (int64_t) f.tail_off, f.n_embd, f.n_ff};
                            oracle.host(oracle_key, "native_geometry", format, sizeof format);
                        }
                    }
''' + anchor)
    anchor = '                        if (cpu_maybe && cpu_arm) {'
    source = once(source, anchor, '''                        if (oracle.dir) {
                            const int64_t available = cpu_maybe;
                            oracle.host(oracle_key, "cpu_maybe", &available, sizeof available);
                            if (oracle.ref) {
                                const auto saved = oracle.load<int64_t>(oracle_key, "cpu_arm", 1);
                                strata_lab_full_oracle::require(saved.size() == 1 && (saved[0] == 0 || saved[0] == 1), "invalid reference CPU arm");
                                cpu_arm = saved[0] != 0;
                            }
                            const int64_t arm = cpu_arm;
                            oracle.host(oracle_key, "cpu_arm", &arm, sizeof arm);
                        }
''' + anchor)
    anchor = '                        if (cpu_maybe) {\n                            std::vector<std::pair<int32_t, int32_t>> cand;'
    source = once(source, anchor, REBUILD + anchor.lstrip())
    anchor = '                        // multi-GPU: the rows of the experts the peer computes go last, as one block [rows_local, T*K)'
    source = once(source, anchor, '''                        if (oracle.dir) {
                            const int64_t resident = m.host_res && m.cache;
                            oracle.host(oracle_key, "resident_present", &resident, sizeof resident);
                            if (resident) oracle.host(oracle_key, "host_res", m.host_res + (size_t) l * m.g->n_expert,
                                                      (size_t) m.g->n_expert * sizeof(*m.host_res));
                            oracle.vec(oracle_key, "on_cpu", on_cpu);
                            const int64_t choice[] = {n_cpu, rows_cpu, n_stream};
                            oracle.host(oracle_key, "cpu_selection", choice, sizeof choice);
                        }
''' + anchor)
    anchor = '                        if (grp_mapped) {\n                            copy_i32(m.slot_dev, m.grp_dev + m.grp_tk, T * K, m.cs);'
    source = once(source, anchor, '''                        if (oracle.dir) {
                            oracle.vec(oracle_key, "cnt", m.cnt);
                            oracle.vec(oracle_key, "off", m.off);
                            oracle.vec(oracle_key, "order", order);
                            oracle.host(oracle_key, "slot", slot_h, (size_t) T * K * 4);
                            oracle.host(oracle_key, "src", src_h, (size_t) T * K * 4);
                        }
''' + anchor)
    anchor = '                        ws::Layer wl;'
    source = once(source, anchor, '''                        if (oracle.dir) {
                            const int64_t shape[] = {wmma_l, (int64_t) mmq_gub, (int64_t) mmq_db, rows_local};
                            oracle.host(oracle_key, "group_geometry", shape, sizeof shape);
                        }
''' + anchor)
    anchor = '                            // STRATA_MMQ_WS=1 (moe_ws.hpp, GP100):'
    source = once(source, anchor, '''                            if (oracle.dir) oracle.vec(oracle_key, "bounds", m.bounds_host);
''' + anchor)
    anchor = '                        mmq::WeightTab tgu, td;'
    source = once(source, anchor, '''                        if (oracle.dir) {
                            const int64_t path[] = {direct, wmma_l, ws_layer, group_gather, group_resident, stage_n};
                            oracle.host(oracle_key, "dispatch_path", path, sizeof path);
                            if (ws_layer) strata_lab_full_oracle::reject("weight-stationary path has no per-group transcript " + oracle_key.str());
                        }
''' + anchor)
    anchor = '                                    if (gp) {   // read in its slot: the guard after the blob is zeroed at the group end'
    source = once(source, anchor, '''                                    if (oracle.dir) {
                                        const int64_t actual[] = {(int64_t) j, e, cslot, gp != nullptr, ns};
                                        oracle.host(oracle_key, "direct_member_" + std::to_string(j), actual, sizeof actual);
                                    }
''' + anchor)
    anchor = '                                pt.mark(kPfGemmGU, cs);\n                                if (wmma_l) {'
    source = once(source, anchor, '''                                if (oracle.dir) {
                                    const std::string suffix = std::to_string(g);
                                    std::vector<int32_t> members(order.begin() + j0, order.begin() + j + 1);
                                    oracle.vec(oracle_key, "group_members_" + suffix, members);
                                    const int64_t shape[] = {(int64_t) j0, (int64_t) j, ngx, maxr, r0, nr, direct, wmma_l, T * K};
                                    oracle.host(oracle_key, "group_shape_" + suffix, shape, sizeof shape);
                                }
''' + anchor)
    anchor = '                            const int64_t o0 = m.off[(size_t) e], ne = m.cnt[(size_t) e];'
    source = once(source, anchor, anchor + '''
                            if (oracle.dir) {
                                const int64_t shape[] = {(int64_t) j, e, o0, ne, 0, 0};
                                oracle.host(oracle_key, "fp16_expert_" + std::to_string(j), shape, sizeof shape);
                            }
''')
    anchor = '                pt.mark(kPfHcWrite, cs);'
    source = once(source, anchor, '''                if (oracle_large) {
                    oracle_gpu(oracle_key, "body_bo", m.bo, (size_t) T * N * 4);
                    oracle_gpu(oracle_key, "body_inj", m.inj, (size_t) T * HC * 4);
                }
''' + anchor)
    anchor = '                if (steered && !cv_fused)   // --control-vector-scaled'
    # Capture after the optional steering, before DFlash2 taps, via the unique preprocessor boundary.
    end_write = '''                    strata::kernels::cvec_apply(m.R, l, T, D, nullptr, 0, nullptr, 0, false, m.cs);
#if defined(STRATA_HAVE_DFLASH2)'''
    source = once(source, end_write, '''                    strata::kernels::cvec_apply(m.R, l, T, D, nullptr, 0, nullptr, 0, false, m.cs);
                if (oracle_large) {
                    const int64_t write[] = {normed, fuse, cv_fused, steered};
                    oracle.host(oracle_key, "hc_write_path", write, sizeof write);
                    oracle_gpu(oracle_key, "hc_write_R", m.R, (size_t) T * D * 4);
                }
#if defined(STRATA_HAVE_DFLASH2)''')
    anchor = '\n        stats_.tokens += T;\n'
    source = once(source, anchor, '''        if (oracle.dir) {
            oracle_gpu(oracle_chunk, "chunk_end_R", m.R, (size_t) T * D * 4);
            ++oracle.chunks;
            oracle.chunk_open = false;
        }
''' + anchor)
    return prefix + source + suffix


def apply(tree, patch):
    tree, patch = Path(tree), Path(patch)
    if patch.exists():
        raise ValueError('FULL_ORACLE_PATCH_OUTPUT_EXISTS')
    path = tree / RELATIVE
    old = path.read_text()
    new = transform(old)
    diff = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                     fromfile='a/' + str(RELATIVE), tofile='b/' + str(RELATIVE)))
    patch.write_text(diff)
    path.write_text(new)
    return {'source_sha256': SOURCE_SHA256, 'patched_sha256': hashlib.sha256(new.encode()).hexdigest(),
            'patch_sha256': hashlib.sha256(diff.encode()).hexdigest(), 'scope': 'full-request diagnostic; original FFN once'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--patch', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(apply(args.tree, args.patch), indent=2))


if __name__ == '__main__':
    main()
