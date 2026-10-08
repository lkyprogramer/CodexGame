# Mac 上的 Pi / Java 测试与原夹具复用

## 1. 题目没有替换

`fixtures/java-agent-{1,2,3}-*`的23个文件直接来自附件`docs/qwen38-4090-vllm-extreme-v1.0/fixtures`，每文件SHA在`references/fixture-lock.json`。不是上轮Kern PoC的新题。与报告WORK/NInfer/vLLM可比较的核心任务继续使用这三题。JDK17必需：原题已有record，不假装JDK8可编。

## 2. Mac配置

`configs/local.example.json`记录Pi binary、Node22 PATH、隔离Pi配置目录、SSH目标、remote_guard和本地隧道。复制后修正**本机真实路径**（2026-09-09实测：Pi在`/Users/luo/.nvm/versions/node/v22.19.0/bin/pi`，v0.85.1，`--approve/--thinking/--tools/--no-skills`均存在；`~/.pi/bin/pi`不存在）。不要写密码/API token。`PI_CODING_AGENT_DIR`只改变Pi配置，不是操作系统sandbox。`configs/pi-models.example.json`的`contextWindow`为200192，与受保护容量一致。

先保存`pi --version`/`pi --help`，检查现有flag（`--print --mode json --no-session --no-extensions --no-skills --tools ...`）。已知旧脚本含`--approve`，若当前版本没有该flag，在任务T01更新锁和profile，而不是静默删掉安全约束。

Pi连接实验兼容端点18441；上游真正的medium设置、top_k/top_p/temperature由统一request normalization验证。旧脚本中Pi `--thinking off` + 服务端medium可能是历史兼容技巧，不直接拿来作为新公平测试。以**引擎收到的渲染后有效参数**为准，对照双方一致，冲突返回错误并修配置。

## 3. 执行与统计

```bash
python3 -m tools.java_runner --config configs/local.json --out results/new-run/java
python3 -m tools.qa_runner --url http://127.0.0.1:18441/v1 \
  --model qwen3.8-27b-lab --out results/new-run/java-qa
```

java_runner在新目录复制题目，Pi只修改production code；结束比对原test/verify.sh SHA，然后建立一份控制端原始测试副本，只拷回候选production code重新验证。symlink拒绝。记录Pi退出、测试退出、sourcechanged、protected_ok、elapsed。通过stdout“测试成功”不算。

30道附加Java语义题由本包实际JDK编译执行得到答案，覆盖整型溢出/类型提升、BigDecimal、Atomic/ConcurrentMap、重试计数、时间单位、集合视图、Optional等。它们是可自动评分的语义holdout，不能替代原工具loop，也不能单凭30/30证明全能力等价。预期答案不发送给模型；调参不许在这些答案上选模型。

## 4. 长Agent不是重复短任务

定向soak在**同一session**连续进行：读设计文档/源码→grep→修改→compile/test→读取错误→修复→提出新增约束→再测试。保存每轮请求与parent/branch关系，用来区分append和真实rewrite。三题各自新会话用于独立成功率，soak用于状态连续性；二者报告分开。

至少覆盖：工具结果在历史中保留（不重读）；再次read同文件形成新token（不能假定KV能按路径去重）；新增日志长块；取消后重试；最近reminder改写；session A/B/A。不同session的回退不是相同slot的普通append。

## 5. 安全限制

提供的Java runner是可信本地实验工具，不是对抗恶意Agent的安全沙箱。使用脱敏小项目、无生产凭据的进程环境；需要强隔离时由控制端在受控VM/容器工作区运行Pi。不能因为保护了test哈希就声称模型无法访问主机文件。
