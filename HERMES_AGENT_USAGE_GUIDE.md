# Hermes Agent 使用范式与 Prompt 模板

## 1. 目标

本文档面向当前 4090 上的 Hermes CLI 使用场景，重点是：

- 默认模型：`openclaw/Qwen3.5-27B-UD-Q4_K_XL`
- 默认 endpoint：`http://127.0.0.1:18343/v1`
- 主要用途：本地 coding / 排障 / 只读分析 / 小范围自动化

这个模型当前是按 `openclaw-executor` profile 在跑：

- `64K`
- `thinking=false`
- `temperature=0.2`
- 单槽

所以最适合的不是“无限自由发挥”，而是：

- 任务目标清晰
- 输出契约明确
- 尽量约束为最小改动
- 优先让 Hermes 用工具查证，而不是空想

## 2. 使用原则

### 2.1 推荐风格

推荐：

- 明确目标
- 明确约束
- 明确是否允许修改文件
- 明确输出格式

不推荐：

- 太泛的开放式问题
- 不给边界，让它重构整个项目
- 既要改代码，又不给验证标准

### 2.2 对这个模型最有效的约束

建议你经常显式写出这些约束：

- `Only make the smallest safe change.`
- `Do not modify files unless I explicitly ask you to.`
- `Use terminal tools to inspect the repo first.`
- `Return strict JSON only.`
- `Summarize findings in 3 bullets max.`

这台模型服务本身偏 executor，不是 planner-first 风格；把约束写清楚，效果会更稳。

## 3. 常用命令模板

### 3.1 纯聊天

```bash
hermes chat -q "Reply READY only" -Q
```

### 3.2 只读仓库分析

```bash
hermes chat -q "Use terminal tools to inspect the current repository. Do not modify files. Tell me the most likely entrypoint and the top 3 modules I should read first." -Q --yolo
```

### 3.3 只读 bug 定位

```bash
hermes chat -q "Use terminal tools to inspect the current repository. Do not modify files. Find the most likely root cause of the failing flow and give the smallest safe fix." -Q --yolo
```

### 3.4 生成严格 JSON

```bash
hermes chat -q 'Return strict JSON only: {"root_cause":"...","fix":"...","files":["..."]}' -Q
```

### 3.5 明确允许改文件

```bash
hermes chat -q "Use terminal tools to inspect the repo, then make the smallest safe fix for the bug. After editing, explain which files changed and why." -Q --yolo
```

## 4. 推荐 Prompt 模板

下面这些模板是按当前 27B executor 模型特性收敛过的。

---

## 4.0 什么时候不要写 `Use terminal tools`

如果你的任务本来就是直接执行型，而不是探索型，就不要先写 `Use terminal tools`。

适合直接下任务的场景：

- 写一个独立脚本
- 修改一个你已经明确指定的文件
- 补一个测试
- 生成一段严格结构化输出
- 写 SQL / JSON / Bash / Python / Java 方法

这类任务更推荐直接用这些动词开头：

- `Write ...`
- `Modify ...`
- `Update ...`
- `Create ...`
- `Return ...`

只有当你希望 Hermes：

- 先看项目结构
- 先查日志
- 先查当前目录状态
- 先自己找入口和依赖

时，再补一句：

```text
Use terminal tools to inspect first.
```

---

## 4.1 仓库入口识别模板

适用场景：

- 新项目上手
- 快速找主入口
- 建立阅读路径

```text
Use terminal tools to inspect the current repository.
Do not modify files.

Goals:
1. Identify the primary runtime entrypoint.
2. Identify the top 3 modules/files I should read first.
3. Explain the likely request/data flow in the smallest useful form.

Output requirements:
- Keep the answer under 6 bullets.
- Include concrete file paths.
- Do not speculate beyond what you can verify from the repository.
```

---

## 4.2 Java / Spring 多文件 bug 定位模板

适用场景：

- service / controller / repository 链路问题
- DTO / transaction / validation 问题

```text
Use terminal tools to inspect the repository.
Do not modify files.

Task:
Find the most likely root cause of this Java/Spring issue and propose the smallest safe fix.

Constraints:
- Prefer verified conclusions over guesses.
- Keep the fix minimal.
- If multiple causes are possible, rank them.
- Do not propose broad refactors.

Output format:
1. Root cause
2. Evidence
3. Smallest safe fix
4. Risks / edge cases
```

---

## 4.3 TypeScript / Node 跨模块分析模板

适用场景：

- runtime / protocol / client 联动问题
- 事件流或消息协议问题

