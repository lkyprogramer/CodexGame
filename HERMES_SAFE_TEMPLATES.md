# hermes-safe 固定模板

## 1. 目标

这份文档把你现在常用的 Hermes 调用方式，统一改写成更适合现网的 `hermes-safe` 模板。

当前默认前提：

- 模型：`openclaw/Qwen3.5-27B-UD-Q4_K_XL`
- endpoint：`http://127.0.0.1:18343/v1`
- `openclaw-executor` profile：
  - `64K`
  - `thinking=false`
  - `temperature=0.2`
  - 单槽

所以模板风格固定为：

- 目标明确
- 约束明确
- 输出契约明确
- 优先最小改动

## 2. 什么时候用哪种模式

- `--mode text`
  - 普通问答、代码建议、根因分析
- `--mode json`
  - 上层脚本或 agent 要机器消费
- `--mode readonly`
  - 对真实仓库做只读分析
- `--mode sandbox`
  - 让 Hermes 真改文件，但只允许在临时 workspace

一个简单判断：

- 真实仓库：默认 `readonly`
- 机器消费：优先 `json`
- 真写文件：必须 `sandbox`

## 3. 最小 smoke

### 3.1 最小可用性

```bash
hermes-safe run --mode text --query "Reply READY only."
```

### 3.2 最小 JSON

```bash
hermes-safe run --mode json --query 'Return strict JSON only. {"status":"ready","endpoint":"local"}'
```

## 4. 只读分析模板

### 4.1 仓库入口识别

```bash
hermes-safe run \
  --mode readonly \
  --cwd /path/to/repo \
  --query 'Identify the primary runtime entrypoint and the top 3 files I should read first. Return strict JSON only with keys runtime_entrypoint, top_files, and reasoning.'
```

适用：

- 新项目上手
- 快速找入口
- 建立阅读路径

### 4.2 最小 bug 根因定位

```bash
hermes-safe run \
  --mode readonly \
  --cwd /path/to/repo \
  --query 'Use terminal tools to inspect first. Do not modify files. Find the most likely root cause of the failing flow and propose the smallest safe fix. Output format: 1. Root cause 2. Evidence 3. Smallest safe fix 4. Risks'
```

适用：

- 先定位问题
- 暂时不改代码
- 需要最小修复建议

### 4.3 TypeScript / Node 跨模块分析

```bash
hermes-safe run \
  --mode readonly \
  --cwd /path/to/repo \
  --query 'Use terminal tools to inspect first. Do not modify files. Trace this TypeScript/Node issue across modules and identify the minimum safe patch. Return strict JSON only with keys root_cause, files, patch_strategy, and risks.'
```

### 4.4 Java / Spring 多文件分析

```bash
hermes-safe run \
  --mode readonly \
  --cwd /path/to/repo \
  --query 'Use terminal tools to inspect first. Do not modify files. Find the most likely root cause of this Java/Spring issue and propose the smallest safe fix. Return strict JSON only with keys root_cause, evidence, files, smallest_safe_fix, and risks.'
```

## 5. 结构化输出模板

### 5.1 严格 JSON 风险总结

```bash
hermes-safe run \
  --mode json \
  --query 'Return strict JSON only with this schema: {"root_cause":"string","confidence":"low|medium|high","files":["string"],"smallest_safe_fix":"string","risks":["string"]}'
```

### 5.2 严格 JSON 变更计划

```bash
hermes-safe run \
  --mode json \
  --query 'Return strict JSON only with this schema: {"summary":"string","files_to_change":["string"],"steps":["string"],"tests":["string"]}'
```

### 5.3 导出结果文件

```bash
hermes-safe run \
  --mode json \
  --query-file /path/to/prompt.txt \
  --output /tmp/hermes-safe-plan.json
```

## 6. 终端 / shell 模板

### 6.1 当前目录与状态

```bash
hermes-safe run \
  --mode readonly \
  --cwd /path/to/repo \
  --query 'Use terminal tools only. Do not modify files. Run pwd and git status --short. Return exactly 2 lines: PWD: <path> and STATUS: <summary>.'
```

