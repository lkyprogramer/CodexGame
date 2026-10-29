# 当前生产组合的 KVRES 对照（2026-10-27）

状态：实验完成。八个定长性能场景均未达到预登记的 4% 改善门；两臂均观测到所列长会话的真实恢复回执，但精确检索失败。原正式回放的 FAILURE 完整保留，编码链关闭组 2/2 完成、开启组 1/2 完成。本轮正式采用门未通过，质量非劣未建立。用户授权在 29 实验环境比较完整配置与仅关闭 KVRES；不修改生产配置，结束保持生产停机。

## 冻结对象

- Python 服务源码：`f615cc8d11c7f705a7c29b2884af415886c21f9c`（A0 + #1536 + CFG-PT）。两臂使用同一隔离 worktree。
- 引擎 SHA256：`819ff262a1742e8b57eedc6203b015f7c9831dd4a94ecacbb5a8b1c865fade3d`，与生产及 A0 实验二进制相同。相对 A0 的 native 源码、include、CMake 无差异，因此复用构建，不伪称重新编译。
- 公共配置：EXACT6、overlap、spec4、int8 KV、131072 总上下文、6144 MiB 会话缓存、#1536=1、PT=0、CPUSHARE=4096、AUTOMAX=16384。
- `base`：上述完整组合，`--kv-resident 0`；`cfg`：上述完整组合，`--kv-resident 20480`。这是唯一行为变量。
- 实验目录：29 `/home/hhtele/strata-lab-4090/workspace/combination/kvres-20261027`；端口 18089。
- 实验配置从当前生产配置生成去密钥副本；cwd/exe/log 指向实验树，专家 profile 使用实验副本，去除 profile-save。原 `config/local.json` 不修改。

## 预登记工作负载

1. 固定回放 6 个配对轮，AB/BA 各 3 轮，每臂 fresh engine，不按结果增减轮数。31 个请求/臂/轮，共 372 个计划请求。
2. 四档 Java 源码输入约 4K / 32K / 64K / 100K；Pi 采样 1.0 / 0.95 / 20，xhigh，2048 定长输出。thinking 与限制 thinking 为 128 的回答诊断分别记录。后者是测量支路，不是生产参数变更。
3. 固定多轮历史：32K 起，追加约 3.2K / 10K / 3.2K / 10K，带先前 reasoning_content，验证 PT=0 的实际读入与复用。
4. 约 68K、100K 的 A→B→A；必须观测本次请求实际恢复不少于 64000 token，返回后精确检索和采样检索均有固定答案。
5. 五个工具 schema 与五个协议题，完整保留失败，不执行工具中任何实际外部操作。
6. 另做 2 对 8 轮真实生成历史的 Python ledger 编码链，seed 42/43、xhigh、最大输出 32768（按精确上下文预算收缩），每链预算 2400 秒。评分仅使用已安装且固定 ID 的 Python Docker 镜像，无网络、只读、非 root、限制资源。它是任务完成筛查，不代表真实 Java 仓库或正式 2pp 非劣。

固定 corpus seed：20261027；初始 corpus SHA256：`c6fadd3f189a8ce58fe49f809e89ec6e184a9013626a5072af4365f8d0a5a8c0`。全文、gold、计数、seed、请求哈希均保存。若先行机制冒烟发现夹具或适配问题，保留失败目录，记录修订原因及新 hash，正式轮开始后不更换题集。

## 指标与停止条件

