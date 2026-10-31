"""Insert a bounded host observer into the frozen P6 serial serve loop only."""
from pathlib import Path
import difflib
import hashlib

SOURCE_SHA256 = "ba0f0a92b152848df4bcb403bc85eec62d21aa041615706f20ba105c5582340f"
HEADER = "include/strata/core/lab_p01b_trace.hpp"
NATIVE = "src/program/generate.cpp"


def patched_source(source):
    replacements = [
        ('#include "strata/platform/memory.hpp"', '#include "strata/core/lab_p01b_trace.hpp"\n#include "strata/platform/memory.hpp"'),
        ('            // STRATA_DECODE_TIMING=1: where a request\'s decode time goes (one line per request)',
         '            strata::lab_p01b::begin_request();\n            // STRATA_DECODE_TIMING=1: where a request\'s decode time goes (one line per request)'),
        ('                const Clock::time_point tw0 = Clock::now();\n                // STRATA_SPEC_PROB:',
         '                const Clock::time_point tw0 = Clock::now();\n                strata::lab_p01b::begin_window(p, T, first_window, merged);\n                // STRATA_SPEC_PROB:'),
        ('                if (aflipped) apply_pending(true);   // 0.1.43:',
         '                strata::lab_p01b::verified(!pipe && n_stages == 1 && !remote_opt && !remote_caches && !peer.valid() && !multi_gpu && !drive.d.fs &&\n                    pending.empty() && !aflipped && (!ajob || (astate == AState::Idle && ajob->idle())));\n                if (aflipped) apply_pending(true);   // 0.1.43:'),
        ('                if (!ver.commit(a + 1, err)) {\n                    if (adapt_thr.joinable()) adapt_thr.join();',
         '                if (adapt_thr.joinable())\n                    strata::lab_p01b::commit_enter(a + 1, -1, -1, true, false, true);\n                else\n                    strata::lab_p01b::commit_enter(a + 1, (int)pending.size(), (int)astate, (bool)ajob,\n                        !ajob || ajob->idle(), false);\n                if (!ver.commit(a + 1, err)) {\n                    if (adapt_thr.joinable()) adapt_thr.join();'),
        ('                if (nonfinite_hit(ver, first_window ? "first decode" : "decode")) {',
         '                strata::lab_p01b::commit_return();\n                if (nonfinite_hit(ver, first_window ? "first decode" : "decode")) {'),
        ('                    std::printf("T %d\\n", (int) outv[(size_t) i]);\n                    if (req_logprobs >= 0)',
         '                    strata::lab_p01b::token(outv[(size_t) i]);\n                    std::printf("T %d\\n", (int) outv[(size_t) i]);\n                    if (req_logprobs >= 0)'),
        ('                    const Clock::time_point tw3 = Clock::now();\n                    auto msd =',
         '                    const Clock::time_point tw3 = Clock::now();\n                    strata::lab_p01b::draft_return();\n                    auto msd ='),
        ('                if (eos) { finish = "stop"; break; }\n                if (stop_req.load()) { finish = "cancel"; break; }\n                x = outv[(size_t) a];',
         '                strata::lab_p01b::end_window();\n                if (eos) { finish = "stop"; break; }\n                if (stop_req.load()) { finish = "cancel"; break; }\n                x = outv[(size_t) a];'),
        ('            if (dec_timing && dec_windows > 0) {\n                const DecSnap d1 = dec_snap();',
         '            strata::lab_p01b::end_request();\n            if (dec_timing && dec_windows > 0) {\n                const DecSnap d1 = dec_snap();'),
    ]
    for old, new in replacements:
        count = source.count(old)
        if count != 1:
            raise ValueError(f"P6 patch anchor count {count}: {old[:100]}")
        source = source.replace(old, new, 1)
    return source


def apply(tree):
    tree = Path(tree)
    path = tree / NATIVE
    original = path.read_text()
    if hashlib.sha256(path.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("P6 source hash mismatch")
    header = tree / HEADER
    if header.exists():
        raise ValueError("Capture header exists; refuse reapplication")
    changed = patched_source(original)
    patch = ''.join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                                       fromfile='a/' + NATIVE, tofile='b/' + NATIVE))
    header.write_bytes(Path(__file__).with_name('lab_p01b_trace.hpp').read_bytes())
    path.write_text(changed)
    return patch


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('tree', type=Path)
    args = p.parse_args()
    print(apply(args.tree), end='')