```text
Use terminal tools to inspect the repository.
Do not modify files.

Task:
Trace this TypeScript/Node issue across modules and find the minimum change needed to fix it.

Constraints:
- Focus on actual call flow and data shape.
- Prefer protocol/source-of-truth files first.
- Keep the proposed patch as small as possible.

Output format:
- Suspected root cause
- Exact files involved
- Minimum patch strategy
- Regression risks
```

---

## 4.4 严格 JSON 方案模板

适用场景：

- 你要把输出喂给别的脚本
- 你不想手动清洗结果

```text
Use terminal tools to inspect the repository.
Do not modify files.

Return strict JSON only with this schema:
{
  "root_cause": "string",
  "confidence": "low|medium|high",
  "files": ["string"],
  "smallest_safe_fix": "string",
  "risks": ["string"]
}
```

建议：

- JSON schema 越简单越好
- 不要一次要求太多字段
- 不要混入自然语言说明

---

## 4.5 只读 shell 运维模板

适用场景：

- 检查目录、进程、日志、git 状态
- 不希望它改任何东西

```text
Use terminal tools only.
Do not modify files.
Do not run destructive commands.

Tasks:
1. Run pwd
2. Run git status --short
3. Summarize the current working state in 3 bullets max
```

---

## 4.6 最小脚本生成模板

适用场景：

- Bash / Python 小脚本
- 你想要它直接给脚本内容

```text
Write a small standalone script for this task.

Constraints:
- Keep it minimal and production-safe.
- Prefer readability over cleverness.
- Include basic error handling.
- No extra explanation inside the code.

Output requirements:
- Return code only.
- Use a single fenced code block.
```

---

## 4.7 允许编辑的最小修复模板

适用场景：

- 你真的要让它改代码
- 想控制改动范围

```text
Use terminal tools to inspect the repository first, then make the smallest safe fix.

Constraints:
- Change as few files as possible.
- Avoid unrelated refactors.
- Preserve current public behavior except for the bug fix.
- After editing, summarize:
  1. files changed
  2. root cause
3. how to verify
```

---

## 4.8 直接写脚本模板

适用场景：

- 直接生成 Bash / Python / Node / SQL 小工具
- 不需要它先探索仓库

```text
Write a small standalone script for this task.

Task:
<put the exact task here>

Constraints:
- Keep it minimal and production-safe.
- Prefer readability over cleverness.
- Include basic error handling.
- Do not add unrelated features.

Output requirements:
- Return code only.
- Use a single fenced code block.
```

示例：

```text
Write a small standalone Bash script that scans all .log files under the current directory and prints the file path plus the count of ERROR lines in the last 24 hours.

Constraints:
- Keep it minimal and production-safe.
- Prefer readability over cleverness.
- Do not modify any files.

Output requirements:
- Return code only.
- Use a single fenced code block.
```

---

## 4.9 直接改指定文件模板

适用场景：

- 你已经知道要改哪个文件
- 不想让它先自由探索

```text
Modify <exact-file-path> for this task.

Task:
<put the exact task here>

Constraints:
- Make the smallest safe change.
- Do not modify any other files unless strictly necessary.
- Preserve existing behavior except for the requested fix.

Output format:
1. What changed
2. Why
3. How to verify
```

示例：

```text
Modify apps/game-runtime/src/runtime/replay.ts to add a size guard before writing replay data.

Constraints:
- Make the smallest safe change.
- Do not modify any other files unless strictly necessary.
- Preserve current behavior except for preventing oversized replay writes.

Output format:
1. What changed
2. Why
3. How to verify
```

---

## 4.10 直接补测试模板

适用场景：

- 逻辑已经比较清楚
- 你只想让它补测试，不想让它乱改业务代码

```text
Add or update tests for this behavior.

Task:
<describe the behavior or bug>

Constraints:
- Prefer the smallest useful test coverage.
- Do not change production code unless it is strictly required to make the test valid.
- Keep the test style consistent with the existing test suite.

Output format:
1. Test files changed
2. Covered cases
3. How to run the tests
```

示例：

```text
Add or update tests for the replay size guard behavior.

Constraints:
- Prefer the smallest useful test coverage.
- Do not change production code unless it is strictly required to make the test valid.
- Keep the test style consistent with the existing test suite.

Output format:
1. Test files changed
2. Covered cases
3. How to run the tests
```

---

## 4.11 直接输出最小修复方案模板

适用场景：

- 你不要它改文件
- 你只要一个可以自己评估的最小修复方案