- 固定输出主指标为 `decode_ms`，同时报告请求 wall、TTFT；以整轮配对、按场景和上下文分层，不把请求数当独立轮数。
- 描述性收益与正式采用门分别报告；正式改善门按既有 A/A 噪声约 2% 冻结为 4%，即时间比 CI 上界 ≤0.96。未达到不写“正式过门”。冷读代价单列，不用 decode 收益遮盖。
- 动态链报告逐轮正确性、完整链完成率、推理和评分耗时；失败链 restricted time 记 2400 秒。有效任务失败仍运行另一臂，基础设施失败中止并保留原始证据。
- 85°C 或 MemAvailable <4096 MiB、GPU 归属变化、CUDA/OOM、token 预算/usage 漂移立即停止。不降低保护阈值。
- 每臂及指定大冷读前等待 GPU ≤55°C，最多 600 秒；等待时间与请求 wall 分开记录。此负载不等价于全天热稳定性验证。
- 恢复回执缺失或固定长检索错误立即停并保留现场。质量与定长输出失败不删除，也不以挑选重跑替代。
- 实际生产服务状态及 13 个保护文件 hash 在前后及每臂检查；只停止本轮创建的实验进程。

## 验证入口

新增 `tools/combination/build_corpus.py`、`run_combo.py`、`run_chain.py`。现有 `cfg --tree` 不能用于本次组合，因为它只替换 cfg 臂源码，base 仍是 A0；本次专用入口明确让两臂使用同一生产补丁树。

已完成结果、原始产物索引、执行命令与最终状态见下节。

## 初始失败与执行修订（在补充运行前记录）

- 初始目录 `replay/`：round 0 / base 的前 13 请求完成，第 14 个 `park-prime-69632` 错答后按原计划中止，保留 `FAILURE.json`。其余配对未运行，不能算 6 轮完成。
- 真值核查：请求原文只有一条 `id=R000738`，`immutable_value=6763216-000738`；模型回答 `1751936`。请求 SHA256 `37e2e41e5c90680245163f34bcf0977eff944add267f1ad4f84f1baed41b725e`。
- 最小复现 `repro/`：同一请求全文、相同 oracle，2 对 fresh-engine，允许模型质量失败继续另一臂，基础设施守卫保持不变。两对共 4 次请求全部返回相同错误 `1751936`，base/cfg 各 2/2 失败；目录完整收尾，final audit PASS，进程退出码 2。
- 采用结论仍受该质量失败阻断；不能用只统计正确请求或换文档重试解除。
- 补充固定性能回放：保留原输入中的 8 个 decode、5 个连续追加、10 个工具/协议请求，6 对、276 请求，另存 `performance-corpus.json` 与 `performance/`。原 8 个长生命周期请求由独立适配器处理，不从整体质量结论删除。
- 原冻结恢复历史填入 canonical 正确答案，在 prime 实际错答时会产生前缀分叉，不能证明恢复刚刚停放的完整会话。因此独立 `run_restore.py` 将每臂自己的实际正文和 reasoning 原样放回历史，分别报告真实恢复事件和答案正确性；历史若不同，不当作固定输入性能配对；本次实际对应请求 hash 相同。该独立诊断的预登记策略允许答案错误或缺少恢复回执记 fail 后继续其余阶段及另一臂，以完整观察机制；工具输出、HTTP/usage、预算、资源和资产/生产漂移仍停止。原正式回放的 FAILURE 不变。
- 本机及 29 定向测试已运行：`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_combination tests.test_combination_chain -v`，23 项通过。16 个模型/配置资产完整 SHA256 冻结，合计 78,212,488,329 字节。

## 固定性能表征结果（已完成）

`performance/` 完成 6 对、12 个 fresh engine、276 个计划请求。96 个定长性能请求全部达到 2048 token；未评分 0、缺项 0、输入 hash 漂移 0。`COMPLETION.json` 为 COMPLETE / final audit PASS。进程退出码 2 来自保留的 3 次工具评分失败，三项统计均为 `REJECT_OR_FIX`，不是基础设施中止。

主指标来自 `performance/statistics/decode_ms/summary.json`。以下正值表示 KVRES 开启后 decode 耗时降低；统计单位是每层 6 个配对轮，采用整轮 log-ratio bootstrap 95% CI，未校正多个场景比较。改善门是 CI 下界 ≥4%，不是点估计 ≥4%。

