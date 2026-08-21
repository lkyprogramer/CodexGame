# Java JWT 验证器安全审查

审查仓库中的 JWT 验证实现。识别能够导致认证绕过、令牌重放或信任边界失效的问题，并给出可执行修复。重点是验证语义，不需要讨论代码风格。

输出必须是单个 JSON 对象，不要使用 Markdown 代码围栏：

{"issues":[{"file":"相对路径","line":1,"severity":"critical|high|medium|low","category":"类别","explanation":"问题、可利用条件与影响","fix":"具体修复方案"}],"summary":"总体结论"}

只报告有代码证据的问题。相同根因不要重复计数。
