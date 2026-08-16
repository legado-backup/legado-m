# P6 发现 / 网络书城（Explore）

> **待改造页升级 v2（2026-08-13）**：对齐 ExploreFragment View 现状（P1 待接线）+ 登记 v2.8 预审 V1-V17 违例 + 内核红线。另一 AI 开发本页时只读本文档 + ui-standards §3.4 规格书。

## 0. 页面身份

- **页面名 / 文件锚点**：ExploreFragment（`ui/main/explore/`，View + ExploreViewModel + ExploreAdapter + SourceFolderAdapter）
- **骨架归类**：S2 列表管理页（分组网格/文件夹/探索控件 3 形态）
- **对应 task**：tasks.md `12.16m`（v2.8 预审 A7）；pages-inventory A7
- **fork 借鉴来源**：forks-deep-dive §11（325506 导航路由）、§7（SourceFolderAdapter 分组）；MoRealm 书源管理

## 1. 设计意图（一段话）

发现页是**全局搜索入口 + 书源分组导航中枢**，核心目标 = **2 步到达目标书城**。与旧版差异：顶栏搜索高亮（全局搜索入口）、分类网格圆角卡片、最近更新横排。**本文档是验收的「为什么」：发现页改造必须保留「探索控件 JS 双求值链」内核红线（evalUiJs/evalButtonClick），同时把搜索/弹窗/菜单/状态收敛到公共组件体系。**

## 2. 布局结构（文字框图 + 区块表）

```
┌──────────────────────────────────────┐
│ 搜索顶栏（Scope V1=私有 SearchView 待  │ ← V1 搜索框待换 SettingsSearchBar
│ 换；Scope V17=顶栏 TitleBar 待换       │   V17 顶栏待换 GlassTopAppBar
│ SettingsSearchBar + GlassTopAppBar）  │
├──────────────────────────────────────┤
│ 分组 Tab / 文件夹视图（V2/V6/V10）      │ ← 按类型5Tab / 按分组动态Tab / 文件夹网格
├──────────────────────────────────────┤
│ 列表 / 探索控件（flexbox 展开）          │ ← 5 种探索控件：url/button/text/toggle/select
├──────────────────────────────────────┤
│ 空态 / 加载态                          │ ← V12：空态裸 TextView → EmptyStatePlaceholder
└──────────────────────────────────────┘
```

| 区块 | 组件（含规格引用） | 数据来源 | 备注 |
|------|-------------------|----------|------|
| 顶栏搜索 | `SettingsSearchBar`（§3.4：待接线）+ 搜索词升 StateFlow | ExploreViewModel | V1/V8 待修 |
| 顶栏 | `GlassTopAppBar`（§3.4：surface 实底） | — | V17 待修 |
| 分组 | `GroupHeader`（§3.4：titleSmall Bold + 徽标） | 分组 6 分支查询 | V10 待修 |
| 文件夹网格 | BoxWithConstraints 断点自适应 | sourceKinds 缓存 | V13 待修 |
| 列表项 | `SettingsClickRow`/`SettingsToggleRow` 复用 | Room Flow | 探索控件保留内核 |

## 3. 组件选型（强制引用 §3.4 规格书）

| 组件 | §3.4 规格摘要（圆角/间距/字号/色槽） | 本页使用点 |
|------|-----------------------------------|-----------|
| `GlassTopAppBar` | surface 实底、titleMedium | 顶栏（V17 待接线） |
| `SettingsSearchBar` | 搜索栏（孤儿） | 顶栏搜索（V1 待接线） |
| `GroupHeader` | titleSmall Bold、行≥48dp、整行折叠 | 分组渲染（V10 待接线） |
| `EmptyStatePlaceholder` | Icon 48dp + 标题 + 副标 | 空态（V12 待接线） |
| `SettingsClickRow` | h16 v12、bodyLarge、行≥48dp | 列表项（探索列表） |
| `SettingsToggleRow` | h16 v12、bodyLarge、v12 垂直内边距 | 探索控件 toggle |

> ⚠️ `SettingsSearchBar` §3.4 当前「孤儿未接线」，接线后登记 ✅；引用前确认无硬编码中文「搜索设置」。

## 4. 交互流程