| 总输入档位 | thinking：decode 耗时降低及 95% CI | 限 thinking=128 的回答诊断 | 4% 改善门 |
|---|---:|---:|---|
| 4K（实际 4095） | 2.35% [1.36%, 3.72%] | 7.43% [3.88%, 10.05%] | 两项均未达到 |
| 32K | 6.38% [2.62%, 9.38%] | 5.19% [1.88%, 8.10%] | 两项均未达到 |
| 64K | 1.74% [0.01%, 3.21%] | -0.26% [-4.38%, 3.04%] | 两项均未达到 |
| 100K | 4.05% [-3.84%, 13.03%] | 4.26% [1.87%, 6.75%] | 两项均未达到 |

4K 回答的 CI 下界为 3.8824%，不能四舍五入为 4% 后判通过。64K 回答和 100K thinking 的 CI 跨零。定长题的“通过”只表示有效性能输出，允许 length 结束，不表示 Java 审查任务完成；回答诊断参数也不等同于正常生产 xhigh 任务。

### 实际前缀复用与读入

核查全部原始 read/reused 记录后修正“冷读”表述：64K/100K 性能题包含前缀复用，不能称为全量冷读。下列计数在所有轮次和两臂一致。

| 请求 | 总输入 token | 实际新读入 | 复用 token |
|---|---:|---:|---:|
| think-4096 | 4095 | 4095 | 0 |
| think-32768 | 32768 | 32768 | 0 |
| think-65536 | 65536 | 49152 | 16384 |
| think-102400 | 102400 | 53248 | 49152 |
| answer-* | 与同档 think 相同 | 5 | 总输入 −5 |
| append-prime | 32771 | 32771 | 0 |
| append-0 / 1 / 2 / 3 | 35993 / 46018 / 49243 / 59268 | 3229 / 10032 / 3232 / 10032 | 32764 / 35986 / 46011 / 49236 |

TTFT 指首个 reasoning / visible / tool 事件，并非首个可见答案。以下为辅助指标；正值表示变慢，不能用它替换预登记的 decode 主指标。

| 路径（总输入 / 新读入） | TTFT 中位数：关闭 → 开启 | 配对 TTFT 增加及 95% CI |
|---|---:|---:|
| 32K / 32K | 7.889 → 8.146 s | 3.27% [2.81%, 3.56%] |
| 64K / 48K | 11.635 → 12.654 s | 8.73% [8.07%, 9.36%] |
| 100K / 52K | 15.204 → 16.404 s | 7.56% [6.48%, 8.37%] |
| 第一次追加约 10K | 3.745 → 4.070 s | 9.44% [6.36%, 12.81%] |
| 第二次追加约 10K | 3.871 → 4.148 s | 8.81% [6.07%, 11.90%] |

两次约 3.2K 追加的 TTFT CI 均跨零。64K thinking 请求整体 wall 增加 2.67% [1.76%, 3.76%]；局部 decode 收益被读入代价抵消。以上是固定顺序负载的分层结果，不生成混合总体提速，也不与历史分项收益相乘。

### 完整质量计数

| 分组 | 关闭 KVRES | 开启 KVRES | 解释 |
|---|---:|---:|---|
| 定长性能有效性 | 48/48 | 48/48 | 仅输出长度及请求有效性 |
| 固定追加历史 | 30/30 | 30/30 | 精确短答筛查 |
| protocol | 30/30 | 30/30 | 5 题 × 6 轮 |
| tool | 29/30 | 28/30 | 5 题 × 6 轮 |

三次 tool 失败均为 `schema-boolean`：round 1/base、round 2/cfg、round 5/cfg，把 `enabled` 输出为字符串 `"False"`。全部保留请求与响应。工具组统计只剩 3 个完整有效配对，属于剔除失败轮后的子集，不将其速度数字作为采用依据；短 protocol 组的局部耗时改善也不替代定长主指标。

历史计数探针每臂为 91/91。5 个工具题本地计数与服务端 usage 存在 8～9 token 差异，在既定 32 token 容差内；其他题一致，不宣称所有请求完全一致。

