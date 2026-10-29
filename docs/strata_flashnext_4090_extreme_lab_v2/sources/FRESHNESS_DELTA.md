# 最终版本增量复核：41cf05a → 4b9e05a / v0.2.6

核查日期：2026-10-25 UTC。PR #3871 的最后 API 核查时间为 13:55:59 UTC；release 查询紧随其后。本文是已审快照与最终执行基点之间的补充，不替换既有源码引用。

## 1. 最终采用的版本身份

| 身份 | 固定值 | 使用方式 |
|---|---|---|
| 用户生产对照 | v0.2.3 `5c8dd322528cc84f68f461ad54a506b9da8fa8d4` + 用户 EXACT6 | 每个候选的生产 oracle；不覆盖 |
| 本轮详细源码审计快照 | `41cf05a06a25dd29103b7b27a2279a3f60c21876` | 保留 audit / P01 / P05 / P06 / P07 中的固定源码链接 |
| 最终新实施基点 | `4b9e05a2a806a3fe24f7b2560d98626c37dade35` | 新隔离 checkout / worktree 的候选 base；先对生产独立基线验证 |
| 最新 app / Terminal release | v0.2.6，2026-10-25T13:45:25Z 发布 | 安装器 / 界面 / Terminal 的产品版本 |
| Control / DeepSeek engine | 0.1.51 | 不等于 Qwen CUDA kernel 更新 |
| Qwen engine packages | 仍为 0.1.50 | release 公告说明和 v0.2.5 为相同文件 |

