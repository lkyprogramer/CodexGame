# 07 · 任务清单（唯一真源）

状态取值见 [AGENTS](../AGENTS.md)。“窗口”一列标 W 的任务需要停生产，通过 `lab_window.sh` 执行。命令见 [08](08_runbooks.md)。

| ID | 任务 | 依赖 | 窗口 | 交付 / 验收 | 状态 |
|---|---|---|---|---|---|
| T00 | 建 `$LAB` 目录；驱动基线 `driver_guard.sh snapshot`；preflight 清单 | — | 否 | `evidence/driver-baseline.txt` 及其 SHA256；`evidence/preflight.json` | PASS |
| T01 | 用户目录安装 Rust（rustup，toolchain 由仓库锁定） | T00 | 否 | `cargo --version`、`rustc --version`；驱动 check 通过 | PASS |
| T02 | 用户目录 conda 安装 CUDA 12.8.1 编译工具（先 dry-run 并 scan） | T00 | 否 | `nvcc --version` 为 12.8；dry-run 包列表 scan 通过；驱动 check 通过 | PASS |
| T03 | venv + modelscope；用 ModelScope 下载 A1–A4（A5/A6 可选）；改名；SHA256 校验；生成 lock | T00 | 否 | `models/models.lock.json`；SHA256 与 [01](01_model.md) §4 全部一致 | PASS |
| T04 | clone Astral 到 49a0a2b，建分支 `inkling-4090`；CPU 侧 `cargo test` | T01 | 否 | 测试输出原文；失败项逐条记录原因 | FAIL |
| T05 | GPU 构建 `ASTRAL_CUDA_ARCHS=89`；用 `cuobjdump` 列出各 fatbin 的 SASS 目标 | T02、T04 | 否 | `astral version` 显示 `["89"]` 和 nvcc 12.8；所有 fatbin 都含 sm_89 | PASS |
| T06 | 构建 llama.cpp b12751（`CMAKE_CUDA_ARCHITECTURES=89`，使用 CUDA 12.8） | T02 | 否 | `llama-cli --version` 显示 commit `532d674` | PASS |
| T07 | W1：`astral hw`、`astral selftest` | T05 | W | 原始输出；selftest 全部 PASS（V0） | PASS |
| T08 | W1：`astral gguf-info A1 --tensors`；`golden_llamacpp.sh A1` | T03、T05、T06 | W | V1；llama.cpp 侧的困惑度、KLD base、eval-callback 日志 | PASS |
| T09 | W1：`verify-embd`、`verify-model` 对 T08 的日志 | T08 | W | V3 PASS | PASS |
| T10 | W1：分词对照；`astral generate` 与 llama.cpp 的前 32 / 128 token | T09 | W | V2；G1 | PASS |
| T11 | WP-A：`ArchProfile::Sm89` 及测试（CPU 侧可完成，W 中复核）；修 T04 的 `mxfp4_block` 测试期望值；定位 T07 的 4 个 MXFP4 selftest 失败（只影响 Qwen 路径，限时 2 h，查不清就记为已知问题并向上游报告） | T07 | 否 | commit；`cargo test` 通过；`astral hw` 输出 `sm89`；MXFP4 失败的根因或已知问题记录 | PASS |
| T12 | W2：噪声底 N0 → Astral KLD / top-1 → V5–V7 | T10 | W | G2 判定表及原始数据 | FAIL |
| T13 | W2：DSpark（A3）`spec-generate` 等价性；接受长度 | T12 | W | V8；接受长度分布 | PASS |
| T14 | W：性能基线，Astral 对 llama.cpp（无草稿 / 带草稿） | T12 | W | [05](05_validation.md) §4 报告；记录 G3 当前差距 | NOT_RUN |
| T15 | WP-B：`ASTRAL_TRACE` 观测 | T12 | 开发否，验证 W | 关闭时逐位一致；JSONL schema 写入 fork 的文档 | NOT_RUN |
| T16 | WP-C：4090 调优循环 | T14 | W | 每轮的 profile 和前后对比；G3 | NOT_RUN |
| T17 | WP-D：长上下文 | T12 | W | G4；16K/32K 对 llama.cpp 的 KLD | NOT_RUN |
| T18 | WP-E：遍数可配置；加载 varloop（A4） | T12、T03 | W | 3 遍时逐位一致；varloop 在 1–6 遍下的运行记录 | NOT_RUN |
| R1–R7 | [06](06_loop_research.md) 的研究 | T15、T18（R4 还依赖 T17 的 KV 布局） | W | 每项交付数据与结论 | NOT_RUN |
| O1 | 可选：tqllm Docker 精确模式对照（需要用户同意） | T12 | W | 4090 上 tqllm 的 tok/s 与 KLD | DEFERRED |
| O2 | 可选：生产 Strata 新版 + SQ-20 在业务集上与 Qwen3.8 对比 | — | W | 由用户另行决定 | DEFERRED |

