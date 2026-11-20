# 08｜观察器开销、数据边界与 Ada profiling

## 1. 不是“记录得越多越好”

记录要解决一个可证伪的问题：例如“父会话恢复耗了多少时间”“GPU是否在等待这一次CPU工作”。默认不要打开全量 per-kernel trace、tensor dump 或 NCU replay。

| 级别 | 内容 | 数据代价上限（新计划建议，非已测） | 用途 |
|---|---|---|---|
| L0 | 现成service/terminal摘要、SSE事件、低频系统采样 | 首选≤1Hz；只在已存在请求完成时补快照；有界文件 | 服务现状、请求/质量、宏观分层 |
| L1 | 默认关闭的新lineage/cache/round/shape固定buffer | 初版总buffer≤16MiB/engine；最多64MiB结构附件/run；重载固定关闭 | 填补当前证据缺口 |
| L2 | 选择一个窗口的CUDA/CUPTI/Nsight活动与依赖 | 原件≤512MiB/捕获；到限停采并记loss；不自动第二次 | 解释无法从L1闭合的关键路径 |

内存与字节上限是本包工程默认草案，P1按实际record尺寸测算后锁定。缓冲不够应减少采样/字段，不申请无限RAM；不得因丢数据偷偷扩大GPU次数。

## 2. observer 的三重门

1. **语义门**：关掉新记录的binary与原版相同输入输出/状态/dispatch；开记录不改变sampler、draft policy、graph capture、chunk/VRAM策略。
2. **完整性门**：预登记窗口没有缺request/seq/required事件，时钟/ID能联结。没有证据的字段明确unknown。
3. **代价门**：单独的observer-off/on对照；正式候选性能比较在observer-off或相同且已验证的低开销配置进行。

本包建议L0服务时间比95%CI上界≤1.01，L1≤1.02；对关键阶段TTFT/E2E分别评，不把一个变快抵另一个变慢。初始3对只作筛选，不能证明门就记 INSUFFICIENT，先减采样或简化，不自动增加重复次数。门值是工程验收目标，不是上游宣称。

P2.0/P3开始前冻结估计器、独立单位、CI方法与其适用假设。三对不能套现有六对工具；精确单侧sign test在n=3时最小p=1/8，不能据此证明95%门，任意小样本bootstrap也不自动有效。只得到描述性差异就标SCREEN_ONLY/INSUFFICIENT；它仍可帮助决定“不需要更多hooks”，但不能赋予正式性能资格。

若L0是来源未确认的Linux发布binary、L1为源码patch binary，两者不能仅凭版本同为0.1.62直接配对。须用同源、同toolchain/features的stock→patched-off→patched-on证明，缺其中一个比较就保留缺口并另行申请预算；不重新解释跨构建差异为observer开销。

L2允许较大扰动，但必须记录observer-on/off差、route/graph变化；只回答profile问题，不能用其wall声明正式速度提升。对扰动敏感问题必要时退回L1，不默认“软件trace不可信”。

## 3. 开关不是统一的布尔值

当前源审计的每个env必须绑定解析位置和关闭方式；见 [06](06_MINIMAL_INSTRUMENTATION.md)。尤其：

- `STRATA_VERIFY_PROFILE=0` 在存在性判断处仍可能走profile分支，影响fork/fusion；baseline用**unset**，不是字符串0。
- `STRATA_COMMIT_TIMING` 的报告可触发event synchronize，不是免费读计数。
- `STRATA_PREFILL_TIMING` 是流中相邻event区间，可能包含CPU分组和copy wait，不等于纯kernel时间。
- `STRATA_DISPATCH_STATS` eager、capture、launch各分母不同；capture存在不证明执行。
- `STRATA_SPEC_TRACE` 可能含token ID/概率/草稿文本关联，不能作为默认脱敏日志。
- 新hooks关闭分支不得调用clock、hash、allocate、文件I/O、GPUevent；开启也不能加每轮同步来“使计时准确”。

源级no-op检查、对象/产物hash、实际命中和性能比较相互独立。profile宏改变了路径则另建profile-only身份。

## 4. RTX4090 能力边界

| 能力 | 结论 |
|---|---|
| CUPTI软件activity / Nsight Systems / CUDA events | 可作为Ada候选工具，但要核本机工具链/OS/权限、实际schema和丢事件；不是保证每种graph可全关联 |
| CUPTI HES | Blackwell及以后特性，4090不适用；借鉴低扰动分层思路，不安排HES移植 |
| Programmatic Dependent Launch | 原生overlap需compute capability≥9.0；sm89不满足，不设置emulated CC伪造资格 |
| device-side CUDA graph | 与PDL不是同一功能；是否移植由资源/依赖决定，不从“无PDL”推导所有device graph都不支持 |
| Nsight Compute | 对指定已知热点的指标/replay诊断；replay结果不当任务E2E样本 |
| NVML功耗/PCIe/利用率 | 窗口/系统或GPU级采样；不能单独当某request的字节、能量或critical wait |

官方依据：[CUPTI HES说明](https://docs.nvidia.com/cupti/main/main.html#hardware-event-system-hes)、[CUPTI Activity API](https://docs.nvidia.com/cupti/api/group__CUPTI__ACTIVITY__API.html)、[CUDA PDL能力边界](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/programmatic-dependent-launch.html)。在线最新文档不意味着可以把用户CUDA12.3替换为最新工具链。

## 5. 有限profile的顺序

1. P0记录现有 `nsys --version`、`ncu --version`、CUPTI/driver来源；未安装则标UNAVAILABLE，不默认安装/改权限。
2. P1用离线sqlite/schema夹具验证 importer；先检查表与列，不硬套旧nsys导出列。
3. P3只对已获得授权、身份绑定的一次确定窗口捕获；先process/context/stream与NVTX correlation，再决定是否需要node级细化。
4. 明确PID复用、range边界、clock变换、eventloss、graph重复launch。先恢复全窗口，再对request裁剪；不先截一段最漂亮的kernel集合。
5. 区间并集用于计算busy；依赖边用于计算完成路径。没有边的不臆造serial链。
6. NCU指标先query当前GPU支持集合，不把sm100指标名照搬；同一硬件不同时挂多个相互干扰的profiler。
7. P3-L2的1引擎/3请求只容纳一条限定profile轨迹。对照复用已有**同一instrumented构建、输入、缓存状态和可比热状态**的off臂（通常来自P3-L1）；不默认在进程中切换启动级env或profiler，不暗加fresh off运行。没有合格对照则INSUFFICIENT，只保留profile解释；另采需单列获批预算。

## 6. 数据与权限边界

默认只保存哈希/匿名ID/数值。模型输出token序列是可还原内容，不能因不是字符串就视为脱敏。C01需要token级离线回放时，使用明确许可的合成/公开文本或本地受限trace，报告只导出聚合。文件路径、工具参数与租户语料不进入公共metrics。

C01所需W09 prompt与committed-token原件不在默认L0/L1摘要里。先查既有合法trace；如缺失，最多将P3-CASE的同一额度改为W09并明确内容采集权限，不增加请求，不默认开STRATA_SPEC_TRACE。proposal只能使用该时点已提交前缀；事后可对照已录未来答案计算oracle上界，但不能将它计为在线命中或实测接受。

不能读取无关凭证、擅自关闭服务、提权profiling或把metadata开关当采集授权。失败/取消/失联时保留run ID、原因和资源清理回执，不自动恢复旧生产服务。

