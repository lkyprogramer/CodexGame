"""Extend the frozen oracle to actual 4096/16384 streamed chunks; diagnostic only."""
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'oracle_replay'))
import full_request_patch
import private_control_patch


def transform(source):
    if hashlib.sha256(source.encode()).hexdigest() != full_request_patch.SOURCE_SHA256:
        raise ValueError('BOUNDARY_SOURCE_DRIFT')
    source = full_request_patch.transform(source)
    once = full_request_patch.once
    source = once(source, '!stream_all && !ps_on && !m.pp, "streamed/peer FFN unsupported "',
                  '!ps_on && !m.pp, "peer FFN unsupported "')
    source = source.replace('p0 == 0 && T == 4090 && l ==',
                            'p0 == 0 && (T == 4096 || T == 16384) && l ==')
    source = once(source, 'strata_lab_full_oracle::require(!fused_l, "fused FFN unsupported " + oracle_key.str());', r'''
                        const int64_t execution[] = {stream_all, fused_l, cpu_share_on(), stream_all_min(), m.ring};
                        oracle.host(oracle_key, "stream_execution", execution, sizeof execution);
                        const int64_t resident = m.host_res && m.cache;
                        oracle.host(oracle_key, "stream_resident_present", &resident, sizeof resident);
                        if (resident) oracle.host(oracle_key, "stream_host_res", m.host_res + (size_t) l * m.g->n_expert,
                                                  (size_t) m.g->n_expert * sizeof(*m.host_res));''')
    anchor = '                        fused::group(m.ids, T * K, (int) K, (int) m.g->n_expert, m.GU, m.slot_dev, m.src_dev, m.cs);'
    source = once(source, anchor, anchor + r'''
                        oracle_gpu(oracle_key, "fused_slot", m.slot_dev, (size_t) T * K * 4);
                        oracle_gpu(oracle_key, "fused_src", m.src_dev, (size_t) T * K * 4);
''')
    control = private_control_patch.CONTROL
    control = control.replace('p0 == 0 && T == 4090 && m.T == 4096',
                              'p0 == 0 && (T == 4096 || T == 16384) && m.T == T')
    control = control.replace('P18_PRIVATE_HC', 'P19_PRIVATE_HC')
    control = control.replace('            Alloc h;', r'''
            size_t free_bytes = 0, total_bytes = 0;
            strata_lab_full_oracle::require(cudaMemGetInfo(&free_bytes, &total_bytes) == cudaSuccess,
                                            "private HC free-memory query");
            const uint64_t required_bytes = lab_hc_set_bytes((size_t) m.T, m.f16_io);
            std::fprintf(stderr, "P19_CONTROL_MEMORY {\"free_bytes\":%zu,\"required_bytes\":%llu}\n",
                         free_bytes, (unsigned long long) required_bytes);
            strata_lab_full_oracle::require(free_bytes >= required_bytes, "private HC control VRAM headroom");
            Alloc h;''')
    source = once(source, private_control_patch.ANCHOR, private_control_patch.ANCHOR + control)
    # Actual extent is recorded even with the numerical oracle disabled for lifecycle tests.
    source = once(source, '        const bool stream_all = m.ring > STAGE && T >= stream_all_min() && m.src != nullptr;', r'''
        const bool stream_all = m.ring > STAGE && T >= stream_all_min() && m.src != nullptr;
        if (std::getenv("STRATA_LAB_BOUNDARY_TRACE"))
            std::fprintf(stderr, "P19_CHUNK {\"p0\":%lld,\"T\":%lld,\"allocated_T\":%lld,\"stream_all\":%s,\"cpu_share_limit\":%lld}\n",
                (long long) p0, (long long) T, (long long) m.T, stream_all ? "true" : "false", (long long) stream_all_min());
''')
    return source
