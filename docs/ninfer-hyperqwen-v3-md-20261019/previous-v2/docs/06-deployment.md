> V3 继承资料：P0—P6 的任务目标和上游合入顺序继续有效。命令依赖须先按根目录 `support/REHYDRATE.md` 恢复。

# 06｜单 RTX 4090 部署验证、切换和回滚

## 1. 操作边界

本次交付没有操作你的服务器。后续 Agent 有服务器权限后，可以按本流程执行已授权的部署测试。正式生产切流、删除数据、修改驱动或外部服务配置不混在普通测试脚本内。默认模式是独立目录构建 + 排空后的串行 replay；生产切换需发布负责人在 gate 中签字。

生产源码目录在历史审计中不是 Git checkout。不要在 `/home/hhtele/ninfer-4090` 直接 reset/clean/pull。新仓库、新 worktree、新镜像在独立位置构建，原目录、旧镜像和现有启动脚本先只读保留。

## 2. P0 采集并冻结实际部署

记录容器的 image ID/digest、Entrypoint/Cmd、端口和挂载；API key/token/password 必须脱敏，容器 Env 不直接倾倒进交付包。记录 GPU UUID/驱动/显存总量/当前计算进程、磁盘余量、模型 SHA、资源 SHA 和代理的实际配置。

历史镜像信息只是线索：`ninfer-4090:prepare-detail`、回滚 tag `ninfer-4090:44a2c6c`，历史模型位于 `/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer`。当前值以现场采集为准，不能把旧 image ID 当作今天的证明。

构建源当前 Dockerfile 使用 CUDA 13.2 Ubuntu24.04；不要根据曾经的旧驱动记录假定兼容，也不要为合并测试自动升级宿主驱动。先用现场 GPU/容器运行时验证兼容；失败就形成环境阻断报告。

## 3. 双构建产物

**生产镜像**继续用 `Dockerfile.sm89-nobake`，不烘焙约 17GiB 模型，不强制 dashboard。固定解析后的 base image digest、工具链与来源 revision；保持 sm89；模型只读 bind mount。

**测试镜像/构建目录**包含 tests 与 benches，`BUILD_TESTING=ON`。现有生产 Dockerfile 是 OFF，因此“镜像成功构建”不能被当成“测试已经运行”。测试模型通过同一只读挂载进入，两份镜像都不拷贝模型到层中。

每个 milestone 构建不可变 tag，例如 `ninfer-4090:merge-p3-<candidate-short-sha>`；生产流程使用实际 image ID/digest，而不是一直覆盖 `latest`。

## 4. 缓存和配置布局

示例结构（路径是规划示例，不是已存在文件）：

```text
/data/ninfer-merge/
  runs/<run-id>/
    source-audit/
    environment/
    baseline/
    phase-P1/.../phase-P6/
  profiles/
    prod-captured.json
    candidate-p3.json
    candidate-p4-rk4v4.json
  cache/
    legacy-prod/                 # original path may be elsewhere; do not move it blindly
    p1-<sha>-legacy-codec/
    p3-<sha>-legacy-codec/
    p4-<sha>-midrise-v1/
    p5-<sha>-snapshot6-image5/
```

实际旧 cache 目录不需要迁移到这个示例布局；原位保留即可。新目录必须独立、可写、带容量和 filesystem reserve；模型目录只读。不同 codec、state ABI、model/adapter manifest 不共写一个 namespace。

磁盘预算要把每个独立 L3 容量、构建缓存、镜像层和证据文件相加。不能因为机器有约 600GB SSD 就预设有足够空闲。不要为了腾空间自动 prune 全部 Docker images 或删除旧 rollback cache。

## 5. 为什么不是蓝绿双实例

单 24GB 4090 上不能把两份 27B 常驻权重当作可行默认方案。因此采用串行 A/B/A：旧镜像 A 运行冻结样本；排空并停止 A；候选 B 运行同样样本；停止 B 并重新运行 A 检查热状态漂移。不同进程显式建立各自冷/热缓存，不能让 B 偷用 A 的 warm 状态。

两个不同端口不代表两个模型可以同时装入显存。测试端口只用于区分路由/日志，不意味着同时启动两个 GPU 容器。

## 6. 每次部署测试的固定状态机

1. **Prepare**：确认 source/image/model/profile/cache 五个身份，镜像已构建，rollback 三件套可读；冻结要运行的 workload 与 gate 阈值。
2. **Quiesce**：在代理层停止接受新的测试相关生产请求或进入明确的维护/重试策略；等待现有队列、active lanes 和异步导出结束。无法排空时终止切换，不强杀长请求来伪造低延迟。
3. **Stop old**：只停止明确匹配的旧容器；不删除它，不杀未知 GPU 进程，不释放旧 cache。确认模型占用释放后再启动候选。
4. **Start candidate**：只读模型挂载、新 cache 目录、受控端口和同样 reasoning/MTP/profile；核对 startup report 中实际 codec/context/adapter，而不是只相信命令行。
5. **Smoke**：model discovery、三种生成协议、短 tool call、一次热追加、一次 cancel；失败立即停候选并恢复 A。
6. **Run phase suite**：短/长/热/冷/并发与相关算子用例，记录原始日志、请求 ID、JUnit、计量样本、图表/汇总；不让 replay 执行外部真实工具写操作。
7. **Restore or approve**：常规测试结束恢复已发布镜像；满足最终发布 gate 且负责人确认后才把候选作为新生产默认。每一步写入 deployment-journal。

## 7. 生产观察门槛

可用部署窗口中的真实流量子集进行观察，但单卡串行期间其余流量必须有明确的维护/重试安排，不能声称有旧实例承接另外 90% 的流量。没有第二张卡或外部后备服务时，不承诺零停机。

建议观察至少 200 个有效请求、20 条多轮会话，并实际覆盖 128K+ 工具历史；报告 token 分布而不是只写总请求数。硬故障即时回滚：错误 cache identity、跨会话/adapter 污染、不可恢复 CUDA 错误、持续 OOM、资源泄漏、工具调用语义损坏、长上下文资格失败。性能软回退按冻结阈值触发 investigation/rollback，不临时放宽指标。

## 8. 回滚必须成套

回滚 = **旧 image digest + 旧完整启动参数/代理映射 + 旧 cache 目录/namespace**。先恢复旧服务，再验证 model/profile、短生成、旧会话恢复和工具协议。不将新 snapshot v6 或 target image v5 喂给旧二进制；不直接把新 cache 拷回旧目录。

回滚演练必须真实启动旧镜像并运行验证，不只是证明 `docker image inspect` 找得到旧 tag。记录实际中断区间、失败/重试请求、恢复是否冷启动、L3 能否读取。回滚旧缓存可能缺失候选期间的新前缀，这是性能代价，不是把版本检查关闭的理由。
