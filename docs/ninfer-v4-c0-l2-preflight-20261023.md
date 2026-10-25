# C0续轮预检拒绝：CPU定位、夹具修复与最小补测准备

本轮已完成CPU定位、夹具修复、定向回归、集成评审及新工具/空账本冻结。已证实原夹具破坏真实提示词前缀，当前证据不要求修改产品。实际深层L2恢复及TTFT收益尚未验证；本轮没有发GPU、HTTP或模型请求。原GPU服务保持停止。

## 根因与事实边界

原r2 seed为`tool_choice=auto`，followup却强制`none`。虽然HTTP `tools`数组未变，`src/serve/request.h:229`令uses_tools=false；`translate.cpp:85–99,230`清空effective_tool_jsons，Qwen模板`chat_template.cpp:366–369`不再渲染开头的`# Tools`。真实token前缀因此变化。

CPU探针调用生产OpenAI解析、语义解析、翻译、Qwen模板、tokenizer及position builder，复用实际6份前端资源及已有C0/BO库。逐项比较token ID、type和三个位置轴，不创建Engine。原4组历史seed/followup的全身份LCP均为1；仅将派生副本followup恢复为auto后，LCP为55483或55562，覆盖其生产策略安全边界55481/55560。原输入及历史记录未改写。

`concurrent_executor.h:3165–3184`的元数据预检可在image解析/import之前拒绝；原`deepest_candidate_agreement=null`不能当作已经解析image并发现payload损坏。上述前缀变化足以解释缓存身份不匹配。CPU探针未导入旧缓存image，也未独立证明所有元数据条件合格，故不宣称引擎整体无缺陷或实际L2已恢复。

另一个问题是实验设计：原r2随机seed输出使P4/C0的真实assistant历史与续轮P/O不同；DONE+1秒早于两端约7.27/15.03秒publication；B请求还引入约19秒队列。原8个Chat功能PASS继续有效，性能有效配对0保持INCONCLUSIVE，不重新解释为提速通过。

## 本轮变更与验证

只改隔离分支的测量工具和新CPU探针。原whole-Chat `pair_evidence`函数AST完全未变；产品1239文件与C0树逐文件一致，无产品重建、提交或推送。SHA摘要、ContentId、缓存格式、生产sampling/context和Pi medium/32768不变。

| 本轮验证 | 实际结果 |
|---|---|
| 新前缀探针构建 | PASS；仅编译该探针，复用已有C0/BO静态库；容器无GPU设备、network=none |
| 历史4对输入的8个CPU正反用例 | 8 PASS；原none负例与修正auto正例均符合预期，未重新发请求 |
| 新固定分支夹具首版 | 1 FAIL/1 PASS；正例LCP55291低于安全边界55293，全部保留 |
| 修订固定分支夹具 | 2 PASS；正例LCP55295覆盖安全边界55293，变更reference负例LCP280 |
| 定向Python回归 | 先13项PASS，再仅补1项发送截止回归PASS；14项唯一测试，未重跑已过用例 |
| Standards / Spec独立评审 | 两轴发现并修复发送截止及未发请求计数问题；最终均无剩余明确发现 |
| 新冻结及plan-only | PASS；21文件、空账本、无runtime/state、授权为PREPARATION_ONLY |
| 实际L2导入、GPU时序及TTFT | NOT_RUN |

固定分支首版用连续USER消息，CPU检查发现安全边界前两个role token不同，因此先停止并保全失败。修订版在两段USER之间使用固定、明确标注的合成ASSISTANT输入；它不是实际seed输出，也不作为真实工具结果续轮证据。该分支仅用于建立相同前缀的受控TTFT对照。

评审发现预约和请求文件fsync可能拖过固定发送时刻。驱动现于所有持久写完成后、`connection.request`紧前再次检查固定时刻及清理截止。超时记录`RESERVED_NOT_SENT_NO_RETRY`，保留预约成本，明确wire未发/无admission，不重试；实际wire及Chat统计排除这些预约。新测试分别覆盖落盘期间跨过+150ms及清理截止。评审代理仅只读，测试由主代理在29执行。

精确执行命令和结果见[构建回执](../output/ninfer-v4-c0-l2-preflight-20261023/probe-build-r1.json)、[历史前缀回执](../output/ninfer-v4-c0-l2-preflight-20261023/prefix-replay-r1.json)、[新前缀回执](../output/ninfer-v4-c0-l2-preflight-20261023/controlled-prefix-r2.json)、[13项回归日志](../output/ninfer-v4-c0-l2-preflight-20261023/targeted-cpu-regression-r1.log)、[发送边界回归](../output/ninfer-v4-c0-l2-preflight-20261023/targeted-send-boundary-r1.log)及[双轴评审](../output/ninfer-v4-c0-l2-preflight-20261023/integration-review.md)。原固定分支失败在同目录`controlled-prefix-r1.*`，不得覆盖。

