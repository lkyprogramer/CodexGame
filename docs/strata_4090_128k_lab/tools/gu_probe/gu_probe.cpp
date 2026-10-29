// One-format, real-fixture parity and complete ExpertPool replay; never runs model-generated code.
#include "lab_gu_kernel.hpp"
#include "strata/kernels/cpu/pool.hpp"
#include "strata/kernels/cpu/expert_layout.hpp"
#include "ggml.h"
#include "ggml-cpu.h"
#include <immintrin.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

using namespace strata::kernels::cpu;
using Clock=std::chrono::steady_clock;
struct Blob { NativeFmt fmt;std::vector<uint8_t> bytes; };
struct Job {size_t blob;int nt;std::vector<std::vector<uint8_t>> act;};
using Batch=std::vector<Job>;
struct Data {std::vector<Blob> blobs;std::vector<Batch> batches;size_t bytes=0;};
static std::vector<uint8_t> load(const std::string& path,size_t expected) {
    std::ifstream file(path,std::ios::binary|std::ios::ate);
    if(!file || (size_t)file.tellg()!=expected)throw std::runtime_error("FIXTURE_FILE_SIZE "+path);
    std::vector<uint8_t> result(expected);file.seekg(0);file.read((char*)result.data(),expected);
    if(!file)throw std::runtime_error("FIXTURE_FILE_READ "+path);return result;
}
static Data dataset(const std::string& path) {
    std::ifstream f(path);int version,nblobs,nbatches;f>>version>>nblobs>>nbatches;
    if(!f || version!=1 || nblobs<1 || nblobs>192 || nbatches<1 || nbatches>256)throw std::runtime_error("FIXTURE_INDEX");
    Data d;
    for(int i=0;i<nblobs;++i) {
        int gu,down;long long embd,ff;size_t row,drow,up,off,bytes,act,h;std::string file;
        f>>gu>>down>>embd>>ff>>row>>drow>>up>>off>>bytes>>act>>h>>file;
        Blob b;std::string error;
        if(!f || gu!=21 || !native_fmt(gu,down,embd,ff,b.fmt,error))throw std::runtime_error("FIXTURE_FORMAT "+error);
        const auto& x=b.fmt;
        if(x.gu_row!=row || x.d_row!=drow || x.up_off!=up || x.down_off!=off || x.bytes!=bytes || x.act_bytes!=act || x.h_bytes!=h)
            throw std::runtime_error("FIXTURE_GEOMETRY_MISMATCH");
        b.bytes=load(file,bytes);d.bytes+=bytes;d.blobs.push_back(std::move(b));
    }
    for(int i=0;i<nbatches;++i) {
        int n;f>>n;if(!f || n<1 || n>ExpertPool::kMaxSplitMulti)throw std::runtime_error("FIXTURE_BATCH");
        Batch batch;
        for(int j=0;j<n;++j) {
            Job job;f>>job.blob>>job.nt;
            if(!f || job.blob>=d.blobs.size() || job.nt<1 || job.nt>MAXT)throw std::runtime_error("FIXTURE_JOB");
            for(int t=0;t<job.nt;++t){std::string file;f>>file;job.act.push_back(load(file,d.blobs[job.blob].fmt.act_bytes));}
            batch.push_back(std::move(job));
        }
        d.batches.push_back(std::move(batch));
    }
    return d;
}
static uint64_t digest(const void* input,size_t n,uint64_t h=1469598103934665603ULL) {
    auto* p=(const uint8_t*)input;for(size_t i=0;i<n;++i){h^=p[i];h*=1099511628211ULL;}return h;
}
static void equal(const void* a,const void* b,size_t n,const std::string& stage) {
    if(std::memcmp(a,b,n)!=0) {
        size_t i=0;while(i<n && ((const uint8_t*)a)[i]==((const uint8_t*)b)[i])++i;
        throw std::runtime_error("BIT_MISMATCH stage="+stage+" byte="+std::to_string(i));
    }
}
static void integer_parity() {
    std::mt19937 random(42);alignas(32) int16_t v[16],s[16];alignas(32) int32_t a[8],old[8],candidate[8];
    const int16_t edge[]={-32768,-32767,-128,-1,0,1,127,32767};
    for(int i=0;i<100000;++i) {
        for(int j=0;j<16;++j){v[j]=i<64?edge[(i+j)%8]:(int16_t)random();s[j]=i<64?edge[(i/8+j)%8]:(int16_t)random();}
        for(int j=0;j<8;++j)a[j]=(int32_t)random();
        _mm256_store_si256((__m256i*)old,_mm256_add_epi32(_mm256_load_si256((__m256i*)a),
            _mm256_madd_epi16(_mm256_load_si256((__m256i*)v),_mm256_load_si256((__m256i*)s))));
        lab_gu_integer_step(v,s,a,candidate);equal(old,candidate,sizeof old,"integer-step");
    }
}
static void direct_parity(const Data& data) {
    integer_parity();size_t dots=0,stages=0;
    std::vector<const std::vector<uint8_t>*> activations;
    for(const auto& batch:data.batches)for(const auto& job:batch)for(const auto& a:job.act) {
        if(activations.size()<32)activations.push_back(&a);
    }
    for(size_t bi=0;bi<std::min<size_t>(32,data.blobs.size());++bi) {
        const auto& b=data.blobs[bi];const auto& fmt=b.fmt;auto dot=ggml_get_type_traits_cpu((ggml_type)fmt.gu_type)->vec_dot;
        for(const auto* input:activations) {
            std::vector<float> reference(fmt.n_ff),candidate(fmt.n_ff);
            const void* act[]={input->data()};float* ff[]={reference.data()};lab_gu_set_mode(false);
            native_gu_rows(fmt,b.bytes.data(),act,1,ff,0,(int)fmt.n_ff);
            for(int r=0;r<fmt.n_ff;++r) {
                for(size_t offset:{(size_t)r*fmt.gu_row,fmt.up_off+(size_t)r*fmt.gu_row}) {
                    float old=0;dot((int)fmt.n_embd,&old,0,b.bytes.data()+offset,0,input->data(),0,1);
                    const float value=lab_gu_dot21((int)fmt.n_embd,b.bytes.data()+offset,input->data());
                    equal(&old,&value,sizeof old,"GU-dot");++dots;
                }
            }
            lab_gu_rows21(fmt,b.bytes.data(),input->data(),candidate.data(),0,(int)fmt.n_ff);
            equal(reference.data(),candidate.data(),candidate.size()*sizeof(float),"SwiGLU");
            // The current pack's real down format: Q2_0 uses the pool's own ActQ path.
            if(q2_native_kernels(fmt.d_type)) {
                ActQ old{},changed{};act_quant_any(reference.data(),(int)fmt.n_ff,old);act_quant_any(candidate.data(),(int)fmt.n_ff,changed);
                equal(&old,&changed,sizeof old,"Q2-quant");
                std::vector<float> x(fmt.n_embd),y(fmt.n_embd);const ActQ* ax[]={&old};const ActQ* ay[]={&changed};
                float* ox[]={x.data()};float* oy[]={y.data()};
                q2_rows_any(b.bytes.data()+fmt.down_off,fmt.d_row,(int)fmt.n_ff/64,ax,1,ox,0,(int)fmt.n_embd);
                q2_rows_any(b.bytes.data()+fmt.down_off,fmt.d_row,(int)fmt.n_ff/64,ay,1,oy,0,(int)fmt.n_embd);
                equal(x.data(),y.data(),x.size()*sizeof(float),"Q2-down");
            } else {
                std::vector<uint8_t> old(fmt.h_bytes),changed(fmt.h_bytes);native_quant_h(fmt,reference.data(),old.data());native_quant_h(fmt,candidate.data(),changed.data());
                equal(old.data(),changed.data(),old.size(),"native-quant");
                std::vector<float>x(fmt.n_embd),y(fmt.n_embd);const void* ax[]={old.data()};const void* ay[]={changed.data()};float* ox[]={x.data()};float* oy[]={y.data()};
                native_down_rows(fmt,b.bytes.data(),ax,1,ox,0,(int)fmt.n_embd);native_down_rows(fmt,b.bytes.data(),ay,1,oy,0,(int)fmt.n_embd);
                equal(x.data(),y.data(),x.size()*sizeof(float),"native-down");
            }
            for(const auto range: {std::pair<int,int>{0,1},{1,17},{17,(int)fmt.n_ff}}) {
                std::fill(candidate.begin(),candidate.end(),-12345.f);
                lab_gu_rows21(fmt,b.bytes.data(),input->data(),candidate.data(),range.first,range.second);
                equal(reference.data()+range.first,candidate.data()+range.first,(range.second-range.first)*sizeof(float),"row-range");
                for(int r=0;r<fmt.n_ff;++r)if((r<range.first || r>=range.second) && candidate[r]!=-12345.f)throw std::runtime_error("ROW_RANGE_OVERWRITE");
            }
            ++stages;
        }
    }
    std::printf("{\"state\":\"PASS\",\"integer_vectors\":100000,\"real_dot_pairs\":%zu,\"expert_stage_pairs\":%zu}\n",dots,stages);
}
struct Prepared {
    std::vector<ExpertJobMulti> jobs;
    std::vector<std::vector<std::vector<float>>> outputs;
    const NativeFmt* fmt=nullptr;
};
static std::vector<Prepared> prepare(const Data& data) {
    std::vector<Prepared> all;all.reserve(data.batches.size());
    for(const auto& batch:data.batches) {
        Prepared p;p.jobs.resize(batch.size());p.outputs.resize(batch.size());p.fmt=&data.blobs[batch[0].blob].fmt;
        for(size_t e=0;e<batch.size();++e) {
            const auto& input=batch[e];const auto& blob=data.blobs[input.blob];
            if(blob.fmt.d_type!=p.fmt->d_type)throw std::runtime_error("MIXED_DOWN_WITHIN_BATCH");
            p.outputs[e].resize(input.nt);auto& j=p.jobs[e];j.blob=blob.bytes.data();j.nt=input.nt;j.fmt=&blob.fmt;
            for(int t=0;t<input.nt;++t){p.outputs[e][t].resize(blob.fmt.n_embd);j.nact[t]=input.act[t].data();j.out[t]=p.outputs[e][t].data();}
        }
        all.push_back(std::move(p));
    }
    return all;
}
static void replay(ExpertPool& pool,std::vector<Prepared>& all) {
    for(auto& b:all)pool.run_split_multi_native(*b.fmt,b.jobs.data(),(int)b.jobs.size());
}
static void pool_parity(const Data& data) {
    auto old=prepare(data),changed=prepare(data);ExpertPool pool(15,true,true);
    std::fprintf(stderr,"LAB_GU_POOL %s\n",pool.placement_line().c_str());
    const auto affinity=pin_current_thread(planned_host_core());
    lab_gu_set_mode(false);replay(pool,old);const uint64_t before=lab_gu_hits();
    lab_gu_set_mode(true);replay(pool,changed);const uint64_t hits=lab_gu_hits()-before;size_t arrays=0;
    for(size_t b=0;b<old.size();++b)for(size_t e=0;e<old[b].outputs.size();++e)for(size_t t=0;t<old[b].outputs[e].size();++t) {
        const auto& x=old[b].outputs[e][t];const auto& y=changed[b].outputs[e][t];equal(x.data(),y.data(),x.size()*sizeof(float),"real-pool-output");++arrays;
    }
    if(!hits)throw std::runtime_error("CANDIDATE_NOT_EXECUTED");restore_thread_affinity(affinity);
    std::printf("{\"state\":\"PASS\",\"batches\":%zu,\"output_arrays\":%zu,\"candidate_row_calls\":%llu}\n",old.size(),arrays,(unsigned long long)hits);
}
static void bench(const Data& data,bool on,double warm,double seconds) {
    auto batches=prepare(data);ExpertPool pool(15,true,true);const auto affinity=pin_current_thread(planned_host_core());
    std::fprintf(stderr,"LAB_GU_POOL %s\n",pool.placement_line().c_str());
    lab_gu_set_mode(on);const auto t0=Clock::now();
    do{replay(pool,batches);}while(std::chrono::duration<double>(Clock::now()-t0).count()<warm);
    const double gu=pool.ms_multi_gu,q=pool.ms_multi_q,dn=pool.ms_multi_down;const uint64_t h=lab_gu_hits();
    std::vector<double> sweep_ns;auto started=Clock::now();const auto realtime=std::chrono::system_clock::now();size_t sweeps=0;
    do {const auto a=Clock::now();replay(pool,batches);sweep_ns.push_back(std::chrono::duration<double,std::nano>(Clock::now()-a).count());++sweeps;}
    while(std::chrono::duration<double>(Clock::now()-started).count()<seconds);
    const double elapsed=std::chrono::duration<double>(Clock::now()-started).count();uint64_t hash=1469598103934665603ULL;
    for(const auto& b:batches)for(const auto& e:b.outputs)for(const auto& t:e)hash=digest(t.data(),t.size()*sizeof(float),hash);
    const uint64_t calls=lab_gu_hits()-h;if(on && !calls)throw std::runtime_error("BENCH_CANDIDATE_NOT_EXECUTED");if(!on && calls)throw std::runtime_error("OFF_EXECUTED_CANDIDATE");
    std::sort(sweep_ns.begin(),sweep_ns.end());
    std::printf("{\"state\":\"COMPLETE\",\"mode\":\"%s\",\"workers\":%d,\"fixture_bytes\":%zu,\"sweeps\":%zu,\"seconds\":%.9f,\"start_epoch_s\":%.9f,\"ns_per_sweep\":%.9f,\"p95_sweep_ns\":%.9f,\"gu_ns_per_sweep\":%.9f,\"quant_ns_per_sweep\":%.9f,\"down_ns_per_sweep\":%.9f,\"candidate_row_calls\":%llu,\"output_hash\":%llu}\n",
        on?"on":"off",pool.workers(),data.bytes,sweeps,elapsed,std::chrono::duration<double>(realtime.time_since_epoch()).count(),elapsed*1e9/sweeps,
        sweep_ns[(size_t)(.95*(sweep_ns.size()-1))],(pool.ms_multi_gu-gu)*1e6/sweeps,(pool.ms_multi_q-q)*1e6/sweeps,(pool.ms_multi_down-dn)*1e6/sweeps,
        (unsigned long long)calls,(unsigned long long)hash);restore_thread_affinity(affinity);
}
static void row_bench(const Data& data,bool on,double warm,double seconds) {
    const auto affinity=pin_current_thread(1);const auto& b=data.blobs[data.batches[0][0].blob];
    const auto& act=data.batches[0][0].act[0];std::vector<float> ff(b.fmt.n_ff);const void* a[]={act.data()};float* out[]={ff.data()};
    lab_gu_set_mode(on);auto started=Clock::now();
    do{native_gu_rows(b.fmt,b.bytes.data(),a,1,out,0,(int)b.fmt.n_ff);}while(std::chrono::duration<double>(Clock::now()-started).count()<warm);
    started=Clock::now();size_t calls=0;
    do{native_gu_rows(b.fmt,b.bytes.data(),a,1,out,0,(int)b.fmt.n_ff);++calls;}while(std::chrono::duration<double>(Clock::now()-started).count()<seconds);
    const double elapsed=std::chrono::duration<double>(Clock::now()-started).count();
    std::printf("{\"state\":\"COMPLETE\",\"scope\":\"one-core-hot-GU-diagnostic-only\",\"mode\":\"%s\",\"calls\":%zu,\"ns_per_call\":%.9f,\"output_hash\":%llu}\n",on?"on":"off",calls,elapsed*1e9/calls,(unsigned long long)digest(ff.data(),ff.size()*sizeof(float)));
    restore_thread_affinity(affinity);
}
static void fallback_parity(const Data& data) {
    const auto& b=data.blobs[0];const auto& act=data.batches[0][0].act[0];
    NativeFmt other;std::string error;if(!native_fmt(17,42,b.fmt.n_embd,b.fmt.n_ff,other,error))throw std::runtime_error(error);
    std::vector<uint8_t> zero(other.bytes);size_t cases=0;
    for(int nt:{1,2,4,8}) {
        const auto& f=nt==1?other:b.fmt;const auto* blob=nt==1?zero.data():b.bytes.data();
        std::vector<std::vector<float>> old(nt,std::vector<float>(f.n_ff)),changed=old;const void* a[MAXT];float* o[MAXT];float* n[MAXT];
        for(int t=0;t<nt;++t){a[t]=act.data();o[t]=old[t].data();n[t]=changed[t].data();}
        lab_gu_set_mode(false);native_gu_rows(f,blob,a,nt,o,0,(int)f.n_ff);const uint64_t before=lab_gu_hits();
        lab_gu_set_mode(true);native_gu_rows(f,blob,a,nt,n,0,(int)f.n_ff);
        if(lab_gu_hits()!=before)throw std::runtime_error("UNSUPPORTED_PATH_EXECUTED_CANDIDATE");
        for(int t=0;t<nt;++t)equal(o[t],n[t],f.n_ff*sizeof(float),"fallback");++cases;
    }
    std::printf("{\"state\":\"PASS\",\"fallback_cases\":%zu}\n",cases);
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string(argv[1])=="caps") {
            const bool supported=lab_gu_vnni_supported();lab_gu_set_mode(true);
            if(lab_gu_vnni_enabled()!=supported)throw std::runtime_error("CAPABILITY_SELECTION_MISMATCH");
            std::printf("{\"supported\":%s,\"old_wide_gate\":%s,\"old_vex_vnni_gate\":%s}\n",supported?"true":"false",cpu_avx512_ok()?"true":"false",cpu_avxvnni_ok()?"true":"false");return 0;
        }
        if(argc<3)throw std::runtime_error("usage: lab_gu_probe parity|pool-parity|bench INDEX [off|on WARM SECONDS]");
        if(!lab_gu_vnni_supported())throw std::runtime_error("NOT_RUN_UNSUPPORTED_ISA");
        const Data data=dataset(argv[2]);const std::string mode=argv[1];
        if(mode=="parity")direct_parity(data);
        else if(mode=="pool-parity")pool_parity(data);
        else if(mode=="fallback-parity")fallback_parity(data);
        else if(mode=="row-bench" && argc==6)row_bench(data,std::string(argv[3])=="on",std::stod(argv[4]),std::stod(argv[5]));
        else if(mode=="bench" && argc==6) {if(data.bytes<256*1024*1024)throw std::runtime_error("WORKING_SET_NOT_DRAM_SIZED");bench(data,std::string(argv[3])=="on",std::stod(argv[4]),std::stod(argv[5]));}
        else throw std::runtime_error("INVALID_MODE_OR_ARGUMENTS");
        return 0;
    } catch(const std::exception& e){std::fprintf(stderr,"GU_PROBE_FAILURE: %s\n",e.what());return 2;}
}
