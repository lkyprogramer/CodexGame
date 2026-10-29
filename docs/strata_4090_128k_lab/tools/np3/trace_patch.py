"""NP-3 P01-02 step 2: add STRATA_LAB_NP3_TRACE to the CPU expert pool (A0 5c8dd322), lab only, off by default.

  python tools/np3/trace_patch.py <strata worktree>

Where a pool phase's time goes, per kind of phase (gate/up or down, by experts in the phase):
  host     pre (wait for every worker parked before it), pub (begin_batch), done (publish -> wait_done returns),
           repark (wait_done -> every worker parked again), gap (end of gate/up -> start of down: the serial quantize)
  threads  wake (publish -> a worker sees the epoch), first claim, last task end, drain exit, rows time, claim time,
           workers that woke and claimed nothing
Each thread adds to its own cache-line-aligned block; the host reads the blocks only after every thread has parked
again (the re-park it waits for orders them) and prints cumulative lines every N phases and when the pool is
destroyed.  Nothing is added to the park spin.  STRATA_LAB_NP3_TRACE=1 prints every 20000 phases, N > 1 every N.
Start-up receipt: `LAB_NP3_TRACE enabled=0|1`.
"""
import sys
from pathlib import Path

tree = Path(sys.argv[1])
hpp = tree / 'include/strata/kernels/cpu/pool.hpp'
cpp = tree / 'src/kernels/cpu/pool.cpp'


def rep(text, old, new, path):
    if text.count(old) != 1:
        sys.exit(f'{path}: anchor found {text.count(old)} times: {old[:80]!r}')
    return text.replace(old, new)


h = hpp.read_text()
h = rep(h, """    bool numa_phase() const { return numa_n_ > 0 && mode_ >= 5; }
""", """    bool numa_phase() const { return numa_n_ > 0 && mode_ >= 5; }
    // STRATA_LAB_NP3_TRACE (lab only; off when unset or 0): where a phase's time goes - the wait before it, the
    // publish, each thread's wake / first claim / rows / last task / drain exit, the wait for `done`, the re-park.
    // Each thread adds to its own block; the host reads the blocks only after every thread has parked again (the
    // re-park it waits for orders them) and prints them every `np3_every_` phases and when the pool is destroyed.
    // Nothing is added to the park spin.
    struct Np3Acc {   // one kind of phase, one thread
        int64_t phases = 0, idle = 0, tasks = 0, wake_ns = 0, first_ns = 0, finish_ns = 0, exit_ns = 0, busy_ns = 0,
                claim_ns = 0;
    };
    struct Np3Host {  // one kind of phase, the host's view
        int64_t phases = 0, experts = 0, nt = 0, bytes = 0, pre_ns = 0, pub_ns = 0, done_ns = 0, repark_ns = 0,
                gap_ns = 0;
    };
    // modes 5 (gate/up) and 6 (down) by experts in the phase (1, 2, 3, 4+), run_phase's modes 0-4, then `run()`
    static constexpr int kNp3Kinds = 14, kNp3Run = 13;
    struct alignas(64) Np3Thread {
        Np3Acc k[kNp3Kinds];
        int64_t wake_at = 0;
    };
    alignas(64) int64_t np3_every_ = 0;   // 0: off.  Written once, by the constructor
    int64_t np3_pub_ = 0;                 // the phase's publish time and kind, written before the publish
    int np3_kind_ = 0;
    std::unique_ptr<Np3Thread[]> np3_;    // n_ + 1 blocks, the host's last
    alignas(64) int64_t np3_phases_ = 0;  // host only from here
    int64_t np3_end_ = 0;
    Np3Host np3_host_[kNp3Kinds];
    int np3_kind(int mode) const;
    void np3_phase_end(int mode, int64_t t0, int64_t t1, int64_t t2, int64_t t3);
    void np3_print(const char* why) const;
""", hpp)
hpp.write_text(h)

