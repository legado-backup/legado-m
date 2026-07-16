# 工作方法论

> 大型任务的工作方法/工作论/工作模式索引，指向具体子规范。
> **来源**：2026-07-17 用户批评"沉淀工作方法，不是记录细节性错误"

## 工作论（3条核心原则）

1. **主动沉淀**：大型任务结束后自觉反思工作方法，不等用户提出
2. **全局思考**：改动功能前6维度盘点 → [global-thinking-checklist.md](./global-thinking-checklist.md)
3. **真机验证**：静态审查无法替代运行时验证，线程问题只能通过运行时日志发现

## 工作方法（3条流水线）

1. **分阶段流水线**：规范先行→数据库→崩溃→功能闭环→UI Bug→规范沉淀→真机测试
2. **问题清单驱动**：维护 issues-found.md，5维度记录，状态回填 → [real-device-test-reuse.md](./real-device-test-reuse.md)
3. **子代理交叉核查**：大型任务完成后用子代理全面核查 → complex-task.md

## 工作模式（4条执行规则）

1. **编译前更新文档** → [version-delivery-sync.md](./version-delivery-sync.md)
2. **调试日志及时清理** → [logging-during-refactoring.md](./logging-during-refactoring.md)
3. **文档同步检查** → [version-delivery-sync.md](./version-delivery-sync.md)
4. **前端主题不硬编码色号/样式**：UI组件必须用 ?attr/* 或 @color/* 引用保持风格统一；DialogFragment/BottomSheetDialogFragment 必须用 ThemeStore 动态设置颜色（应用级暗色主题不激活 values-night） → [global-thinking-checklist.md](./global-thinking-checklist.md) G2/G4

## 何时加载

- 大型任务（10+文件/多Issue）开始时
- 新对话开始时检查工作方法
