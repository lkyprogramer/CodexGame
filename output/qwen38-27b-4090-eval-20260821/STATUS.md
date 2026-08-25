# S-list 执行状态

## core（进行中）

启动：2026-08-21 06:28Z · `core-chain.sh` PPID=1  
Latin-square：

- seed 11：Sharp → grug → Fable → Salience → ColdFusion
- seed 29：grug → Fable → Salience → ColdFusion → Sharp
- seed 47：Fable → Salience → ColdFusion → Sharp → grug

新 QCB runner 会记 thinking chars + 每轮 token。结束自动切回 WORK。

```bash
ssh hhtele@192.168.10.29 'tail -n 30 /home/hhtele/qwen38-27b-4090-eval-20260821/logs/core-chain.log'
```
