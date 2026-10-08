# 05 每个 Phase 结束后的统一测试

## 1. 执行原则

每个Phase的所有开发Task先完成局部编译/单测，合并到**同一个集成提交**，再运行完整phase suite。Gate只对这个提交、这个Predictor、这个环境成立。开发任务的绿色状态不能代替阶段验收。

完整流程：CPU契约→GPU算子→真实制品→阶段专项→A/B性能→恢复检查→人工/独立AI复核证据。GPU相关步骤在一个独占维护窗口串行执行；不允许candidate与oracle同时常驻。

## 2. Gate 状态

| 状态 | 含义 | 是否允许推进 |
|---|---|---|
| PASS | 所有required检查有非空证据且通过 | 是 |
| FAIL | 已运行且至少一项失败 | 否 |
| INCONCLUSIVE | 波动、统计证据不足、观察无法归因 | 否；可缩小声明范围 |
| BLOCKED_RESOURCE | 缺GPU/权限/磁盘/依赖/制品 | 否 |
| NOT_RUN | 未执行 | 否 |
| SKIPPED_OPTIONAL | 仅可选P7或非资格化范围未做 | 不能替代必需Gate |

退出码约定：0=PASS；2=FAIL；3=INCONCLUSIVE；4=BLOCKED_RESOURCE。78或77之类上游skip都必须转换为“未得到证据”，不能让外层命令以0伪报成功。

## 3. 测试层级与归属

| 层级 | 内容 | 首次必需阶段 |
|---|---|---|
| Contract | split区间、shape、布局、cache来源、cli验证 | P1起，每阶段 |
| Oracle injection | 相同encoded state + 相同schedule | P1；P5扩展MTP再做 |
| Numerical Op | StateOnly独立FP64 oracle + native误差带 | P2 |
| Training | 数据隔离、shuffle、checkpoint重载、数值收敛 | P3 |
| End-to-end no-spec | CED16→tail→首token→连续decode | P4 |
| Engine integration | MTP、cache、cancel、checkpoint、restore | P5 |
| Agent quality | patch、compile、tests、tools、长上下文 | P6 |
| Split progression | CED24、CED32各自完整回归 | P7A/P7B |
| Delivery | off默认、文档/启动/恢复、制品身份 | P8 |

## 4. 数值检查

**Teacher injection：**在相同kernel路线、dtype、chunk与确定性设置下，注入张量必须字节相同；原生off路径不得改运算序列。若首token不一致，先定位第一处分歧，不以“浮点正常波动”直接忽略。允许不同执行算法的误差只在显式新numerical profile中讨论。

**StateOnly：**每fixture同时计算FP64 oracle、native GDN final state、新StateOnly final state。定义NRMSE=`||X−Y||₂/max(||Y||₂,1e−8)`。建议准入：`E_new <= max(1.1*E_native, 1e-4)`；最大元素误差建议按 `A_new <= max(1.1*A_native, 8*eps32*max(1,max(abs(S_oracle))))`，其中 `eps32=1.1920928955078125e-7`。NRMSE与绝对误差两项同时满足，阈值在P0冻结。不能用重新拟合阈值掩盖某一层恶化。

覆盖T={1,2,3,15,16,17,31,32,127,128,129,1023,1024,1025,2048}；zero/random/large state；small/large key；beta0/1；g0/强负；非零conv历史；head grouping；完全alias/无alias/非法partial alias；tail截断；canary内存。大T只在已验证profile测，别让test因尺寸过大进入未知fallback。

**Learned approximation：**不要求bitwise，但必须报告逐层state误差、Teacher-forced同token序列下full-vocab KL、NLL差和任务正确率。采样自由rollout分叉后不能把两个不同token前缀的logits直接作KL。

## 5. 统一性能 Gate（研发门槛）

| 项目 | 目标/失败线 |
|---|---|
| `off` 路径 | p50 TTFT / decode不劣化超过3%；置信区间或噪声不足则INCONCLUSIVE |
| CED16冷prefill | 64K和128K各自p50 TTFT至少1.10×，配对bootstrap95%下界>1.00×；1.15×为stretch目标 |
| 200K | P6必须有真实输入200000token+明确输出余量，不能用短输入配置max-context冒充 |
| decode | 同MTP模式、sampling、context下≥native的95%，且≥20tok/s；若MTP接受率改变则以端到端综合判定 |
| hot cache | p50≤native×1.03，p95≤native×1.05；restore状态和warm方式相同 |
| Agent端到端 | cold/large-append目标中位完成时间≥1.05×；所有成功/失败/超时均计入，不仅统计成功快样本 |
| 资源 | candidate峰值仍有≥512MiB实测GPU余量，无OOM/swap风暴，保留native262144能力 |
| 失败/回退 | 性能样本所有fallback计成本；基准campaign出现未解释fallback不能宣称达标 |

上述性能和统计评估必须同配置配对。原型GDN benchmark更快不能单独解锁发布。

## 5.1 P3 可学习性准入线（不是部署质量保证）

为避免“有正向信号”成为主观判断，P3先采用以下可执行研发门槛，并在P0冻结：未见group的加权validation loss同时≤未训练初始化模型的80%、≤按训练集通道均值预测的80%；32K和64K free-running state NRMSE的p95≤0.50；64K p95误差 / max(32K p95误差,1e−6)≤2.0；所有层无NaN/Inf。通道均值baseline不能读取validation/test统计。

这些阈值只是决定是否值得接入P4，绝不等同“近似足够准确”。P4/P6实际任务失败时不能援引P3 loss通过作为豁免。达到数据/rank上限仍过不了则NO-GO。

## 6. 质量决策线

P4：至少24个未见过的smoke任务；schema、编译、精确检索等关键可验证项不出现baseline成功而candidate失败。通不过就停在P4，不开展MTP优化。

P6：24个独立Java/Pi任务×3 seeds、12类长上下文fixture×指定位置/长度，以及原生协议回归。总完成率观察差不低于−2个百分点，且关键数据/patch/tool用例不得出现新增可复现回归。小样本只允许“限定场景实验通过”，**不能声称能力无损或统计学等效**。

统计证据不足但观察Gate通过时，P6可标记 `PASS scope=private_opt_in`；`production_quality_proven=false`。需要更强证据时按06中的单侧退化率上界扩展独立任务。不得将private Gate偷换成生产默认启用资格。

## 7. 每阶段最低证据

`run_manifest.json`、`test-results.json`、`metrics.jsonl`、`gate.json`、`phase-report.md`。保存命令argv（脱敏）、exit code、actual test count、skipped列表、source/build/predictor/base SHA、toolchain和GPU信息、sampling/chat模板、实际token长度、随机seed、原始计时。

为Task重新编译或训练新checkpoint后旧Gate自动失效。A/B试验顺序使用固定seed打散，以ABBA/BAAB方式减小温度漂移；native和candidate分别预热且清理实验cache，不动用户生产cache。

## 8. 重验和失败停止

每个Phase可针对明确根因做最多两轮修复→重跑失败项+受影响回归→最后完整Gate。根因涉及前一Phase合同必须回退重开该Phase。出现数据泄漏、Teacher误用、来源混用或生产保护失败，先修证据链，不继续跑更多性能样本。

长测前preflight失败直接退出；不在用户没授权的情况下安排后台任务或持续等待GPU。异常退出执行恢复，恢复失败清楚报告，不吞异常。