## 实际历史恢复结果（已完成）

`restore/` 每臂一个 fresh engine、两档 A→B→A→sampled，共 16 个请求。返回历史使用该臂实际输出，包含错答，不填入标准答案。本次两臂对应请求 hash 和可见输出均相同。`COMPLETION.json` 为 COMPLETE / final audit PASS；进程退出码 1 来自答案失败。两臂生产状态与 13 个保护 hash 前后完全一致。

| 总输入档位 | 关闭 / 开启实际恢复 token | 返回请求新读入 | 恢复机制 | 每臂长检索结果 |
|---|---:|---:|---|---|
| 约 68K | 69625 / 69625 | 26 / 26 | 两臂均观测真实恢复 | prime、restore、sampled 均失败（0/3） |
| 约 100K | 102385 / 102385 | 42 / 42 | 两臂均观测真实恢复 | prime、restore、sampled 均失败（0/3） |

每臂两个短 side 问题通过（2/2），六个长检索失败（0/6）。约 68K prime 的错误仍为 `1751936`；每臂恢复后的四个 follow-up 答复只返回目标值的数字前半段，遗漏 `-序号` 后缀，因此不满足固定精确值 oracle。两臂观测到相同失败，不能归因于 KVRES，也不能据此证明正式质量非劣。恢复机制成立与回答正确是两个结果。

本检查只覆盖所列两个实际会话及这次恢复，不证明完整 128K、并发、取消或长期运行安全。

## 真实生成历史编码链（已完成）

`live-chain/` 完成 seed 42/43 的两对、四条八轮链；31/32 轮通过，但完整链成功为关闭组 **2/2**、开启组 **1/2**。任务时钟从计数探针结束后开始，包含推理、评分与编排，不含模型加载和臂间冷却。每条预算 B=2400 秒，失败链 restricted time-to-success 按 B 计，不能把较早失败算成更快完成。

| seed | KVRES | 成功轮数 / 完整链 | 实际任务时间 | restricted time-to-success | 总生成 token | 最大输入 token |
|---|---|---|---:|---:|---:|---:|
| 42 | 关闭 | 8/8，完成 | 704.28 s | 704.28 s | 88906 | 4241 |
| 42 | 开启 | 8/8，完成 | 844.89 s | 844.89 s | 109080 | 4613 |
| 43 | 关闭 | 8/8，完成 | 596.85 s | 596.85 s | 75217 | 4903 |
| 43 | 开启 | 7/8，失败 | 541.04 s | **2400.00 s** | 70326 | 4408 |

seed 43 开启臂第八轮的累计检查结果为 `[true,false,false,false,false,false,false,false]`。原生成 Python 代码块第145行使用未定义的 `dst_balance`，前一行已扣减来源余额；静态核查只有该名字的读取，没有绑定。异账户转账会触发错误，解释了原 Docker 评分中既有功能的失败。未修补生成代码、未补生成、未用重跑覆盖失败。原代码 SHA256 为 `6bc411e6e7abbfe3f37341b2c412bd56dd9a0d35834c6d3093e19b95995e5b79`，原响应保存在 `live-chain/pair-01-cfg/turn-07.response.json`。

seed 42 开启臂任务时间较长，同时生成 token 增加约22.7%，不能把任务耗时差解释成纯 decode 回退。两对只是同一合成任务的两个 seed；没有正式质量非劣样本量，也不足以将单个生成缺陷因果归因于 KVRES。实际输入仅159～4903 token，不能称为长上下文 Java/Pi 任务验证。

评分使用既有不可变 Docker 镜像 `sha256:ec7d6c95cd3692a2e2d228a8b1ca74e4025b54121fcc4c5da6f09cfa473315ad`；无网络、只读、非 root、资源限制。模型代码未在宿主机执行。此阶段 COMPLETE / final audit PASS，进程退出码1表示链评分失败，生产保护前后相同。


