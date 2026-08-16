# P1 书架（Bookshelf 主 Grid）

> **已接线页升级 v2（2026-08-13）**：本文档为「对齐现状 + 登记违例」式升级，另一 AI 开发本页时只读本文档 + ui-standards §3.4 规格书，禁止自行发明样式。

## 0. 页面身份

- **页面名 / 文件锚点**：书架 BookshelfScreen（`ui/main/bookshelf/`，BookshelfScreen.kt + BookshelfItems.kt；View 壳 BaseBookshelfFragment + BooksFragment 遗留）
- **骨架归类**：S2 列表管理页（网格/列表双形态，页内分组 Tab）
- **对应 task**：tasks.md `12.16j`（v2.8 复审）、`14.2/14.3`（书架 P0 实施）；pages-inventory A3（style1）/A4（style2）/A5（View 壳）/A6（旧 BooksFragment，N 可删）
- **fork 借鉴来源**：forks-deep-dive §1（HapeLee/325506 FastScrollLazyVerticalGrid）、§9.2（legado-archive 书架）；MoRealm 网格角标

## 1. 设计意图（一段话）

书架是用户每日入口，核心目标 = **高频可达、一眼可读、分组清晰**。与旧版差异：① 网格封面双形态（网格/列表）已由 Compose `LazyVerticalGrid/LazyColumn` 统一；② 未读角标用页内 `ShelfUnreadBadge`（主题强调色 primary 底 + 亮度自适应文字 + 纯数字不截断）、加载态用 `ShelfGridSkeleton`、空/错态用 `EmptyStatePlaceholder`；公共 `BadgeDot`（error 底圆点+99+）仅底部导航 `PillNavigationBar` 接线。③ 分组 Tab + 下拉刷新 + 回顶保留原交互。**本文档是验收的「为什么」：书架页任何改造不得破坏「封面大图 + 圆角卡片 + 底部角标」的信息层级。**

## 2. 布局结构（文字框图 + 区块表）

```
┌──────────────────────────────────────┐
│ 分组 Tab（ScrollableTabRow 横向滚动）   │ ← A3 现状，分组筛选
├──────────────────────────────────────┤
│ ┌────┐ ┌────┐ ┌────┐                 │
│ │封面 │ │封面 │ │封面 │  LazyVerticalGrid │
│ │圆角 │ │    │ │    │  GridCells.Fixed  │
│ │书名 │ │    │ │    │  (1-4 用户选)       │
│ │●角标│ │    │ │    │  BadgeDot          │
│ └────┘ └────┘ └────┘                 │
├──────────────────────────────────────┤
│ 下拉刷新 PullToRefreshBox │ 空态/加载态占位 │
└──────────────────────────────────────┘
（View 壳 BaseBookshelfFragment 承载 12 菜单 + configBookshelf 对话框，红线保留）
```

| 区块 | 组件（含规格引用） | 数据来源 | 备注 |
|------|-------------------|----------|------|
| 分组 Tab | `BookGroupTabs`（ScrollableTabRow） | `upGroup()` LiveData | 现状保留 |
| 网格/列表 | `LazyVerticalGrid` / `LazyColumn` + `key` | `flowByGroup`+`sortedByBook` Room Flow | 列数由 `AppConfig.bookshelfLayout` 驱动 |
| 未读角标 | `BadgeDot`（§3.4：error 底/10sp/99+） | `showUnread` 配置 | 已接线 ✅ |
| 加载态 | `ShelfGridSkeleton`（§3.4：surfaceVariant/呼吸动画） | — | 已接线 ✅ |
| 空/错误态 | `EmptyStatePlaceholder`（§3.4：Icon48+标题+副标） | — | 已接线 ✅ |

## 3. 组件选型（强制引用 §3.4 规格书）

| 组件 | §3.4 规格摘要（圆角/间距/字号/色槽） | 本页使用点 |
|------|-----------------------------------|-----------|
| `ShelfUnreadBadge` | 页内私有：primary 底、8dp 圆角、labelSmall Bold 纯数字不截断、文字亮度自适应（badgeTextBright） | 网格/列表未读角标（BookshelfScreen.kt:332/:382/:518）✅ |
| `BadgeDot` | error 底、10sp Bold、count>99 显示 99+、-1 纯圆点 | 仅底部导航 PillNavigationBar（PillNavigationBar.kt:126）✅ |
| `ShelfGridSkeleton` | surfaceVariant 卡片、呼吸动画、按网格列数 | 首次加载（BookshelfScreen.kt:113）✅ |
| `EmptyStatePlaceholder` | Icon 48dp outline + 标题 bodyLarge + 副标 bodyMedium | 空态 + 错误态重试 ✅ |

> ⚠️ §3.4 组件均 ✅ 无 🔴，可直接引用。本页私有组件 1（ShelfUnreadBadge，对齐原版 BadgeView 未读角标形态，不归入 §3.4 公共组件族）。

## 4. 交互流程

