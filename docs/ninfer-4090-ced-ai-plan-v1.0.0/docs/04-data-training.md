# 04 Teacher 数据、可学习性与单卡训练

## 1. 固定目标，不做“顺手微调”

Teacher 是用户当前 `.ninfer` 制品在固定 native compute profile 下的真实中间张量。Base weights 全程不变；Predictor 是唯一训练参数。不能拿另一个 BF16 HF checkpoint 的激活替代当前量化引擎的 Teacher，也不能将 LoRA 或量化变化同时纳入本次实验。

训练工具放在实验根的兄弟目录 `ced-research/`，不把训练框架塞进 NInfer runtime；这样与当前仓库推理/外部训练分工一致。[S09] 不要求用户创建第二个公开 GitHub 项目。

## 2. 必须先解决的数据体积

CED-16，包含 h_split、final_hidden、4组 attention K/V、12组 pre-conv QKV 和 FP32 gates：

```text
per_token_bytes = 2*5120 + 2*5120
                + 4*(2*2048)
                + 12*(2*10240 + 4*96)
                = 287232 bytes/token
```

100000 个完全标注 token 约 26.75 GiB；100万约 267.52 GiB，尚不含校验信息和 anchor states。不能对每个长 prompt 的每个位置、每个层都永久保存完整标签。

默认 rolling dataset 上限 128GiB、日志8GiB、checkpoint8GiB，SSD 至少保留64GiB或初始可用容量20%中的较大者。预算不足不能删除生产模型/cache来腾空间。`tools/budget.py` 给出各 split 的估算，真实字节由导出计数验证。

## 3. 数据设计

先以完整 source repository / 独立 session 为单位划分 train/validation/test，比例约70/15/15；固定 manifest 后再切 chunk。来自同一 repo 的复制文件、相邻版本、同一会话、语义近重复必须归同一组。人工编写的 final acceptance 测试题完全不进入训练集。

建议内容覆盖：Java源文件35%、diff和测试20%、编译/运行日志20%、长工具输出15%、中文需求与说明10%。这些比例是训练设计，不是验证集权重。只使用用户允许本地处理的语料；不得主动上传或下载来源不明的大型语料。

Teacher 处理的总上下文可以很长，但只选择**连续标注窗口**：每个窗口128/256/1024 token，窗口位置覆盖前5%、25%、50%、75%、95%，同时保留相应 token positions 与原始 prefix。不能只用序列开头训练、却宣称200K有效。

| 阶段 | 标签预算 | 用途 |
|---|---:|---|
| plumbing | 4096 token | 检查导出、训练、序列对齐 |
| learnability | 32768 token | rank256初试，分层归一化误差 |
| qualification | 累计最多262144 token | 有正向信号后扩展；约70.1GiB标签 |
| bounded extension | 最多另一个262144 token | 只为修复已定位长上下文/域偏差，滚动淘汰自有旧shard |

每次最多2GiB shard；边写边计数、flush+原子rename；如果达到磁盘上限，结束该轮并给出明确状态，不产生可被当作完整数据使用的半文件。

## 4. 单卡调度与内存

流程：Teacher 导出完成→退出27B进程→确认GPU无其他占用→加载小型Predictor训练→保存checkpoint→卸载训练进程→加载candidate资格化。禁止同时把 teacher、student full model、optimizer 一起放进24GB。

默认训练：PyTorch独立环境；BF16 forward、FP32 optimizer state；AdamW，lr=1e-3，weight_decay=0.01，grad_clip=1.0，固定seed17，100步warmup；microbatch=64标注token、累计1024token/step；最多3epochs或6000steps先到者停止。版本以P0可安装的固定wheel锁定并记录，不使用浮动依赖。

每一批共享 trunk，只逐个 head 计算损失并反传，最后统一 optimizer.step；禁止为每一层复制一套 trunk 和 optimizer。必要时通过 latent gradient accumulation 降低保留图峰值。模型参数默认目标<100M，硬上限200M；runtime BF16 weights硬上限512MiB。训练进程峰值默认限制20GiB。

## 5. 损失与尺度

Teacher 每个层/张量的通道 RMS 仅由 train 集统计，并冻结在训练manifest。分层 normalized MSE 再按层平均，避免6144维V或某大范数层支配所有梯度。

```text
L = 1.0 * mean_layer(L_attn_K + L_attn_V)
  + 1.0 * mean_layer(L_preconv_QKV)
  + 0.2 * mean_layer(L_exp_g + L_beta)
  + 0.5 * L_final_hidden
  + 0.1 * L_state_anchor          # after pointwise model is stable
```

Attention K损失同时报告 raw projection 与真实norm+RoPE之后的方向误差。GDN gate loss用exp(g)和beta而非只对极端负g做MSE。任何NaN/Inf，训练步立即失败，记录具体head，不能自动nan_to_num掩盖。

## 6. GDN state-anchor distillation

仅有 token MSE 可能让小误差沿recurrent state累积。第二步在离线小窗口中加入状态损失：保存窗口起点S0、该层conv history和窗口终点Teacher state；从S0用预测输入运行同样数学递推。

不要在PyTorch里对“全48个GDN层×48 heads×100K”的FP32状态做无截断自动微分。默认一次1个层、4个value heads、32token窗口；通过后提升到128token，truncated BPTT，detach窗口边界。Teacher S0只用于训练监督；candidate真实推理不得使用Teacher S0。

长程 validation 分两类：teacher-initialized local windows（局部误差）与从零/合法自身prefix连续推进的free-running synthetic state（累积误差）。不能用前者替代后者。

## 7. 验证不等于训练

NInfer不是自动微分框架。本计划不要求穿过量化27B runtime反向传播KL；全模型logits KL用于离线checkpoint选择与最终验证，不虚构一个现成gradient接口。

阶段P3输出可学习性报告；只有P4 runtime接入后才能得出端到端质量结论。允许最多rank128/256/512三个受控实验或两次有根据的数据修订；不可无限追加语料并越过预算。

## 8. MTP final-hidden head

h_final target为source在final norm之后、MTP实际消费的BF16列。shift在MTP准备时完成，不把`t+1` token的hidden当作`t`标签。该head在P3训练，P4 no-spec可不执行；P5启用后成本必须计入prefill。

## 9. 可学习性停止条件

任一条件成立则NO-GO或保持在当前阶段：训练/validation误差无明显收敛；state误差随32K→64K→128K无界放大；达到rank/数据上限仍不满足P4质量Gate；资源预算不满足；只是训练样本变好而未见repo/session变差。

报告必须包含train/validation/test分组数、labels数量、Teacher处理总token、持久化字节、峰值显存、step数、early-stop原因、逐层误差分位数。不能只给一个平均loss截图。
