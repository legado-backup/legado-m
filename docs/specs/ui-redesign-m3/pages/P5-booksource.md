# P5 书源管理（BookSource · S2 列表管理页样板）v2

> **本文档为 S2 支干样板页的详细设计文档**（另一 AI 交付书源管理 Compose 化时**唯一视觉依据**，配合 ui-standards §3.4 组件规格书使用）。2026-08-12 已接线 BookSourceScreen.kt(1006 行)+BookSourceItems.kt(430 行)，本文档对齐现状并固化规格。

## 0. 页面身份

- **页面名 / 文件锚点**：BookSourceActivity（View 壳）→ `ui/book/source/BookSourceScreen.kt` + `BookSourceItems.kt`
- **骨架归类**：S2 列表管理页
- **对应 task**：tasks.md 12.16q/r（首实施+修正门禁）、V-1~V-4 真机验证、pages-inventory C1
- **fork 借鉴来源**：forks-deep-dive §7.1 HapeLee / §7.3 MoRealm / §11.3 325506（ListScaffold/7 导入三处分叉）

## 1. 设计意图

书源是阅读器最高频管理页。目标：**三视图（列表/紧凑/网格）可切换 + 分组折叠 + 多选批量 + 搜索过滤**，一屏不丢核心功能点；样式统一走 §3.4 规格书，杜绝「巨丑/丢三拉四」。现状：ListLayoutMenu 已接入三视图+排序 6、SelectActionBarCompose 批量栏、多选状态收敛（isSelecting=selectedUrls 派生）。

### 1.1 fork 差异化设计采纳（把 forks-deep-dive §7.1/§7.3 的学习落到本页结构，非只引番号）

| # | 差异化设计 | fork 来源 | 在本页落点 |
|---|-----------|----------|-----------|
| F1 | **条目卡片化**：选中 2dp `primary` 描边 + 背景色动画（enabled=surfaceContainerHigh / disabled=surfaceVariant 30%）+ 主行名称+校验分 N/4（≥4 tertiary / ≥2 secondary / else error Bold）+ 副行 group·url | MoRealm SourceItem | §2/§3 条目：`BadgeDot` 源类型徽标保留，条目宽化，编辑/删除进 `AppMenuSheet` 不再三按钮并排 |
| F2 | **登录态 AssistChip**：配 loginUrl 才显示，已登录 `✓ primaryContainer` / 未登录 `LockOpen outlined` | MoRealm | §3 组件表新增 `AssistChip`（待建，登录辅助） |
| F3 | **空态 CTA**：图标 48dp + 「暂无书源/无匹配结果」+ CTA 按钮「导入书源」 | MoRealm | §6 空态 `EmptyStatePlaceholder` 补 CTA 按钮链导入 |
| F4 | **统计条**：Search 下「共 N 个书源 / 启用 M」labelSmall | MoRealm | §2 搜索区下补统计条（启用数/总数） |
| F5 | **排序交互**：点同维度翻升降序、点新维度切 key 保留方向；enum 用 **String key 持久化**（非 ordinal） | MoRealm | §5 排序：`ListLayoutMenu` 排序项补「点同维翻转 + String key 持久化」 |
| F6 | **拖拽排序**：`sort==Default && !groupByDomain` 时可拖拽，拖完 diff 对比防无变化提交 | HapeLee ReorderableSelectionItem | §4 交互：分组态外网格/列表支持拖拽排序（成本可控，P2 待定） |
| F7 | **多选选中集持久化**：`selectedUrls = rememberSaveable(listSaver)` + BackHandler 优先退多选（现状已收） | MoRealm | §5 状态：补 `listSaver` 旋转存活 |
| F8 | **分组折叠**：折叠箭头 + 组名 titleSmall Bold + 「启用/总数」徽标 + 整行点击切折叠 | MoRealm GroupHeader | §2 分组：`GroupHeader` 补「启用数/总数」徽标（现状已有折叠，补徽标） |