直接来源：[v0.2.6 release](https://github.com/Niko1221/Strata/releases/tag/v0.2.6)、[release API](https://api.github.com/repos/Niko1221/Strata/releases/latest)、[新 CMake project version](https://github.com/Niko1221/Strata/blob/4b9e05a2a806a3fe24f7b2560d98626c37dade35/CMakeLists.txt#L11)、[新 Terminal 版本](https://github.com/Niko1221/Strata/blob/4b9e05a2a806a3fe24f7b2560d98626c37dade35/strata_cli/__init__.py#L11)。release 关于 Qwen 包相同的说法是官方发布声明；本次没有重新下载两版全部二进制并逐文件比较，所以不把源码相同写成已经验证所有 binary hash 相同。

## 2. 本地完整 tree diff 的结论

使用本地 `git diff <old> <new>`，而不是可能被 GitHub changed-files 上限截断的 compare response。结果为 **55 files changed，422 insertions，133 deletions**。核心目录不是“看起来没改”，而是 Git tree object ID 完全相同。

| 路径 | 旧/新共同 Git object ID | 结论 |
|---|---|---|
| `src/core` | `821f57a9bf4f7faa11d02c9856ea35cf926b9b43` | verify、MTP、head、session等实现逐文件相同 |
| `include/strata/core` | `62bc5eb16ac39d5edb03d90dbc50400682c0c5e1` | 核心接口相同 |
| `src/kernels/cpu` | `bcfbc217a1044b401eba38d0de43b660e5be2d02` | pool、ISA、IQ/Q2/quant、CPU micro相同 |
| `src/kernels/cuda` | `5275f0aa0816129ca5c01fab59102e7f2c82db9a` | CUDA kernel与分派相同 |
| `include/strata/kernels` | `bcb6c26bd1ae4cd90178b0247b72969f3bf39655` | kernel接口相同 |
| `src/prefill` | `f28e93824a899050e50cb8e85bc6f7645ee4cfbe` | scratch、MMQ、GDN_CHUNKED和prefill owner相同 |
| `include/strata/prefill` | `16a00fb1ce336a496340d24388df4b98848de0fe` | prefill接口相同 |
| `src/kernels/cpu/kq_cpu_bench.cpp` | `0655bc0ea525874030bd36261194f779e5547424` | PR3871的benchmark修复仍未进入此树 |

完整机器可读核查另存 `freshness_blob_identity.json`。目录的 Git tree hash 相同意味着目录下对象与路径相同；不意味着不同 compiler / flags 构建出的二进制性能必相同。

本地仓库存在 shallow history 边界，直接 `git log old..new` 会列出过多历史，故未用它认定增量提交数。此限制不影响指定两个提交对象的 tree-to-tree 差分及 object ID 核验。

## 3. 对本任务有影响的实际差异

### 3.1 Qwen C++：仅 spec-split 注释纠正

`src/program/generate.cpp` 只有一行注释变化：`Options::spec_split` 不再描述为 exact，明确因窗口 batch shape 不同而不与 no-split 逐 bit 一致。没有相应执行代码变化。

对实验的要求是：**不要将 `--spec-split` 放入无条件 E 档优化。**如果某个候选改变 verify 的 group / nt / split shape，必须面对实际舍入和接受结果的差异，不能用“每个kernel都没改”推出端到端相同。现有 P01 保持原 expert group / nt 的合同继续有效；P07 对数值路径重新分类的要求也继续有效。

新源码：[generate.cpp L709](https://github.com/Niko1221/Strata/blob/4b9e05a2a806a3fe24f7b2560d98626c37dade35/src/program/generate.cpp#L709)。注释中的历史慢幅不是本机新测量，本报告不将它当作4090预测。

### 3.2 CMake：版本号变化，target定义未变

`CMakeLists.txt` 从 `project(strata VERSION 0.1.50 ...)` 改为 `0.1.51`，其他内容没有变化。因此前述计划引用的已有 target、条件构建、CTest 名、默认 CUDA arch 与每 TU 编译 flags 继续成立。也不能看到新 CMake version 就说 Qwen engine package 已升为0.1.51。

### 3.3 Serve：空 messages 和单 token 速率

`serve/frontend.py` 新增 `require_messages`，OpenAI chat 路由在模板转换后调用，空消息请求返回400。测试fixture和warmup请求必须包含至少一条合法消息，不能用空 messages 的失败响应作为低延迟“成功”。

`serve/server.py` 的 Monitor统计和 `answer_speed` 不再从 engine `generated=1` / 极短 `decode_ms` 给出虚高tok/s；新增测试覆盖这一情况。这个改动是测量口径修复，**不是解码变快或变慢**。比较不同Control版本时，统一以原始生成token数、明确定义的TTFT / first-to-last span / 完整wall计时；1-token请求可测试TTFT，不能代表稳态decode速率。原始fallback路径仍应按其真实代码解释，不凭release摘要声称所有单token场景一律返回同值。

新源码：[frontend.py L542](https://github.com/Niko1221/Strata/blob/4b9e05a2a806a3fe24f7b2560d98626c37dade35/serve/frontend.py#L542)、[server.py L5516](https://github.com/Niko1221/Strata/blob/4b9e05a2a806a3fe24f7b2560d98626c37dade35/serve/server.py#L5516)、[server.py L5650](https://github.com/Niko1221/Strata/blob/4b9e05a2a806a3fe24f7b2560d98626c37dade35/serve/server.py#L5650)、[server.py L7136](https://github.com/Niko1221/Strata/blob/4b9e05a2a806a3fe24f7b2560d98626c37dade35/serve/server.py#L7136)。

### 3.4 DeepSeek专用性能变化不属于FlashNext现成功能

`src/dsv41/ds4_model.cu` 与 `ds4_experts_rule.hpp` 增加CPU-side experts全量copy-in的条件与Windowscommit-room限制。release给出的R9700/251GB RAM提速属于DeepSeek和该硬件条件。**不能把它写成64GB、4216、FlashNext已自动获得的新驻留优化。**FlashNext的expert source / pool在本次delta没有改动。

直接源码：[ds4_experts_rule.hpp](https://github.com/Niko1221/Strata/blob/4b9e05a2a806a3fe24f7b2560d98626c37dade35/src/dsv41/ds4_experts_rule.hpp)、[ds4_model.cu](https://github.com/Niko1221/Strata/blob/4b9e05a2a806a3fe24f7b2560d98626c37dade35/src/dsv41/ds4_model.cu)。其余主要差异是Windows卸载、监控UI、AMD/WSL提示、setup local-feed与版本文档，不改变本任务的Linux/CUDA低层优化顺序。

## 4. PR3871的实时状态

GitHub API在2026-10-25 13:55:59 UTC返回：

```json
{
  "state": "open",
  "merged": false,
  "merged_at": null,
  "head_sha": "b5dadce98478d2451f246afa240724b3011d54a2",
  "base_sha": "41cf05a06a25dd29103b7b27a2279a3f60c21876",
  "updated_at": "2026-10-25T11:58:37Z"
}
```

来源：[PR3871](https://github.com/Niko1221/Strata/pull/3871)、[API](https://api.github.com/repos/Niko1221/Strata/pulls/3871)，状态快照保存为 `pr3871_fresh_status.json`。API的open/unmerged与新树的benchmark blob identical互相支持：**升级到新head不会自动修复P06-02所述基准问题。**实施者仍需单独审查/适配该benchmark-only补丁；它不构成引擎加速。

## 5. 哪些文档需要改，哪些保留

| 文档 | 处理 |
|---|---|
| 版本总表、实验manifest、执行README | 新执行base写4b9e05a；app/Terminal0.2.6、Control0.1.51、Qwenengine0.1.50分开 |
| kernel audit、P01 CPU pool、P05 prefill | 核心源码结论保留；附本delta，固定41cf链接保留 |
| P06 CPU ISA | PR3871仍open；新增无VBMI TU、真实dtype与pack合同不变 |
| P07 GPU kernels | 保留核心代码引用；首段注明新执行base与blob identity |
| spec-split相关实验 | 明确非bitwise；新分组/shape不能自动列E |
| 测试生成器 / 报表 | 非空合法messages；1-token不作为decode tps胜负证据 |
| DeepSeek donor / release摘要 | 标为家族与硬件限定，不能变成FlashNext既有功能 |

没有为了追版本更换上游工作树、修改引擎或运行GPU编译。最终核查只执行只读diff / object身份读取和文档静态验证；新基点的实际运行、数值和性能仍须由执行计划在目标机器完成。
