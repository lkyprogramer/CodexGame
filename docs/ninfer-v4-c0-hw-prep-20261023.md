# C0最小实机驱动与账本准备结果

无需GPU的准备、定向离线验证和双轴集成评审已完成。**未启动服务，未发GPU、模型或HTTP请求；原GPU服务保持停止。** 本轮不授予Chat性能、K4或生产发布资格。

## 冻结交付

直连`ssh 29`，隔离分支`codex/c0-hw-driver-20261023`。驱动集成树`0e5efa0fd62d60a90060b9896a1d4e115495e879`；HEAD仍O，未创建commit、push或部署。原C0产品树`4d31af405fca9c70bd39a71257f83f4eeebbd0bc`的1239文件逐一核对不变；P4/C0已有二进制和BO依赖直接复用，不重编、不重跑旧CPU、Baseline、native或grader。18处G1差异、C1缺口及旧失败保留。

远端源码`/home/hhtele/ninfer-v4-c0-hw-prep-20261023/source/tests/c0/hardware`；[补丁](../output/ninfer-v4-c0-hw-prep-20261023/hardware.patch)与[源码身份](../output/ninfer-v4-c0-hw-prep-20261023/source-identity.json)。冻结运行目录：`/home/hhtele/ninfer-v4-c0-hw-prep-20261023/prepared-window-r1`。冻结SHA：`b09cb8d9ac7adc8f63af562ca6221a5f1522896c4aab8904b0d931f87aabffe7`。[冻结回执](../output/ninfer-v4-c0-hw-prep-20261023/prepared-window-r1/freeze-receipt.json)

新增控制器/独立guardian、累计预算、Chat驱动、纯离线分析器、准备脚本及定向测试。`--plan-only`实际通过；直接调用授权合同的负例按预期拒绝。真实`--run`没有调用；没有创建运行state或runtime目录，账本wire/model/submission/warmup均0。授权文件保持`NOT_AUTHORIZED_PREPARATION_ONLY`。[准备回执](../output/ninfer-v4-c0-hw-prep-20261023/preparation-receipt.json)

## 可执行范围与总预算

| 项目 | 两版本累计上限 | 当前实用 |
|---|---:|---:|
| 新Chat Completions | 8 | 0 |
| 服务内置warmup提交 | 2 | 0 |
| 模型提交（含warmup） | 10 | 0 |
| wire（8 Chat＋4 telemetry GET） | 12 | 0 |
| 新direct native Op / capture / replay | 0 / 0 / 0 | 0 |
| 关闭准入并开始清理 | 第720秒 | 未进入窗口 |
| 硬窗口 | 900秒 | 未进入窗口 |

顺序执行P4 baseline→C0 candidate，每版本4个新Chat：A seed、B独立seed、A续轮、B续轮。两个新约64KiB参考前缀和真实SHA工具调用；续轮保留实际assistant reasoning/content/tool_calls，再接本机真正执行的工具结果，不能预造模型输出。B用于切换驻留状态，避免A→A一直resident看不到L2。只用Chat Completions和只读telemetry，不新增其他业务协议或代理验证。

每次服务启动已有1个native warmup，模型输出预算4是原实现内置值；本轮不改它，也不另发HTTP warmup。两次启动共2提交，8个正式Chat均保留medium／32768，以及原temperature1/top_p.95/top_k20、context/KV262144等参数。模型文件、两个serve SHA及实际server_start/每请求采样合同均绑定。无adapter证据复用且运行时再次检查，避免额外decision warmup。

## 源码核对后修正的测量安排

原提案“copy完成事件后1秒”不能实时执行：`concurrent_executor.h`先在内存记录copy时间，但listener要等publication完成才输出日志。现改从对应seed完整SSE DONE的单调时间延迟1秒续轮，不等待导出完成；并发两条会话链保留真实调度误差。导出copy/publication时间只做事后关联，不伪装为实时信号，不改产品观测代码。

每个请求从canonical X-Request-ID关联到request_start/request_done、Engine ID、completion_export_job_id和export记录；完整body/raw/header/哈希、实际P/O、结束原因、TTFT/queue/prefill/decode/total、真实cache source/restored bytes均保留。role-only帧不计首语义输出；客户端语义交付时间和服务器TTFT分别记录，不称为真实token ITL。完整启动时间和所有新Chat wall均保留，GPU进程首次EVP耗时不可单独观测时为null；复用CPU测得约1.904ms，不声称实机已测。

