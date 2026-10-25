# P3 Chat Completions 修补与离线验证

2026-10-23（目录沿用任务开始时的20261022标识）。结论：**OFFLINE_VERIFIED_LIVE_RECHECK_PENDING**。隔离补丁可构建，新增定向合同及集成代码评审完成；旧最小实机结果仍为 **P3_MINIMUM_CHAT_ONLY_NOT_PASSED**，完整P3、性能及生产发布不取得资格。

本轮通过`ssh -J jump 29`执行，等价于当前`jssh 29`。只操作新隔离根`/home/hhtele/ninfer-v4-p3-chat-repair-20261022`；没有停止、切换或部署现网，没有模型、GPU或生产HTTP请求。后续实际GPU窗口采用最新政策：原GPU服务保持停止，直到用户要求恢复。本轮当前运行的原服务未停。

## 原因与修补

**多余转义：证据支持模型对含糊提示的解释分歧。** 原nonstream返回的工具参数JSON合法，但逻辑text为44 UTF-8字节，相对严格38字节预期多6个字面反斜杠。原reasoning明确讨论两种解释并选择保留反斜杠；同输入stream样本选择一次JSON解码。两请求除stream及stream_options外相同，不能据此要求随机生成逐次相同。

追踪Executor输出、GenerationService、QwenToolCallStream及OpenAI外层JSON序列化，未发现nonstream路径额外插入语义反斜杠。原始token IDs与解析前模型markup未保存，不能逐token还原模型输出；新的parser夹具标为`DERIVED_EQUIVALENT_NOT_RAW_MODEL_MARKUP`。详见[原始证据归因](../output/ninfer-v4-p3-chat-repair-20261022/escaping-attribution.json)。

修补诊断提示：末行是JSON string literal，只解码一次，然后原样传入逻辑Unicode字符串；保留一次解码后仍存在的合法反斜杠。严格38字节预期、真实工具输入/hash检查不变，44字节仍被拒绝。没有添加通用unescape，没有改产品parser、采样或输出预算。新模型行为是否满足澄清后的合同尚待实机补测，旧FAIL不改写。

**代理增量交付：确认存在实现缺陷。** 冻结原代理的SSE路径调用`resp.read(8192)`，可等待填充或结束，扣住已经到达的完整参数帧。隔离副本只将SSE读取改为`read1(8192)`；nonSSE路径仍用原读取方式。受控上游发出参数帧后，必须等客户端确认收到才允许terminal/EOF，排除了“等结束后一次交付也算流式”的假通过。chunked与Content-Length两种路径均证明旧实现不能提前交付、新实现能够提前交付。真实模型经代理的提前交付仍待补测。

## 源码与构建身份

- 分支：`codex/p3-chat-repair-20261022`，未创建提交或推送。
- 继承实机已测树：`b3fc67df1a7fd3fbac318a3505b38c0d48a3beb2`。
- 最终候选树：`fe1ad3328d2caad003dc51f8c0ab288e1e26df6a`。
- HEAD仍为O：`e0b05f7cb46adae2787be2ccbe605e1b0c9b3923`；继承U17输入`f4089901fa17b83ecbb21bd2bde17bf614c3bf03`。树身份不替代merge commit/上游ancestry资格。
- 相对继承树共7文件：诊断提示、代理副本/说明、3个新测试文件及CMake注册。18处G1差异和既有产品源码保持。
- BO固定CUDA13.2/SM89/Release/27B-only镜像`sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`，复用原构建缓存。容器runc、network=none、无GPU设备，4CPU/12GiB；只新增构建host测试目标，原应用二进制SHA不变。

[最终补丁](../output/ninfer-v4-p3-chat-repair-20261022/chat-repair-fe1ad33.patch) SHA `ee9339d97ec7a15aec21af938999c87472aae11a2573e80e176eb443d3533d68`；[完整源码归档](../output/ninfer-v4-p3-chat-repair-20261022/source-fe1ad33.tar.gz) SHA `64e80241cb8c110523de6650ebb239a7009676d53448d548771e7ce37af30dab`。隔离副本未安装到原服务。

## 实际验证及失败保留

| 验证 | 结果 | 证据/范围 |
|---|---|---|
| 原代理本地因果负例 | 2 FAIL、其余3 PASS | `proxy-test-r1`；原实现阻塞首帧 |
| 修补代理本地合同 | 5 PASS | `proxy-test-r2`；含SSE两种传输、UTF-8/JSON、非流式和400可见性 |
| 新C++ parser→SSE/非流式JSON合同 | 18场景 PASS | BO-r2；XML/Hermes、3逻辑值、3种合法UTF-8分片 |
| 提示/严格输入/采样预算合同 | 3 PASS | BO-r1；后续仅复用，未重跑 |
| 29上旧代理因果负例 | 2个预期断言FAIL | BO-r3；准确匹配withheld gate、无导入ERROR |
| 29上修补代理因果合同 | 2 PASS | BO-r2；通过后不再重跑 |
| 新目标构建、Python静态编译、diff检查 | PASS | 固定BO及最终源码树 |
| 集成代码评审 | 无剩余阻塞finding | 独立只读评审；评审者未执行测试 |

