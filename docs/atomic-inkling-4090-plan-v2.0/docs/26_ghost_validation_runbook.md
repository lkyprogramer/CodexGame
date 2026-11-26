# 26 · Ghost增量测试、测量合同与复现手册

**状态：20项GX测试全部NOT_RUN。** 本篇定义未来在目标环境执行的测试，不把本次源码审计、作者CI或辅助工具测试混入GPU结果。原48项TC/QC/PF/SV继续有效，v1.1时总计划测试数68；v1.2另增AX28项，原有共96项；v2再增加LX/UX/MX，总数见当前test-catalog。

## 1. 新增测试目录

| ID | 场景与输入 | 必须满足的oracle/失败行为 |
|---|---|---|
| GX01 | main/tag/PR head、同名不同GGUF、不同binary/模板/dispatch、过期reference缓存、R/head/conv/pool几何错误 | 固定完整指纹；几何不符在launch前拒绝；未知路径BLOCKED；不能按basename或EXACT字符串授参考资格 |
| GX02 | 同资产R3，至少32短prompt，逐visit/slot中间态和最终logits | 首个偏差可定位；E/N分类与冻结容差一致；无共同资产时不生成同目标speedup |
| GX03 | 一个physical专家被不同loop/phase多次访问，部分冷热visit | 权重只计一次，trace保留visit维度；不能共享未授权KV/conv或重复计权重内存 |
| GX04 | 源布局、重编码、staging、双缓冲与graph同时存活 | 按真实bytes计峰值；110→134扩张正确；不把mmap/RAM释放等同实际PSS下降 |
| GX05 | 完整层、热度、成本评分三策略，固定与held-out trace | 预测收益和真实CPU/GPU关键路径分别记录；hit率提高不能单独PASS性能 |
| GX06 | 热度phase shift、循环热点不同、context增长挤压专家、未知hot文件 | 不读未来token信息；安全重新准入，最坏迁移/尾延迟有界；预算不足显式失败或合格回退 |
| GX07 | 每个换出/换入阶段注入取消、短读、OOM、旧lease/graph引用 | 只在event完成且generation一致后发布；半更新不可见，错误context退役 |
| GX08 | IQ3_S所有编码/符号/scale类、行/专家边界、padding、畸形block | dequant与约定dot逐值/逐结果核对；非法输入失败；布局身份和分配膨胀完整 |
| GX09 | 布局相同但activation/head/kernel归约方式变化，含near-tie logits | 存储E与计算N分开；KL/top1等采用原冻结容差；不能用局部bit-identical覆盖整条路径 |
| GX10 | prefill B1与各支持B，P=B-1/B/B+1、多个块、循环边界 | teacher-forced逐位置state/logit一致；固定relative bias、sink、conv/SWA与position |
| GX11 | expert分组后scatter、top-k重复边界、padding、稀疏路由与归约 | 输出回到原token/槽顺序；数值改变显式N类；sort/gather/scatter计入时间 |
| GX12 | 每个relay超时，尤其最后handoff；CPU异常、迟到ack、取消 | 错误sticky；没有污染logit/token/tool提交；错误epoch不可复用，预算内重建 |
| GX13 | 100次load/unload、capture失败、图更新、pool并发调用、worker退出 | 无活动地址被释放/复用；资源可回收；单调用者约束成立；host/GPU量测无持续泄露 |
| GX14 | A→B→A及A→B→C→A；前缀编辑、不同epoch/loop/codec | 恢复与重算的完整Inkling状态及后续输出按合同一致；不只检查KV长度 |
| GX15 | 大小会话混合、host预算边缘、快照驱逐、恢复峰值、复制途中失败 | 先reserve再copy再发布；预算覆盖weights/layout/staging/opening/live snapshot/保留量；失败释放预留 |
| GX16 | one-hot lookup proposal，采样含top-k/top-p/惩罚；接受/拒绝与恢复 | acceptance/residual使用实际过滤后p；proposal为确定性复制；一般draft不能套此特例；合成分布和GPU状态分开验证 |
| GX17 | 接受前缀每一位置遇EOS、max_new、emit取消；随后save/restore/续写 | 未commit后缀的KV/conv/controller/采样历史不泄漏；仅缩短pos不能通过；RNG按原事件合同处理 |
| GX18 | Inkling各真实head几何、short/global/SWA、sink/bias/softcap、Q4 codec切换 | 逐路径明确dispatch；不支持组合加载前拒绝；通用TC/Q4不冒充Inkling资格 |
| GX19 | held-out Java/copy-heavy/new-code/review/tool，短/64K/128K与冷热 | 平衡AB/BA、实际token、全部失败case、独立case统计；沿原G3/G4/G5/SLO门槛 |
| GX20 | 空fixture、缺pair、错误hash、只打印FAIL但exit0、缺usage、synthetic混入 | 比较器FAIL/BLOCKED且非零退出；缺token标null不可换成chunk；无原始证据不能授gate PASS |

