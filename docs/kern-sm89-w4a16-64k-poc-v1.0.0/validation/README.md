# 本交付验证记录

本目录只记录**交付包辅助工具与测试夹具**在文档生成环境中的验证，不代表用户4090上的Kern实现。

## 已实际执行

- `bash scripts/self_check.sh`：63项Python辅助工具测试，含SSE分片/UTF8、权重头、内存账、清单限制、证据缺失/篡改/NaN/输出不足、进程超时和信号清理、维护控制面mock、任务依赖与文件完整性。
- Python compileall 与所有随包shell脚本 `bash -n`。
- 三个Java8夹具：原始版本全部真实失败；在临时副本上加入已知正确修复后全部通过。原夹具保持有bug，参考修复不放入Agent工作目录。详见`java-fixtures.json`。
- `configs/evidence.template.json`交给结果判定器：退出78、`BLOCKED`，未验证的包不会生成`POC_GO`。
- ZIP归档完整性与内容SHA256在打包后另行检查。

## 日志解释

`*-red.log`是修复前故意暴露缺陷的RED回归证据；**不是最终状态**。最终看`self-check.log`/`tooling-tests.log`。单测中构造的“完整结构→POC_GO”只是判定器测试，内容明确写`test-only`，没有拿它当GPU成绩。

维护控制面的测试用mock替代了systemctl、nvidia-smi和模型健康接口；没有暂停用户服务。另有真实的本地子进程超时/信号测试，但这些子进程不运行模型。

## 明确未执行

| 内容 | 状态 |
|---|---|
| 用户RTX4090设备探针/nvcc编译 | NOT_RUN |
| Kern Rust构建、SM89 CUDA内核实现与运行 | NOT_RUN |
| W4A16模型下载/真实权重重排 | NOT_RUN |
| 同权重GPU oracle、state/logits数值对比 | NOT_RUN |
| 实际64K输入与2K持续输出 | NOT_RUN |
| Pi连接真实模型完成Java三题 | NOT_RUN |
| 用户机器生产暂停/恢复 | NOT_RUN |
| 精确Qwen tokenizer实例运行 | NOT_RUN（生成器算法以测试encoder验证） |
| 两小时或更长实机soak | NOT_RUN |

GitHub连接器完成了源码查阅，但生成容器直接访问GitHub的下载遇到DNS失败。因此不宣称本环境克隆或编译了上游仓库。包内是固定来源的开发合同，不携带上游cubins或权重。

最终GPU资格证据由开发AI在目标机T03–T23实施时生成。签发此包的实际状态是`DEVELOPMENT_KIT_READY / GPU_NOT_RUN`。
