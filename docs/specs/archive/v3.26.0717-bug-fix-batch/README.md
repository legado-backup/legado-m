# v3.26.0717 真机测试 Bug 批量修复

> ⚠️ 归档待定（2026-08-30 文档规整）：设计停滞超 7 天，如需恢复实施请移回 docs/specs/ 并更新状态

> 状态：✅ 已实施（Issue-2/3/5.x 源码注释实证，勾选已同步）

## 功能概述

针对 v3.26.071619debug 版本真机测试发现的 6 个问题进行批量修复，覆盖订阅源解析并发显示、高亮规则颜色选择器主题适配、替换规则崩溃、设置项数值显示、域名分组排序逻辑、书源/订阅源视图布局。

## 核心能力

1. 修复订阅源编辑页面解析并发显示逻辑（未配置时显示继承的系统配置值）
2. 修复高亮规则颜色选择器在暗色主题下预设色块全部显示白色的问题
3. 修复阅读时使用替换规则导致 ConcurrentModificationException 崩溃
4. 修复其他设置页 rss/图片并发下方文字不显示当前设置数的问题
5. 修复域名分组/智能排序/反序复选框三类问题
6. 评估书源/订阅源视图布局与书架的对齐情况

## 文档索引

- [spec.md](./spec.md) - 需求规格（Intent/Scope/Approach/Requirements/Scenarios）
- [design.md](./design.md) - 技术设计（Technical Approach/ADR/Data Flow/File Changes）
- [tasks.md](./tasks.md) - 任务清单（按 Phase 组织）
- [issues-found.md](./issues-found.md) - 测试问题追踪

## 日志来源

- 路径：`temp/tmp/Downloadslogs.(1)..zip`（最新 2026-07-17 08:21 日志）
- 关键崩溃：`crash-2026-07-16-22-27-36-1784212056748.log`
  - 异常类型：`java.util.ConcurrentModificationException`
  - 调用栈：`ArrayList$Itr.checkForComodification` → `ReadBook.ruleMatchesOfChapter` → `ContentTextView.upHighlight`

## 影响范围

- 订阅源编辑：`RssSourceEditActivity.kt`
- 高亮规则：`HighlightRuleEditDialog.kt` + `HighlightColors.kt` + ColorPickerDialog 主题适配
- 阅读核心：`ReadBook.kt`（并发安全）
- 其他设置：`OtherConfigFragment.kt`
- 书源管理：`BookSourceActivity.kt` + `BookSourceViewModel.kt`（域名分组/排序/反序）
- 视图布局：`BookSourceAdapterCompact.kt` / `BookSourceAdapterGrid.kt` / `RssSourceAdapterCompact.kt` / `RssSourceAdapterGrid.kt`