```text
Propose the smallest safe fix for this issue.

Task:
<describe the issue>

Constraints:
- Do not modify files.
- Do not propose broad refactors.
- Keep the patch surface as small as possible.
- Prefer concrete file/function suggestions.

Output format:
1. Root cause
2. Smallest safe fix
3. Files/functions involved
4. Risks
```

---

## 4.12 直接返回结构化输出模板

适用场景：

- 你要把结果喂给别的程序
- 你只要结构化结论，不要过程

```text
Return strict JSON only.

Schema:
{
  "root_cause": "string",
  "files": ["string"],
  "smallest_safe_fix": "string",
  "risks": ["string"]
}

Task:
<describe the issue>
```

或者更简单：

```text
Return strict JSON only with:
{
  "script_name": "string",
  "purpose": "string",
  "code": "string"
}
```

## 5. 对这个模型最实用的几条经验

### 5.1 优先让它“查证”，不要先让它“脑补”

推荐：

```text
Use terminal tools to inspect...
```

不推荐一上来就：

```text
Explain why this bug happens
```

因为当前模型 profile 偏 executor，带着工具走，命中率更高。

但如果任务本身是纯执行型，例如写脚本、改指定文件、补测试，那就直接下任务，不需要先探索。

### 5.2 输出契约越硬，结果越稳

例如：

- `Return strict JSON only`
- `Return exactly 3 bullets`
- `Return exactly one line in the form ...`

这种约束对当前模型很有效。

### 5.3 让它做“最小修复”，不要让它做“最佳重构”

推荐：

```text
Find the smallest safe fix.
```

不推荐：

```text
Refactor this module in the best possible way.
```

因为后一种会引入不必要发散。

### 5.4 单轮目标要清楚

比起一轮里同时让它：

- 找 bug
- 改代码
- 写测试
- 写运维脚本
- 写总结

更稳的方式是拆成两轮：

1. 先定位 + 方案
2. 再编辑 + 验证

## 6. 当前不建议的使用方式

对当前这套 Hermes + 27B executor，不建议默认这样用：

- 超长开放式 brainstorming
- 多轮自由规划后再自己决定改很多文件
- 混合过多输出格式要求
- 同时要求工具调用、严格 JSON、长篇解释

这些并不是一定不行，而是稳定性会明显变差。

## 7. 推荐的实际工作流

### 工作流 A：先分析再改

第一轮：

```text
Use terminal tools to inspect the repository. Do not modify files. Find the most likely root cause and the smallest safe fix.
```

第二轮：

```text
Apply the smallest safe fix you proposed. Change as few files as possible. Then summarize changed files and verification steps.
```

### 工作流 B：先拿结构化结论

第一轮：

```text
Use terminal tools to inspect the repository. Return strict JSON only with root_cause, files, smallest_safe_fix, risks.
```

第二轮再决定是否让它改。

### 工作流 C：shell / 运维辅助

```text
Use terminal tools only. Do not modify files. Check pwd, git status --short, and the last 50 lines of the relevant log file, then summarize the current state in 3 bullets.
```

### 工作流 D：直接写脚本

```text
Write a small standalone script for this task.
Keep it minimal and production-safe.
Return code only.
```

### 工作流 E：直接改指定文件

```text
Modify <exact-file-path> for this task.
Make the smallest safe change.
Do not modify any other files unless strictly necessary.
```

### 工作流 F：直接补测试

```text
Add or update tests for this behavior.
Prefer the smallest useful coverage.
Keep the style consistent with the existing suite.
```

## 8. 最小示例

### 8.1 Java bug 分析

```bash
hermes chat -q "Use terminal tools to inspect the current repository. Do not modify files. Find the most likely root cause of the current Java/Spring bug and propose the smallest safe fix. Output: 1) root cause 2) evidence 3) smallest safe fix 4) risks." -Q --yolo
```

### 8.2 严格 JSON

```bash
hermes chat -q 'Use terminal tools to inspect the repository. Do not modify files. Return strict JSON only with schema: {"root_cause":"string","files":["string"],"smallest_safe_fix":"string","risks":["string"]}' -Q --yolo
```

### 8.3 真正执行最小修复

```bash
hermes chat -q "Use terminal tools to inspect the repository first, then make the smallest safe fix. Change as few files as possible. After editing, summarize changed files, root cause, and verification steps." -Q --yolo
```

## 9. 总结

对当前这套环境，最稳的用法不是把 Hermes 当“无限自由的超大代理”，而是把它当成：

- 会查代码
- 会查 shell
- 会按约束产出
- 会做最小修复

的本地 executor。

只要你把边界写清楚，这套组合在实际 coding / 排障 / 脚本辅助场景里是可用的。
