# P00 — 最新基线、测量与实验资格

**Goal：**让每一个后续结论可重算、可归因。**依赖：**无；先读README、01机器事实、02基线、12–14验收。**产物：**最新基线资格回执、真实tensor和资源账、成本trace、冻结数据与正确的统计适配器。此计划属于测量建设，不宣称直接提速。

## P00-01 冻结机器、生产及模型身份

执行本包`START_HERE_AI.md`的init/doctor/assets，保留inventory原件；读取生产服务定义但不改变其状态。补充`lscpu -J`、`numactl --hardware`（若已有）、`nvidia-smi -q`、`lsblk -o NAME,MODEL,SIZE,ROTA,MOUNTPOINTS`、`free -m`、`findmnt`、`cmake --version`、`nvcc --version`、`perf --version`。缺工具写NOT_AVAILABLE，不为盘点自动安装或改系统。不要转储完整环境变量、HTTP密钥或私钥。

确认两根DIMM/当前频率、NUMA、物理核与SMT映射、PCIe当前/最大代际和宽度、SSD剩余空间、swap/THP、driver、温度/功率限制。PCIe配置值不等于实测带宽；后续使用现有工具做有界pinned H2D/D2H，记录复制大小和DDR争用。历史36GB/s不当成此刻实测。

以生产配置解析每个GGUF分片、native pack、tokenizer、template、MTP及profile；记录SHA256与文件尺寸。权重hash一次计算后可凭文件身份复用，不能只hash首个分片。`asset_files`补充非GGUF资产。实际路径由inventory填入，任何`/ABSOLUTE/`占位未填都BLOCKED。

**通过条件：**真实机器仍满足本包假设；如果CPU/GPU/模型变化，更新机器记录并重排资格，不沿用本包排名。旧生产exe SHA、EXACT6、spec4和0.5提案阈值分别核实，不把采样min_p改成0.5。

## P00-02 固定latest源码与构建依赖

源锁见`sources/LOCK.json`。`bootstrap`只创建独立clone和base worktree，不更新生产。记录GGML固定提交、CMakeCache、编译器版本与完整flags，配置只生成sm89。

```bash
python -B -m lab.cli --config config/local.json bootstrap
python -B -m lab.cli --config config/local.json build
```

预期生成`workspace/trees/base/build-lab/strata`与`LAB_BUILD.json`；返回源码和exe hash。当前机器报告使用venv CMake4.4.3，不能假设PATH上的系统3.25满足构建。不要用`-march=native`掩盖TU的ISA资格；不要擅自加fast-math。

**失败处理：**依赖下载失败、CMake版本不符、sm89构建失败，只标BLOCKED并保存日志；不改源锁到另一个“能编译”的提交后继续比较。

## P00-03 最新基线初筛与后续正式资格，保留两个参考

在已有维护授权且GPU独占后，冻结corpus、完成tokenizer校验，运行`mig`的`p`（当前部署二进制）与`base`（最新锁）两臂。MIG的p臂是部署binary/serve树在归一化实验配置下重放：cache由local覆盖，parallel=1，batch移除，实验port等按runner合同固定；不是原样生产流量回放。

实验端口18089。实验cache预算从0开始用于纯decode/prefill资格；缓存行为另设小预算逐级升到实际6144MiB，不能把cache-off MIG当全部生产行为通过。

```bash
python -B -m lab.cli --config config/local.json corpus --suite full
# 将上一命令返回的实际corpus绝对路径填在下行，先dry-run再执行。
python -B -m lab.cli --config config/local.json mig
python -B -m lab.cli --config config/local.json mig --execute --corpus /ABSOLUTE/FROZEN/corpus.json
```

以上现有corpus/MIG命令**仅用于严格smoke初筛**：生成器固定temperature=0、thinking=False，full长序列为4/32/64/96/120Ki token档，不能据此声称真实sampled-thinking、任务非劣或park/restore已通过。下一段所列是正式基线资格的额外要求，须先完成P00-06/07适配器/数据建设后回到本步骤验收。

正式短JSON/tool/Java、greedy与真实sampled-thinking、8/32/64K及预算允许的122K附近分别报告；Java必须有固定镜像JDK与参考测试，SKIPPED不能当PASS。保留当前ADAPT_OVERLAP=1，记录最新auto async被排除的有效原因。检查新源码的tensor快路径是否真的被调用。

**通过条件：**协议/状态/质量门合格、必要性能未退化、资源余量有界。最新不通过可继续在latest修复，但不覆盖生产。此前P→A0 MIG已经做过，不重复伪装新工作。

## P00-04 修正CPU基准并导出真实调用清单

