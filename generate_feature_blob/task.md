# 任务列表：修复 Batch Feature Generator 警告与日志异常

## 1. 抑制 FutureWarning 警告

- [ ] 在 `run_batch.py` 中引入 `warnings` 模块。
- [ ] 配置过滤规则，忽略 `insightface` 触发的 `FutureWarning`。

## 2. 优化日志输出结构

- [ ] 简化 `run_batch.py` 中的成功/失败输出前缀。
- [ ] 增加处理单个用户时的耗时统计（可选），使日志更具参考价值。
- [ ] 确保最后的总结信息能够完整输出。

## 3. 验证与回归测试

- [ ] 在虚拟环境中运行脚本，确认警告消失。
- [ ] 观察日志输出是否整齐且包含总结信息。