| 触发 | 行为 | ≤2 步？ | 备注 |
|------|------|--------|------|
| 点分类卡片 | 进 ExploreShowActivity（保留加载/分页） | ✅ | |
| 点搜索框 | 进 SearchActivity 搜索结果页 | ✅ | |
| 长按分类 | 编辑书源/分组（V3 PopupMenu 待下沉 AppMenuSheet） | ✅ | V3 待修 |
| 下拉刷新 | 加载最新书目 | ✅ | |
| 探索控件 | 5 种控件 JS 求值（url/button/text/toggle/select） | — | **内核红线：evalUiJs/evalButtonClick 逐字平移** |

## 5. 状态管理（§4 范式）

- **⚠️ V6 违例待修**：ExploreViewModel 26 行零数据流 + Fragment 私有态（currentGroup/currentType/isShowingFolder）+ Adapter 持 exIndex/scrollTo/lastClickTime/sourceKinds 五份运行时状态——需收敛为 VM StateFlow + 受控组件。
- 数据源：Room Flow + `flowWithLifecycleAndDatabaseChange`（已合规 ✅）
- **内核红线**：InfoMap LruCache(99)/sourceKinds 缓存/SourceLoginJsExtensions 桥被 WebBook+BookSourceExtensions 跨模块引用，**逐字平移**；ExploreKind.equals 只比 title/type/url/action/default 不含 chars/viewName/style——§4.3 陷阱适用，Compose 化需 Ui 轻量模型或拆易变参数。

## 6. 三态（加载/空态/错误态）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | 现状无骨架屏 | **V13 待修**：页面级骨架屏 |
| 空态 | 裸 TextView（fragment_explore.xml:35-47） | **V12 待修**：`EmptyStatePlaceholder` |
| 错误 | 仅 AppLog.put 无占位 | **待修**：错误占位 + 重试 |

## 7. i18n 与无障碍

- **⚠️ V7 待修**：英文 strings.xml 中文值 5 key（type_text..type_video）+ source_group_mode* + layout_list_compact
- **⚠️ V8 待修**：view_search.xml:19 搜索硬编码（共享 17 页继承）——**P1 接线前置序第一位**
- **⚠️ V9 待修**：日志中文（发现界面更新数据出错 :380）
- **⚠️ V14 待修**：触控目标不足（item_find_book.xml:34,43 20dp 图标）
- 新增文案走 strings.xml（zh+en）双语；Icon contentDescription。

## 8. 验收标准（另一 AI 交付前必须逐条通过）

- [ ] 布局与 §2 框图一致（搜索顶栏 + 分组/文件夹 + 列表/探索控件）
- [ ] 组件全部来自 §3 表，规格与 §3.4 逐项一致
- [ ] **内核红线**：evalUiJs/evalButtonClick JS 双求值链 + InfoMap LruCache + sourceKinds 缓存 + SourceLoginJsExtensions 桥逐字平移，行为零漂移
- [ ] **P1 接线前置序全过**：V8（view_search 中文 hint）→ V1（SettingsSearchBar+StateFlow）→ V17（GlassTopAppBar）→ V2（ListLayoutMenu）→ V3/V4/V5（菜单/Dialog 族）→ V10（GroupHeader）→ V7/V12/V16（i18n/空态/回执门禁）
- [ ] 三态齐全；空态/错误态文案 i18n
- [ ] 无硬编码色/字号；无私有复制组件
- [ ] 真机功能点覆盖用例全过（FR-11，MEmu+ai_tests\venv）
- [ ] §3.3 实施回执已填（tasks + pages-inventory A7）
- [ ] grep 无 `android.util.Log.d/e` 残留

## 9. 绘图 Prompt（可选）

```
Material 3 Android 阅读App"发现"网络书城页高保真：顶部醒目圆角搜索框，
下面2列分类图标卡片（圆形图标+中文名），底部一横滚动书籍封面推荐，
浅色米白背景大量留白，低饱和护眼，无高饱和装饰，中文界面
```

## 10. 变更记录

- 2026-08-13：v2 升级——对齐 ExploreFragment View 现状，登记 v2.8 预审 V1-V17 违例 + 内核红线（JS 双求值链逐字平移），P1 接线前置序（对应 task 12.16m）。
