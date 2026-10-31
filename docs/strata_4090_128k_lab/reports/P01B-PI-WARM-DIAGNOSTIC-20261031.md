# frontier/P01B · 自然 EOS 真实 Pi 历史暖态诊断

结论：**执行 COMPLETE；候选资格 INSUFFICIENT。** 用户授权的一次单引擎、最多三请求全部完成，无重试、无替补。最小采集补齐了完整 host 窗口、原始输出 token IDs 和限定条件下的串行依赖边；没有获得值得进入 native 优化的候选。生产保持停机，未部署。

本批次使用新合同，保留 P01 的941<2048短输出终态。P01B接受自然EOS，2048仅为上限；它不改变P05的固定2048正式性能合同，也不把任务完成或采集完成当质量PASS。

## 实际请求

| 请求 | 完整输入 | read / reused | 输出 | TTFT | 完整请求wall |
|---|---:|---:|---:|---:|---:|
| prime | 103183 | 103183 / 0 | 941 | 29.3292s | 35.9042s |
| append_1 | 89212 | 80868 / 8344 | 576 | 21.5172s | 25.9828s |
| append_2 | 89498 | 291 / 89207 | 774 | 2.1513s | 8.4737s |

TTFT为首个thinking事件。三个请求均正常完成；真实追问、采样seed、模型/模板和reply reuse=1/PT0保持。每次回传本引擎实际正文/thinking，不填充追问，不执行工具。这是来自Pi session的脱敏HTTP诊断投影，不是实际Pi工具任务的质量验收。模型工具意图仍由tool_choice=none和服务边界拒绝，不因HTTP成功宣称质量通过。

整个live adapter墙钟178.1738s，包括启动、现场复核、三个请求和资源交还，未超3600秒。实际native PID2398799，server PID2398793，coordinator PID2398731；只有一个native引擎、三次HTTP尝试，没有额外校准、对照、profiler或补跑。

## 最小采集与身份

独立树 `workspace/trees/frontier-p01b-20261031` 基于P6 `5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d`，保留原六文件Python port。native差量仅generate.cpp中的host observer调用和新增header；原数学/分派语句、CUDA调用、graph节点、融合和同步保持，PROFILE/原TRACE均未启用。实际新二进制SHA256：

`cdfb67469b4cd22c1f1ee8ec28768e810433b91ea85cfdf43a8e8cef382e3341`

5150个源码文件冻结全SHA，原P6基线二进制仍保持原SHA；实际10272槽，native完整STRATA环境恰等P00环境加唯一`STRATA_LAB_P01B_TRACE`路径。控制配置只派生研究树/workspace路径，引擎配置与资产身份保持。没有以新二进制冒充原P6字节身份。

每窗6个host时间点；静态上限2048窗口/2048输出ID，请求后导出，不在窗口内分配或写文件。独立源码审阅修复了adapt线程启动后读pending容器的采集竞争；并排除first/merged/T1、peer/remote、多stage和未完成异步分支。初次CPU编译后又做最终增量构建；实际执行版本由CAPTURE_BUILD和executed_sources冻结。

29号机g++ CPU probe验证完整记录、token/window两类溢出及CLOCK_MONOTONIC包络，PASS。State188464bytes；640000窗口合成测试净平均145.28473ns/window，低于预登记5000ns门。该结果不证明GPU运行无采集扰动。没有无采集GPU对照，也不据此宣称因果加速。

## 实际窗口与可筛查成本

三请求共939个完整窗口、2291个原始emitted token ID，无溢出；ID数量与SSE usage吻合，完整时序落在对应HTTP单调时钟包络内。原始IDs直接记录native T输出位置，未从文本重新分词。REQUESTS中的旧SSE字段仍明确缺少SSE原始IDs；native文件及ANALYSIS另存实际IDs和canonical hash。

| 请求 | 窗口 / 源码闭合host边 | 全部verify返回→commit进入间隙 | 占本次native decode观测 | 源码闭合部分 |
|---|---:|---:|---:|---:|
| prime | 347 / 155 | 7.4222ms | 0.1126% | 0.0723ms |
| append_1 | 212 / 97 | 5.9878ms | 0.1340% | 0.0781ms |
| append_2 | 380 / 142 | 7.7395ms | 0.1224% | 0.0659ms |

