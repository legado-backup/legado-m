# L-D7 订阅收藏（RssFavorites）轻量设计文档

> **轻量版**：本页继承族文档 `pages/P7-rss.md`（S2 列表管理骨架），本文只写「继承 + 差异」。开发本页只读本文档 + P7 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：RssFavoritesActivity + RssFavoritesFragment（`ui/rss/favorites/`，View，复用 fragment_rss_articles）
- **所属族文档**：`pages/P7-rss.md`
- **骨架归类**：S2 列表管理页
- **对应 task**：tasks.md `12.5E`；pages-inventory D7（优先级 P3）
- **fork 借鉴来源**：无独立借鉴

## 1. 继承声明（本页复用什么）

- 复用骨架：S2 列表管理骨架（见 P7 §2）+ 复用 D4 fragment_rss_articles 文章列表
- 复用组件（§3.4）：`GlassTopAppBar`、`EmptyStatePlaceholder`、`ConfirmDialog`
- 复用状态范式：ViewModel + Room Flow（rssStarDao）；分组 Tab 动态

## 2. 差异点（与族文档唯一不同处）

| 维度 | 本页差异 | 说明 |
|------|---------|------|
| 布局结构 | 分组 Tab（rssStarDao.flowGroups 动态 + 单组隐藏）；ViewPager 滑动切换 | 独有 Tab 结构 |
| 交互 | 菜单跳转分组 setCurrentItem；onResume 定位当前分组 | 独有 |
| 功能点 | 删除整组 deleteByGroup；删除全部 deleteAll | 批量删除 |
| 条目 | 点击→ReadRss.readRss；长按→delStar 确认 | 复用 D6 路由 |

## 3. 组件选型（§3.4 规格引用，仅列差异组件）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `EmptyStatePlaceholder` | Icon 48dp + 标题 + 副标 | 空收藏 |
| `ConfirmDialog` | M3 AlertDialog 卡 18dp、destructive 确认钮 error | 删除整组/全部/条目确认 |

## 4. 三态（继承族文档，仅列差异）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 收藏列表骨架屏 |
| 空态 | `EmptyStatePlaceholder` | 空收藏/空分组 |
| 错误 | `EmptyStatePlaceholder` | 错误分支 + 重试 |

## 5. i18n 与无障碍

- 新文案 `strings.xml` 双语；无硬编码中文/色/字号（同族文档）；分组 Tab 触控 ≥48dp

## 6. 验收标准（轻量）

- [ ] 复用 S2 骨架 + fragment_rss_articles，无私有复制组件
- [ ] 功能点对照 pages-inventory D7 无遗漏（分组 Tab/ViewPager/菜单跳转/onResume 定位/删除整组/删除全部/条目点击长按）
- [ ] 三态齐全；i18n 通过
- [ ] 真机功能点覆盖用例通过；§3.3 实施回执已填

## 7. 变更记录

- 2026-08-13：初始建立（关联 pages-inventory D7），task 12.5E
