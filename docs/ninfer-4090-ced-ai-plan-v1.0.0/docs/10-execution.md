# 10 AI 执行手册与最小协作流程

## 1. 第一轮必须做的动作

读取00、AGENTS、01、03、07和当前Phase；运行本包结构校验；明确“这是计划，不是已有代码”。然后执行P0。用户此轮仅要求计划包，不等于已经授权实际停止生产。

```bash
export PLAN_ROOT="$(pwd)"
export LAB_ROOT="${LAB_ROOT:-$HOME/experiments/ninfer-ced-20260911}"
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
python3 "$PLAN_ROOT/tools/validate_package.py"
python3 "$PLAN_ROOT/tools/planctl.py" show P0
```

P0的resolved配置才是后续工具输入，不能直接把蓝图experiment.json当成已探测主机事实。production pause默认false；缺授权不自动停服务。

## 2. 任务粒度与并行边界

每个Task是可独立审查的交付单元。先写具体反例测试→开发→局部验证→提交集成分支。所有Task合并后跑一次完整Phase Gate。局部单测不等于提前跑全量Phase，也不等于可以忽略明显错误直到最后。

CPU侧可并行：文档/训练reader/fixture/报告工具；共享runtime文件只给一个owner。GPU工作全部由一个队列串行执行，Teacher/训练/真实模型验证也不同时进行。不能由每个subagent各自启动27B容器。

建议角色为Runtime、Kernel、ML、Evaluation、Integrator；同一个AI可以依次承担。没有多agent工具就顺序执行，不为流程完整而伪造worker。

## 3. Source与实现偏移

执行固定44a2c6c副本。若本地来源不同，P0生成diff摘要，继续使用固定baseline可复现源，不在工作中途自动merge最新上游。对`@source_map`键必须读实际调用方后定位；不能猜名字新建一个没有接入的“相似文件”。

代码架构允许为完成目标做必要调整，但本包以现有shared Program/family/target leaf分工为默认。不要为了这次实验改造整个engine成通用模型框架。

## 4. 每次worker接到Task的完整上下文

给worker：该Task完整章节、03接口、依赖Task的已提交接口和产物、允许修改文件、local测试命令、禁止项。不能只给“实现P2”或上一轮聊天的模糊摘要。

共享新增接口先由owner提交再派发依赖任务。worker返回：commit、files、合同、local检查、已知限制、是否请求GPU排队；Integrator复核实际diff，不只信总结。

## 5. Phase Gate

准备同一candidate build与Predictor；确认数据split及threshold lock未变；运行11定义的统一命令。查看raw输出、非空case count、exit77/skip、timings和恢复检查。按templates填写报告，不以AI的主观“看起来不错”替代自动断言。

Gate=PASS后才能推进。P3的PASS仅表示prequalified learnability，不是可部署；P6的PASS可能仅private_opt_in。具体资格域必须保留。

## 6. 重启与接力

换会话后读取最新gate.json和task-record，不从自然语言“都开发好了”推断完成度。验证source/binary/predictor/config hashes与证据匹配，再显示下一可运行Task。

计划附带planctl只导航，不是engine验证器。后续P0实现的run_phase才负责执行与证据完整性；任何工具都不能凭JSON status证明GPU真实运行，需同时核对日志和产物。

## 7. 什么时候停止

无授权、GPU不可用、磁盘不足、依赖无可复现版本：BLOCKED并交付当前证据，不循环等待。数值/训练/质量不合格：FAIL/NO-GO，按09有界修复。P7未通过仍可交付P6最优档，不因“计划写了32/32”而强行完成。

## 8. 结束时给用户的内容

首先交付当前实物/报告，然后列最高通过Phase、有效配置、真实提升与质量差、限制和生产是否恢复。只给一个明确下一动作，不附带多个无关优化项目。不能承诺后台继续训练或稍后自动送结果。