> 🌐 **分组态渲染首选「单列表 + 分组折叠」**（fork 均单列表无三视图，`forks-deep-dive §7.4`）：三视图按原版红线保留，但分组态优先走折叠渲染路径（`GroupHeader`），而非切网格视图。

## 2. 布局结构

```
┌─────────────────────────────────────────┐
│ GlassTopAppBar 磨砂顶栏：返回│书源(N)│搜索│ListLayoutMenu│
├─────────────────────────────────────────┤
│ 分组筛选 Chips（全部/启用/分组，横向滚动单选）│
├─────────────────────────────────────────┤
│ LazyColumn/LazyVerticalGrid（三视图切换）  │
│ ┌─────────────────────────────────────┐ │
│ │ 条目：开关 │ 名称(16sp) │ 分组徽标 │   │ │
│ │        网址/最近(14sp 灰)             │ │
│ │        左滑=SwipeActionContainer      │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ SelectActionBarCompose 批量栏（选中时滑入）│
└─────────────────────────────────────────┘
```

| 区块 | 组件（规格引用） | 数据来源 | 备注 |
|------|----------------|----------|------|
| 顶栏 | `GlassTopAppBar`（§3.4：surface α0.86，API31+ blur 待修） | — | 16 项菜单已下沉 `AppDropdownMenu` |
| 布局切换 | `ListLayoutMenu`（§3.4 受控：当前值+onSelect 传入） | AppConfig 持久化 | 三视图+排序 6 |
| 分组 | 分组 Chips + `GroupHeader`（§3.4：h16 v8，titleSmall Bold） | VM StateFlow | |
| 列表 | `LazyColumn`+`BookSourceItems` 条目 | VM StateFlow | key=bookSourceUrl（§4.3 去重陷阱）；**网格断点已收敛（2026-08-13，源码核实 `BookSourceScreen.kt`）：列表/紧凑视图（currentLayout 0/1）= 单列 LazyColumn 无断点；网格视图（currentLayout 2，`:356-361`）`<400→2 / <600→3 / <800→4 / ≥800→6` 列；FolderGrid 文件夹网格（`:438-443`）`<400→3 / <600→4 / ≥800→5` 列；规格 §1.4 已同步对齐（原 480/840 废弃）** |
| 批量栏 | `SelectActionBarCompose`（受控批量栏） | selectedUrls 派生 | BackHandler 优先退多选 |

## 3. 组件选型（§3.4 规格引用）

| 组件 | §3.4 规格摘要 | 本页使用点 |
|------|-------------|-----------|
| `SettingsClickRow` | h16 v12、bodyLarge、onSurface/onSurfaceVariant | 紧凑视图行 |
| `BadgeDot` | error 底、10sp、>99 显示 99+ | 源类型徽标（用 SourceTypeBadge 语义色，§1.1 豁免④） |
| `SwipeActionContainer` | 左滑操作区固定宽、error 删除/primary | 条目左滑 |
| `AppMenuSheet` | AppModalBottomSheet、条目 h16 v12、destructive error | 长按富操作 |
| `EmptyStatePlaceholder` | Icon 48dp+title bodyLarge+subtitle bodyMedium | 空态 |
| `ShelfGridSkeleton` | 呼吸动画 surfaceVariant | 加载态 |
| `SettingsSearchBar` | 搜索栏（§3.4，已接线） | 顶栏搜索（接线于 BookSourceScreen.kt:215） |
| `SelectActionBarCompose` | 受控批量栏（对应真值表 `SelectActionBar` View 存量，Compose 侧迁移为受控批量栏） | 多选批量操作 |
| `AssistChip`（🆕 待建，fork F2） | 登录态辅助 chip：已登录 `✓ primaryContainer` / 未登录 `LockOpen outlined`，配 loginUrl 才显示 | 条目登录态（MoRealm F2） |

> ✅ 违例封口同步（2026-08-13 已随 §3.4 修复）：`GlassTopAppBar` 已降级 surface 纯色实底（无 blur 封口）；`SettingsCard` 圆角 12→18dp、内边距 12→16dp 已修。**待修违例**：`BookSourceItems.kt:357` `fontSize=24.sp` 硬编码字号（审计 2，见 §8）。

