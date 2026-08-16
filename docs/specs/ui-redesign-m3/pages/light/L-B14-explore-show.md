# L-B14 发现页分页（ExploreShowActivity）· 轻量设计文档

> **轻量版**：本页继承族文档 `pages/P6-explore.md`（S2 列表族）的骨架/组件/状态范式，本文只写「继承 + 差异」。开发本页只读本文档 + `P6-explore.md` + ui-standards §3.4 规格书。

## 0. 页面身份
- **页面名 / 文件锚点**：ExploreShowActivity（`ui/book/explore/`，View）
- **所属族文档**：`pages/P6-explore.md`（继承 S2 列表族）
- **骨架归类**：S2 列表管理页
- **对应 task**：tasks.md `12.52`；pages-inventory B14（优先级 P3）
- **fork 借鉴来源**：—

## 1. 继承声明（本页复用什么）
- 复用骨架：S2 列表管理页（P6 §2）+ 分页加载范式（滚动到底加载下一页）
- 复用组件（§3.4）：`GlassTopAppBar`（exploreName 标题）、`EmptyStatePlaceholder`（空态/错误态）、`AppNumberPickerDialog`（跳页 NumberPicker）、`AppTextDialog`（LoadMoreView 错误重试提示）
- 复用状态范式：`ViewModel + StateFlow`（分页游标 + isClearAll 切换）

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 数据源 | 分页发现列表（游标分页） | 滚动到底加载下一页 / 顶部上翻上一页 |
| 布局结构 | 单列表 + 顶栏 exploreName 标题 | — |
| 交互 | 跳页 NumberPicker（1-999，跳页 isClearAll）；LoadMoreView 错误重试；点击→BookInfoActivity（判入架） | 分页边界 + 跳页为私有交互 |
| 功能点 | 加载下一页/上翻上一页/跳页/错误重试/点击入详情 | 对照 pages-inventory B14 无遗漏 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `AppNumberPickerDialog` | L2 NumberPicker 弹窗 | 跳页 1-999 |
| `EmptyStatePlaceholder` | Icon 48dp + 标题 + 副标 | 空列表/加载失败错误态 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 分页加载骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 无发现数据 |
| 错误 | `EmptyStatePlaceholder` / `AppTextDialog` | 分页加载失败重试 |

## 5. i18n 与无障碍
- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）；触控 ≥48dp、Icon contentDescription

## 6. 验收标准（轻量）
- [ ] 复用 P6 骨架/组件，无私有复制组件
- [ ] 功能点对照 pages-inventory B14 无遗漏（滚动加载/上翻/跳页 isClearAll/错误重试/点击判入架）
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录
- 2026-08-13：初始建立（关联 pages-inventory B14），task 12.52