参考[PR3871](https://github.com/Niko1221/Strata/pull/3871)固定head见锁；它是benchmark修复。审查`src/kernels/cpu/kq_cpu_bench.cpp`的量化和Q2_0调用是否与`src/kernels/cpu/pool.cpp`一致。当前实际奇层Q2_0 down special-case不是旧微基准路径；先写一条会检测调用分支的回归测试，再移植修复。

导出偶/奇层GU/down格式、shape、row尺寸、tail/Hadamard、输入ActQ、nt分布、miss专家数分布、各分支调用计数。建议一次性诊断manifest，避免每个token刷日志。微基准至少包括nt=1/2/4/5/8、1/2/8/80/96/97个miss边界、实际权重流式与LLC热两种；不能只测随机密集浮点矩阵。

**必须产物：**`tensor_inventory.json`、`cpu_callsite_manifest.json`、修复前失败/修复后通过的bench路由测试、raw耗时和字节口径。不能把bench修复写成引擎加速。

## P00-05 全窗口关键路径与显存主存账

主要源：[verify.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/verify.cpp)、[pool.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/kernels/cpu/pool.cpp)、[expert_cache.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/core/expert_cache.cpp)、[prefill.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/prefill/prefill.cpp)、[generate.cpp](https://github.com/Niko1221/Strata/blob/41cf05a06a25dd29103b7b27a2279a3f60c21876/src/program/generate.cpp)。

拟新增诊断输出`window_trace.jsonl`（本包未实现引擎插桩）：window_id、committed_target_tokens、draft_accepted、target_bonus、proposal、T、context_filled、CPU miss数量和nt、resident/mapped/DMA字节、phase wall边界、graph key、路由hash、effective策略、prefill/restore事件。各时钟统一来源，GPU事件与host时钟只在可校准点关联。采样输出、批量写盘，测插桩开销。

用已装perf定位CPU热点/自旋/内存吞吐；若nsys/ncu存在，单独profile一小段真实shape，正式测量不带ncu。GPU busy中的`wait_flag`不是有用算力；区分wait期间CPU在算、主线程在quant、还是等待线程屏障。若perf权限变化，记录而不是自动扩大权限。

显存账至少：常驻dense/热专家、expert slots、KV、GDN/conv、MTP权重与状态、verify图/临时、prefillregion、copy staging。RAM账至少：mmap/native权重、CPU预包、pinned激活与KV、conversation snapshot、allocator保留、工具/JVM、文件页。记录持有者、生命周期、实际字节和峰值；共享alias不能重复相加，reserved与used分开。

**通过：**window_wall可从依赖关系解释，计时和资源账无未解释大项；若总phase和大于wall仅因重叠，明确展示，不把两者相加。

## P00-06 正式性能与真实任务适配器（明确拟新增）

已修复工具支持严格smoke、任意pair、分层和缺失门；正式任务不是已实现接口。拟新增`lab/task_campaign.py`、`lab/task_statistics.py`与独立测试；不要把它们写进shell直到实现并注册CLI。

1. 输入冻结task_id、模板/工具定义、环境镜像、总wall预算B、token/重试预算、成功oracle、流量权重。运行结束保存`run_valid/task_success/failure_kind`与全部原始记录。
2. 模型错误与任务预算耗尽是有效失败；基础设施错误使配对无效；OOM/crash硬拒绝。实现restricted time：成功actual wall，失败B；不取两者成功交集。
3. 冻结AB/BA paired rounds或实现ABBA宏块（13协议）。保存process实例与warmup/reset身份；多window不是独立样本。按paired单位重采样，保存seed、次数、版本、完整ratio；零discordance质量使用已交付quality_gate，不用退化bootstrap。
4. 正式性能采用14文档门槛；smoke内置探索性阈值不是正式采用门。加入缺轮、双臂缺题、重复、float/bool、NaN、基线有模型失败、全成功、task预算、环境timeout、OOM、场景分层、吞吐方向等回归测试。
5. 增加受控非STRATA allocator环境对照仅允许预登记`MALLOC_MMAP_THRESHOLD_`或指定`GLIBC_TUNABLES`子项，并记录差异、清理作用域；不能把任意env注入开放。现`cfg --env`仍只接收STRATA，直接传MALLOC会被拒绝。
6. 实现park/restore adapter，消费离线plan但必须从真实引擎日志确认状态事件、session/token身份；同文本二次请求不能冒充恢复。

**反例驱动测试：**更快但做错半数任务的候选必须失败；30题都对不能自动通过2pp NI；假heartbeat不能延长HTTP绝对截止；配置漂移/外来GPU进程必须中止本轮而保留证据。

## P00-07 质量与holdout冻结

先修工具，再生成新的dataset ID；附件缺失的14题不得重建后沿用旧hash。至少覆盖12文档各类，真实Java任务至少30个筛查；正式独立样本规模按预期差异与区间宽度预登记。调参集与holdout分离。用户私有代码在本机保存，不上传训练；公开输出只脱敏统计。

**完成回执：**`BASELINE_READY.json`分别列smoke_ready、formal_quality_ready、formal_performance_ready、state_ready；每项标记PASS/BLOCKED/SKIPPED/NOT_RUN并链接证据。MIG初筛只标MIG_SMOKE_PASS，缺正式适配器时不能给整个BASELINE_READY总PASS。P00全部前置并非要求所有理论研究都做完，但没有对应测量输入的方向不能晋级性能结论。