## 4. 交互流程

| 触发 | 行为 | ≤2 步 | 备注 |
|------|------|-------|------|
| 点击条目 | 进编辑（BookSourceEditActivity） | ✅ | 多选态时=勾选切换 |
| 长按条目 | 进多选（onItemLongClick=enterSelect） | ✅ | |
| 启用开关 | 即时启用/禁用（本地 db 不重请求） | ✅ | |
| 左滑 | 快捷：编辑/调试/复制 URL | ✅ | SwipeActionContainer |
| 顶栏更多 | 批量选择/导入导出（含智能导出 <30% 仅选中） | ✅ | AppDropdownMenu |
| 分组 chip 长按 | 分组管理 | ✅ | |
| 拖拽排序 | `sort==Default && !groupByDomain` 时条目可拖拽排序，拖完 diff 对比防无变化提交 | ✅ | MoRealm 改 HapeLee F6，P2 成本可控 |
| 物理返回 | 多选态优先退多选（BackHandler enabled=isSelecting） | ✅ | |

## 5. 状态管理（§4 范式）

- 数据源：`BookSourceViewModel` + `Room Flow`（bookSourceDao flowAll/flowSearch）→ `collectAsStateWithLifecycle`
- 多选态：**`isSelecting = selectedUrls.isNotEmpty()` 派生**（禁独立标志，§4.4）
- 搜索词：VM StateFlow（受控）；Compose 侧 searchVisible 与 View 侧 composeSearchQuery 状态**必须收敛到 VM**（R5 违例已修）
- 分组折叠集：`rememberSaveable`，切分组方式清空失效 key
- 排序：`ListLayoutMenu` 受控，**点同维度翻升降序、点新维度切 key 保留方向**（MoRealm F5），enum 用 **String key 持久化**（§2 S2 排序交互，非 ordinal）
- 多选选中集：`isSelecting = selectedUrls.isNotEmpty()` 派生 + `rememberSaveable(listSaver)` 旋转存活（MoRealm F7）

## 6. 三态

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载 | `ShelfGridSkeleton` | 首次加载 |
| 空态 | `EmptyStatePlaceholder`（title=book_source_empty_title 已 i18n）+ **CTA「导入书源」按钮**（MoRealm F3） | R4 已修 |
| 错误 | `EmptyStatePlaceholder` 错误分支 | |

## 7. i18n 与无障碍

- R3 已修：`BookSourceItems.kt:335`「源」硬编码→stringResource
- R2 已修：`sourceCoverColorPalette` 8 色 + `SourceTypeBadge` 4 色登记 §1.1 豁免
- 触控 ≥48dp；图标 contentDescription

## 8. 验收标准

- [x] 布局与 §2 框图一致
- [x] 组件全部来自 §3 表，规格对齐 §3.4（违例项登记待修）
- [x] 三态齐全；空态文案 i18n（R4）
- [ ] 无硬编码色/字号（R2，**待修**：`BookSourceItems.kt:357` `fontSize=24.sp` 硬编码字号，审计 2）;无垃圾代码
- [x] 搜索态收敛 VM（R5）
- [ ] 真机功能点覆盖全过（FR-11：三视图切换/排序/多选批量/分组折叠/搜索过滤/导入导出）
- [x] §3.3 实施回执已填（tasks 12.16q/r）
- [x] grep 无 `android.util.Log.d/e` 残留

## 9. 绘图 Prompt

```
Material 3 Android 阅读App 书源管理页高保真：卡片列表每行含圆形启用开关
+ 书源名 + 灰色网址，分组chips可横滑，扁平磨砂顶栏，留白充足，
一个卡片左滑露出底操作（编辑/调试），柔和低饱和配色，卡片圆角18dp。
```

## 10. 变更记录

- 2026-08-13：v1 按 v2 模板重写（对齐已接线现状 + §3.4 规格引用 + 验收清单）
