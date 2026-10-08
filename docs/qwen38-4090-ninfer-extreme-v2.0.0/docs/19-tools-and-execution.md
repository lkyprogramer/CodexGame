# 辅助工具：现在能运行什么，开发后运行什么

## 1. 立即可运行（不碰GPU/生产）

```bash
bash scripts/self_check.sh
python3 -m tools.preflight --out results/host-facts.json  # 在GPU主机采事实
python3 -m tools.source_audit /home/hhtele/ninfer-4090 --out results/base-source.json
python3 -m tools.cli artifact /data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer \
  --hash > results/artifact-inventory.json
```

示例重定向前先运行`mkdir -p results`。artifact hash会读18GB磁盘，不占GPU；不要每轮重复读取影响I/O。preflight在Mac跑会记录Mac而不是GPU事实，所以按角色执行。CPU工具只需Python3.10+（主机3.11满足），Java工具需JDK17，Pi工具在Mac。

## 2. 现有端点的独立probe

```bash
python3 -m tools.http_probe --url http://127.0.0.1:18441/v1 \
  --request configs/request-medium.json --out results/new-http.json
```

它真实发请求，默认不保存完整输出、仅指标和结构。结果中的客户端估算不作为GPU gate。engine round采集需要T02实装对应adapter，不能靠这个工具凭空获得AL。

## 3. 正式资格编排

复制`configs/qualification.template.json`，由T01/T16写入真实绝对命令、cwd、超时、新鲜evidence路径，并将`ready`置true。每个run使用新run_id和目录；已有evidence会被拒绝。**模板不可直接当完成的优化执行程序**。CUDA补丁未实现时，它应保持not ready。

GPU主机放好`tools/remote_guard.py`后，Mac运行：

```bash
mkdir -p logs
ALLOW_PRODUCTION_PAUSE=1 nohup bash scripts/run_qualification.sh \
  configs/local.json configs/qualification.local.json results/run-unique \
  > logs/run-unique.log 2>&1 &
tail -f logs/run-unique.log
```

runner打印`[i/N] START`与退出/证据状态，保存progress.json与SUMMARY.json。**EVIDENCE_COLLECTED不是测试通过**，必须运行各项真实numeric/quality gate；genericrunner不会替你判定CUDA正确。

## 4. 手动检查

```bash
python3 -m tools.cli rounds results/rounds.jsonl
python3 -m tools.cli gate results/qualification-facts.json
```

`gate`缺字段返回BLOCKED、退出2；即使候选通过仍只返回CANDIDATE_PASS_NOT_RELEASED，必须用户批准上线。必填字段见`contracts/qualification.schema.json`；2026-09-09新增`paired_n`（主桶配对数，<8→BLOCKED）与`aa_noise_abs`（A/A噪声底，>0.03→BLOCKED）；`capacity`门值为200192（`tools.metrics.PROTECTED_CAPACITY`）。`paired_summary`要求≥8配对（pilot可传`min_pairs`但结果`gate_grade=false`），`ci95_low`已是bootstrap与t区间中更保守者。

## 5. 不包含什么

本包没有编译好的CUDA改造、没有伪造DFlash2/lookup引擎adapter、没有训练权重和凭据。C++ header是待实现接口约束，CPU概率函数是数学参考。已有安全/harness代码均有单测，但SSH/Docker/systemd/真实Pi/GPU路径在生成环境无法验证，必须T01的维护演练和后续GPU门验证。

## 6. 长输入的可运行生成工具（可选依赖）

先在GPU host从只读artifact抽取约数十MiB tokenizer JSON，再scp到Mac，避免复制整个18GB模型。此操作不执行模型代码：

```bash
python3 -m tools.extract_tokenizer /data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer --out results/tokenizer.json
```

在隔离的控制端venv安装`configs/requirements-capacity.txt`，执行：

```bash
python3 -m tools.long_prompt --tokenizer results/tokenizer.json --tokens 196000 --out results/capacity-corpus
```

生成器给出精确**raw content** token数，不是chat template后的prompt数；最终必须读取服务端usage验证总长。含5个随机needle与非恒定代码片段，适合容量/检索，不适合拿复制型生成速度证明真实Agent吞吐。答案通常少于2048token，持续速度要另用实际任务输出足量样本。
