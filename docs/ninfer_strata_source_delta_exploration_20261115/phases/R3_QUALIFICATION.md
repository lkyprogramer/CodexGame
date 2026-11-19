# R3 — 数值、状态、服务与观测资格

前置：R2门、用户明确硬件窗口、非零approved预算、OwnedServer身份、GPU独占、合格baseline与oracle。本文所有动作目前NOT_RUN。

## R3-T1 最小模型/状态资格

建议只选一个固定candidate配置；不能在资格失败后扫rank/k/W。调用既有harness/OwnedServer，入口由R0绑定；本包不增加第二套service launcher。

- [ ] 运行前核exactbinary/model/config/clock/memory并记录；不匹配不运行。
- [ ] 默认关闭A先资格；C只改已批准变量。H2diagnostic双算是资格模式，不作性能数据。
- [ ] 沿原数值oracle比较Target/选中head行、greedy tokens与混合状态；首/中/末拒绝、EOS、remaining<W、cancel是最少边界。
- [ ] D1覆盖copy→MTP fallback、连续copy、编辑/相似源；验证实际未执行proposal与catch-up，不以CPU布尔证明。
- [ ] H2覆盖sidecar匹配、低频/中日韩/工具token、fallback、Graph复用；Target完整词表不变。
- [ ] 短追加、save/restore、下一请求cache状态沿旧服务合同验证；无合法同身份证据不得继承PASS。
- [ ] sampled未单独获准/证明时确认实际走baseline；不要把它“临时开一下”当无成本测试。

所有state差/NaN/污染硬停止，不继续性能。取消/超时/OOM记录并计预算。

## R3-T2 观测中性与容量

- [ ] 使用原collector相同身份的observer资格；若原资格不适用，执行获批on/off配对。
- [ ] 回放相同合法输入，trace确认分支/Graph/catch-up，正式速度只使用off。
- [ ] 记录prefill/decode/restore峰值、host RAM、sidecar/scratch生命周期；原context capacity与安全余量保持。
- [ ] 校验事件掉失、unknown、跨时钟关系和overlap；不把duration总和当whole round。
- [ ] 仅trace看起来快不能升级候选；新增同步或observer超门需停止/修复后另审，不复用污染样本。

## R3-T3 有界预试

使用R3剩余明确预算与预先指定case，最多一个A/C预试；不用于最终CI，也不据此挑正式holdout。报告完整round成本/正式token、请求wall、TTFT、质量/失败与资源。

若预试只有局部head/planner快而整round不改善，或copy-only之外回归，关闭本适配。不可扩大W或减context挽救。无足够额度则INCOMPLETE，不能借R4配对填R3资格缺口。

## M0维护路径分离

M0不是D1/H2候选，若另获维护授权，在自己的experiment_id/budget执行已列精确continuation卡。已有helper单测复用；验证末轮committed input rows、next token与后续fallback原因。不能把M0修复顺便加入C，使性能比较变成多因素。

## Phase gate

Reviewer独立核数值/state/sampler证据；Verifier核raw/identity、观测中性、资源及全部失败。输出`NUMERIC_QUALIFIED`、`STATE_QUALIFIED`、`SERVICE_QUALIFIED`、`OBSERVER_QUALIFIED`四项，不把它们合并为性能PASS。只有全部要求成立才可申请R4，不自动获授权。
