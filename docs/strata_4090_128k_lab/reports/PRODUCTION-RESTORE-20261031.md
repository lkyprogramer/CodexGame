# 29 · 恢复既有生产服务

结论：**RESTORED，服务active/running/enabled，模型已加载。** 2026-10-31用户明确要求恢复生产，root通过`jssh 29`启动既有`openclaw-qwen38-next.service`。本次恢复覆盖此前“生产保持停机”的当前状态要求；此前报告中的停机回执仍保留原时间和事实。

没有替换代码、二进制、权重、配置或systemd单元，没有升级或新部署。Astra零候选收口、F02 DEFERRED_NEW_EVIDENCE、P01/P01B/F03历史终态、六项FAIL和P05 BLOCKED_EVIDENCE保持。没有追加GPU实验或推理冒烟请求。

## 启动与认证

启动前只读确认unit指向`/home/hhtele/strata-0.2.3/run-iq3_xxs.sh`，工作目录为`/home/hhtele/strata-0.2.3`；服务inactive/dead/enabled，18343和18089无监听，GPU1MiB/42°C、无compute，MemAvailable约56.4GiB。

初次非交互sudo和systemd启动均被系统认证拒绝，备用管理员SSH登录也未成功；这些尝试没有启动服务。用户随后明确默认账号认证方式，经远端TTY交互sudo执行`systemctl start openclaw-qwen38-next.service`，exit0。认证信息未写入工作区、命令参数或本报告。

服务只启动一次，没有执行restart、stop、enable、daemon-reload或权限修改。

## 实际验收

2026-10-31 **12:49:47北京时间**，直连`http://127.0.0.1:18343/health`返回HTTP200，`loaded=true`、`status=ok`，模型`openclaw/Qwen3.8-next`，`max_context=131072`。

12:50:44北京时间进一步只读核对：

| 检查 | 结果 |
|---|---|
| systemd | active/running/enabled；MainPID2404594；NRestarts0 |
| 服务进程 | Python2404594；native2404600，均在同一service cgroup |
| 实际native | `/home/hhtele/strata-0.2.3/engine/strata`；工作目录为生产树；`--max-context 131072` |
| 监听 | 后端127.0.0.1:18343；NGINX0.0.0.0:28343；实验端口18089无监听 |
| `/v1/models` | HTTP200，包含`openclaw/Qwen3.8-next` |
| NGINX未认证`/v1/models` | HTTP401，既有认证边界仍在 |
| GPU | 总占用23598MiB、44°C；唯一compute为生产native PID2404600 |

上述证明服务和模型就绪，不等于任务质量、128K实际请求或长时稳定性通过。没有发送推理请求，没有重跑CPU/GPU实验或质量题集。本轮未重新hash13保护文件；启动动作未修改其配置，既有内容身份核验仍引用F03回执，不冒称新hash核验。

## 当前交接

生产保持运行，不能再按旧停机回执启动独占GPU实验。未来需要停生产、进入新GPU实验或改变生产配置时，须由用户明确给出对应范围。当前性能探索继续维持零候选收口；本次恢复不解除任何性能或质量门。

运行回执保存在`workspace/frontier/production-restore-20261031/`。本地仅更新当前入口、状态报告和清单，保留所有已关闭实验报告。包与文档检查另记`PACKAGE_CHECKS.json`；不运行无关游戏测试。
