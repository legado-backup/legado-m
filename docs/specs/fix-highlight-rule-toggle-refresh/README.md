# 修复高亮规则开关切换不即时刷新（fix-highlight-rule-toggle-refresh）

> 状态：✅ 已完成（2026-08-30 编译门禁 BUILD SUCCESSFUL 6m8s；MEmu L2 四项断言 ALL PASS；测试包 legado_miss_app_3.26.083009.apk）
> 创建：2026-08-30

## 功能概述

修复高亮规则管理页（HighlightRuleActivity）复选框选中/取消后列表不即时刷新、需退出重进才生效的 Bug。

## 根因

1. `onEnableToggle` 回调**原地修改**数据对象（`rule.enabled = enabled`），同一实例经 ViewModel 回流列表。
2. 项目 Kotlin 2.3.10，Compose 编译器**强跳过模式**默认开启：带 unstable 参数（`HighlightRule` 为 var 字段类）的 Composable 可跳过，unstable 参数按**引用相等**比较 → 同实例 → `HighlightRuleItem` 被跳过重组 → Checkbox 不重绘。
3. 退出重进从 Store 反序列化出**新实例**，引用不同才重绘——与症状完全吻合。

## 核心能力

- 开关切换即时生效（copy 创建新实例 → 引用变化 → 行重组）
- 全面排查同类模式（子代理全量审计结论：全项目仅此一处确认）
- 前端设计规范补齐"Compose 列表状态不可变更新"约束，杜绝复发

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | 意图/范围/方案（含替代方案与缺点）/需求/场景 |
| [design.md](./design.md) | 技术方案/架构决策（ADR）/数据流/文件变更 |
| [tasks.md](./tasks.md) | 任务清单 + AOAdapt 日志 |

## 排查结论（2026-08-30 子代理全量审计）

- **确认 Bug 仅 1 处**：`HighlightRuleActivity.kt:58-61`
- **已排除**：ReplaceRule/RssSource/BookSource/DictRule/TxtTocRule/AutoTask/RecycleBin 等 28 处 Compose 列表桥接页均已采用 copy 模式
- **坏味道备忘**（非本 Bug 类）：`RssViewModel.disable()` 原地改（走 RecyclerView 渲染，无重组失效）
