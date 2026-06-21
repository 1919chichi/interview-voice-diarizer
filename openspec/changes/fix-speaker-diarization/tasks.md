## 1. Speaker 标准化与诊断

- [x] 1.1 添加 `additions.speaker`、数值零和缺失 speaker 的失败测试
- [x] 1.2 实现无损 speaker 提取及 `Speaker unknown` 降级
- [x] 1.3 添加原始/规范化 Speaker 基数不一致的失败测试
- [x] 1.4 实现不含转写正文的 Speaker 诊断和 CLI 边界校验

## 2. 多簇角色映射与安全降级

- [x] 2.1 添加多 Speaker 聚合、双 Speaker 和单 Speaker 降级的失败测试
- [x] 2.2 扩展 `RoleMapping` 并实现确定性的逐 Speaker 角色推断
- [x] 2.3 更新转写重标记和问答分组以使用逐 Speaker 映射
- [x] 2.4 添加无效、缺失和未知 Speaker 的 LLM 映射失败测试
- [x] 2.5 实现 LLM 角色映射校验、补齐和启发式回退

## 3. 声道感知音频转换

- [x] 3.1 添加单声道和双声道转换参数的失败测试
- [x] 3.2 实现源声道检测并在转换时保留至多两个声道

## 4. 输出与回归验证

- [x] 4.1 更新报告测试以覆盖不可判定和多簇角色输出
- [x] 4.2 使用已有 `raw-asr.json` 验证真实 Speaker 数量在标准化后保持一致
- [x] 4.3 运行完整 pytest、ruff 和 OpenSpec 校验
