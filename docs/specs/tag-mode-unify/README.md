# 书架订阅标签样式统一（tag-mode-unify）

> 位置：`docs/specs/tag-mode-unify/` ｜ 索引：[`docs/INDEX.md`](../../INDEX.md)

## 功能概述

统一「书架」与「订阅」两个页面的分类/分组标签样式，全部对齐 Rimchars archive 的 `MainTopBarView` 顶栏标签模式：

- 顶栏 `titleSelect`（分组名 + 向下箭头）可点击，弹出分组切换菜单（多级/全部分组）。
- `primaryBar` 横向胶囊分组标签（`RoundedTagBarView`），点击切换。
- `tagsBar` 书本标签栏（第二级标签），点击按标签过滤。
- 通过右侧 `filterToggleButton` 向下展开/收起多级标签栏。

解决当前「书架用 Compose `ScrollableTabRow`、订阅用 `RoundedTagBarView` 胶囊」，两处标签风格不一致且书架缺失下拉/多级的问题。

## 文档索引

| 文档 | 内容 |
|------|------|
| [README.md](./README.md) | 功能概述、文档索引、状态标记 |
| [spec.md](./spec.md) | Intent / Scope / Approach（含 Alternatives + Drawbacks）/ Requirements / Scenarios |
| [design.md](./design.md) | Technical Approach / ADR / Data Flow / File Changes |
| [tasks.md](./tasks.md) | 任务清单 + AOAdapt 日志 |

## 状态标记

**🔄 开发中**

> 检查点 1（设计方案审查）已通过（2026-08-24）：
> - 用户确认三大铁律：一套标签体系（MainTopBarView/RoundedTagBarView）/ 可被主题·顶栏·管理设置控制 / 保留 Compose 列表、不搬 ViewPager。
> - 取舍 1（接受）：默认（非 regular）顶栏风格不显示分组胶囊条，仅顶栏 regular 风格显示横向分组胶囊——与 archive/订阅一致。
> - 取舍 2（接受）：RoundedTagBarView 胶囊分组长按编辑分组失效，分组管理走「更多菜单→分组管理」——与 archive 一致。