## 关键路径

T00 → (T01, T02, T03 并行) → T04 → T05 → **W1**（T07–T10）→ T11 → **W2**（T12–T13）→ T14 → T15 / T16 / T17 / T18 → R1–R7。

P0（T00–T06）不需要停服，可以立即开始。第一次停服是 W1（约 60 分钟），需要先与用户确认时间。

## 执行记录

| 任务 | 时间（UTC，2026-11-26） | 结果 |
|---|---|---|
| **T00** | 02:43 | 基线 `driver-baseline.txt` 的 SHA256 为 `d1bdd9b7…`；驱动 610.57.04，kernel 6.1.0-17-amd64；preflight rc=0 |
| — | 02:43 | 按用户指示**彻底停掉 Strata**（inactive，显存 1 MiB），用户说恢复之前保持停止；停服期间 GPU 任务不再需要 `lab_window.sh` |
| **T01** | 03:15 | rustc / cargo 1.100.0；驱动比对一致 |
| **T02** | 03:44 | 第一次走官方 conda-forge 太慢，中止后改用清华镜像，40 s 装完（包集合与第一次的 dry-run 相同）；之后补装 `cuda-driver-dev`、`cuda-nvml-dev`；nvcc 12.8.93；三次 scan 都无命中；驱动比对一致 |
| **T03** | 02:44–03:32 | A1–A6 全部下载，逐文件 SHA256 校验通过，写入 `models.lock.json`；大文件约 25 MiB/s |
| **T04** | 03:45 | 15 个测试集通过；**`astral-quant` 的 `tests::mxfp4_block` 失败**：`e8m0_scale_half(0)` 返回 2^-128 = 2.938736e-39，这是正确的次正规数，而期望值 `2f32.powi(-128)` 在 Rust 1.100 下算成了 0.0。这是测试写法的问题，不是 kernel 缺陷；MXFP4 只用于 Qwen，不影响 Inkling。修复（期望值改成 `f32::from_bits(1 << 21)`）归入 T11 |
| **T05** | 03:46 | 7 个 fatbin 全部只含 `sm_89` cubin；`astral version` 输出 `["89"]`，nvcc 12.8.93 |
| **T06** | 03:57 | llama.cpp 532d674，编译用 9 分 21 秒；`libcuda.so.1` 解析到系统驱动库，cublas / cudart 来自用户目录的 12.8 |
| **T07–T10** | 06:08–06:16 | Strata 停止期间直接执行，未经 `lab_window.sh`；脚本在 `tools/w1/`，结果在 `$LAB/runs/w1/20261126T060811Z/`；前后驱动比对一致 |
| **T07** | 06:08 | `astral hw` 正常（cc 8.9、128 SM、L2 72 MiB、`profile: null`，后者留给 T11）。**selftest 76/80**，连跑 3 次失败的都是同样 4 项，全部是 MXFP4：`gemv_mxfp4_f32 n5120 k17408 b4`、`gemm_mxfp4_mma_{f32,f16x} n5120 k17408 b8`、`gemm_mxfp4_mma_f32 n48 k4160 b8`，误差 0.09–0.16，容差 4e-6。前三项的误差在不同运行间略有变化。split-K 的划分只取决于 SM 数，不像是 4090 特有的原因，根因未查明。A1 不含 MXFP4 张量（见 T08），Inkling 用到的 NVFP4、Q8_0、BF16、F32 kernel 全部 PASS。按冻结阈值，V0 判 FAIL |
| **T08** | 06:08–06:12 | V1：NVFP4 ×40（11.466 GB）、Q8_0 ×154（6.000 GB）、F32 ×518、BF16 ×32，对齐填充为 0，与 A100 记录一致。llama.cpp 侧 PPL 3.2351 ± 0.0528（llama.cpp 文档语料，c2048 × 16）；KLD base `kld_base_c512x8.bin` 816 MB；eval-callback 日志 11227 行 |
| **T09** | 06:12 | V3 PASS：`verify-embd` 的 sum 差 5.4e-5；`verify-model` 覆盖 48 个 slot，全部 ok，`l_out` 的最大 max\|d\| 为 0.428（l_out-41），`result_output` 为 6.0e-2 |
| **T10** | 06:13–06:16 | V2 PASS：bench 的 `prompts_set_a` 16 个 prompt 经 chat 模板后，Astral `/tokenize` 与 llama-server `/apply-template` + `/tokenize` 的 token id 完全相同；另有 10 条原始文本（中日韩、emoji、代码、特殊 token），`llama-tokenize` 与 HF `tokenizer.json` 也全部一致。V5 PASS：贪心 128 token 中前 65 个相同；第 65 位 llama.cpp 的 top-2 是 " In"（-1.039）和 "\n"（-1.160），margin 0.121 < 0.5，Astral 选了 "\n"。参考：Astral decode 143.6 tok/s，llama-server 66.7 tok/s（单次运行、未开 `-fa`，不作为 G3 数据） |
| **T11** | 06:29–06:39 | fork 分支 `inkling-4090` 上的本地提交（未推送）：`c240d53` 新增 `ArchProfile::Sm89`（F80 族，FP8 张量核，无 FP4，验证级别 Logic），并修正 `mxfp4_block` 的期望值（`2f32.powi(-128)` 只在 debug 构建下得 0，release 构建正常；修正前已在 debug 下复现失败）；`d17a519` 修复 T07 的 MXFP4 失败。**根因**：`DeviceBuffer::zeroed` 的 `cuMemsetD8`、`copy_from_slice` / `VmmRegion::write` 从分页内存发起的 `cuMemcpyHtoD` 都排在 legacy 默认 stream 上，函数返回时可能还没执行完；而 Astral 的 stream 都是 `CU_STREAM_NON_BLOCKING`，与它们没有先后关系，紧接着启动的 kernel 可能读到未传完的输入，或者写好的输出又被清零覆盖。诊断依据：失败的输出整行为 0、每次个数不同；换成 sm_80 SASS 编译、在前面垫 1 GiB 分配，现象都不变。修复方法是这两处返回前同步 legacy stream。修复后 selftest 连续 3 次 80/80；Inkling 的 `verify-model` 输出和 128 token 贪心序列逐字节相同；decode 144.0 tok/s；权重加载从约 13 s 变为 12–18 s。`cargo test`、`fmt` 通过；clippy 只有上游原有的 warning。T07 据此改判 PASS |
| **T12** | 06:41–07:04 | `d3b402e` 新增 `astral dump-logits`（按 llama.cpp KLD base 的格式逐 token 导出 log-prob）和 `cmp-prefill` 的诊断输出；分析脚本在 `tools/w2/`。`kld.py` 算出的 N0 与 llama.cpp 内置统计一致（平均 0.002013 对 0.002014，p99 0.02842 对 0.02843），用来校验脚本本身。**V4 PASS**：N0（llama.cpp ub512 对 ub1）平均 0.00201、p99 0.0284；Astral（decode 路径）对 llama.cpp 平均 **0.00180** ≤ 0.005，p99 **0.0228** ≤ 0.0568；参考 margin ≥ 0.5 的 1754 个位置上 top-1 一致率 **99.94%**（唯一分歧点 margin 0.843）；两边 PPL 3.5352 / 3.5359。**V5 PASS**：16 个 prompt 的第一个分歧点都是近似平局（参考 margin < 0.5）。**V6 PASS**：16 × 500 个位置共 94 处不一致，margin 最大 0.584。参考序列用了 `ignore_eos`，有 2 个位置被强制改了 token，比对时改用参考的原始 top-1。**V7 FAIL（按冻结阈值）**：16 个 prompt 的 argmax 全部相同，但全词表最大差有 8 个超过 1.0（最大 3.6，都落在概率可以忽略的尾部 token），概率窗口内（距 top 16 以内）只有 1 个超过 1.0（1.18）；KL(step‖prefill) 最大 0.0147。对照：llama.cpp 自己 ub512 对 ub1 时，概率窗口内最大差 > 1.0 的位置占 19.4%，p99 为 3.15；Astral 对 llama.cpp 是 18.0%。所以 V7 的 1.0 阈值比参考实现自身的噪声还严，是否修订由用户决定 |
| **T13** | 07:05–07:12 | **V8 PASS**：16 个 prompt 用 `spec-generate`（DSpark，k = 6，512 token），teacher-forced 检查中投机 token 与普通贪心不同的位置每个 prompt 0–15 个，最大 logit 差 0.605 ≤ 1.0。接受情况：每轮 1.84–3.93 个 token，草稿接受率 14–49%；投机解码平均 183 tok/s，普通贪心 143 tok/s，提速 1.28 倍（单个 prompt 1.0–1.87 倍）。注意：这些 prompt 沿用 V2 的模板输出，末尾没有 `<\|message_model\|>` 生成提示，模型并不是在助手回合里作答，接受率可能偏低。T14 必须带上生成提示 |