c = cpp.read_text()
c = rep(c, """        spin_before_sleep_ = std::chrono::microseconds((std::max)(0, std::atoi(e)));
""", """        spin_before_sleep_ = std::chrono::microseconds((std::max)(0, std::atoi(e)));
    if (const char* e = std::getenv("STRATA_LAB_NP3_TRACE")) {   // lab only, see np3_print: 1 = every 20000 phases
        const long long v = std::atoll(e);
        np3_every_ = v <= 0 ? 0 : v == 1 ? 20000 : v;
    }
""", cpp)
c = rep(c, """    scratch_.resize((size_t) n_);
    wstate_.reset(new std::atomic<int32_t>[(size_t) n_]);
""", """    scratch_.resize((size_t) n_);
    if (np3_every_ != 0) np3_.reset(new Np3Thread[(size_t) n_ + 1]);
    std::fprintf(stderr, "LAB_NP3_TRACE enabled=%d every=%lld workers=%d\\n", np3_every_ != 0 ? 1 : 0,
                 (long long) np3_every_, n_);
    wstate_.reset(new std::atomic<int32_t>[(size_t) n_]);
""", cpp)
c = rep(c, """ExpertPool::~ExpertPool() {
    const ExpertPool* self = this;
""", """ExpertPool::~ExpertPool() {
    if (np3_every_ != 0 && np3_phases_ > 0) np3_print("final");
    const ExpertPool* self = this;
""", cpp)
c = rep(c, """        seen = epoch_.load(std::memory_order_acquire);
        parked_of(id).fetch_sub(1, std::memory_order_acq_rel);   // leaving the park
""", """        seen = epoch_.load(std::memory_order_acquire);
        if (np3_every_ != 0) np3_[(size_t) id].wake_at = now_ns();
        parked_of(id).fetch_sub(1, std::memory_order_acq_rel);   // leaving the park
""", cpp)
c = rep(c, """    const int s = numa_n_ == 0 ? 0 : id >= 0 ? wslice_[(size_t) id] : hslice_;
    for (;;) {
""", """    const int s = numa_n_ == 0 ? 0 : id >= 0 ? wslice_[(size_t) id] : hslice_;
    const bool tr = np3_every_ != 0;   // STRATA_LAB_NP3_TRACE: this thread's claims and rows, timed
    int64_t t = tr ? now_ns() : 0, tc = 0, first = 0, last = 0, busy = 0, cl = 0, ntask = 0;
    for (;;) {
""", cpp)
c = rep(c, """        if (ci < 0) break;
        const uint32_t i = (uint32_t) ci;
        if (id >= 0) wstate_[(size_t) id].store(ci, std::memory_order_relaxed);
""", """        if (ci < 0) break;
        if (tr) {
            tc = now_ns();
            cl += tc - t;
            if (ntask == 0) first = tc;
        }
        const uint32_t i = (uint32_t) ci;
        if (id >= 0) wstate_[(size_t) id].store(ci, std::memory_order_relaxed);
""", cpp)
c = rep(c, """        } else {
            done_.fetch_add(1, std::memory_order_release);
        }
    }
}
""", """        } else {
            done_.fetch_add(1, std::memory_order_release);
        }
        if (tr) {
            t = now_ns();
            busy += t - tc;
            last = t;
            ++ntask;
        }
    }
    if (tr) {
        Np3Thread& me = np3_[(size_t) (id >= 0 ? id : n_)];
        Np3Acc& a = me.k[np3_kind_];
        const int64_t pub = np3_pub_;
        ++a.phases;
        a.tasks += ntask;
        a.exit_ns += now_ns() - pub;
        if (id >= 0) a.wake_ns += me.wake_at - pub;
        if (ntask == 0) {
            ++a.idle;
            return;
        }
        a.first_ns += first - pub;
        a.finish_ns += last - pub;
        a.busy_ns += busy;
        a.claim_ns += cl;
    }
}

int ExpertPool::np3_kind(int mode) const {
    if (mode < 5) return 8 + mode;
    const int64_t per = mode == 5 ? nfmt_->n_ff : nfmt_->n_embd;
    return (mode == 5 ? 0 : 4) + (int) (std::min)((int64_t) 4, mrows_ / per) - 1;
}

void ExpertPool::np3_phase_end(int mode, int64_t t0, int64_t t1, int64_t t2, int64_t t3) {
    const int64_t t4 = now_ns();
    Np3Host& h = np3_host_[np3_kind_];
    ++h.phases;
    h.pre_ns += t1 - t0;
    h.pub_ns += t2 - t1;
    h.done_ns += t3 - t1;
    h.repark_ns += t4 - t3;
    if (mode == 6 && np3_end_ != 0) h.gap_ns += t0 - np3_end_;   // since gate/up ended: the intermediate's quantize
    np3_end_ = t4;
    if (mode >= 5) {
        const int64_t nb = mrows_ / (mode == 5 ? nfmt_->n_ff : nfmt_->n_embd);
        h.experts += nb;
        for (int64_t e = 0; e < nb; ++e) h.nt += mjobs_[e].nt;
        h.bytes += mode == 5 ? nb * nfmt_->n_ff * 2 * (int64_t) nfmt_->gu_row : nb * nfmt_->n_embd * (int64_t) nfmt_->d_row;
    }
    if (++np3_phases_ % np3_every_ == 0) np3_print("periodic");
}

void ExpertPool::np3_print(const char* why) const {
    static const char* const names[kNp3Kinds] = {"gu1", "gu2", "gu3", "gu4+", "dn1", "dn2", "dn3", "dn4+",
                                                 "m0",  "m1",  "m2",  "m3",  "m4",  "run"};
    const int threads = n_ + 1;
    const auto us = [](int64_t ns, int64_t n) { return n > 0 ? (double) ns / (double) n / 1e3 : 0.0; };
    for (int k = 0; k < kNp3Kinds; ++k) {
        const Np3Host& h = np3_host_[k];
        if (h.phases == 0) continue;
        Np3Acc w;   // the workers' sums; the host's own block is np3_[n_]
        for (int i = 0; i < n_; ++i) {
            const Np3Acc& a = np3_[(size_t) i].k[k];
            w.phases += a.phases; w.idle += a.idle; w.tasks += a.tasks; w.wake_ns += a.wake_ns;
            w.first_ns += a.first_ns; w.finish_ns += a.finish_ns; w.exit_ns += a.exit_ns; w.busy_ns += a.busy_ns;
            w.claim_ns += a.claim_ns;
        }
        const Np3Acc& o = np3_[(size_t) n_].k[k];
        const int64_t worked = (w.phases - w.idle) + (o.phases - o.idle), tasks = w.tasks + o.tasks;
        const double done = us(h.done_ns, h.phases), busy = us(w.busy_ns + o.busy_ns, h.phases);
        std::fprintf(stderr,
                     "LAB_NP3_TRACE %s %s phases=%lld | host us: pre %.2f pub %.2f done %.2f repark %.2f gap %.2f"
                     " | threads us: wake %.2f first %.2f finish %.2f exit %.2f busy/phase %.2f (util %.3f)"
                     " task %.2f claim %.3f | tasks/phase %.2f host %.3f idle %.3f | experts/phase %.3f nt/expert %.3f"
                     " MB/phase %.4f GB/s done %.2f busy %.2f\\n",
                     why, names[k], (long long) h.phases, us(h.pre_ns, h.phases), us(h.pub_ns, h.phases), done,
                     us(h.repark_ns, h.phases), us(h.gap_ns, h.phases), us(w.wake_ns, w.phases),
                     us(w.first_ns + o.first_ns, worked), us(w.finish_ns + o.finish_ns, worked),
                     us(w.exit_ns + o.exit_ns, w.phases + o.phases), busy,
                     done > 0 ? busy / (threads * done) : 0.0, us(w.busy_ns + o.busy_ns, tasks),
                     us(w.claim_ns + o.claim_ns, tasks), (double) tasks / (double) h.phases,
                     tasks > 0 ? (double) o.tasks / (double) tasks : 0.0,
                     w.phases > 0 ? (double) w.idle / (double) w.phases : 0.0,
                     (double) h.experts / (double) h.phases, h.experts > 0 ? (double) h.nt / (double) h.experts : 0.0,
                     (double) h.bytes / (double) h.phases / 1e6, h.done_ns > 0 ? (double) h.bytes / (double) h.done_ns : 0.0,
                     w.busy_ns + o.busy_ns > 0 ? (double) h.bytes * threads / (double) (w.busy_ns + o.busy_ns) : 0.0);
    }
    // per thread over the native row phases (kinds 0-7): a core that wakes or finishes late shows here
    std::string wake, fin, share;
    int64_t all_tasks = 0;
    for (int i = 0; i < threads; ++i)
        for (int k = 0; k < 8; ++k) all_tasks += np3_[(size_t) i].k[k].tasks;
    for (int i = 0; i < threads; ++i) {
        Np3Acc a;
        for (int k = 0; k < 8; ++k) {
            const Np3Acc& b = np3_[(size_t) i].k[k];
            a.phases += b.phases; a.idle += b.idle; a.tasks += b.tasks; a.wake_ns += b.wake_ns; a.finish_ns += b.finish_ns;
        }
        char buf[64];
        std::snprintf(buf, sizeof buf, "%s%.2f", i ? "," : "", i < n_ ? us(a.wake_ns, a.phases) : 0.0);
        wake += buf;
        std::snprintf(buf, sizeof buf, "%s%.2f", i ? "," : "", us(a.finish_ns, a.phases - a.idle));
        fin += buf;
        std::snprintf(buf, sizeof buf, "%s%.2f", i ? "," : "", all_tasks > 0 ? 100.0 * (double) a.tasks / (double) all_tasks : 0.0);
        share += buf;
    }
    std::fprintf(stderr, "LAB_NP3_TRACE %s threads(native, host last) wake_us %s | finish_us %s | tasks_pct %s\\n", why,
                 wake.c_str(), fin.c_str(), share.c_str());
}
""", cpp)
c = rep(c, """void ExpertPool::run_phase(int mode, int n_tasks) {
    wait_parked("before a phase");
    mode_ = mode;
    njobs_ = n_tasks;
    const uint32_t e = begin_batch(n_tasks);
    if (host_works_) drain(-1, host_scratch_, e);
    wait_done(n_tasks);
    wait_parked("after a phase");
""", """void ExpertPool::run_phase(int mode, int n_tasks) {
    const bool tr = np3_every_ != 0;   // STRATA_LAB_NP3_TRACE
    const int64_t t0 = tr ? now_ns() : 0;
    wait_parked("before a phase");
    mode_ = mode;
    njobs_ = n_tasks;
    int64_t t1 = 0, t2 = 0, t3 = 0;
    if (tr) {
        np3_kind_ = np3_kind(mode);
        t1 = np3_pub_ = now_ns();
    }
    const uint32_t e = begin_batch(n_tasks);
    if (tr) t2 = now_ns();
    if (host_works_) drain(-1, host_scratch_, e);
    wait_done(n_tasks);
    if (tr) t3 = now_ns();
    wait_parked("after a phase");
""", cpp)
c = rep(c, """    hstate_.store(kIdle, std::memory_order_relaxed);
    hstate_ms_.store(now_ms(), std::memory_order_relaxed);
}

void ExpertPool::run_split(ExpertJob* jobs, int n) {
""", """    hstate_.store(kIdle, std::memory_order_relaxed);
    hstate_ms_.store(now_ms(), std::memory_order_relaxed);
    if (tr) np3_phase_end(mode, t0, t1, t2, t3);
}

void ExpertPool::run_split(ExpertJob* jobs, int n) {
""", cpp)
c = rep(c, """    mode_ = 0;
    const uint32_t e = begin_batch(n);   // done, then head (release), then the epoch: the batch is described first
""", """    mode_ = 0;
    if (np3_every_ != 0) {   // STRATA_LAB_NP3_TRACE: the workers' side of a run() batch (the host's: the three phases)
        np3_kind_ = kNp3Run;
        np3_pub_ = now_ns();
        ++np3_host_[kNp3Run].phases;
    }
    const uint32_t e = begin_batch(n);   // done, then head (release), then the epoch: the batch is described first
""", cpp)
cpp.write_text(c)
print('patched', hpp, cpp)