## 后续最小实机范围与预算

新profile为`CONTROLLED_PREFIX_BRANCH_TTFT_V1`，当前仅准备，不执行。P4→C0顺序，每端：telemetry-before → 新seed完成 → 依据其durable `engine_slot=0`和digest条件erase retained GPU lane → 固定branch → 本地日志导出核对 → telemetry-after。沿用既有slot erase合同；仅操作本窗口候选，保留L2，不动原服务或原缓存目录。erase等待GPU copy完成，不等待publication。

branch固定在seed SSE DONE+10.0秒、容差150ms发送；这是依据旧publication耗时事先冻结的时间。若erase/落盘来不及，拒发并停止，不自适应延迟、不追加请求。两端请求字节相同，不包含随机生成的assistant历史；实际seed和branch输出仍须严格通过原精确工具名/operand/finish_reason断言，工具结果本地计算并保留，不再发工具结果续轮。

| 项目 | 总上限 |
|---|---:|
| 新Chat | 4（每端seed+branch） |
| 内置warmup | 2 |
| 模型提交（含warmup） | 6 |
| wire | 10（4Chat+4telemetry+2条件erase） |
| 新direct native / capture / replay | 0 / 0 / 0 |
| 预计实际窗口 | 6–10分钟 |
| 候选清理 / 硬截止 | 第12分钟 / 第15分钟 |

这是一个n=1机制与首响应延迟pilot。准入比较必须同时满足：相同seed/branch请求字节、实际branch P、生产采样（RNG seed除外）及seed导出byte shape；两端queue≤50ms；P4浅命中≤512且computed_prefill≥P−512；C0实际source=l2、restored_bytes>0、深命中≥45000且computed_prefill≤P−45000；P4 seed发布晚于branch发送、C0早于发送。发送时刻不冒充实际cache lookup时刻，真实命中与prefill记录仍必需。

只在全部控制条件成立后，首个非空content/reasoning/tool delta的客户端TTFT减少≥5%才记`PILOT_TTFT_SIGNAL_NOT_K4`，否则INCONCLUSIVE。保留服务端TTFT、完整Chat wall和全部启动/导出成本作描述。该结果不证明decode、整轮Chat、质量、统计p95或V04/K4/生产资格。

## 身份、保全与未覆盖项

- 远端隔离根：`/home/hhtele/ninfer-v4-c0-l2-preflight-20261023`，分支`codex/c0-l2-preflight-20261023`。
- P4产品树`35d3dd9e4aa96b1f56f2e9c55482946bd9911cde`；C0产品树`4d31af405fca9c70bd39a71257f83f4eeebbd0bc`。二进制SHA按[源身份](../output/ninfer-v4-c0-l2-preflight-20261023/source-identity.json)及[冻结回执](../output/ninfer-v4-c0-l2-preflight-20261023/preparation-receipt.json)复核。
- 最终driver tree `130bcf5414fc89d971f368fc81e9aafdda7753dd`；[13文件补丁清单](../output/ninfer-v4-c0-l2-preflight-20261023/repair-files.json)与[补丁](../output/ninfer-v4-c0-l2-preflight-20261023/repair.patch)绑定评审。
- 新冻结根`prepared-window-l2-r3`，freeze SHA `1b0f1c596aa15f5e41d337f139d936c51ac52131ecd6d3c5efabc1e384127dd1`。原账本全0、无runtime/state，未调用`--run`。
- 本轮未重跑旧Baseline、C0 SHA31/58/7、已过native/Graph/G1、原8Chat或grader；18处G1差异、旧C1附件缺口、r1/r2成本及所有失败保留。
- CPU证明不代替image导入、实际缓存命中和GPU时序；固定窗口可能因publication波动、seed shape差异、队列或工具质量失败而INCONCLUSIVE，届时保留失败，不为寻求通过追加样本。
- 原服务STOPPED、原image/参数/cache目录身份不变、GPU无计算进程。`p95=null`，`optimization_qualification=false`，K4和生产发布均未取得资格。

更新后的V4入口、任务注册表和预算已同步本轮事实。新[收尾回执](../output/ninfer-v4-c0-l2-preflight-20261023/final-summary.json)、文档校验及备份校验单与原始日志分开保存；不能把派生报告冒充原始运行证据。
