// Run only in the declared GPU maintenance window. This is not a throughput benchmark.
#include <cuda_runtime.h>
#include <cstdio>
#define OK(x) do { cudaError_t e=(x); if(e!=cudaSuccess){fprintf(stderr,"%s\n",cudaGetErrorString(e));return 2;} }while(0)
__global__ void probe(int *p) { *p=89; }
int main(){cudaDeviceProp p{};OK(cudaGetDeviceProperties(&p,0));int driver=0,run=0;OK(cudaDriverGetVersion(&driver));OK(cudaRuntimeGetVersion(&run));
int *d=nullptr,h=0;OK(cudaMalloc(&d,sizeof(int)));probe<<<1,1>>>(d);OK(cudaGetLastError());OK(cudaDeviceSynchronize());OK(cudaMemcpy(&h,d,sizeof(int),cudaMemcpyDeviceToHost));OK(cudaFree(d));
printf("{\"name\":\"%s\",\"cc\":\"%d.%d\",\"driver_api\":%d,\"runtime_api\":%d,\"global_bytes\":%zu,\"shared_optin_bytes\":%zu,\"probe\":%d}\n",p.name,p.major,p.minor,driver,run,p.totalGlobalMem,p.sharedMemPerBlockOptin,h);
return (p.major==8&&p.minor==9&&h==89)?0:3;}
