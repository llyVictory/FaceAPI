# 任务列表：修复 Batch Feature Generator 警告与日志异常

## 1. 抑制 FutureWarning 警告

- [x] 在 `run_batch.py` 中引入 `warnings` 模块。
- [x] 配置过滤规则，忽略 `insightface` 触发的 `FutureWarning`。

## 2. 优化日志输出结构

- [x] 简化 `run_batch.py` 中的成功/失败输出前缀。
- [ ] 增加处理单个用户时的耗时统计（可选），使日志更具参考价值。
- [x] 确保最后的总结信息能够完整输出。

## 3. 功能扩展：本地照片单条录入

- [x] 创建 `process_local.py` 脚本（或集成到 `run_batch.py`）。
- [x] 实现从本地路径读取图片并提取特征存入数据库。
- [x] 支持通过命令行参数传入 `user_id` 和 `image_path`。

## 4. 性能与健壮性优化 (针对 1w+ 数据)

- [x] 实现“增量更新”逻辑：只处理目标表中不存在特征的用户。
- [x] 在 `database.py` 中优化查询 SQL。