GX02的32短prompt是机制定位最低覆盖，不替代原TC05或质量集；GX13的100次资源循环是增量压力检查，不替代G6的8小时运行。各适用测试只有真实执行且保留raw后才改变状态。

## 2. 需要新增的trace字段

| 类别 | 字段与口径 |
|---|---|
| 路由 | request/step/phase、physical layer、logical visit、expert ID、route weight、resident generation |
| 专家工作 | CPU/GPU选中数、命中/缺失数、每阶段时间、是否在critical path；同时保留wall time |
| 布局 | 源tensor hash/type、layout hash、原/新bytes、repack时间、peak host/device allocation |
| 搬运 | 实际H2D/D2H bytes与event时间、pinned占用、换入/换出次数、slot发布generation |
| 主机 | CPU线程运行/等待、RSS/PSS、major page faults、磁盘读取、NUMA/频率；不能仅凭逻辑read计SSD |
| 图与relay | shape key、capture/replay/update时间、buffer generation、relay ticket/ack/timeout/err、drain结果 |
| 快照 | 实际bytes、D2H/H2D/序列化、token边界、完整组件、命中/失效/驱逐原因 |
| 用户结果 | TTFT/首可见/首tool、reasoning/visible/tool tokens、queue、请求与Agent E2E、任务验收 |

字段进入T01原始事件日志及run `measurements`的扩展区域，单独写字段schema与单位。不能用NaN、0或空字符串冒充缺测；缺测为null+reason。采集开销单独测，禁用profile与启用profile各留对照。

## 3. 消融计划

每次只选一个实际瓶颈，不要求全部候选都进入实现。

| 实验 | A | B | 固定条件 |
|---|---|---|---|
| 驻留 | 已资格固定放置 | 循环/成本模型放置 | 同权重/格式/预算/context；不把更低精度混入 |
| 动态交换 | 最佳固定放置 | 滞回交换 | 同slot数、layout和trace采集；全部迁移计入 |
| 布局 | 原编码计算 | 精确runtime重排 | 同数学值/算术；若改变算术拆成另一个N实验 |
| Prefill | 已资格原B实现 | 同B专家分组 | 同token IDs、R、KV、P/N、预算；再独立探索B |
| Relay | 安全分段图 | 受控mapped候选 | 同CPU pool/放置；等待、超时、初始化计入 |
| Parking | 会话切换后重prefill | 完整host恢复 | 同任务与前缀，单active=1，同host预算 |

探索12pairs用于判断方向，确认≥30独立case、至少3时间块和10000次case bootstrap。保持原14的中位数/gmean区分、p95样本与CI、失败惩罚口径。跨引擎数字必须声明配置/数值差异；同模型文件不自动形成单机制因果对照。

## 4. 当前可运行与后续命令分开

### 4.1 PACK_READY：本包工具

```bash
python3 -B -m unittest discover -s tests -v
python3 tools/preflight.py --help
python3 tools/paired_stats.py --help
```

它们不执行Ghost或Atomic模型。测试仍是包内辅助工具的9项；GX是未来工程验收。

### 4.2 SOURCE_REFERENCE：固定Ghost参考构建

前置：目标机T00已核实AVX2/FMA、Rust、NVRTC/driver、磁盘和实验窗口。不要安装未知版本依赖或升级整机驱动来追求能启动；缺条件先BLOCKED。

在新的实验父目录运行：

