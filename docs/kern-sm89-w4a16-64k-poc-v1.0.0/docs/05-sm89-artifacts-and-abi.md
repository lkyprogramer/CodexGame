# SM89制品、ABI与设备能力

## 一个必须先修的上游细节

`tools/handwritten.py` 在`target/cubins`缓存手写核；带defines的变体用名字/时间戳决定是否重新编译，arch来自`KERN_SM`但不进入文件名身份。[S08]

新实现必须使用：

`artifact_key = SHA256(source_closure + compiler_version + compiler_binary_sha + flags + defines + arch + ABI + shape_contract)`。

目录为`target/cubins/sm89/<toolchain-key>/<artifact-key>/`。不能以mtime判断正确，也不能仅用文件名里写sm89作为兼容证据。切arch、编译器、flags、header任一个都必须cache miss。

## 明确禁用的特性

4090 CC8.9的P0禁止引用：sm100/sm103/sm120 cubin、PDL、thread-block cluster、TMA tensor map、WGMMA/TCGEN05及Blackwell FP4专用核。关闭manifest的PDL标志不等于二进制不含其指令。需要SASS核查与实际module加载。[S09]

Ada每block shared-memory opt-in上限99KiB，静态默认48KiB；上游verifier允许更大shared memory不意味着Ada支持。加载后查询实际`cudaFuncGetAttributes`与device属性，检查静态+动态总量，不能只看manifest动态字段。[S09]

## 最小探针

在固定工具链容器内、授权维护窗口：

```bash
nvcc -O3 -arch=sm_89 scripts/gpu_probe.cu -o work/gpu_probe
./work/gpu_probe > results/gpu-probe.json
```

此探针验证一个小kernel能运行与CC8.9，不验证Marlin、GDN或64K。

## ABI登记

每个module保存：入口mangled名、源码commit/license、cubinSHA、SM、编译flags、shape/constexpr、参数size/offset/方向、strides、shared-memory、grid、引用权重codec。

Triton会删除等于1的参数并固化divisibility，不能凭函数名推断真实ABI。用实际捕获实例、编译IR/metadata与`cuFuncGetParamInfo`交叉核对。两个实例参数布局相同，也可能因constexpr不同而计算不同。[S02]

`poc_tools.cli lint`只是附加的保守SM89静态检查；还必须运行Kern verifier、实际ABI校验和compute-sanitizer。声明自洽不证明cubin数学正确或内存安全。
