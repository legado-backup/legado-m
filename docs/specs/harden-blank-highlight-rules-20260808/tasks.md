# 高亮规则空数据自动修复 - 任务清单

> **创建时间**：2026-08-08

## Phase A: 代码加固

- [ ] A.1 HighlightRuleStore.load() 插入"全空规则→reset"检测
- [ ] A.2 编译通过

## Phase B: 真机验证

- [ ] B.1 注入"12 条全空 name/pattern"数据到模拟器测试包
- [ ] B.2 启动高亮规则页，验证自动恢复 12 条内置规则
- [ ] B.3 验证正常数据不触发 reset（无多余自愈日志）
- [ ] B.4 验证混合数据（1 正常 + 11 空）不触发 reset

## Phase C: 文档同步

- [ ] C.1 docs/INDEX.md 收录 spec
- [ ] C.2 issues-found.md 记录 H-1 状态
- [ ] C.3 ai_memory_main.md 记录 BUG-H01 与自愈加固
- [ ] C.4 updateLog.md 更新（编译前）

## Phase D: 验收交付

- [ ] D.1 调试日志清理检查（无残留 Log.d）
- [ ] D.2 用户确认

## AOAdapt 日志

（如无偏差可省略）