只将已有verify/head同步完成后、没有未完成必要并行支路的host间隙建为依赖边。其余间隙保留UNKNOWN，不把CPU pool累计时间、异步commit返回或draft返回当GPU全局完成。GPU内部区间、expert dtype/nt、CPU任务完成/park拆分仍未知。

在本次采集条件下，两条warm请求即使把表中**整个host间隙**全部删除，所对应份额也不足0.14%，远低于4%筛查门。该窄方向没有立项空间。此结论不覆盖所有host工作或GPU内部，更不是无插桩严格上界或全局NO_GAIN；没有具体新机制，资格保持INSUFFICIENT，P02不自动执行。

## 首次append大量重读的离线核对

对三份实际请求用同一冻结模板/tokenizer做CPU重渲染，没有追加推理请求。两个append均与“上一真实请求+上一真实输出+冻结Pi追问”完全相等，所有原消息对象保留；没有删历史凑预算。

prime→append_1的渲染token最长公共前缀为8468，实际reuse8344；append_1→append_2分别为89210与89207。差额124/3没有进一步归因，不能说LCP与reuse完全相等。

模板95–104/120行根据最后user位置与preserve_thinking决定历史thinking渲染。因此大规模前缀改变与PT0的上下文相关渲染相吻合，这是有源码支持的解释；尚未拆开每个变化token，也没有证明新的缓存缺陷。第二次append已只新读291token，不能把首次投影转换的重读外推为持续缓存失效。单链不能证明未来稳态性能。

## 资源与交还

105个guard样本，无中止；GPU峰值74°C、23702MiB，MemAvailable最低5950MiB。native RSS最高50485.64MiB、VmSwap最高348.88MiB；三个请求major-fault增量分别3433/33/243。这些是容量与计数观察，没有建立fault/swap到阻塞墙钟的因果关系，不据此调整内存策略。

最终只读回执：2026-10-31 11:05:40北京时间，生产inactive/dead/enabled；13保护SHA、原P6二进制、控制配置和引擎配置未变；GPU1MiB/43°C、无计算进程，18089可bind，三个所属PID均不存在，临时key已移除。本轮没有清理超时或HAND_BACK失败。

## 验证与证据

- root本轮相关Python测试49项PASS；采集门修订后重跑P01B17项PASS，原32项证据复用。独立Reviewer另外运行P01B17项和旧runner7项PASS。
- 29号机独立研究树CUDA12.3/sm89 Release构建PASS，mandatory build开关保持；g++ observer CPU probe PASS。它们与唯一GPU执行分别记录。
- 原始导出92个文件，共13112270bytes，下载后逐文件长度/SHA全部匹配。压缩包SHA256：`e75a3fc776360829a35aa20cf046252c5392f75064811886780903a234bc738c`。不包含私有runtime config、native/probe二进制或模型权重。
- 原件：`workspace/frontier/p01b-20261031/`；RAW_MANIFEST与实际执行源码保留。完整GPU/HTTP执行由root完成；独立审阅的本地原件范围另记frontier/reports/P01B_REVIEW.md与P01B_TEST.md，不冒称独立SSH/GPU复现。
- 包收尾：主清单397项、frontier严格清单78项、181条子包相对链接检查及git diff --check全部PASS。离线validator输出gpu_validation=NOT_RUN仅表示该工具自身不执行GPU，不能覆盖本报告的实际运行证据。
- 首次包收尾命令cwd错误，且新增跨子包Markdown链接被现有边界拒绝；已修正工作目录和引用方式，重跑上述失败检查通过，未重跑GPU。无游戏runtime/protocol改动，未运行无关pnpm全仓测试。

## 停止点

P01B执行结束，不再追加同类GPU样本或进入候选开发。保留原六项FAIL，P05仍BLOCKED_EVIDENCE；无新优化采用、无部署。后续只有明确的新机制差量和可闭合依赖证据才提出新合同，不以泛host调度、旧候选改名或单条swap观测延长本批次。
