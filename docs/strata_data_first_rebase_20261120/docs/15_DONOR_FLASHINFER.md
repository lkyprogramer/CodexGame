# 15｜FlashInfer：借 shape 与证据体系，谨慎评估算子替换

## 1. 固定来源与研究边界

stable [v0.7.5](https://github.com/flashinfer-ai/flashinfer/releases/tag/v0.7.5) → `9aa920602276537b27e017a762a71e3437fc7f0d`；main `6fd1320260a8224b8a0d69c8cca8235aed65b3b2`。发布北京时间11/19 07:03:58。以下明确区分release已有API和main新增/搬迁路径；没有运行用户4090或FlashInfer benchmark。

FlashInfer是推理算子库，不是可以直接替换Strata serving/cache/CPU offload的完整引擎。主线是C++/CUDA，不能为了收shape把Python/PyTorch依赖塞进Strata热路径。

## 2. fi_trace：算子样本与完整时间线不同

stable [fi_trace.py](https://github.com/flashinfer-ai/flashinfer/blob/9aa920602276537b27e017a762a71e3437fc7f0d/flashinfer/fi_trace.py) 与 [template.py](https://github.com/flashinfer-ai/flashinfer/blob/9aa920602276537b27e017a762a71e3437fc7f0d/flashinfer/trace/template.py) 记录op定义、shape axes、dtype、const axis、参考实现。dump按const组合去重，stateful wrapper需要已绑定实例才拿得到plan状态。

优点是可移交、可复跑的operator workload description。限制是没有每次执行的频率、请求身份、CPU/GPU依赖和总成本。只拿一个shape的快样本，不能代表一次100K真实会话。

借鉴到本包：**WorkloadSignature + 次数/工作量census + 少量有界时序**。同family不同logical/physical rows、cache codec、context或verify width分开；profile解释可回链到请求，不另建全量tensor语料库。

## 3. autotune provenance，比“找个更快tile”更重要

[autotuning.rst](https://github.com/flashinfer-ai/flashinfer/blob/9aa920602276537b27e017a762a71e3437fc7f0d/docs/autotuning.rst)、[autotune_cache.py](https://github.com/flashinfer-ai/flashinfer/blob/9aa920602276537b27e017a762a71e3437fc7f0d/flashinfer/autotune_cache.py) 保存GPU/软件环境、runner/tactic、测量政策、胜者/次优、margin、候选数量。环境不匹配跳过旧缓存。只有一个候选时runner-up为空，不能伪造margin。

main HEAD [#9534回退提交](https://github.com/flashinfer-ai/flashinfer/commit/6fd1320260a8224b8a0d69c8cca8235aed65b3b2)撤回“超出最大已调优bucket直接用最大桶策略”。SGLang只在256-token尺度调优后，8K–16K prefill错误复用小tile导致退化；另一vLLM off-grid问题由key对齐修复。这里的启发不是加大搜索：

| 必须记录 | 防止哪种错误 |
|---|---|
| 实际shape与tuned bucket | 训练/调优覆盖不等于运行覆盖 |
| route/tactic和fallback reason | 环境变量“已设置”不等于实际走到 |
| winner/runner-up/candidate count/margin | 近似平局与单候选不伪装显著收益 |
| cold/warm/graph/measurement policy | 捕图、首次JIT和稳态不可混 |
| 独立E2E回执 | 微基准胜利不自动提任务速度 |

本轮不批准自动调参器。先给现有Strata dispatcher增加可审计签名与fallback原因。

## 4. 两个名字相近的 QSA API

| 路径 | 真正限制 | 对本用户 |
|---|---|---|
| stable `flashinfer/qsa.py::qsa_forward/qsa_indexed_forward` | cuDNN Frontend1.32+；BF16、D256等固定条件；SM100/103/107，indexed更窄 | 不是Ada实现，不立直接接入项 |
| main `flashinfer/sparse.py::qsa_sparse_paged_attention` | SM80–SM90默认核，含sm89；BF16 query、D256、GQA group1–16；KV BF16/FP8-e4m3/NVFP4；没有INT8KV | 架构上可能可用，但当前模型/布局/缓存必须实证匹配 |
| v0.7.5 GDN ReplaySSM tree | tcgen05、SM100/103、FP32状态池、4–8token | 不可把整个库的Ada支持当此功能支持 |

源：[stable QSA](https://github.com/flashinfer-ai/flashinfer/blob/9aa920602276537b27e017a762a71e3437fc7f0d/flashinfer/qsa.py)、[main sparse API](https://github.com/flashinfer-ai/flashinfer/blob/6fd1320260a8224b8a0d69c8cca8235aed65b3b2/flashinfer/sparse.py)、[CUDA实现](https://github.com/flashinfer-ai/flashinfer/blob/6fd1320260a8224b8a0d69c8cca8235aed65b3b2/include/flashinfer/attention/qsa_sparse_paged.cuh)、[测试](https://github.com/flashinfer-ai/flashinfer/blob/6fd1320260a8224b8a0d69c8cca8235aed65b3b2/tests/attention/test_qsa_sparse_paged_attention.py)。

main新header路径在固定v0.7.5中不存在；[API毕业/分发修复提交](https://github.com/flashinfer-ai/flashinfer/commit/1658f0bf02b65fe9a71862286f6da546d0fce890)明确处理实验源未进wheel导致JIT失败。不要从main文档生成stable wheel安装命令；旧experimental路径是否存在也是另一个事实，不能凭404断言整个旧功能不存在。

NVFP4路径在旧GPU上可以是软件解包后BF16/FP16 MMA，不是4090原生NVFP4 Tensor Core。输出BF16取整后再gate、page table、越界/负索引、scale语义也影响正确性，不能只比张量shape。

## 5. 对照当前Strata需要什么

只做兼容卡，不先移植：

1. 从实际GGUF/dispatch核定模型是否对应QSA；不能用通用“Flash-Next”名字推断。
2. 绑定KV codec/layout、head_dim、heads/GQA、page/index语义、稀疏召回算法、rope/gate/rounding、GPU与toolchain。
3. 核定当前QSA/attention在新基线中的暴露完成路径，旧F04结论未被新名字推翻。
4. 若是INT8KV等不兼容，直接NOT_APPLICABLE；不切KV格式来凑“速度对比”。
5. 若全匹配且确有独立差量，才另建数值oracle、snapshot/graph与低成本局部试验合同；不与本轮C01/C02同时开启。

## 6. API logging 的代价也应借鉴

[api_logging.py](https://github.com/flashinfer-ai/flashinfer/blob/9aa920602276537b27e017a762a71e3437fc7f0d/flashinfer/api_logging.py) level5统计可能触发 `.item()` 同步或图中的统计kernel；level10 dump/replay flush明确同步与CPU拷贝。[profiler](https://github.com/flashinfer-ai/flashinfer/blob/9aa920602276537b27e017a762a71e3437fc7f0d/flashinfer/profiler/__init__.py)导出buffer也有CPU materialization。

因此复用它的可复现格式与reference思想，不照搬在线全量dump。把L0/L1/L2拆开、明示采样和丢失、把profile-only结果与observer-off E2E分开，是比换一个库更可靠的第一步。

## 7. 最小可交付

P1完成shape契约、版本/硬件覆盖负例；P2给一个真实已走路径输出签名；P3给出它在实际任务中的次数/物理工作量/时间边界；不匹配的API形成明确N/A卡。无需下载新模型，也无需为了此项运行PyTorch服务器。

