# 单卡发布与回滚手册

此文主要是未来优化发布步骤。2026-10-20用户已明确授权通过jssh 29执行已有27B的baseline、停止Strata并使用脚本监控/定时唤醒；范围见 [baseline合同](../plans/05-baseline-29-execution.md)。该授权不包含本轮优化实现或新候选发布。实际host/unit/image/恢复命令先核对，沿用已有27B配置，不猜服务或静默换codec。

## 三种资格分开

代码完成、GPU资格、production promotion分别记录。Phase统一review通过不自动把feature设默认。H5为低成本闭环，H8为含DFlash2/检索的完整闭环；H6被资产阻断时仍可交付H5，不伪称H8完成。

## 不可变发布单元

release记录包含：P6/候选commit、镜像digest、Target artifact fingerprint、proposal/draft companion fingerprint、policy hash、tokenizer/template hash、KV/snapshot版本、compile/CUDA profile、资格矩阵、资源账本、旧镜像+参数+缓存目录、schema与proxy契约。proposal单独换profile也重新核对Graph/backend-state identity。

## 执行顺序

1. 在独立worktree和builddir完成阶段合入；复核无未提交生产overlay丢失。
2. 构建新镜像而不启动并发27B；保存旧镜像digest及可读配置（去掉密钥）。
3. 关闭外部流量入口/排空，确认active=0且异步export完成；停止旧实例才启用新实例。
4. 新实例使用新namespace与缓存目录，模型只读mount；启动时打印实际resolved profile/资源与target identity，缺资格即失败。
5. 短smoke→tool/多轮→真实长上下文→限定真实流量。观察TTFT、committed speed、pending/fault、GPU memory、工具正确性。
6. 故障/超门槛立即排空停新，恢复旧镜像+旧参数+旧缓存目录；启动完成后用原请求验证。无论是否发生异常，至少做一次实际切回演练。

不能只把flag关掉就说跨snapshot版本已回滚。不能将新缓存复制到旧目录。热基准和冷基准分别初始化：并行端口不是隔离显存，单卡不默认双模型共驻。

## 运行停止条件

OOM、非法访问、unexpected engine retirement、旧golden质量失效、旧schema/tool兼容回归、warm TTFT或长上下文超冻结门槛，均停止promotion。计数器缺失、fallback过多、没有真实长prompt测量也不能放行。长块不能合格时回退到最后已合格短块；不继续尝试逐轮“出错重试”制造好看吞吐。

每阶段review变化若涉及可执行文件，重新绑定新commit与buildhash，不能沿用旧artifact的性能证据。