### 6.2 搜索关键符号

```bash
hermes-safe run \
  --mode readonly \
  --cwd /path/to/repo \
  --query 'Use terminal tools only. Do not modify files. Find where RuntimeMetrics is produced and consumed. Return strict JSON only with keys producers, consumers, and notes.'
```

### 6.3 日志归纳

```bash
hermes-safe run \
  --mode readonly \
  --cwd /path/to/logdir \
  --query 'Use terminal tools only. Do not modify files. Inspect the relevant log files and return strict JSON only with keys symptom, frequency, likely_root_cause, and next_check.'
```

## 7. 写脚本模板

这些场景不需要先让它探索整个仓库，直接走 `sandbox`。

### 7.1 写一个 Bash 脚本

```bash
hermes-safe run \
  --mode sandbox \
  --workspace /path/to/workspace-template \
  --query 'Create a small standalone Bash script named triage.sh that scans .log files under the current directory and prints filename plus ERROR count. Keep it minimal.' \
  --validation-cmd 'bash -n triage.sh'
```

### 7.2 写一个 Python 小工具

```bash
hermes-safe run \
  --mode sandbox \
  --workspace /path/to/workspace-template \
  --query 'Create a minimal Python script that reads replay.jsonl and prints per-session turn counts. Keep the output deterministic and the implementation simple.' \
  --validation-cmd 'python3 script.py < sample.jsonl'
```

## 8. 最小改文件模板

### 8.1 修一个明确文件里的 bug

```bash
hermes-safe run \
  --mode sandbox \
  --workspace /path/to/workspace-template \
  --query 'Modify app.py to fix the bug with the smallest safe change. Do not refactor unrelated code.' \
  --validation-cmd 'pytest -q'
```

### 8.2 多文件最小修复

```bash
hermes-safe run \
  --mode sandbox \
  --workspace /path/to/workspace-template \
  --query 'Fix the bug across the provided files with the smallest safe change set. Preserve public behavior except for the bug fix. Keep file edits minimal.' \
  --validation-cmd 'pytest -q'
```

### 8.3 生成可消费的修复结果

```bash
hermes-safe run \
  --mode sandbox \
  --workspace /path/to/workspace-template \
  --query 'Fix the issue with the smallest safe change. At the end, summarize exactly what changed and why.' \
  --validation-cmd 'pytest -q' \
  --output /tmp/hermes-safe-fix.json
```

## 9. openclaw 场景推荐模板

### 9.1 Executor 风格只读诊断

```bash
hermes-safe run \
  --mode readonly \
  --cwd /path/to/repo \
  --query 'Use terminal tools to inspect first. Do not modify files. Focus on the smallest safe fix. Return strict JSON only with keys root_cause, files, smallest_safe_fix, and risks.'
```

### 9.2 Executor 风格沙箱修复

```bash
hermes-safe run \
  --mode sandbox \
  --workspace /path/to/workspace-template \
  --query 'Fix the issue with the smallest safe change. Keep the output concise. Do not refactor unrelated code.' \
  --validation-cmd 'pytest -q'
```

### 9.3 Executor 风格脚本编写

```bash
hermes-safe run \
  --mode sandbox \
  --workspace /path/to/workspace-template \
  --query 'Write a small standalone script for this task. Keep the implementation simple, deterministic, and easy to review.' \
  --validation-cmd 'python3 -m py_compile script.py'
```

## 10. 实际使用建议

当前这套 `hermes-safe + openclaw-executor`，最稳的工作流是：

1. 真实仓库先走 `readonly`
2. 确认根因和最小修复方案
3. 把相关文件复制到临时 workspace
4. 再走 `sandbox`
5. 用验证命令收口

不要默认一上来就让 Hermes 直接写真实仓库。

## 11. 不推荐的写法

对当前模型和当前 Hermes 封装，不推荐默认这样写：

- “随便看看这个项目然后帮我改”
- “把整个模块重构一下”
- “想怎么改就怎么改”
- “一边探索一边直接修改真实仓库”

更稳的做法永远是：

- 明确模式
- 明确范围
- 明确输出契约
- 明确验证命令
