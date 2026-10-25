# 候选选择与生产发布

注册表是唯一机器源。`attribution_only`只完成K0，不实施优化。14个candidate scope是可选替代项，不是14轮必做；对应publication只增加实际生产K4-GATE，当前不执行。候选集合精确列ID，不自动补完整P0—P6或所有H/K/S阶段。

| 候选scope | 实验节点 | 特殊前提 |
|---|---|---|
| `cpu_sha_candidate` | C0-T01 | K0已定位CPU hash；actual Chat收益需独立证明 |
| `correction_candidate` | K1-T01, K1-T02 | K0实测路径与资源准入 |
| `kernel_candidate` | K2-T01 | K0实测路径与资源准入 |
| `workspace_candidate` | K3-T01 | K0实测路径与资源准入 |
| `projection_overlap_candidate` | K3-T02 | K0实测路径与资源准入 |
| `lookup_candidate` | H1-T01, H1-T07 | K0实测路径与资源准入 |
| `draft_head_candidate` | H2-T01, H1-T07 | K0实测路径与资源准入 |
| `w8_candidate` | H3-T01, H1-T07 | K0实测路径与资源准入 |
| `w16_candidate` | H3-T01, H4-T01, H1-T07 | W16需W8技术证据 |
| `dflash2_candidate` | H6-T01, H1-T07 | 匹配27B资产 |
| `global_retrieval_candidate` | H7-T01, H1-T07 | feature版才绑定H6；token版独立 |
| `utility_candidate` | S0-T01 | 只用已有合格route，不等所有路线 |
| `upstream_selective_candidate` | UP-T01 | 只改UP合并模式，full需共享收益/耦合依据 |
| `upstream_full_candidate` | UP-T01 | 只改UP合并模式，full需共享收益/耦合依据 |

每个候选包含共享K0及一次K4资格。`dependency_overrides`只把K4-T01绑定本次选中的branch；不绕过采样/状态门禁。组合两个改动时新建明确的组合scope并检查相互影响，不默认跑所有排列组合，也不能叠乘各自收益。global feature的额外H6证据绑定、utility选用route的资格应写入本次实验回执；不将不相干路线作为静态前置。

候选scope的存在不授予实施/GPU/下载/训练或生产权限。当前只修订文档，原GPU服务保持停止。完整发布需以后明确授权与实际回退/交还验证。
