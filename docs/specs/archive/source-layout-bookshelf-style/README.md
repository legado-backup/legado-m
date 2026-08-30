# 书源/订阅源布局参考书架重构（Issue-6 方案D）

> 状态：✅ 实施完成（源码实证 25/51 勾选，布局/Adapter/upSourceHost 链路全落地；余 T4/T5 真机验证）

## 功能概述

让书源/订阅源列表的视觉布局和功能模式与书架完全对齐：**书架有3种视图（列表/紧凑列表/网格），书源/订阅源也要有相同的3种视图且布局结构参考书架**。

## 核心能力

1. **视觉一致性**：书源/订阅源列表左侧有首字图标（66x90dp列表 / 48x64dp紧凑 / 自适应网格），右侧有多字段信息，结构同书架
2. **功能一致性**：书源/订阅源也支持3种模式（列表/紧凑列表/网格），与书架模式对齐
3. **保留原有功能**：多选（CheckBox）、启用开关（Switch）、编辑/更多按钮、调试状态、发现标识
4. **订阅源新增列表模式**：与书源/书架对齐3种模式

## 文档索引

| 文档 | 内容 |
|------|------|
| [spec.md](./spec.md) | Intent/Scope/Approach/Requirements/Scenarios |
| [design.md](./design.md) | Technical Approach/ADR/Data Flow/File Changes |
| [tasks.md](./tasks.md) | 任务清单 + 进度跟踪 |

## 背景

### 用户原始诉求

> "我说过，你的书源订阅源首页模式参考书架布局呀，艹！"
>
> "你自己思考怎么样更合理！我要求的是尽可能一致，视觉一致性，功能一致性！"

### 方案演进

| 方案 | 内容 | 状态 |
|------|------|------|
| A | 调整字号对齐书架 | 否决（治标不治本） |
| B | 增加视觉层次（增加字段/图标） | 否决（局部修改） |
| C | 保持现状 | 否决（违背用户要求） |
| **D** | **三种模式全面参考书架布局重构** | **用户确认** |

## 涉及模块

| 模块 | 文件 | 变更类型 |
|------|------|---------|
| 书源列表 | `item_book_source.xml` | 完全重写（已完成） |
| 书源紧凑列表 | `item_book_source_compact.xml` | 完全重写（待实施） |
| 书源网格 | `item_book_source_grid.xml` | 字号对齐（待确认） |
| 订阅源列表 | `item_rss_source.xml` | 完全重写（待实施） |
| 订阅源紧凑列表 | `item_rss_source_compact.xml` | 完全重写（待实施） |
| 订阅源网格 | `item_rss_source_grid.xml` | 字号对齐（待优化） |
| Adapter代码 | `BookSourceAdapter.kt` 等 | 新增控件绑定（待实施） |
| 扩展函数 | `SourceExt.kt` 或新建 | sourceInitial() + sourceUrlHost() |

## 关联文档

- `v3.26.0717-bug-fix-batch/problem-6-evaluation.md` — 方案A/B/C评估，已被否决
- `source-layout-redesign/` — 视图模式扩展+排序+类型筛选（与本spec正交，独立实施）
- `source-layout-detail-refinement/` — 标签+分组两模式（与本spec正交，独立实施）

## 状态

- 设计文档：✅ 已创建
- 实施进度：
  - item_book_source.xml：✅ 已完成（前次对话已完成重写）
  - 其他5个布局文件：⏳ 待实施
  - Adapter代码：⏳ 待实施
- 验证：⏳ 待编译+真机测试
