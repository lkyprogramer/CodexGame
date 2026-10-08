# Qwen3.8-27B / RTX4090 · NInfer Extreme v2

**本包采用 Claude 的“回到 NInfer 增量优化”方向，并修正其宽度、E8、Sage、质量证据和性能推算问题。它是AI开发与验证执行包，不是已经实现的CUDA补丁或推理引擎。**

基线：单RTX4090，Xeon4216/PCIe3x16，62.5GiB RAM，915GiB NVMe（最近557GiB可用），KMD610.57.04/UMD13.3，宿主CUDA12.3、容器13.2。Pi与Java工具在Mac。生产NInfer44a、rk4v4-e8、MTP3、262144窗口保持不动，作为基线与回滚点。

**2026-09-09 修订**：经实机只读复核与用户决策，候选profile的**受保护容量为200192**（不是生产的262144），GPU主机sudo/journal/模型目录权限已配置并验证，DFlash2 W8显存账、44a会话持久化缺口、已有采样/遥测能力、Suffix链延长方案、统计门与筛选预算均已写回包内。事实基线见[docs/22](docs/22-machine-verified-facts-and-revisions.md)，与其他文档冲突时以它为准。

## 先读

1. [审计结论](docs/00-review-and-decision.md)
2. [实机复核事实与决策记录](docs/22-machine-verified-facts-and-revisions.md)
3. [机器与控制端](docs/01-machine-topology.md)
4. [架构与状态](docs/03-architecture-and-state.md)
5. [AI入口](AGENT_START.md)
6. [任务DAG与执行计划](docs/17-ai-execution-plan.md)

## 路线

```text
事实/证据/安全链路 → 同口径控制实验（rk8@200192 对照 + 现成DFlash2机会测量）
       ├─ Suffix链延长 + 现有MTP（v1零bridge，W≤6；首选小增量）
       ├─ T07 W8路径收益门 → DFlash2独立迁移（companion/算子/状态事务/会话持久化）
       └─ 实测热点 → W16 / d256 Prefill
                        └─ A4仅独立高风险研究
```

不是所有分支都必须实现。达不到收益就提交失败证据并停，不能为了“极致”引入更多未验证复杂性。受保护容量200192；rk8v4与DFlash2 W8争同一块≈1.6GiB显存，200192下二选一（docs/22 §3.3）。

## 立即执行（不占GPU）

```bash
bash scripts/self_check.sh
cp configs/local.example.json configs/local.json   # pi_bin 已是 Mac 真实路径 ~/.nvm/versions/node/v22.19.0/bin/pi
python3 tools/next_task.py
```

本包CPU工具只用Python标准库。Java原题需JDK17+。`tools/preflight`在GPU host运行；Pi runner在Mac。原23个Java夹具文件逐字节保留；另有30道由实际JDK执行得到答案的语义QA。GPU主机的sudoers（仅`systemctl stop/start openclaw-qwen38-ninfer.service`免密）、`systemd-journal`组、vLLM W4目录属主已于2026-09-09配置并验证（docs/22 §1.2），T01不再被此阻塞。

## 交给开发AI

读取`PROMPT_FOR_AI.md`并遵循`AGENT_START.md`。每个task独立diff/测试/证据。先做CPU，GPU维护需批准并走lease；控制AI不能依赖即将停掉的本机模型。

## 开发后的一小时筛选

T01/T16写好真实adapter与local资格计划后：

```bash
mkdir -p logs
ALLOW_PRODUCTION_PAUSE=1 nohup bash scripts/run_qualification.sh \
  configs/local.json configs/qualification.local.json results/run-new \
  > logs/run-new.log 2>&1 &
tail -f logs/run-new.log
```

模板`ready:false`是有意的：没有新引擎实现时不会停生产或伪造成功。既有HTTP和Java探针可以对授权端点独立执行，见[工具说明](docs/19-tools-and-execution.md)。

## 证据与交付边界

- 两份Claude文档与五份关键评测报告保存在`input-review/`，保留原始hash/脱敏说明。
- `[Sxx]`指向[外部源台账](references/SOURCES.md)。[逐条审计](references/CLAIM_AUDIT.md)区分支持、修正与未知。
- `validation/`仅是本包CPU、夹具和静态验证记录；GPU全部NOT_RUN。
- 代码退出0只表示该命令成功，不是完整资格通过；缺任何必须证据就BLOCKED。
- 最终工具只给CANDIDATE_PASS_NOT_RELEASED，不自动切换生产。

不包含模型权重、凭据、完整旧源码树、生成过的CUDA二进制或未经本机验证的性能承诺。

## 本次交付校验

[生成物验证记录](validation/GENERATION_REPORT.md)：原始生成时66项CPU单测、23个原题文件hash、3题失败/临时修复对照、30个Java语义JDK求值；生成时GPU、真实SSH与Pi均NOT_RUN。

2026-09-09修订后：`scripts/self_check.sh` 74项CPU单测在macOS/Python3.14通过（含修正后的`safe_child`路径解析）；`check_bundle.py` DAG/夹具/链接通过；GPU主机只读SSH复核与sudo验证见docs/22。GPU实验仍未运行。
