// Trusted 24 MiB calibration for the experimental CUDA allocation tracer.
#include <cuda_runtime_api.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unistd.h>
int main() {
    void *allocated=nullptr, *registered=nullptr;
    if (posix_memalign(&registered,4096,16u<<20)!=0) return 2;
    std::memset(registered,0,16u<<20);
    auto a=cudaHostAlloc(&allocated,8u<<20,cudaHostAllocPortable|cudaHostAllocMapped);
    auto b=cudaHostRegister(registered,16u<<20,cudaHostRegisterPortable);
    std::printf("pid=%d alloc=%d register=%d\n",getpid(),a,b);
    if (a!=cudaSuccess || b!=cudaSuccess) return 3;
    FILE* status=std::fopen("/proc/self/status","r"); char line[512];
    while (std::fgets(line,sizeof(line),status))
        if (std::strncmp(line,"VmLck:",6)==0 || std::strncmp(line,"VmPin:",6)==0 || std::strncmp(line,"VmRSS:",6)==0) std::printf("%s",line);
    std::fclose(status);
    const auto c=cudaHostUnregister(registered),d=cudaFreeHost(allocated);
    std::free(registered);
    return c==cudaSuccess && d==cudaSuccess ? 0 : 4;
}