归因门槛：基线必须实际`source=none/no_alias/restored_bytes=0`、prefix hit0且完整prefill；候选必须真实L2恢复且减少computed prefill。还要求对应正文/工具参数/实际结果及P/O、stop、采样配置一致，基线发送时处于copy后publication前、候选已完成，DONE+1秒误差≤150ms、两版queue差≤50ms。只在派生比较视图归一化未被Qwen模板渲染的opaque tool IDs；原wire和ContentId完全保留。单靠发送时间、两版都L2命中、浅复用、不同输出或缺字段不能证明SHA服务收益。

两组均满足门槛且受限桶完整Chat wall降低≥5%也只给pilot信号；p95=null、optimization_qualification=false、K4=false。未形成L2/目标窗口或可比样本即INCONCLUSIVE，不增加请求寻找好结果。单lane的B请求可能排队到两版发布都完成，因此这次小预算可能只得到缺口判断，不能保证测得提速。

## 失败与自动接续

每wire和warmup在动作前durable预留，全局累计且同unit不可重发。完整SSE DONE/framing、durable模型终态、空闲scheduler及实际admitted数量、所有相关导出终态共同决定能否接续；HTTP200或只有request_done不够。未知结果、坏SSE/JSONL、身份漂移立即阻断后续未预留请求及下一版本。

已知模型质量失败照实FAIL。依赖它的续轮若无法合法构造，以`SKIPPED_KNOWN_DEPENDENCY`记录成本0和原因，不伪造、不用替代请求补数；独立会话和另一版本在证实drain后可继续。`COMPLETE_ACCOUNTED`只表示每项已知结果或明确未发送，绝不等于模型质量PASS或已运行8个请求。

独立guardian先ready再允许create，持有继承的同一GPU lease；owner丢失或720秒到达就关闭准入。仅停止精确本窗口标签的候选，超时重新验身份后精准kill，不删除证据；确认driver退出，核对原停止容器及原缓存dev/inode。不能确认清理就写`CLEANUP_NEEDS_ATTENTION`，不得报告已清干净。真实GPU启动/清理竞争仍未实测，本轮只具源码和mock证据。

## 已执行的必要验证与评审

新增驱动/预算/解析/生命周期测试首轮52项通过；修复后仅跑新增及受影响10项，通过，共57个唯一用例／62次执行，失败0。覆盖重复发送/额度耗尽/已知依赖跳过/未知阻断、坏Content-Length或缺DONE、日志损坏、监听权限回退与PID漂移、启动和实际采样合同、role帧、guardian/清理、原容器/缓存保护，以及“双端都L2不能归因”的负例。没有运行旧SHA backend测试或重测2.149倍结果。[首轮](../output/ninfer-v4-c0-hw-prep-20261023/cpu-new-driver-tests-r1.log) · [定向补证](../output/ninfer-v4-c0-hw-prep-20261023/cpu-targeted-r2.log)

Standards与Spec独立只读评审均通过。发现并已修复：运行端口字段、监听权限回退、完整传输与Engine终态分离、真实合同校验接入、role帧首语义时刻、已知失败的零成本依赖记账，以及真实cache miss归因。评审代理未执行测试或SSH；测试由root实际执行。14个驱动文件冻结，其中12个Python文件AST解析及集成diff检查通过，旧C0的78份证据hash验证且旧产品源码不变。

## 执行入口与预计耗时

准备已经完成，原1–2工程小时不再算剩余等待。后续获明确GPU授权时，绑定当前root／freeze SHA／planned window ID／同一预算，执行冻结入口：

```bash
cd /home/hhtele/ninfer-v4-c0-hw-prep-20261023/prepared-window-r1
PYTHONDONTWRITEBYTECODE=1 python3 controller.py --run
PYTHONDONTWRITEBYTECODE=1 python3 analyze_pilot.py --root /home/hhtele/ninfer-v4-c0-hw-prep-20261023/prepared-window-r1
```

第二条是离线汇总，失败窗口也要执行并披露缺口；当前不生成有效GPU授权，也未执行第一条。完整[README](../output/ninfer-v4-c0-hw-prep-20261023/prepared-window-r1/README.md)及[空账本](../output/ninfer-v4-c0-hw-prep-20261023/prepared-window-r1/budget-ledger.json)已交付。

预计实机**8–15分钟**，依据是旧启动约103秒×2、两版本8个新Chat及清理。64KiB前缀和medium实际输出耗时尚未测；长输出可能在第12分钟被截止，保留未完成证据而不降低输出预算或续额度。原服务始终保持停止，仅清理候选；生产发布另行独立。
