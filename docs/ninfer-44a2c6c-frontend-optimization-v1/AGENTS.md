# 本实施包使用约束（补充，不替换 NInfer 原仓规则）

## 目标与边界

唯一主目标是降低已定位的 CPU tokenization 延迟，且保持指定提交的完整前端语义。先解决单请求边界重复编码，再解决跨请求重算。不得借机迁移模型、升级 CUDA、整树 merge 新上游或改 GPU 调度。不是通用多租户框架，也不建设第二套 HTTP 服务。

原仓 AGENTS.md 的产品/所有权规则继续适用；本包由用户明确要求的固定 commit、测试证据及回滚边界属于专项约束。工作分支、源文件哈希与 overlay 记录用于排除版本混淆，不得把流程维护变成主项目。

## 正确性

整数 token 和元数据逐项相等，不能以模型回答看起来正常替代。完整 legacy oracle 必须来自独立的锁定 baseline，不能和 candidate 共用新增边界算法。针对同位置 added-token 选择，保留旧版 ID 优先规则，不替换为最长匹配。

需要单独证明 NFC、词预切分和 BPE 的切割边界。原始 bytes 的 common prefix 只是一项条件，不是充分条件。普通 EOF 不视为安全重启点。错误输入必须保持拒绝，不能通过丢掉 hint 或插入分隔符“修复”。

## 执行

共享文件单写者。先保存现网配置和 prepare-detail overlay；只在独立 worktree 修改。每个任务必须有失败测试、通过测试、残留检查。任何功能开关必须默认保守，并标清是否已经实现。一次 GPU 只运行一个 27B；不得在生产对同一请求额外跑一遍完整 GPU shadow。

## 证据

`PASS`、`FAIL`、`SKIP`、`NOT_RUN` 独立记录。缺硬件、缺资源、缺授权不是通过。仅 `request_done` 全部 stop_token 不能证明工具正确、任务成功或不存在其他 request_error。

默认日志禁止正文、工具参数、密码、token、请求头。测试输入用合成数据；真实 trace 仅在用户受控主机回放。性能使用逐请求成对值、独立会话分层，禁止 p50 相减相加或以短请求淹没长请求。

## 代码规范

C++20；中文文档、英文标识与代码注释。前端逻辑归属 `src/targets/qwen3_8/impl/frontend/`，不是 CUDA Ops。明确缓存预算、引用生命周期、锁范围；不能使用进程全局无界 map、const_cast 或持锁 BPE。保持当前 tokenizer 资源、模板及 artifact 格式。源文件引用必须固定完整 commit。