```bash
git clone --no-checkout https://github.com/affifuddin-hazam/ghost-infer.git ghost-infer-reference
cd ghost-infer-reference
git checkout --detach b6cd02e099af2453f3674e047d5f89152f8a662d
git rev-parse HEAD
git status --short
RUSTFLAGS='-C target-cpu=x86-64-v3' cargo build --release --locked --bin ghost-infer
RUSTFLAGS='-C target-cpu=x86-64-v3' cargo test --release --locked --bin ghost-infer
sha256sum target/release/ghost-infer Cargo.lock
```

保存Rust/NVRTC版本、build日志、实际test/ignored数及binary hash。现有CI为84/6只是来源快照，现场数量不符时核对版本/target cfg，不能改预期让它通过。CPU构建成功仍不是CUDA成功。

### 4.3 SOURCE_REFERENCE：Inkling CLI诊断

G00必须先生成锁定的模型路径、同一模板处理后的token ID列表及安全资源profile。以下环境变量由执行者根据锁文件填写；不提供随意的token ID或漂移的模型下载命令。

```bash
: "${GHOST_MODEL:?Set the absolute path of the locked GGUF asset}"
: "${GHOST_PROMPT_IDS:?Set the exact comma-separated token IDs from the frozen fixture}"
: "${GHOST_RESERVE_MB:?Set the approved measured reserve for this profile}"
target/release/ghost-infer inkling-check "$GHOST_MODEL" "$GHOST_PROMPT_IDS"
GHOST_INFER_CUDA_ARCH=89 GHOST_INFER_INK_CTX=4096 \
  GHOST_INFER_INK_RESERVE_MB="$GHOST_RESERVE_MB" \
  target/release/ghost-infer inkling-gpu-check "$GHOST_MODEL" "$GHOST_PROMPT_IDS"
GHOST_INFER_CUDA_ARCH=89 GHOST_INFER_INK_CTX=4096 \
  GHOST_INFER_INK_RESERVE_MB="$GHOST_RESERVE_MB" \
  target/release/ghost-infer inkling-gpu-gen "$GHOST_MODEL" "$GHOST_PROMPT_IDS" 128
```

这些命令是已核查的Ghost CLI入口，但输出是诊断数据，不自动签发PASS。input+output必须在ctx内，G00保存actual token与截断信息。首次NVRTC编译、加载、热身单列。禁止直接把通用 `serve --kv q4 --draft ...` 加到Inkling入口，禁止把4096修改为131072就宣布P128K通过。

### 4.4 PLANNED_AFTER_T01：Atomic候选资格

以下工具由原T01实现，profile由对应G任务创建，当前包不包含这些实现：

先切回包含T01工具的Atomic实验工作树；上一节所在的 `ghost-infer-reference` 不含这些Atomic工具。`profiles/ghost-transfer-paired.json`由本次被选中的G任务创建并冻结，职责见25末节。

```bash
python3 tools/inkling-lab/lab.py validate --manifest profiles/inkling-prefill-grouping.json
python3 tools/inkling-lab/lab.py qualify --suite G2 \
  --manifest profiles/inkling-prefill-grouping.json --out evidence/G03-correctness
python3 tools/inkling-lab/lab.py run \
  --manifest profiles/ghost-transfer-paired.json --out evidence/ghost-transfer-paired
python3 tools/inkling-lab/lab.py compare \
  --baseline evidence/ghost-transfer-paired/baseline \
  --candidate evidence/ghost-transfer-paired/candidate --out evidence/ghost-transfer-compare
```

paired profile沿用pair-plan-example，包含各自能力key、共同AB/BA schedule、固定因素与允许差异。G2输出不作G3计时基线；compare必须读取真实新生成的成对目录。

## 5. 停止与收尾

source_present、author_report、ci_observed、target_measured是证据来源标签，不替换原run的evidence_kind。作者CPU CI以外部记录保存；本机CPU工具以cpu_reference/synthetic_test等真实类别记录；只有实际目标4090推理才能使用target_4090。

出现状态污染、错误tool提交、超时后继续commit、NaN、越界、预算失守或缺失真实输入计数，立即失败并保留现场。只对copy-heavy有效、微基准快但E2E无益、CI仅证明编译，均不能转为主力迁移PASS。

每个候选最终交付TASK、EXPERIMENT、必要的DECISION、原始run与gate记录。组合之前先完成单项资格；最终仍满足原G3/G4/G5/G6与当时G7授权，不以新增Ghost文档覆盖旧门槛。
