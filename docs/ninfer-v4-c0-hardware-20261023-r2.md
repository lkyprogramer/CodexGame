# C0 r2最小实机补测结论

**驱动修复、Chat严格功能及生命周期最小验证通过；C0的Chat服务性能验收仍为INCONCLUSIVE。** 直连`ssh 29`完成P4→C0，8个新Chat全部通过，自动接续、导出排空和候选清理正常。没有重发r1请求或重跑旧Baseline、已通过的CPU/native/grader。原GPU服务保持停止，采样、context和Pi medium/32768不变。

## 修复与开发身份

隔离分支`codex/c0-hw-repair-20261023-r2`，驱动树`b8431b377d4e990c254437c1e10dfb714079b5d7`，HEAD仍O；无commit、push或生产部署。只改7个驱动/测试/说明文件，1239个产品文件逐字节未变，复用原P4/C0二进制和BO依赖，没有重编。

- seed改用已有服务合同支持的`tool_choice=auto`。仍严格要求模型真实调用一次`sha256_text`、实参等于指定文本，并在真实本机SHA结果返回后输出精确摘要。未放宽工具、结束原因或结果断言。
- 非200响应头到达即关闭新增发送，保留完整raw/header。只有完整指定HTTP400、Content-Length/JSON错误结构、canonical ID，以及响应EOF后的同实例idle/准入未增加日志证明齐全，才持久记已知准入前夹具失败；不等不存在的Engine终态，不算模型质量失败，不增加wire。证明缺失最多10秒即保守停止，其他错误不泛化为已知拒绝。
- 子进程异常或stage缺失明确停止，不补造原附件；离线分析区分从未执行与已尝试中止。

本轮实机没有HTTP400；新增拒绝终态分支由定向CPU回归验证，没有额外发送请求制造拒绝。root在29实际执行15个新增或直接受影响CPU用例，全部通过；两条独立只读集成评审均通过，代理未执行SSH或测试。[修复补丁](../output/ninfer-v4-c0-hardware-20261023-r2/repair.patch) · [定向CPU结果](../output/ninfer-v4-c0-hardware-20261023-r2/cpu-targeted-r1.log) · [评审](../output/ninfer-v4-c0-hardware-20261023-r2/integration-review.md)

## 冻结、预算和实机结果

新冻结目录`/home/hhtele/ninfer-v4-c0-hw-repair-20261023-r2/prepared-window-r2`；回执SHA `7b7682a9904cb807268e2b2fd52d88d741a7b3194da022d43bae813b65d2a338`。20份工具/夹具SHA、空账本、产品二进制、原服务停止/GPU空闲、原缓存和模型身份核验后，绑定本次授权单次启动。[冻结回执](../output/ninfer-v4-c0-hardware-20261023-r2/freeze-receipt.json) · [启动回执](../output/ninfer-v4-c0-hardware-20261023-r2/launch-receipt.json)

| 项目 | 上限 | 实际 |
|---|---:|---:|
| 新Chat | 8 | 8，全部PASS |
| 内置warmup | 2 | 2 |
| 模型提交（含warmup） | 10 | 10 |
| wire | 12 | 12：8 Chat＋4 telemetry |
| 新direct native Op / capture / replay场景 | 0 / 0 / 0 | 0 / 0 / 0 |
| 关闭准入并开始清理 | 720秒 | 自然完成即清理 |
| 硬窗口 | 900秒 | **345.047秒完成收尾** |

两版本各完成A/B seed及真实工具结果续轮，共4条工具链。12个wire均有request/body/header/raw/outcome及SHA，8个Chat完整唯一SSE DONE，canonical ID→Engine终态→导出job关联一致。每端实际admitted=5（4 Chat＋1 warmup），结束时运行/等待/预填充/待解码全0；unknown=false，pending exports为空。P4容器退出后才启动C0，没有GPU并存或重启。

候选、controller、guardian、driver均退出，GPU compute apps为空。原`ninfer-4090-prod`仍停止/PID0，原镜像、参数、cache dev/inode `66306/24150039`及模型身份未变；没有自动恢复。[机器汇总](../output/ninfer-v4-c0-hardware-20261023-r2/final-summary.json) · [清理](../output/ninfer-v4-c0-hardware-20261023-r2/prepared-window-r2/cleanup.json) · [最终回读](../output/ninfer-v4-c0-hardware-20261023-r2/evidence/final-host-readback.json)

## 性能观察及未通过的条件

| 本窗口描述性指标（各n=1） | P4 | C0 |
|---|---:|---:|
| 完整服务READY耗时 | 108.233秒 | 56.926秒 |
| A seed相同1,338,953,132字节导出，copy完成至publication完成 | 15.032秒 | 7.267秒 |

对应观察差为47.40%和51.66%。未控制执行次序、页缓存及状态内容差异，不能据此归因C0净收益、统计显著性或普适Chat提速。完整启动包含首次provider初始化，但GPU进程首次EVP不能单独观察，保留null，原CPU约1.904ms只作复用证据。

**有效Chat性能配对为0。** 四个目标续轮在两版本均为`source=none / final_miss_reason=preflight_rejected / restored_bytes=0`，没有形成“P4缺alias而完整prefill、C0已就绪且真正L2恢复”的机制对照。B seed两端都有277-token浅L2复用，不能当目标续轮收益。随机assistant reasoning/输出和后续P/O不相等，A续轮queue差也超过冻结50ms门槛，不能用少量wall差宣称达到≥5%服务收益。[逐请求指标](../output/ninfer-v4-c0-hardware-20261023-r2/chat-metrics.csv) · [冻结分析结果与拒绝原因](../output/ninfer-v4-c0-hardware-20261023-r2/prepared-window-r2/pilot-analysis.json)

CPU合同与本轮Chat功能结果保持有效；V04的服务收益没有证明，p95=null、optimization_qualification=false、K4=false，生产发布未执行。本轮不追加请求寻找可通过样本，也不把完整性能资格重新设为其它性能开发的前置。

## 原始失败、缺口与证据保存

r1首个具名tool_choice完整400、2wire/1warmup成本和原账本保持不变；原outcome/stage缺失仍是原始缺口，外置核对说明已知拒绝，不补造。r1的86份持久附件与原归档SHA再次核验；18处G1差异、C1附件缺口及全部历史失败继续保留。两次窗口累计实际14wire、9个Chat尝试（8次入模）、3warmup，共11次实际模型提交，分窗记账。

r2本轮137个远端文件全部采回，含全部冻结工具、原始请求/响应、账本、stage、日志和Docker身份；本轮没有新增原始运行附件缺口。归档SHA `973384d58260147861cb70918e2a59bc5b208b413f23dd45aef75f4c9c1613b7`；远端保存在`/home/hhtele/ninfer-v4-c0-hw-repair-20261023-r2/execution-r2-evidence.tar.gz`。[完整证据包](../output/ninfer-v4-c0-hardware-20261023-r2/remote-evidence.tar.gz) · [可复现离线核验](../output/ninfer-v4-c0-hardware-20261023-r2/verify_evidence.py)

辅助核验的首次错误另保留：全量diff检查遇到原CPU夹具既存EOF空白；收尾采集器误用“空账本启动守卫”，离线回读首版误用本机路径检查远端路径。均在测量外以范围正确的只读检查修正，未重发模型/HTTP、未重启候选、未改冻结工具或运行证据。离线核验及最终独立结果审计通过。
