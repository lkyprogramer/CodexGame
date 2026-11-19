# R0 — 身份、历史与准入绑定

前置：只读访问已获准；硬件/HTTP预算仍0。产物路径相对于LAB_ROOT；以下新CLI是待实现接口，不是本包已带脚本。若已有等价工具，绑定后复用。

只读核查许可不包含新增工具代码。若现场缺`audit_inputs.py`等adapter，必须先取得`implementation_approval_id`对应的CPU/离线开发授权，再按最小失败测试→实现→验证执行；未批准时仅生成手工绑定清单/规格并BLOCKED，不替用户改仓库。

## R0-T1 当前身份与能力矩阵

文件：`runs/<id>/binding.json`、`runs/<id>/source_inventory.json`；如确缺读取器，拟新增`tools/frontier/donor_delta_20261115/audit_inputs.py`及其CPU测试。

- [ ] 读取本包source_lock与目标仓库AGENTS；只读记录git HEAD、tree、dirty diff、编译参数、目标sm、binary hash。
- [ ] 若将复制donor实现而不仅借设计，绑定各自LICENSE/NOTICE及兼容性审阅；未经确认不搬代码/二进制。不得推定所有项目使用同一许可。
- [ ] 区分公开b0、P3/P4隔离候选、用户实际服务；缺当前binary/model信息不自动启动服务取证。
- [ ] 记录模型/草稿头/tokenizer/remap/KV codec/context/W/K/采样/Graph/cache模式。CPU/驱动/功耗上限以既有记录或获准只读查询绑定。
- [ ] 为所有未知填null＋reason，禁止用donor或历史值覆盖。
- [ ] 最小验证：40位SHA格式、binary/model散列格式、字段类型、null身份不能PASS；文件不含token/key/private prompt。

建议只读命令（变量必须先从已批准binding确定，不使用默认HOME）：

```bash
git -C "$delta_source_root" rev-parse --verify HEAD
git -C "$delta_source_root" status --porcelain=v1
git -C "$delta_source_root" show --no-patch --format=fuller HEAD
```

上述仅核源码，不能证明线上运行身份。`audit_inputs.py --spec <spec.json> --inventory <inventory.json> --out <binding.json>`拟返回0=绑定成功、10=缺身份、12=历史/合同冲突；不得启动引擎或补下载。

## R0-T2 历史差量台账

文件：`runs/<id>/history_delta.md`，不改旧台账原件。

- [ ] 九条NInfer路线、Strata关闭项逐条映射；保留局部成功与整链失败的区别。
- [ ] 查后续H2/H7/W16/DF2是否另有回执；未找到只写SOURCE_UNBOUND。
- [ ] P14 coarse attribution已有、export修复已CPU实现，避免从头开发。
- [ ] 对D1分别列planner、source集合、skip和width；H2写已有计划细化。
- [ ] 最小验证：每个old_route_id有固定来源和scope；没有“所有lookup都失败/从未做过H2”等越界结论。

T1/T2可并行，不能共同修改spec。

## R0-T3 K-PAIR / M0只读卡

文件：`runs/<id>/pair_gap.json`、`runs/<id>/maintenance_m0.md`。

- [ ] K-PAIR：绑定P3/当前small-T route、Q4/Q5成员、编译宏、launch与graph节点；明确sm89禁用PDL。
- [ ] 没有最终P3源就SOURCE_UNBOUND，不写“当前尚缺融合”。
- [ ] M0：查当前二进制是否包含stop-bound CUDA路径；复用已有helper测试原件，不再复制。
- [ ] 核“remaining不足＋窗内EOS＋next turn不fallback”的既有精确回执；没有则只给维护卡。
- [ ] 最小验证：当前路径存在性/实际guard与固定URL；没有任何GPU/HTTP操作。

## R0-T4 冻结合同

依赖T1–T3。文件：spec/budget/decision副本；不得改模板冒充run。

- [ ] 确定研究适用family、实际baseline、唯一候选变量和明确排除项。
- [ ] 绑定controller、OwnedServer、oracle、stats工具的实际版本/入口；其不存在时停止，不在本包补整个平台。
- [ ] 同意数据权限与脱敏范围；静态代码读取不等于真实hidden导出许可。
- [ ] 冻结R1数据清单、开发/holdout划分及机会门。GPU approved仍0。
- [ ] 最小验证：不完整模板必须被拒；只有完整spec可继续离线工作。

## Phase gate

Reviewer独立查重复探索与身份；Verifier只复核文件/hash/schema/guard。输出`reviews/R0_review.md`与`R0_verification.md`。任一关键身份未绑定→BLOCKED，不让实现者以“先试试”跳过。K-PAIR/M0单独UNKNOWN不必阻塞完全独立且已绑定的D1/H2，但不得给它们性能预算。

## R0-E0 可选分支：仅采集baseline证据

这是解决R1缺当前head/mandatory-draft/catch-up基准成本或真实轨迹的**独立申请入口**，不是隐含权限，也不是候选试跑。现有合格原件充足则跳过。没有数据时也允许直接BLOCKED交接，不强迫采集。

前提：已绑定baseline身份；原foundation测量能力存在且可按其合同资格；用户另批准数据用途、硬件和存储。使用独立`experiment_id`与BudgetLedger；候选D1/H2均关闭，W/model/codec等不变，不改旧H1/H3，不比较candidate或扫描参数。

建议上限仅用于审批：2次engine、6请求、8192生成token、20分钟GPU窗口；storage cap执行前填定。只采预注册的baseline路径/真实数据，必要on/off检查沿旧foundation资格，不以小样本必然可通过。R0-E0不得借R3/R4额度，失败不自动续。

输出当前有效identity、匿名trace/hidden授权范围、head-only/AR/mandatory维护等可测字段与误差；无法直接测的candidate catch-up仍为UNKNOWN，不能通过“baseline没此开销”填0。若对catch-up没有可审的安全成本界，D1-S继续BLOCKED，不能为了取证先改Candidate。

独立Reviewer/Verifier检查观测、隐私、身份与预算；合格原件只回填R1，不直接进入R2。若测量底座本身未实现，回到旧foundation的相应开发/授权任务，本包不另建collector。当前R0-E0批准额度仍0、未执行。