精确命令保存在各BO `status.json` 的argv与deadline中。主要目标为`cmake --build /build --parallel 4 --target ninfer_p3_tool_escape_regression_test`；首轮CTest仅选新增Cpp与prompt两个目标，后续仅复测失败Cpp。代理远端只执行两个因果方法，未重跑已通过的3项未变路径。

以下过程失败全部保留，未当模型质量失败，也未放宽断言：

1. 应用补丁时因新克隆复用mtime、index stat未刷新而拒绝；确认内容等于原树后刷新index，原失败及恢复回执保存。
2. 评审发现新增夹具切到半个UTF-8码点，与真实Decoder发布合同不同；在执行前改为完整码点分片，产品parser未改。
3. BO-r1新Cpp夹具向序列化函数传`stop`，却断言`tool_calls`。按真实调用合同修正调用参数，原断言保留；原失败与prompt PASS分别入账。
4. BO-r2旧代理负例因根路径挂载触发Python pycache导入IndexError。原runner仅按exit=1曾误标预期负例；这个结果**不作为因果复现证据**。BO-r3只修挂载路径，并要求两条指定断言失败且无ERROR后才完成负例补证。原日志及原status均保留，不能只看BO-r2的顶层状态。

最终证据以[汇总](../output/ninfer-v4-p3-chat-repair-20261022/final-summary.json)、BO-r3语义核验及其复用的BO-r1/r2正例为准。[远端原件归档](../output/ninfer-v4-p3-chat-repair-20261022/offline-evidence.tar.gz) SHA `8d9bd8fd955d823f0d8bdb544299c4ab7acff73998d4315935e653c4bef04979`，已下载并核对SHA；[交付回执](../output/ninfer-v4-p3-chat-repair-20261022/offline-delivery.json)绑定最终源码树。

原现网容器ID`86cb6d9ae7348fb928570e60290d2dc8ac933170a3c7bca32016ff347e2e1ddd`、镜像`sha256:e753e2283db78bbe2fe1fc92b9d45300a27fd5765b367c434c9023cbf2cb1cb3`、PID77758、args/binds前后一致；原代理PID1950及SHA`4b0cefa5c1c785c43303e1d261969e889cd5989a95c135bb14998c96f5f6ea11`保持。缓存挂载保持原目录，没有写入原缓存或更改服务启动策略。

## 最小实机补测

本轮只准备[两项新请求及预算](../output/ninfer-v4-p3-chat-repair-20261022/proposed-recheck/plan.json)，未启动窗口。下一窗口需冻结两项专用账本及仅清理候选的控制器，不能运行旧版自动恢复原服务的入口。

| 范围 | 新模型生成 | 候选wire |
|---|---:|---:|
| native Chat nonstream，澄清提示、相同38字节预期 | 1 | 1 |
| 隔离修补proxy Chat stream，首参数早于同server终态、严格参数检查 | 1 | 2（客户端+代理上游） |
| 直接候选服务前后telemetry | 0 | 2 |
| 合计 | 2 | 5 |

保守计入1次内建启动warmup，最多3次模型提交；0恢复wire，0新增Op/Graph/native场景/Pi。无额外health/models/warmup HTTP、无自动重试或剩余额度转移。旧stream/replay/cancel、136数值场景及原Baseline/grader均不重跑。

预计 **5–8分钟**，硬上限 **15分钟**，第12分钟开始清理候选，保留3分钟。启动≤180秒、单HTTP≤90秒、HTTP阶段≤300秒。该估计基于旧窗口9分37.83秒中已完成的GPU场景、6请求及107.34秒恢复被移除；新模型思考和加载耗时仍有波动，不是测得的新窗口时间。后续原GPU服务停止后一直保留停止状态，直到用户要求恢复；本轮未停止当前服务。

## 保留边界

旧P3 4 PASS/1 FAIL/1 INCONCLUSIVE、18处G1差异、P2两次失败及C1附件缺口、P3原fixture失败和Baseline全部限制不回写。原实机归档SHA再次核对相同。B29的278项及8+2评分不重跑。采样仍T1/top_p.95/top_k20/presence0/medium，诊断O4096和Pi原32768不变。p95=null、optimization_qualification=false；本轮离线合同通过不代表真实模型质量、真实代理提前交付、完整P3或生产资格通过。
