"""Apply the lab-only, default-off GU accounting/capture patch to the frozen tree."""
from pathlib import Path
import shutil
import sys


def replace(text, before, after):
    if text.count(before) != 1:
        raise ValueError('profile patch anchor count: '+str(text.count(before))+' '+before[:80])
    return text.replace(before, after)


def apply(tree):
    tree = Path(tree)
    h = tree/'include/strata/kernels/cpu/pool.hpp'
    s = h.read_text()
    s = replace(s, 'class ExpertPool {', 'class LabGuProfile;\nclass ExpertPool {')
    s = replace(s, '    int n_ = 0;', '    std::unique_ptr<LabGuProfile> lab_gu_profile_;\n    int n_ = 0;')
    h.write_text(s)
    p = tree/'src/kernels/cpu/pool.cpp'; s=p.read_text()
    s = replace(s, '#include "strata/kernels/cpu/pool.hpp"', '#include "strata/kernels/cpu/pool.hpp"\n#include "lab_gu_profile.hpp"')
    s = replace(s, '    wstate_.reset(new std::atomic<int32_t>[(size_t) n_]);',
                '    if (std::getenv("STRATA_LAB_GU_PROFILE")) lab_gu_profile_.reset(new LabGuProfile(n_+1));\n    wstate_.reset(new std::atomic<int32_t>[(size_t) n_]);')
    old='                    native_gu_rows(*nfmt, mjobs_[e].blob, mjobs_[e].nact, mjobs_[e].nt, ff, r0, r1);'
    new='''                    const int64_t gu_start = lab_gu_profile_ ? lab_gu_now_ns() : 0;
''' + old + '''
                    if (lab_gu_profile_) lab_gu_profile_->work(id >= 0 ? id : n_, nfmt->gu_type,
                        mjobs_[e].nt, r1-r0, lab_gu_now_ns()-gu_start);'''
    s=replace(s,old,new)
    s=replace(s, '        const auto a = std::chrono::steady_clock::now();\n        run_phase(5, mtasks_);',
                '        if (lab_gu_profile_) lab_gu_profile_->capture(f, mjobs_, nb);\n        const auto a = std::chrono::steady_clock::now();\n        run_phase(5, mtasks_);')
    old='        ms_multi_down += std::chrono::duration<double, std::milli>(d - c).count();'
    s=replace(s,old,old+'''
        if (lab_gu_profile_) lab_gu_profile_->phase(f, mjobs_, nb,
            std::chrono::duration_cast<std::chrono::nanoseconds>(b-a).count(),
            std::chrono::duration_cast<std::chrono::nanoseconds>(c-b).count(),
            std::chrono::duration_cast<std::chrono::nanoseconds>(d-c).count());''')
    p.write_text(s)
    p=tree/'src/kernels/cpu/native_expert.cpp';s=p.read_text()
    anchor='#include "strata/kernels/cpu/native_expert.hpp"'
    s=replace(s,anchor,anchor+'\n#include "lab_gu_profile.hpp"')
    anchor='    const ggml_vec_dot_t dot = traits(f.gu_type)->vec_dot;'
    s=replace(s,anchor,anchor+'\n    lab_gu_oracle(f.gu_type, nt, reinterpret_cast<const void*>(dot));')
    p.write_text(s)
    shutil.copy2(Path(__file__).with_name('lab_gu_profile.hpp'), tree/'src/kernels/cpu/lab_gu_profile.hpp')


if __name__=='__main__':
    apply(sys.argv[1])
