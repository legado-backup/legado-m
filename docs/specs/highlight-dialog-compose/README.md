# Highlghit 三弹框 Compose 化迁移

## 功能概述

archive 迁移完成后，`highlight/` 三弹框（`HighlightRuleEditDialog` / `HighlightRuleGroupManageDialog` / `HighlightPresetRuleDialog`）仍是 `BaseDialogFragment + dialog_highlight_* XML`（View 体系），是 Compose UI 收敛的遗留尾巴。本次将三者统一切换到 `ComposeDialogFragment` 基类，配合 `AppDialogFrame` / `AppComposeDialogs` 等既有 Compose 容器，完成 View → Compose 的等价迁移，保留既有功能、数据模型与回调契约，不丢功能。

用户明确要求：不留尾巴，先生成设计文档，再按 `tasks.md` 分段实施。

## 核心能力

- **三弹框 Compose 化**：`HighlightRuleEditDialog`（高复杂，样式通道 + Span 预览）、`HighlightRuleGroupManageDialog`（中复杂，分组列表 + 增删改 + 导出）、`HighlightPresetRuleDialog`（低中复杂，预设规则添加）全部改为继承 `ComposeDialogFragment`。
- **样式体系按收**：窄宽档位（`DialogWidth`/`Confirm`/`Management`）、底部 `Gravity.BOTTOM`、墨水屏支持等均收敛到 `ComposeDialogFragment` 基类，替代 `setLayout + BaseDialogFragment 二参` 旧式写法。
- **复用既有 Compose 组件**：`AppDialogFrame`、`AppEditDialog`、`GroupManageComposeDialog`（分组管理直接对照薄壳受控范例）。
- **零业务回归**：非 Room 的 SharedPreferences 存储（`HighlightRuleStore` / `HighlightRuleGroupStore`）、回调契约（`onChanged` / `onSelectGroup` / `onAddRule`）、`ReadBook.upHighlightRules()` 联动全部保留。

## 文档索引

| 文档 | 说明 |
|------|------|
| [spec.md](./spec.md) | 规格说明（Intent / Scope / Approach / Requirements / Scenarios） |
| [design.md](./design.md) | 技术方案（Technical Approach / ADR / Data Flow / File Changes） |
| [tasks.md](./tasks.md) | 任务清单（`- [ ] X.Y` 格式 + AOAdapt 日志） |

## 状态标记

✅ 实施完成（核对 2026-08-25：三弹框均 ComposeDialogFragment，5 布局 + 1 menu 已删，待全量编译门禁）