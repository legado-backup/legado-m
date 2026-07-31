# 高亮规则丢失修复 + 恢复默认规则 - 项目导航

> **创建时间**：2026-07-29
> **来源**：用户反馈"优化完事了，原来我自己设置的高亮规则没了"+ "能不能初始化一些常规的高亮内容规则进去软件里面"
> **状态**：🔄 设计中
> **优先级**：P0（用户数据丢失 + 功能缺失）
> **前置 spec**：[highlight-rule-fix-20260727](../highlight-rule-fix-20260727/)（已实施核心修复，本 spec 修复其引入的回归 + 补齐恢复默认功能）

---

## §1 项目简介

### 1.1 背景

前序 spec `highlight-rule-fix-20260727` 实施了高亮规则系统的 6 项修复（isRegex 修正、首启播种、upsert、即时生效、fill 快绘补画）。实施后用户反馈两个问题：

1. **用户自定义规则丢失**：实施后用户自己设置的高亮规则消失
2. **无法重新初始化常规规则**：用户清空规则后无法恢复内置常规规则

### 1.2 核心目标

| 指标 | 当前值 | 目标值 | 修复来源 |
|------|--------|--------|---------|
| 用户自定义规则保留率 | 愈合逻辑覆盖用户改过的 pattern | 用户改过的 pattern 不被覆盖 | R-1：愈合逻辑增加 pattern 前置判断 |
| 恢复默认规则能力 | 无入口（reset() 仅 load() blank 分支调用） | 菜单提供"恢复默认规则"入口 | R-2：新增恢复默认菜单 |
| 恢复默认模式 | 无 | 合并模式（保留自定义+补充缺失内置）+ 覆盖模式（确认后重置） | R-2 |
| tasks.md/INDEX.md 同步 | 未更新（前序 spec 实施后未同步文档） | 全部更新 | R-3：文档同步 |

### 1.3 问题清单总览

| 编号 | 问题 | 优先级 | 根因一句话 | 关键证据 |
|------|------|--------|-----------|---------|
| R-1 | 用户编辑过的内置规则 pattern 被愈合覆盖 | P0 | `shouldRefreshBuiltin` 只判断 `!rule.isRegex` 就触发刷新，缺少"pattern 是否与内置一致"前置判断；`normalizeRules` 的 `builtin.copy()` 不保留 safeRule 的 pattern/sampleText/name | HighlightRuleStore.kt:281-294 + 383-394 |
| R-2 | 清空规则后无法恢复内置常规规则 | P1 | `reset()` 全工程仅在 `load()` blank 分支调用，无 UI 入口；用户清空后 stored="[]" 非 blank 不触发播种 | HighlightRuleStore.kt:45-48 + HighlightRuleActivity.kt:43-58 |
| R-3 | 前序 spec tasks.md 未更新 + INDEX.md 未收录 | P2 | 实施后未执行文档同步 | tasks.md 全 `[ ]` + INDEX.md 无条目 |

---

## §2 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 功能规格：问题现象/根因/验收标准 + 非目标 + Approach（含 Alternatives Considered + Drawbacks） |
| [design.md](./design.md) | 技术设计：根因源码锚点 + 修复方案代码片段 + ADR 决策 + 数据流 + 文件变更 |
| [tasks.md](./tasks.md) | 任务清单：按 Phase 组织 + `- [ ] X.Y` 格式 + 验收勾选框 |

## §3 实施策略

- **Phase A（止血）**：修复 `shouldRefreshBuiltin` 愈合逻辑，增加 pattern 前置判断，停止覆盖用户改过的 pattern → 编译验证
- **Phase B（恢复默认）**：新增"恢复默认规则"菜单，支持合并模式 + 覆盖模式 → 编译验证
- **Phase C（文档同步）**：更新前序 spec tasks.md 状态 + 本 spec INDEX.md 收录 + updateLog
- **Phase D（验收交付）**：真机验收 + 调试日志清理

> **实施顺序理由**：Phase A 改动最小、止血用户数据丢失；Phase B 补齐恢复默认功能；Phase C 文档同步；Phase D 验收。