| 触发 | 行为 | ≤2 步？ | 备注 |
|------|------|--------|------|
| 点击封面 | 进书籍详情 BookInfo / 直达正文（设置项可选） | ✅ | 现状 |
| 长按封面 | 阅读/详情/置顶等操作 | ✅ | A3 现状 |
| 点击分组 Tab | 切换分组，`saveTabPosition` 记忆 | ✅ | |
| 下拉刷新 | `PullToRefreshBox` 重新拉取 | ✅ | |
| 点击分组 Tab 重选 | `gotoTop()` 回顶 | ✅ | A1 手势 |
| 顶栏搜索 | 进书籍搜索（ContentResolver 应用内+网络同步） | ✅ | |

## 5. 状态管理（§4 范式）

- 数据源：`flowByGroup` + `sortedByBook`（Room Flow）→ `collectAsStateWithLifecycle`；ViewModel 收敛（style1/style2 各写一份 upConnect/loading/booksJob 重复订阅归 Phase4 收敛队列）
- 受控组件：`LazyVerticalGrid` 数据流 + `upGroup()` LiveData，状态提升
- **⚠️ 违例待修（v2.8 V1）**：`BookshelfScreen:81-85` 5 项易变 Config 值用 `remember{}` 首帧快照（bookshelfLayout/showBookname/showUnread/showBookshelfReadProgress/showLastUpdateTime）——§4.2 违例，改设置在其它页后回书架不刷新。修复=P1 队列换 `AppConfigFlow`/`collectAsState` 或观察 EVENTBUS。
- **⚠️ §1.4 例外登记**：网格列数 `GridCells.Fixed(spanCount)`（BookshelfScreen:262）由用户显式选择（1-4 列）驱动，属用户控制，登记为 §1.4「网格列数随宽度自适应」例外（与 GeneratedCover 8 色同类豁免）。

## 6. 三态（加载/空态/错误态）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton`（BookshelfScreen:113 loading 分支） | 已接线 ✅ |
| 空态 | `EmptyStatePlaceholder`（图标+文案+去添加按钮） | 已接线 ✅ |
| 错误 | `EmptyStatePlaceholder` 错误分支 + 重试 | 已接线 ✅ |

## 7. i18n 与无障碍

- **⚠️ 违例待修（v2.8 V3）**：`BookshelfItems.kt:125` GeneratedCover 徽章 `"本地"/"在线"` 硬编码中文；BookshelfViewModel 业务 toast 5 处（"添加网址失败"/"添加网址出错"/"导出书籍出错"/"格式不对"/"书籍不能为空"）；BaseBookshelfFragment waitDialog `"添加中..."`×2——入 §6.1 存量清零清单，随改造迁移 strings.xml（zh+en）。
- 触控 ≥48dp；封面图 contentDescription；颜色只 colorScheme。

## 8. 验收标准（另一 AI 交付前必须逐条通过）

- [ ] 布局与 §2 框图一致（分组 Tab + 网格/列表 + 下拉刷新 + 三态齐全）
- [ ] 组件全部来自 §3 表，规格与 §3.4 逐项一致
- [ ] **V1 已修**：5 项易变 Config 值不再 `remember{}` 帧固定（改 Flow/事件刷新）
- [ ] **V3 已修**：GeneratedCover 徽章 + VM toast + waitDialog 全部 strings.xml 双语
- [ ] 无硬编码色/字号；无私有复制组件（私有组件 0 保持）
- [ ] 真机功能点覆盖用例全过（FR-11，MEmu+ai_tests\venv）
- [ ] §3.3 实施回执已填（tasks + pages-inventory A3）
- [ ] grep 无 `android.util.Log.d/e` 残留

## 9. 绘图 Prompt（可选）

```
Material 3 Android 阅读App 书架页 高保真UI：3列圆角封面网格（封面16:9），
浅色米白主题大量留白，顶部分组Tab横向滚动，封面圆角卡片18dp，
底部小圆点未读角标，封面下方书名灰字，底部NavigationBar 4个圆角图标Tab，
整体低饱和护眼色，无高饱和撞色，像素精度，中文界面
```

## 10. 变更记录

- 2026-08-15（D-9 回填）：未读角标真实实现为页内私有 `ShelfUnreadBadge`（primary 底/8dp 圆角/纯数字不截断/文字亮度自适应），此前声明 `BadgeDot` 已接线 BookshelfItems.kt:323/:449 实为不存在（文件仅 124 行）；回填真实实现并将 `BadgeDot` 接线改回仅 `PillNavigationBar`。色槽定案=主题色 primary（响应 b6 需求），硬编码 Color.White 已收敛为 badgeTextBright 自适应。
- 2026-08-13：v2 升级——对齐 BookshelfScreen 已接线现状（BadgeDot/ShelfGridSkeleton/EmptyStatePlaceholder 三组件接线 ✅），登记 V1（Config 快照）/V3（i18n）违例修复队列（对应 task 12.16j 复审清单）。
