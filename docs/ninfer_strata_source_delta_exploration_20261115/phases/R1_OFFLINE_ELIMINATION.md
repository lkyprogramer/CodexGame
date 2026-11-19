# R1 — 离线机会检查，允许零候选退出

依赖R0门；无需GPU/服务。T1与T2数据和文件独立，可并行；T3统一决策。

执行现有只读工具与新增工具代码是不同权限：`copy_replay.py`、`head_feasibility.py`及测试若尚不存在，需要单独CPU/离线开发授权和`implementation_approval_id`；本次文档授权不隐含修改仓库。没有授权则停在接口/数据需求清单，不运行未来CLI。

## R1-T1 D1来源/编辑回放

拟新增文件（已有等价H7工具则复用）：

- `tools/frontier/donor_delta_20261115/copy_replay.py`
- `tests/frontier/donor_delta_20261115/test_copy_replay.py`
- `runs/<id>/d1/{dataset_manifest.json,opportunity.json,cost_bounds.json}`

- [ ] 先写CPU反例fixture和失败断言，覆盖hash碰撞/重复相似函数/单多token插删/索引失效/accepted≠committed。
- [ ] 实现只读token trace回放；每条trace含model/tokenizer/prompt/output身份与原baseline轨迹；不能从运行中服务取新轨迹。
- [ ] B1与B2同source集合、同W、同max_drafts；B0始终是绑定的当前baseline。旧H1 ring另名H1_REF，仅做历史/离线参照，不重新申请H1 GPU窗口。
- [ ] 用冻结任务清单运行，报告所有case和holdout，不只算命中任务。
- [ ] 结合当前已合格成本数据估算真实skip与catch-up；无数据为null，不能过净益门。
- [ ] 最小测试：单元测试＋一份匿名真实trace读写/identity测试；合成case只检功能。

待实现CLI合同：

```bash
python3 -m unittest discover -s tests/frontier/donor_delta_20261115 -p 'test_copy_replay.py' -v
python3 tools/frontier/donor_delta_20261115/copy_replay.py --spec runs/ID/spec.json --traces runs/ID/input/traces.jsonl --out runs/ID/d1/opportunity.json
```

其中`ID`需替换为已冻结experiment_id；该CLI不得执行shell、加载CUDA/模型或自动调用生成API。未知W/语义/身份退出10；恶意/损坏输入退出12；无机会仍正常产出REJECT/NO_OPPORTUNITY，不作为工具异常。

## R1-T2 H2 head成本与资产账

拟新增：`tools/frontier/donor_delta_20261115/head_feasibility.py`、对应`test_head_feasibility.py`；产物`runs/<id>/h2/{asset_inventory.json,cost_bounds.json,feasibility.json}`。

- [ ] 从现有模型metadata及绑定源码取得真实V'/D/codec/group/remap；不加载GPU，不下载donor权重。
- [ ] 绑定当前head-only与AR分项原件；P14仅辅助，禁止填成当前占比。
- [ ] 计算sidecar/现存head/临时workspace/Graph及长context各峰值共存关系，范围不明则给上下界。
- [ ] 审核是否已有合法真实hidden数据、许可用途与保留期；没有数据只给静态可行性，不造recall数字。
- [ ] 若已有CPU可处理的真实hidden和原head数据，可获准做单一rank/k资产候选及oracle评估；不能安装/调用大GPU作业。
- [ ] 最小测试：字节单位、padding、重复计数、missing成本/shape拒绝、hash mismatch、峰值不能用free差替代。

待实现CLI：

```bash
python3 -m unittest discover -s tests/frontier/donor_delta_20261115 -p 'test_head_feasibility.py' -v
python3 tools/frontier/donor_delta_20261115/head_feasibility.py --spec runs/ID/spec.json --assets runs/ID/h2/asset_inventory.json --costs runs/ID/input/costs.json --out runs/ID/h2/feasibility.json
```

## R1-T3 淘汰与单候选决策

- [ ] 每个候选填写机制差量、历史重叠、当前证据等级、适用任务比例、净成本区间和未知项。
- [ ] 仅乐观上界不允许PASS；upper bound都过不了门则直接关闭。
- [ ] D1若只在copy任务成立就冻结copy-only范围和非copyfallback，不把故事/思考速度塞入结论。
- [ ] H2是旧H2接续，需要明确允许实施该细化；若用户后来已有等价测试，立即去重关闭。
- [ ] 两者都可行时优先更低风险/更少显存/更强证据的一条；把另一条DEFERRED，不并行修改两个机制。
- [ ] 两者都不合格，输出NO_QUALIFIED_CANDIDATE、保留baseline并结束本包，不进入R2。

## Phase gate

Reviewer查是否把扩大来源/宽度/省draft混为一因；Verifier从原trace与元数据独立重算机会/字节账。两者不得改holdout或阈值。CPU工具PASS但当前真实成本未知→BLOCKED；可提出R0-E0 baseline-only取证申请，见[R0](R0_BINDING.md)，不得在R1内自行启动GPU或以“先实现再测”绕过机会门。