## 资源与生产收尾

下表来自逐臂遥测，均没有触发 abort。它是有限实验的观测，不是全天热稳定性或内存泄漏证明。

| 阶段 | KVRES | 最高 GPU 温度 | 峰值显存 | 遥测最低 MemAvailable |
|---|---|---:|---:|---:|
| 性能表征 | 关闭 | 76°C | 23726 MiB | 7756 MiB |
| 性能表征 | 开启 | 75°C | 23724 MiB | 6125 MiB |
| 实际历史恢复 | 关闭 | 73°C | 23726 MiB | 10083 MiB |
| 实际历史恢复 | 开启 | 74°C | 23724 MiB | 8343 MiB |
| 编码链 | 关闭 | 75°C | 23726 MiB | 12137 MiB |
| 编码链 | 开启 | 76°C | 23724 MiB | 10324 MiB |

性能请求边界的额外内存快照中，开启臂最低为6118.83 MiB，略低于周期遥测点。主机 swap 使用在这些请求边界为约601～890 MiB；未连续采集换页吞吐，不能宣称没有换页干扰。恢复/编码链没有 HTTP、usage、预算、CUDA/OOM 或 GPU 归属错误。沿用既有噪声设置4%改善门，本轮未另跑新的 A/A 噪声实验。

最终检查时间 **2026-10-27 14:23:53 +08:00**（原始 `FINAL_STATE.json` 为06:23:53 UTC）：

- `openclaw-qwen38-next.service` 为 inactive/dead，仍 enabled；没有启动生产服务。
- 13个受保护文件的 SHA256 与实验前完全一致，含生产配置、启动脚本、二进制、profile、7个生产源码文件及旧实验配置/HEAD。
- 14个预先保存的执行源码文件仍与运行路径一致；23份运行配置的临时密钥已移除。
- GPU 1 MiB、43°C，无计算进程；无本次驱动或服务进程残留；MemAvailable 60674080 KiB（约57.9 GiB）。

## 原始证据与重放

29原始目录保留为 `/home/hhtele/strata-lab-4090/workspace/combination/kvres-20261027`，隔离源码树 `workspace/trees/combo-kvres-20261027` 也保留用于重放。本地副本为包内 [workspace/combination/kvres-20261027](../workspace/combination/kvres-20261027/ARTIFACTS.md)，该目录被 Git 忽略。

| 目录 | 实际请求数 | 结果与用途 |
|---|---:|---|
| `replay/` | 14 | 原372请求计划在首个长检索失败后停止；保留 FAILURE |
| `repro/` | 4 | 同一请求两对 fresh engine，4/4同错；COMPLETE，质量失败 |
| `performance/` | 276 | 六对固定表征；COMPLETE，3次工具失败；分层统计在 `statistics/` |
| `restore/` | 16 | 实际历史恢复；COMPLETE，12次长检索失败 |
| `live-chain/` | 32 | 四条八轮链；COMPLETE，31轮通过、3条完整链成功 |

合计342条计入各阶段的请求记录，不能合并为一个质量通过率，也不是342个独立任务；每臂另有两个固定短计数资格探针和一个历史计数探针，不计入342条测量记录。历史探针的完整请求/响应单独保存；旧公共 `validate_counter` 不落盘两个短探针的完整响应，输入可从冻结源码重建。这是辅助资格探针的留存缺口，不将其宣称为已完整保存的测量记录。609个原始文件逐一通过下载后的 SHA256校验，342个记录的实际请求body重新计算hash均匹配，三份corpus hash一致。

关键索引：[原始哈希清单](../workspace/combination/kvres-20261027/RAW_MANIFEST.sha256)、[本地完整性复核](../workspace/combination/kvres-20261027/LOCAL_INTEGRITY_CHECK.json)、[分阶段资源和编码链汇总](../workspace/combination/kvres-20261027/ANALYSIS_SUMMARY.json)、[最终状态](../workspace/combination/kvres-20261027/FINAL_STATE.json)。

