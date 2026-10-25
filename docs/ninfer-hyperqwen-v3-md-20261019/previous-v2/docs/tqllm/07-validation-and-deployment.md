> V2 参考快照：P7—P12 不再是执行权威；按根目录 `plans/00-master-plan.md` 和 `plans/01-v2-migration-map.md` 执行。本文保留历史设计与来源，不表示实现完成。

# 测试、统一Review、部署与回滚

## 测试层次

第一层是无GPU的policy、token-index、identity、layout、预算和状态机测试；第二层是原始checkpoint及相同Target代表值的独立reference；第三层是CUDA算子逐层数值；第四层是同Target完整greedy序列和GDN/前缀事务；第五层才是HTTP/真实Agent/性能。所有层都有自己明确的claim，不能用Python工具测试替代NInfer CUDA资格。

新建CTest target均在task中标注“待实现”，由Integrator注册到`tests/CMakeLists.txt`。验证先`ctest --show-only=json-v1`确认target存在；正则零匹配失败；GPU必测skip=77视为BLOCKED不是PASS。旧B0/oracle/边界/prepare_detail/协议/缓存测试继续跑，不能为新backend删旧suite。

## 核心负例

| 领域 | 必须证明 |
|---|---|
| 选择器 | Decision/非greedy/未资格/缺archive不进入DFlash2；成本缺失不当0；资源未加载不按需要临时下载 |
| 外部提案 | 0/部分/全接受、bonus/stop/length、假Lookup匹配，只有许可前缀提交 |
| Target数值 | K=3/4/5对应width4/5/6，与ordinary同Target精确；首分歧定位到层与GDN记录 |
| 特征 | 已提交tokenfrontier和featurefrontier可能差1；拒绝的行不进archive；正确layer输出时点 |
| global检索 | 第0页、最后页、不满页、>4096chunk候选、ties、越界/重复、32远端chunks预算 |
| 位置 | rawposition与virtualpositionoracle分别验证；只Draft重定位，Targetcache/RoPE不变 |
| 异步 | cancel/lane复用/rewrite/adapter切换后迟到stage不能发布；所有lease与fence释放 |
| graph | replay指针不变、资源generation变化失效、eager/graph一致、hostrefresh不假装在图里 |
| 缓存 | 有Target无Draft照样命中Target，转MTP/None；旧E8cache明确拒绝；新archive不能污染Targetalias |
| 接口 | OpenAI/Responses/Anthropic流的tool args、stop与usage，均只见已提交token |

## 每个Phase的统一gate

所有task产物合入同一个stage commit，独立reviewer读完整diff与来源账本、核对设计及失败用例；同一commit上重新build/CPU/GPU/HTTP suite。并行worker自己的测试仅作局部证据。review修改源码后重跑受影响测试，所有GPU性能结果绑定commit、Target/draft artifact、配置、CUDA/driver、UUID、负载hash。

`phase_gate.py`只核实证据一致性与required checks，不鉴定截图或日志真伪；审核者须看原始GPU证据与实际进程结果。P7—P12模板均PENDING，签名/测量字段留空是有意阻断。

## 运行手册与权限

参考checkout只读。实施可本地创建feature worktree；不得写用户原部署目录或执行远端push。P7从原P6已资格tag创建实验分支，不重新做34个上游提交。所有新feature默认off；`--spec-policy`/`--dflash2-artifact`等是任务实施后才有的新选项，现在不能对旧二进制运行。

单卡串行A/B/A。只有在已获本次具体部署窗口授权后，由执行Agent停止/排空旧实例、运行候选、完成同一轮验证并按结果恢复/保留；user本次请求文档不等于现在有远端生产操作授权。不得同时启动两套27B，再把OOM当算法失败；不与训练/压测并行占卡。

## 发布档位

E1=P8/P9合格优化，原MTP/Target主线；E2=P10合格ringDFlash2；E3=P11合格globalDFlash2。每档固定允许请求类型、最大实际context、并发、drafterasset和fallback。E2/E3未获采用不阻止使用E1。P10/P11正确性/预算失败或实验未执行时gate阻断；实验全部完成但无增益时允许gate记录“研究完成、promotion=DECLINED”，不能宣称性能合格。P12只发布QUALIFIED档位。若高阶任务本身BLOCKED，另出E1/E2局部资格报告，P12全扩展gate不算通过。

回滚保留P6/E1上一合格镜像、完整启动参数、旧独立Target缓存目录；candidate的draftarchive随进程关闭销毁，不迁移回旧版本。不得删除历史Target缓存以“解决兼容性”，也不能让不同模型/codec共用可写目录。验收一次真实rollback后的warm/cold、toolchain与监控恢复，不能只写回滚脚本未执行。


## 研究阶段通过与默认采用：四状态准则

`implementation=COMPLETE`要求声明范围内代码/测试已完成；`correctness/resource=PASS`是进入下个GPU研究阶段的前提；`measurement=COMPLETE`要求冻结矩阵真实跑完；`promotion=QUALIFIED|DECLINED`由增益/回退线计算。只有QUALIFIED才能写入默认release enabled_features。

因此P10 ring-only可能正确、满足显存但速度不及MTP：必须记录DECLINED并保持off，但可进入P11测试检索是否改善。不能因缺GPU、缺资产、错误token、OOM而将measurement改为COMPLETE；这些依然BLOCKED。P11全部实验跑完却无增益时，交付“不采用”的实测结论是任务完成，不是性能通过。P12可以发布仅E1并明确实验功能未采用；所有研究task未跑则不能通过全扩展gate。
