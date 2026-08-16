# L-D4 RSS 文章列表（RssArticles/RssSort）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P7-rss.md`（S2 列表管理骨架），本文只写「继承 + 差异」。开发本页只读本文档 + P7 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：RssArticlesFragment + RssSortActivity（`ui/rss/article/`，View，5 种文章样式网格/瀑布流）
- **所属族文档**：`pages/P7-rss.md`
- **骨架归类**：S2 列表管理页
- **对应 task**：tasks.md `12.40`；pages-inventory D4（优先级 P1）
- **fork 借鉴来源**：无独立借鉴

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 列表管理骨架（见 P7 §2）：GlassTopAppBar + SettingsSearchBar + 列表项 + EmptyStatePlaceholder
- 复用组件（§3.4）：`GlassTopAppBar`、`ListLayoutMenu`、`EmptyStatePlaceholder`、`AppNumberPickerDialog`
- 复用状态范式：ViewModel + Flow；列表 DiffUtil 增量更新

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 布局结构 | RssSortActivity **多分类多行标签**（setupMultiLineTabs 按数量 1/2/3 行分块 + 横屏减 1 行 + updateTabSelection/ensureTabVisible） | 独有 Tab 布局 |
| 数据源 | sortUrl 解析（JSON map / 单 URL / sortUrls）；翻页 menu_page→`AppNumberPickerDialog`（按 ruleNextPage 配置显隐） | 独有 |
| 文章样式 | **5 种**：0 列表 / 1 / 2 / 4 网格（2/2/3 列）/ 3 瀑布流 StaggeredGrid（2/3 列） | 布局切换 ListLayoutMenu |
| 交互 | 下拉刷新 loadArticles；滚动加载更多 LoadMoreView；预加载模式 isPreload（阈值 5 提前触发）；分页跳转 + 位置记忆（VideoPlay/ImagePlay lastPlayedArticleLink） | 独有 |
| 路由 | 点击→readRss 按 type 路由网页/图片/视频 + 携带分页上下文 | 智能分发 |
| 返回键 | 搜索态返回键回列表 | — |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `ListLayoutMenu` | DropdownMenu 两区、选中 primary | 文章样式布局切换 |
| `AppNumberPickerDialog` | Slider+输入双联动 | 分页跳转 |
| `EmptyStatePlaceholder` | Icon 48dp + 标题 + 副标 | 空文章列表 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 文章列表骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 无文章空态，title 走 strings.xml |
| 错误 | `EmptyStatePlaceholder` | 错误分支 + 重试 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）；触控 ≥48dp

## 6. 验收标准（轻量）

- [ ] 复用 S2 列表骨架，无私有复制组件
- [ ] 功能点对照 pages-inventory D4 无遗漏（5 样式/多行标签/sortUrl 解析/翻页/预加载/DiffUtil/位置记忆/路由）
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 pages-inventory D4），task 12.40
