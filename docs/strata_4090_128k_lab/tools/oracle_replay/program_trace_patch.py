"""Record actual successful MTP extents and live PLE scalars for the GEN1 oracle."""
import hashlib
from pathlib import Path

SOURCE_SHA256 = 'ba0f0a92b152848df4bcb403bc85eec62d21aa041615706f20ba105c5582340f'


def transform(source):
    if hashlib.sha256(source.encode()).hexdigest() != SOURCE_SHA256:
        raise ValueError('PROGRAM_TRACE_SOURCE_DRIFT')

    def add_after(anchor, addition):
        nonlocal source
        if source.count(anchor) != 1:
            raise ValueError('PROGRAM_TRACE_ANCHOR: ' + anchor[:80])
        source = source.replace(anchor, anchor + addition, 1)

    add_after('            cur = ids;', r'''
            if (std::getenv("STRATA_LAB_ORACLE_DIR")) {
                if (max_new != 1) { std::fprintf(stderr, "P14_FULL REJECT GEN1 required\n"); return 86; }
                std::fprintf(stderr, "P14_FULL_REQUEST {\"input_tokens\":%lld,\"max_new\":%lld,\"use_mtp\":%s}\n",
                    (long long) n, (long long) max_new, use_mtp ? "true" : "false");
            }
''')
    add_after('            if (!e.empty() || (use_mtp && !batched && !mtp.prefill(R_rows, nxt.data(), T, p0, e))) return false;', r'''
            if (std::getenv("STRATA_LAB_ORACLE_DIR") && use_mtp)
                std::fprintf(stderr, "P14_FULL_MTP_RANGE {\"stage\":\"chunk\",\"batched\":%s,\"requested_start\":%lld,"
                    "\"requested_rows\":%lld,\"start\":%lld,\"end\":%lld,\"first_needed\":%lld,\"kv_mode\":%d}\n",
                    batched ? "true" : "false", (long long) p0, (long long) T,
                    (long long) std::min(p0 + T, std::max(p0, mtp.first_needed())), (long long) (p0 + T),
                    (long long) mtp.first_needed(), mtp.kv_state().kv_mode);
''')
    add_after('                // the window\'s first a + 1 tokens are in the session now (the last output is not: it is next x)', r'''
                if (std::getenv("STRATA_LAB_ORACLE_DIR") && merged && use_mtp)
                    std::fprintf(stderr, "P14_FULL_MTP_RANGE {\"stage\":\"merged\",\"batched\":false,"
                        "\"requested_start\":%lld,\"requested_rows\":%d,\"start\":%lld,\"end\":%lld,"
                        "\"first_needed\":%lld,\"kv_mode\":%d}\n", (long long) p, T - 1,
                        (long long) std::min(p + T - 1, std::max(p, mtp.first_needed())), (long long) (p + T - 1),
                        (long long) mtp.first_needed(), mtp.kv_state().kv_mode);
''')
    add_after('                                               nullptr, gated_proposal ? &generation : nullptr);', r'''
                if (std::getenv("STRATA_LAB_ORACLE_DIR"))
                    std::fprintf(stderr, "P14_FULL_DRAFT_CALL {\"called\":%s,\"produced\":%lld,\"max_new\":%lld,\"T\":%d}\n",
                        (use_mtp && !eos && produced_n < max_new) ? "true" : "false",
                        (long long) produced_n, (long long) max_new, T);
''')
    add_after('                        // the live running state comes off the device in one synchronous copy', r'''
                        if (std::getenv("STRATA_LAB_ORACLE_DIR"))
                            std::fprintf(stderr, "P14_FULL_STATE_META {\"live_tokens\":%zu,\"ple_prev\":[%d,%d],"
                                "\"ple_token\":%d,\"gdn_ord0\":%lld,\"gdn_alloc\":%lld,\"qsa_ord0\":%lld,"
                                "\"qsa_alloc\":%lld,\"mtp_first_needed\":%lld,\"mtp_window\":%lld,\"mtp_mode\":%d}\n",
                                live.size(), ss.ple_prev[0], ss.ple_prev[1], ss.ple_token,
                                (long long) ss.gdn_ord0, (long long) ss.gdn_alloc, (long long) ss.qsa_ord0,
                                (long long) ss.qsa_alloc, (long long) mtp.first_needed(), (long long) mtp.window(),
                                mtp.kv_state().kv_mode);
''')
    return source


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    args = p.parse_args()
    args.source.write_text(transform(args.source.read_text()))