`SOURCE_MANIFEST.json`/`source/`保存14个阶段前冻结的核心执行文件。`replay-package/`另外保存62个依赖文件，明确标为收尾时采集，见 `REPLAY_PACKAGE.json`；不将收尾快照伪称为运行前冻结。16个模型/配置资产共78212488329字节的原始身份在 `assets.json`；模型及引擎不复制进数据包，重放使用29已有资产和隔离树。

三份corpus SHA256：

- 原始31题：`c6fadd3f189a8ce58fe49f809e89ec6e184a9013626a5072af4365f8d0a5a8c0`。
- 性能23题：`7e148fc7147995b64b235a48d0c2d5cab8bd877a57e6e91a2734a4a80d7fa5e6`。
- 精确失败复现：`eed2e5f2f7c3d04610fe1d2d5de6b1a2ea39403464a091bf31838bb7e8485152`。

以下为实际执行入口；重新运行必须换用新的 `--out` 目录，不能覆盖本轮证据。原配置已是去密钥实验副本，不指向生产端口。

```bash
cd /home/hhtele/strata-lab-4090
LAB_PYTHON=/home/hhtele/strata-0.1.43.1/.venv/bin/python
KVRES_TASK=workspace/combination/kvres-20261027
KVRES_TREE=workspace/trees/combo-kvres-20261027

$LAB_PYTHON -B tools/combination/run_combo.py --config "$KVRES_TASK/config.json" --tree "$KVRES_TREE" --corpus "$KVRES_TASK/corpus.json" --out "$KVRES_TASK/replay" --rounds 6 --execute
$LAB_PYTHON -B tools/combination/run_combo.py --config "$KVRES_TASK/config.json" --tree "$KVRES_TREE" --corpus "$KVRES_TASK/repro-corpus.json" --out "$KVRES_TASK/repro" --rounds 2 --execute
$LAB_PYTHON -B tools/combination/run_combo.py --config "$KVRES_TASK/config.json" --tree "$KVRES_TREE" --corpus "$KVRES_TASK/performance-corpus.json" --out "$KVRES_TASK/performance" --rounds 6 --execute
$LAB_PYTHON -B tools/combination/run_restore.py --config "$KVRES_TASK/config.json" --tree "$KVRES_TREE" --corpus "$KVRES_TASK/corpus.json" --out "$KVRES_TASK/restore" --execute
$LAB_PYTHON -B tools/combination/run_chain.py --config "$KVRES_TASK/config.json" --tree "$KVRES_TREE" --out "$KVRES_TASK/live-chain" --pairs 2 --image sha256:ec7d6c95cd3692a2e2d228a8b1ca74e4025b54121fcc4c5da6f09cfa473315ad --task-budget-s 2400 --execute
```

所有请求保护保持131072总上下文、4096安全余量、MemAvailable≥4096MiB、温度<85°C及实际GPU归属检查。计数器和服务端共同使用PT=0。只跑生成脚本或 dry run 不算重放成功；必须另检查对应质量结果和最终审计回执。

## 工具验证与未覆盖范围

实际运行的本机定向验证：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_combination tests.test_combination_chain -q  # 本机23项通过
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_combination_restore -q  # 8项通过，本机
```

29也执行相同两个模块，23项通过，原输出保存在 `unit-tests.log`。

仓库要求的 `pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm test:integration`、`pnpm build` 均退出0，日志保存在原始目录的 `local-verification/`。构建仅有既有Phaser大chunk提示；本轮复用已核对的原生引擎二进制，未重编CUDA引擎。文档与新增文件的范围检查另列于 `VALIDATION.md`。

未覆盖：真实Java/Pi仓库任务、正式2pp质量非劣、完整128K连续会话、并发/取消、长时热稳定性和生产流量。原正式回放已有硬质量失败，性能八个定长场景也没有达到4% CI门；本轮不形成新的ADOPT结论，不自动修改或恢复生产。
