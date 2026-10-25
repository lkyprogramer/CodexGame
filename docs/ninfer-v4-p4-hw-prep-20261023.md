# P4最小实机驱动准备与验证账本

状态：**P4_HARDWARE_MINIMUM_PREPARED_GPU_NOT_RUN**。已通过直连`ssh 29`完成隔离驱动、无GPU增量构建、离线账本验证、双轴集成评审及冻结。此次实际GPU场景、模型提交、推理HTTP、grader均为0；没有执行实机验收。原GPU服务继续停止，镜像、参数、缓存目录身份和原代理未变。

## 身份与复用

- 输入为[已完成的P4开发交付](ninfer-v4-p4-20261023.md)，输入树`0fe9e9517846af82dea4f62c30be85ebc0b4e075`。新分支`codex/p4-hw-prep-20261023`，新源码树`35d3dd9e4aa96b1f56f2e9c55482946bd9911cde`。无新commit，HEAD仍为`e0b05f7cb46adae2787be2ccbe605e1b0c9b3923`，不声称merge ancestry。
- 远端隔离根`/home/hhtele/ninfer-v4-p4-hw-prep-20261023`；本机源码`/tmp/ninfer-v4-p4-hw-prep-20261023/source`。源码只新增/修改三个测试文件，不改引擎、codec产品实现或生产配置。完整源码归档在[本轮证据目录](../output/ninfer-v4-p4-hw-prep-20261023/)，1235个Git blob逐一核对。
- 复用Baseline、BO、G1、P1—P3与P4既有构建和通过证据。本轮没有重跑旧Baseline、grader、已过host/Web测试、P3的136场景或旧四个native场景。18处G1差异、两次P2失败、C1末次telemetry附件缺口及其它历史失败全部保留。缺失附件不补造。
- BO仍为CUDA13.2/SM89/Release，镜像`sha256:8be4d008e107636f575401dc8b225d7ee44ebce51a505e37659978f5b2f6a251`。27B serve沿用既有构建，SHA`8884da24e63856355a2db1048c942452fe6bdd6d25aaaf517cb162f231ad8846`。本轮模型整文件SHA沿用原证据、不重读18GB；新冻结绑定实际dev/inode/size/mtime，发生变化则拒绝执行。

## 已准备的真实路径

数值入口为`ninfer_gqa_attention_test --p4-minimum-run NEW_ABS_OUT`；纯CPU目录入口为`--p4-minimum-plan`。新`tests/p4/minimum_numeric.h`限定8个唯一场景、操作与Graph预算，并在效果发生前fsync记账。数值仍使用已有独立FP64 oracle、精确codec参考、cache字节/guard及原容差，不放宽断言。A1/A3在两次replay前恢复正确输入状态；A4独立分段参考不冒用其它压缩路径的输出。

缓存入口为`ninfer_p4_export_native_driver --run-p4 MODEL 5 NEW_ABS_OUT LEGACY_SLOT`，只执行新scenario5。实际旧v4 slot来自P2的`native-case-2/original.slot`，159877831字节，SHA`dd7a20ac3140742bc065ee7e84f28ce334469573e5c494d60e8b794523dedd3d`。已复制到本轮私有只读夹具，SHA相同；没有重跑旧模型来造附件。此slot不等于C1缺失的HTTP附件。新驱动拟验证：旧snapshot4经真实restore明确拒绝且lane不污染；新snapshot5同步/后台保存一致；同Engine恢复digest一致；新Engine从独立L3目录恢复真实前缀。两次提交前后分别持久化reservation/request ID，未结束结果不重发。

Chat仅覆盖OpenAI Chat Completions的原生nonstream及私有代理stream两项；复用P3已有严格38字节参数与增量交付断言，在P4 midrise profile下补测，并新增同前缀cache命中且computed<prompt的检查。仅私有代理端口，原代理不替换。Messages/Responses不在当前范围，不为它们造PASS。

## 后续最小实机范围与预算（本轮未执行）

| 阶段 | 单轮固定范围 | 硬预算 |
|---|---|---|
| midrise数值 | rk8v4/rk4v4/rk2v4-e8各T6、T66，base61；rk4v4的A4 prefix63、1000 | 8场景，36次direct Op API |
| standalone Graph | 六个codec场景各A1/A3；两个A4场景 | 14次capture、28次replay；capture内14次Op声明 |
| 新旧缓存隔离及恢复 | 仅scenario5，旧4拒绝/新5恢复/跨Engine L3 | 1场景，2次Engine提交，2次模型加载 |
| Chat Completions | native nonstream + proxy stream及prefix复用 | 2个客户端模型请求，2次提交 |
| HTTP审计 | 2 client + 1 proxy upstream + 2 telemetry | 总5个wire，恢复wire=0 |
| serve启动 | 仅一次新候选启动 | warmup=1次提交，1次模型加载 |
| 全窗口 | 顺序执行上述一次；不调优、不重试、不回收失败额度 | **含warmup最多5次模型提交、3次模型加载** |

