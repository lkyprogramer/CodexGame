#pragma once
// Lab-only serial serve observation. No CUDA calls, allocation or I/O in a window.
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>

namespace strata::lab_p01b {
constexpr int kWindows = 2048, kTokens = 2048;
struct Window {
    int64_t begin = 0, verified = 0, commit_enter = 0, commit_return = 0;
    int64_t draft_return = 0, end = 0, context = 0;
    int T = 0, kept = 0, emitted = 0, pending = 0, astate = -1;
    bool first = false, merged = false, clean = false, job = false, idle = false, adapt = false;
};
struct State {
    const char* prefix = std::getenv("STRATA_LAB_P01B_TRACE");
    Window windows[kWindows]{};
    int32_t tokens[kTokens]{};
    int request = -1, count = 0, ntokens = 0;
    int64_t begin = 0;
    Window* current = nullptr;
    bool overflow = false;
};
inline State& state() { static State s; return s; }
inline int64_t now() {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}
inline void begin_request() {
    auto& s = state(); if (!s.prefix) return;
    ++s.request; s.count = s.ntokens = 0; s.current = nullptr; s.overflow = false; s.begin = now();
}
inline void begin_window(int64_t context, int T, bool first, bool merged) {
    auto& s = state(); if (!s.prefix) return;
    const int i = s.count++; s.current = i < kWindows ? &s.windows[i] : nullptr;
    if (i >= kWindows) s.overflow = true;
    if (s.current) { *s.current = {}; s.current->begin = now(); s.current->context = context;
        s.current->T = T; s.current->first = first; s.current->merged = merged; }
}
inline void verified(bool clean) {
    auto* w = state().current; if (w) { w->verified = now(); w->clean = clean && !w->first && !w->merged && w->T > 1; }
}
inline void commit_enter(int kept, int pending, int astate, bool job, bool idle, bool adapt) {
    auto* w = state().current; if (w) { w->commit_enter = now(); w->kept = kept;
        w->pending = pending; w->astate = astate; w->job = job; w->idle = idle; w->adapt = adapt;
        w->clean = w->clean && pending == 0 && (!job || (astate == 0 && idle)) && !adapt; }
}
inline void commit_return() { auto* w = state().current; if (w) w->commit_return = now(); }
inline void token(int32_t id) {
    auto& s = state(); if (!s.prefix) return;
    if (s.ntokens < kTokens) s.tokens[s.ntokens++] = id; else s.overflow = true;
    if (s.current) ++s.current->emitted;
}
inline void draft_return() { auto* w = state().current; if (w) w->draft_return = now(); }
inline void end_window() { auto& s = state(); if (s.current) s.current->end = now(); s.current = nullptr; }
inline void end_request() {
    auto& s = state(); if (!s.prefix) return;
    const auto end = now(); char path[4096];
    const int n = std::snprintf(path, sizeof(path), "%s.%d.json", s.prefix, s.request);
    if (n < 0 || n >= (int) sizeof(path)) return;
    // Exclusive creation preserves original evidence if a caller reuses a prefix.
    std::FILE* f = std::fopen(path, "wx"); if (!f) return;
    std::fprintf(f, "{\"schema_version\":1,\"request_index\":%d,\"clock_domain\":\"steady_clock\","
        "\"start_ns\":%lld,\"end_ns\":%lld,\"total_windows\":%d,\"window_limit\":%d,"
        "\"overflow\":%s,\"token_ids\":[", s.request, (long long)s.begin, (long long)end,
        s.count, kWindows, s.overflow ? "true" : "false");
    for (int i = 0; i < s.ntokens; ++i) std::fprintf(f, "%s%d", i ? "," : "", s.tokens[i]);
    std::fprintf(f, "],\"windows\":[");
    const int count = s.count < kWindows ? s.count : kWindows;
    for (int i = 0; i < count; ++i) {
        const auto& w = s.windows[i];
        std::fprintf(f, "%s{\"window_id\":%d,\"begin_ns\":%lld,\"verified_ns\":%lld,"
            "\"commit_enter_ns\":%lld,\"commit_return_ns\":%lld,\"draft_return_ns\":%lld,"
            "\"end_ns\":%lld,\"context_tokens\":%lld,\"T\":%d,\"kept\":%d,\"emitted\":%d,"
            "\"first\":%s,\"merged\":%s,\"clean_serial_gap\":%s,\"pending\":%d,\"astate\":%d,"
            "\"async_job\":%s,\"job_idle\":%s,\"adapt_spawned\":%s}", i ? "," : "", i,
            (long long)w.begin, (long long)w.verified, (long long)w.commit_enter,
            (long long)w.commit_return, (long long)w.draft_return, (long long)w.end,
            (long long)w.context, w.T, w.kept, w.emitted, w.first ? "true" : "false",
            w.merged ? "true" : "false", w.clean ? "true" : "false", w.pending, w.astate,
            w.job ? "true" : "false", w.idle ? "true" : "false", w.adapt ? "true" : "false");
    }
    std::fprintf(f, "]}\n"); std::fclose(f);
}
}  // namespace strata::lab_p01b
