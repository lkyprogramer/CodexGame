# W4A16权重与Marlin接入

## 源合同

选择dbirks版本：group_size128、symmetric、num_bits4、actorder=null、compressed-tensors pack-quantized，activations为BF16；小的GDN控制投影、lm_head、MTP、vision保留BF16。[S05]

`weight_packed`、`weight_scale`等**真实tensor名和shape从下载文件读取**；不要把HF统计的packed元素数误当模型参数量，也不要凭模型名字推定packing。

## 不重写一个错误的“通用int4 decoder”

优先在oracle实际加载后捕获它交给Marlin的packed buffer、scale排列、group index/zero约定、padding与workspaces。把这组结果输出为新safetensors，保留原model目录只读。运行期Kern不能依赖Python/PyTorch执行MatMul；导出和oracle阶段可以使用它们。

每层同一输入分别比较：原compressed-tensors在oracle的线性输出、导出packed内容回到oracle的输出、新SM89入口输出。只有三者闭环才接进整个模型。

## 三组测试不能省

1. 编码边界：int4所有16个码值、scale=0/小值/大值；零点/符号/两个nibble顺序；group边界127/128/129；非整tile尾部。
2. 实际几何：M=1/2/7/8/16/128/256/512；K/N取本模型真实投影，特别是5120→96控制投影不要错当quantized GEMM。
3. 重排幂等与完整性：repack不能重复应用；每个输出buffer带codec+producer版本+输入SHA，加载不匹配就拒绝。

## host launcher不是cubin

Marlin的Python包装可能执行repack、选择kernel、分配workspace、维护locks和动态shared memory。抓到一个launch不等于完整算子。为每个M形状冻结完整host准备语义，再用flat CUDA ABI入口或schema-v4 Op内部多launch表达。不要把需要PyTorch Tensor对象的C++ extension函数伪装为runtime extern。

raw-input→packed准备应在load阶段完成。热decode禁止把完整4bit矩阵解压为BF16再调用cuBLAS；这既浪费带宽也破坏24GB预算。若调试临时单层解压，输出必须标为DIAGNOSTIC，不能进入性能成绩。

## GDN/MLP拼接

QKV+gate、GDN qkvz、ba、gate_up的拼接次序必须来自oracle与源config。拼接shape吻合不代表语义正确。每个融合buffer输出index map，至少测试一个单hot通道，排除q/gate或a/b交换。