36 direct + 28 replay = 64次执行的语义Op；capture内14次声明单列，不叠加为实际kernel数。14/28仅约束standalone Op驱动；Engine内部Graph不在该计数器内，不能声称全模型仅14次capture。每个Graph只capture一次、replay两次，无额外调优迭代；所有场景仅一轮，失败即停止后续，不重置账本。

预计独占GPU **8–12分钟**，是根据既有装载/Chat耗时给出的规划估计，尚无本轮GPU耗时。硬上限 **20分钟**，第 **17分钟** 开始清理候选并保留3分钟。分段上限：数值120秒、缓存420秒、serve启动180秒、Chat阶段300秒；均受全窗口截止约束，不能各自重新计时延长总窗口。这里只清理本轮候选，不恢复或自动启动原服务。

profile保持context/KV=262144、temperature1/top_p0.95/top_k20/presence0、medium/default32768、MTP3。HTTP诊断O4096、native诊断O8属于短工具/缓存夹具，不是Pi任务预算；没有Pi请求，Pi medium/32768不变。容量不足直接记录BLOCKED/FAIL，不降context、不另起更小profile。

## 本轮验证与评审

| 项目 | 实际结果 | 原始证据 |
|---|---|---|
| 两个变更驱动无GPU增量构建 | PASS，11.057371秒；无`/dev/nvidia0`或`/dev/nvidiactl` | [build-r1.json](../output/ninfer-v4-p4-hw-prep-20261023/remote-delivery/evidence/build-r1.json)、同目录log |
| 编译后的有限目录/describe | PASS，CPU-only目录与预算一致 | [numeric-plan.json](../output/ninfer-v4-p4-hw-prep-20261023/remote-delivery/evidence/numeric-plan.json) |
| 首轮新离线合同 | 7 PASS、1 ERROR，原错误保留 | [r1日志](../output/ninfer-v4-p4-hw-prep-20261023/preparation-tests-r1.log) |
| 修复与定向复测 | 3/3 PASS：补齐测试state前提；清理新owner竞态回归；原容器拒绝清理 | [r2日志](../output/ninfer-v4-p4-hw-prep-20261023/preparation-tests-r2.log) |
| Python语法 | 11个helper编译通过；不执行其外部动作 | [工具来源与SHA](../output/ninfer-v4-p4-hw-prep-20261023/tool-provenance.json) |
| 冻结/交付 | 17个冻结输入SHA、本远端工具逐字节与源码1235 blob一致 | [冻结回执](../output/ninfer-v4-p4-hw-prep-20261023/remote-delivery/prepared-window/freeze-receipt.json) |
| 最终原服务/代理/GPU只读检查 | 原服务STOPPED；Id/image/Config/HostConfig/Mounts相同；缓存66306/24150039；proxy1950/shim相同；GPU空闲 | [远端最终回执](../output/ninfer-v4-p4-hw-prep-20261023/remote-delivery/evidence/remote-final-receipt.json) |

离线唯一初始ERROR是新测试未设置`cleanup_deadline_epoch`，已修正测试夹具，没有放宽产品断言。首轮部署tar提取遇远端Python不支持`filter=`；在未提取、未冻结、未启动任何请求时停止，改为显式检查成员路径/类型后完成部署，原日志保留。二者均是准备工具/夹具问题，不登记模型失败。

**Standards：** 独立只读评审未发现规范阻断；原FP64判据、有限目录、真实restore和新旧记录边界均保持。

**Spec：** 首轮发现继承cleanup helper先无锁读旧state、后关闭窗口，可能遗漏刚登记的proxy/driver owner。已改为同一state_lock内读取最新owner并切到CLEANING；新增回归准确模拟该交错。独立只读复核确认finding关闭，无剩余具体问题。评审者未运行测试；上述3/3由主代理执行。真实GPU进程/Graph/HTTP清理仍需实机证明。

## 执行与验收边界

远端冻结入口为`/home/hhtele/ninfer-v4-p4-hw-prep-20261023/prepared-window/controller.py`，freeze SHA为`d0850be9004505295b90335772fe480afb0c4ec9328299fe2f3c0ddbd8094ca8`。默认调用只输出计划；不存在`authorization.json`，仅有明确NOT_AUTHORIZED的模板。本轮授权只到无GPU准备，不启动未来窗口。后续获得对应预算授权后，只能在新账本上执行一次；未知终态保全后停，不自动重发。冻结源码/二进制/依赖/模型stat/旧slot SHA任一漂移都拒绝执行。

当前完整P3/P4、128K/192K/248K质量容量、真实decision adapter、正式配对性能/长期资源/发布均UNQUALIFIED。最小实机即使通过，也不覆盖P4-T06全部具名断言或P4-GATE。p95=null，optimization_qualification=false；没有测得性能收益。本次准备不实施greedy proposal或Target sampling策略改动。
