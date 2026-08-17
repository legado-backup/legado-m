# 前端 UI 工程规范 · ui-standards（权威）

> 本文件是 ui-redesign-m3 的**工程级标准规范**，回答硬约束：「统一样式风格布局、全前端每页复用、工程级项目级标准、能指导后续优化其它页面时快速知晓规范」。
> 任何新页面 / 改页面 / Compose 化，**先查本规范**：① 定页面类型骨架 → ② 从组件六族选组件 → ③ 套主题/状态/三态规范 → ④ 过改造检查清单 → ⑤ 写真机功能点覆盖用例。
> 配套文件：pages-inventory.md（全量84页功能点核对表）、design.md（ADR 决策依据）、implementation-spec.md（组件签名规格）。

---

## 1. 设计基石（Design Foundation）

### 1.1 主题接入（强制）
- **所有 Compose 页面必须包 `LegadoTheme {}`**（读 ThemeStore 5 核心色 → `ThemeSpec.toM3Scheme()` → MaterialTheme 34 槽位）。
- 需要背景图时用 `ComposeActivitySupport.setLegadoContent / LegadoThemeWithBackground`（debug 工具族已用此模式）。
- 页面内**禁止** `Color(0x...)` 硬编码色值；必须取自 `MaterialTheme.colorScheme` 或 `ThemeSpec` 派生槽位。
- 字体：禁止写死字号；用 `MaterialTheme.typography`（M3 13 级 scale，见 android-ui-optimization spec）。
- 圆角：`corner_*` token（4/8/12/16dp），**卡 18dp / 按钮 12dp** 为全局默认（Design Pillar）。
- 间距：4dp grid，档位 4/8/12/16/24/32；触控目标 ≥48dp。

> **例外登记（2026-08-11 实施者复盘，2026-08-12 增补）**：①「封面视觉定色」允许 `Color(0x...)`——`BookshelfItems.kt:98-105` GeneratedCover 8 色渐变（BlueGrey800/BlueGrey700/Brown800/Brown700/Grey800/BlueGrey600/Brown900/Grey700）与书架 MoRealm 封面风格绑定，属内容呈现非 token 语义色，登记豁免后计入 KPI「非内核页硬编码色=0」的已知例外清单；② 阅读器内核（TextChapterLayout 等 N 不迁移页）沿用原色，豁免同款登记；③ **书源封面定色**（2026-08-12 v2.11 BookSource 复审 R2 登记）——`BookSourceItems.kt:312-321` `sourceCoverColorPalette` 8 色（BlueGrey800/BlueGrey700/Brown800/Brown700/Grey800/BlueGrey600/Brown900/Grey700）为书源封面视觉定色，同称 GeneratedCover 封面范式，豁免登记；④ **书源类型徽章语义色**（2026-08-12 R2 登记）——`BookSourceItems.kt:381-387` `SourceTypeBadge` 按类型（text/audio=#4CAF50/image=#2196F3/file=#FF9800/video=#E53935）固定语义色，属类型分类标识色，豁免登记（后续可按需收敛为 `ThemeSpec` 语义槽位）。

### 1.2 主题色使用优先级
1. `MaterialTheme.colorScheme.primary / onPrimary / surface / surfaceVariant / outline` 等 34 槽位
2. `ThemeSpec` 派生工具（contrastOn 等）
3. 语义色：error 用 M3 标准红（夜 `#FF897D`）
4. ⚠️ 阅读器内（ReadBookConfig 独立配色）不套用全局，走 `ReadBookConfig` 每书配色（红线）

### 1.3 布局栅格
- 页面边距 16dp；卡片间距 8-12dp；列表项 48dp 基准高；分组标题 8dp 间距。
- 同类型页（列表管理/表单编辑/详情）骨架必须一致（见 §2）。

### 1.4 方向与自适应（统一策略，禁止页面另起方向逻辑）

> 核验（2026-08-11）：源码已有方向控制体系但文档未固化，Compose 化时若各页自行处理会失统一。以下为唯一方向策略：

- **阅读器方向**：由用户设置驱动——`AppConfig.screenOrientation`（0-5：unspecified/portrait/landscape/sensor/reverse_portrait/reverse_landscape，MoreConfigDialog 可配），`BaseReadBookActivity` 统一应用。Compose 化保留该逻辑，不做别的方向分支。
- **WebView 内容方向**：书源/订阅源 JS 可控制方向（`portrait`/`portrait-primary`/`landscape`/`any` 等字符串 → ActivityInfo 映射，见 WebViewActivity/BottomWebViewDialog/ReadRssActivity），**内容驱动方向，页面不拦截**。
- **沉浸页全屏方向**：Video 按 `VideoPlay.isPortraitVideo` 在 SENSOR_PORTRAIT/LANDSCAPE 间切换；退出全屏还原。Audio/ImageGallery/漫画沿用各自自适应逻辑。
- **configChanges**：Manifest 已声明 `locale|keyboardHidden|orientation|screenSize|smallestScreenSize|screenLayout|uiMode`——Compose 页面状态用 `rememberSaveable` 保活，**不得依赖 Activity 重建恢复方向态**。
- **新页面方向**：一律不写 `requestedOrientation`，跟随系统；仅上述三类既有场景保留方向控制。
- **大屏/横屏自适应**：网格类列表（书架/书源/订阅源/探索）列数随宽度自适应（`BoxWithConstraints` 或 maxWidth 断点）。**断点收敛（2026-08-13，以已接线 S2 样板实际实现 `BookSourceScreen.kt` 为准）**：书源网格视图（currentLayout 2）`<400dp→2 / <600dp→3 / <800dp→4 / ≥800dp→6` 列；书源列表/紧凑视图（currentLayout 0/1）= 单列 LazyColumn 无断点；FolderGrid 文件夹网格 `:438-443` `<400dp→3 / <600dp→4 / ≥800dp→5` 列。~~原紧凑<480/中等480-840/宽≥840 废弃~~。`ListLayoutMenu` 网格 N 列入参已支持。**维度澄清（2026-08-13 审计定案）**：网格列数档位（400/600/800）是**内容自适应档位**，独立于任何页面骨架断点；本 §1.4 不再做全局骨架断点（紧凑/中/宽）约束，各页网格列数按上表执行即可。

---

## 2. 页面骨架模板（6 类，全站复用）

> 每类骨架 = 「标准结构 + 组件选型 + 状态管理范式」。改造任何页面先归入一类；**同一类页面不允许各写各的布局**。

### S1 主框架 Tab 页（MainActivity）
- 结构：`PillNavigationBar`（AD-17）+ 内容区 + 可隐藏 Tab + 角标 `BadgeDot`。
- 现况：MainActivity 用 BottomNavigationView → 待换 PillNavigationBar；角标书架上新已实现。

### S2 列表管理页（书源/替换/词典/书架/搜索/发现/RSS/设置子页等）
- 结构：`GlassTopAppBar`（磨砂顶栏：返回/标题/搜索入口/菜单）→ `SettingsSearchBar`（需搜索时）→ `LazyColumn / LazyVerticalGrid` 列表 → 底部行为栏/空态。
- **搜索（统一）**：凡含搜索的列表页（书架搜索/书源筛选/订阅源搜索/全局搜索/发现搜索）一律走 `SettingsSearchBar` + 搜索词升到 ViewModel StateFlow（受控组件），禁止各页写私有收缩式搜索框。
- 列表项选型：
  - 设置/配置行 → `SettingsClickRow` / `SettingsToggleRow`
  - 卡片分组 → `SettingsSection` + `SettingsCard`
  - 摘要/入口 → ~~`SummaryCard`~~（已删除 2026-08-16 孤儿清理）
  - 统计 → `MetricGrid`
  - 数字角标 → `BadgeDot`（**禁止页面私有复制角标**）
- 手势：左滑操作 → `SwipeActionContainer`；长按菜单 → `AppMenuSheet`（BottomSheet 富操作）；顶栏更多/条目更多 → `AppDropdownMenu`（替代全仓 20+ 处私有 PopupMenu）；多选批量 → `SelectActionBar`（公共组件，见 §3）。
- **布局切换 + 排序（统一组件 `ListLayoutMenu`，禁止各页私有实现）**：凡列表页需切换展示样式（列表/紧凑/网格 N 列/带图）或需排序（多选项+升降序），统一用 `ListLayoutMenu`（顶栏菜单，含当前态持久化）。页面只传入：布局选项（图标+label）/排序选项（key+label）/当前值/onSelect。覆盖：书架 layout1/2、书源三视图（列表/紧凑/网格 2-6）、订阅源三视图+文件夹、RSS 文章 5 样式、替换/词典拖拽排序、ReadRecord 排序。
  - **排序交互（fork 采纳，2026-08-11，from MoRealm BookSourceManageScreen）**：下拉首行独立「当前：升序（点切降序）」条目；维度列表当前项 ✓+primary；**点同维度 = 切升降序，点新维度 = 换 key 保留方向**；排序 enum 用 String key 持久化（禁 ordinal，防增删枚举旧值崩溃，MoRealm `SourceSortKey.fromKey` 容错 fallback）。
- **分组列表（统一 `GroupHeader`，2026-08-11 fork 补证新增）**：凡列表页按 分组/域名/类型 聚合（书源、订阅源、发现、替换等有分组含义的列表），统一用分组 Chips（筛选当前分组方式，横向滚动单选）+ 可折叠 `GroupHeader`（MoRealm 模式）：
  - 结构：折叠箭头（右/下）+ 组名（titleSmall Bold）+ **「启用数 / 总数」徽标** + 组操作菜单（全部启用 (N)/全部停用 (N)，数量写进文案，由 `AppMenuSheet`/`AppDropdownMenu` 承接）。
  - 整行点击切折叠；折叠集 `rememberSaveable` 保存，切分组方式时清空失效 key；LazyColumn 内 `key = "group:xxx"` + contentType 分组头。
  - 覆盖：书源（domain/类型/分组）、订阅源（类型/分组）、发现、替换词典等。与 `ListLayoutMenu` 配合：布局切换（列表/网格）+ 分组折叠为并行的两种组织方式（原版三视图保留，分组态优先走折叠渲染）。
- **多选列表（fork 采纳，2026-08-11）**：选中集 `rememberSaveable(listSaver)` 保存（旋转/进程死亡不丢）；`BackHandler(enabled = isSelecting)` **物理返回键优先退出多选**；批量条 `SelectActionBar`；支持滑选（`DraggableSelectionHandler` 覆盖层，HapeLee 模式）。
- 加载态：首次加载 `ShelfGridSkeleton`（骨架屏，替代 CircularProgressIndicator）；增量刷新 `PullToRefreshBox`；空态统一占位（图标+文案+操作按钮）。
- 状态管理：**列表数据 = ViewModel + StateFlow/Flow.collect（受控组件模式）**，禁止 Fragment 内散落多个 `mutableStateOf` 订阅重复逻辑（见 §4）。

### S3 表单/编辑器页（书源编辑/替换编辑/自动任务/词典/CodeEdit 壳）
- 结构：`GlassTopAppBar` + 表单容器（`SettingsCard` 分组字段）或代码编辑区 + 底部保存/取消。
- 编辑页共性（from CodeEdit 系）：KeyboardToolPop（undo/redo/帮助插入）、全屏编辑跳 CodeEditActivity、未保存退出拦截。
- 规则字段输入：CodeView + `addLegadoPattern/addJsonPattern/addJsPattern` 补全（内核行为，保留）。
- 状态管理：字段全部提升为 `ViewModel` 数据类 + `onSave` 校验；未保存拦截用 `runCatching` 对比原始值。

### S4 详情/阅读页（书籍详情/BookInfo/ReadRss/WebView 壳）
- 结构：可滚动主体 + `GlassTopAppBar` + 底部操作栏（或 Sheet）。
- 详情页 `BookInfo`：共享折叠封面 + 多 Tab 信息流（P3 大纲）。
- 阅读页：**正文引擎保留原生 View（AD-02）**，浮层/菜单/设置全部 `AppModalBottomSheet`（AD-06 Sheet hub）。
- 长按/点击：沿用原九宫格/选词/文本工具条逻辑（内核交互，保留）。

### S5 全屏沉浸页（阅读器/漫画/音频/视频/图片画廊）
- 结构：沉浸式 edge-to-edge（`enableEdgeToEdge`）+ 浮层自动隐藏（3s）+ 边缘返回。
- 手势：保持各页独有手势（漫画 WebtoonFrame/视频双指/图片画布）——**沉浸页允许专属交互，但视觉 token（角标/进度条/工具条样式）复用全局**。
- 浮层组件：`AppModalBottomSheet` / `BookTocBookmarkSheet`（目录书签高亮三 Tab）。
- **阅读器框架（2026-08-11 补充，见 pages/P2-reader.md 权威版）**：正文 View + 浮层 Compose 壳-核分离（推翻早期"阅读页不动"保守结论，fork 已验证：HapeLee AndroidView 桥接 / MoRealm 仿真翻页退回 View）——
  - 正文引擎（ReadView/PageView/page/ 29 文件）**零改动**（AD-02 红线 6 条见 P2-reader §四）。
  - UI 壳（read_menu/search_menu/config 弹窗族/TextActionMenu）**渐进 Compose 化**：`ReadBookRouteScreen` 编排壳 + `ReadBookController` 多接口桥接 + `ReaderViewport` 尺寸接缝。
  - 弹层统一**单一 `activeSheet` 单态 + 三类渲染**（常驻 show / when 条件 / activeDialog）；BackHandler 优先级链（弹层→搜索→自动翻页→菜单路由→退出）。
  - 顶/底栏：磨砂（半透明 surface + RenderEffect blur API31+，低版本纯色降级，**不引第三方 blur 依赖**）+ Material Slider + 拖动时菜单 alpha≤30% 实时预览；底栏支持悬浮药丸形态。
  - 迁移路径 R0-R4（桥接层→菜单壳→弹层单态→搜索层→选区/胶囊），每阶段过 §7 检查清单 + §3.3 回执。

### S6 弹窗/透明窗（登录/扫码/验证码/协议分发/导入确认）

> 用户追问（2026-08-11）：弹框布局样式/风格是否有统一组件化方案？——设计：**弹窗统一三层体系**（详见下方），存量 Dialog（确认/输入/数字选择/文本查看等全仓几十处）逐类收敛到统一 Dialog 组件族，页面禁止各写各的弹窗样式；阅读器浮层按 AD-06 走 Sheet hub。

- **L1 浮层面板**（内容多/需多 Tab/可拖拽）→ 统一 `AppModalBottomSheet`（Sheet hub，AD-06；阅读器目录/书签/高亮/设置/搜索浮层等）。
- **L2 语义 Dialog 族**（轻量单刻意交互，M3 居中对话框）→ 统一组件族（见 §3 组件表）：`ConfirmDialog`（确认/删除）、`AppEditDialog`（单/多字段文本输入，替代 DialogEditText/规则小窗）、`AppSelectDialog`（单列表选择，替代 GroupSelectDialog/SourcePicker/主题列表）、`AppNumberPickerDialog`（替代 NumberPicker 系）、`AppTextDialog`（文本/MD/HTML 查看，替代 TextDialog/MD Dialog/更新日志）、`AppWaitDialog`（阻塞等待，替代 WaitDialog）。**全部复用 Settings* 行/卡片 + MaterialTheme，禁止页面私有 Dialog 布局**。
- **L3 透明窗壳**（FileAssociation/OnLineImport/VerificationCode/OpenUrlConfirm）：保留系统透明样式壳（协议分发不可改），内容行统一 `SettingsClickRow`。

---

## 3. 组件目录（ui/widget/components/ 55 文件 + 待建清单下移）

> 使用规则：**先查此表再实现**。凡公共库已有组件，页面禁止私有复制实现（frontend-synthesis P4）。孤儿组件（未接线）在接线前标注 `@DesignPending` 或直接在本表标注状态。
>
> **待建组件（标 🆕 待建）规格 = §3.4 精确规格书（2026-08-13 收敛专项二已全部精确化）**：四维（容器/圆角、内边距、字号、色槽）+ 高度/触控逐项给精确值，且已逐组件挂精确 task（tasks.md §13，12.28-12.3C）。本目录只列组件族归属与用途，开发规格以 §3.4 为准。

| 族 | 组件 | 状态 | 用途 |
|----|------|------|------|
| **主题** | `ThemeSpec`（toM3Scheme/contrastOn/hueShift） | ✅ 在用 | 5色→34槽位 |
| **主题** | `ThemeSync`（全局版本信号） | ✅ 在用（主题架构 v2，2026-08-17） | applyTheme/recreateActivities bump→全 Compose 即时换肤（零重建）；LegadoTheme/GlassTopAppBar/PillNavigationBar/ThemeConfigScreen 组合中读 version 订阅 |
| | `ColorPickerSheet` | ✅ 在用（L-E2 主题设置页，2026-08-17） | 色盘弹层：MATERIAL_COLORS 预置网格+HSL 三滑块（色相彩虹渐变轨道）+hex 活预览；AppModalBottomSheet 容器 |
| | `SettingsColorRow` | ✅ 在用（L-E2 主题设置页，2026-08-17） | 色设置行（RowIcon+标题/副标+36×28dp 8dp 圆角色块预览，outlineVariant 描边） |
| **导航** | `PillNavigationBar` | ✅ 已接线（S1 MainActivity，2026-08-12） | S1 主框架底栏（AD-17） |
| **顶栏** | `GlassTopAppBar` | ✅ 已接线（S4 B6 BookInfoActivity，2026-08-12） | S2/S3/S4 磨砂顶栏 |
| **设置** | `SettingsSection` | ✅ 在用 | 分组标题 |
| | `SettingsCard` | ✅ 在用 | 卡片容器（标题+extra 插槽） |
| | `SettingsClickRow` | ✅ 在用 | 点击行（图标块+标题+副标+尾值+箭头） |
| | `SettingsToggleRow` | ✅ 在用 | 开关行（M3 Switch） |
| | `SettingsSelectableRow` | ✅ 已接线（DictRule/AutoTask/TxtTocRule，2026-08-16 P1 收敛 E4） | 多选+开关+拖拽行（72dp，受控 Checkbox/Switch/拖拽回调，替代三页逐字重复私有行） |
| | `SettingsSearchBar` | ✅ 已接线（S2 BookSource，2026-08-11） | 搜索栏（S2/S6 列表页搜索入口） |
| | `RowIcon` | ✅ 在用 | 统一 36dp 图标块（被 ClickRow/ToggleRow 复用） |
| | `MetricGrid` | ✅ 在用 | 统计卡网格 |
| | `SplicedColumnGroup` | ❌ 已删除（2026-08-16 孤儿清理） | 连体圆角组卡片 |
| **列表/展示** | `SummaryCard` | ❌ 已删除（2026-08-16 孤儿清理） | 摘要卡片 |
| **列表/展示** | `AssistChip` | ✅ 已建（2026-08-16） | 登录态辅助 chip（配 loginUrl 才显示，已登录 ✓ primaryContainer / 未登录 LockOpen outlined）；from MoRealm F2，P5 书源条目登录态（task 12.3C） |
| | `ShelfGridSkeleton` | ✅ 在用 | 书架骨架屏（呼吸动画） |
| | `VerticalScrollbar` | ✅ 已接线（2026-08-16 → DownloadManageScreen 下载管理页长列表滚动指示条） | LazyList/LazyGrid 快速滚动条 |
| **反馈** | `AppModalBottomSheet` | ✅ 已接线（Phase4 阅读器浮层/ImportSourceSheet/S6，2026-08-13） | 统一底部弹层容器（真值行 §3.4） |
| | `BookTocBookmarkSheet` | ✅ 已接线（S5 阅读器，2026-08-12 Phase4 12.24） | 目录/书签双 Tab Sheet（现状基座） |
| | `ThemedSnackbarHost` | ❌ 已删除（2026-08-16 孤儿清理） | 主题化 Snackbar |
| | `BadgeDot` | ✅ 在用（PillNavigationBar 接线） | 数字角标（count>99 显示 99+） |
| **Dialog 族** | `ConfirmDialog` | ✅ 已建（2026-08-12） | 确认/删除确认（L2）；destructive→确认钮 error 色 |
| | `AppEditDialog` | ✅ 已建（2026-08-12） | 单/多字段文本输入（EditField 列表，替代全仓 DialogEditText 系） |
| | `AppSelectDialog` | ✅ 已建（2026-08-12） | 单列表选择（RadioButton 高亮，替代 GroupSelect/SourcePicker/主题列表） |
| | `AppNumberPickerDialog` | ✅ 已建（2026-08-12） | 数字选择（Slider+输入双联动，替代 NumberPicker 系） |
| | `AppTextDialog` | ✅ 已建（2026-08-12） | 文本/MD/HTML 查看（Markwon 渲染，替代 TextDialog/MD Dialog） |
| | `AppWaitDialog` | ✅ 已建（2026-08-12） | 阻塞等待（替代 WaitDialog） |
| **菜单** | `AppMenuSheet` | ✅ 已建（2026-08-12） | 长按条目 BottomSheet 富操作（数据驱动 MenuAction 列表） |
| | `AppDropdownMenu` | ✅ 已接线（S4 B6 BookInfoActivity 16 项顶栏菜单，2026-08-12；MenuAction 扩展 checked 勾选态） | 顶栏更多/条目更多下拉（M3 DropdownMenu 封装） |
| | `SelectActionBar` | ✅ 已有（View） | 多选批量操作栏（ui/widget/SelectActionBar.kt，10+ 页在用；Compose 化时保留并迁移为受控组批量栏） |
| **导入** | `ImportSourceSheet` | ✅ 已接线（S6 ImportRssSourceDialog 样板，2026-08-13；8 个 Import Dialog 共用） | 导入类弹窗统一底部面板（顶部标题+菜单/列表勾选+状态徽标+底部全选-取消/取消/导入） |
| **交互** | `SwipeActionContainer` | ✅ 已接线（BookSourceItems，2026-08-16） | 左滑固定操作区 |
| **列表工具** | `ListLayoutMenu` | ✅ 已建 | 布局切换（列表/紧凑/网格 N 列）+ 排序（多选项+升降序）顶栏菜单，含当前态持久化（受控组件，当前值+onSelect 由页面传入/持久化，2026-08-11 落地） |
| **列表工具** | `LazyListFastScroller` | ⚠️ 孤儿 | LazyList 快速滚动条（FastScroller 吸附滚动） |
| **列表工具** | `GroupHeader` | ✅ 已建（2026-08-12） | 分组列表折叠头（折叠箭头+组名+启用数/总数徽标+组操作菜单），配合分组 Chips；from MoRealm BookSourceManageScreen（2026-08-11 核验） |
| **阅读器** | `ReadMenuGlassButtonSurface` | ✅ 已建（2026-08-16） | 阅读器顶/底栏按钮原语（玻璃 48dp/普通 40dp 圆形，selected 高亮+长按+自定义图标）；from HapeLee ReadBookMenuBar（2026-08-11）；**task 12.28** |
| | `ReadMenuSlider` | ✅ 已建（2026-08-16） | 阅读器进度/亮度 Material Slider（拖动时菜单 alpha≤30% 实时预览，松手 commit）；from HapeLee/MoRealm；**task 12.29** |
| | `ReaderBookSheet` | ✅ 已建（2026-08-16） | 目录/书签/高亮 三 Tab 弹层（TabRow+HorizontalPager，maxHeight 72%）；from HapeLee sheet/ReaderBookSheet；**task 12.2A** |
| | `ReaderMoreActionsSheet` | ✅ 已建（2026-08-16） | 更多操作弹层（4 列网格+分页，20+ 动作数据驱动+编辑模式）；from HapeLee；**task 12.2B** |
| | `ReaderViewport` | ✅ 已建（2026-08-16） | 正文尺寸接缝（width/height/density/padding/PAGED\|SCROLL\|DOUBLE_PAGE），coordinator 回调 `ChapterProvider::upViewSize` + `awaitViewport`；from HapeLee；**task 12.2C** |
| | `TextActionSelectionMenu` | ✅ 已建（2026-08-16） | 阅读器选区工具条（View 坐标锚点 textMenuPosition 桥接，色盘 2 行 6 色，无二级）；替换 TextActionMenu；from 现状 TextActionMenu；**task 12.2D** |
| | `HighlightStyleDialog` | ✅ 已建（2026-08-16） | 高亮选色 chooser（色板+下划线 2 行 6 色，直接改样式无二级）；升级自现有 HighlightStyleDialog（B1 阅读器）；**task 12.2E** |
| **列表工具** | `ListCard`（含 BookListCardMetrics） | ✅ 已建（2026-08-16） | 可复用条目卡片（clip 圆角+背景+heightIn+combinedClickable，布局与交互解耦，content 以 metrics 参数抛出）；from legado-archive BookListCardComponents（2026-08-12 深挖）；**task 12.2F** |
| **菜单族** | `ModernActionPopup` | ✅ 已建（2026-08-16） | 通用弹层菜单（Action(title,invoke) 数据驱动，替代全仓 PopupMenu/菜单入口）；from legado-archive（2026-08-12 深挖，全 fork 通用）；**task 12.31** |
| **Dialog 族** | ComposeDialog 家族（TextInput/TextForm/NumberPicker/MultiChoice/Confirm/SingleChoice/ActionList/FetchedModel） | ✅ 已建（2026-08-16） | 对齐 6 待建清单扩展：8 类 Compose Dialog 统一 AppDialogStyle 底框；TextInput/SingleChoice/ActionList 已落 3 类（TextInputDialog/SingleChoiceDialog/ActionListDialog，基于 BaseComposeDialogFragment）；from legado-archive AppComposeDialogs（2026-08-12 深挖）；**task 12.32** |
| **Dialog 族** | `BaseComposeDialogFragment` 基类 | ✅ 已建（2026-08-16） | 31 行 ComposeView+DisposeOnViewTreeLifecycleDestroyed+LegadoTheme 包裹，子类仅需实现 `DialogContent()` —— Dialog 族 6 统一宿主基类；from Legado_Max（2026-08-12 深挖，优先于自造骨架）；**task 12.33** |
| | `AppConfirmDialog` | ✅ 已建（2026-08-16） | Material3 AlertDialog 封装，destructive=true 时确认钮 error 色，14 处实战验证；from Legado_Max（2026-08-12 深挖）；**task 12.34** |
| | `MultiSelectDialog` 内容模型 | ✅ 已建（2026-08-16） | 分组多选+总大小+全选/全不选，MultiSelectItem/Group 数据模型干净；覆盖 Dialog 族缺失的「多选类」；from Legado_Max（2026-08-12 深挖）；**task 12.35** |
| **Sheet 导航** | Sheet 内多级导航模式 | ✅ 已建（2026-08-16） | sealed ManageScreen + AnimatedContent 横向滑动 + BackHandler 返回链，单 AppModalBottomSheet 承载 7 页面（SetList→SetDetail/BrowseSources→SourceBrowseDetail），对应 S6 弹窗多级页面统一方案；通用化 `ManageScreenHost`/`ManageScreenHeader` + sealed `ManageScreen(depth)`；from Legado_Max HomepageModuleManageSheet（2026-08-12 深挖）；**task 12.38** |
| **Sheet 导航** | `ManageScreenSheet`（落地文件） | ❌ 已删除（2026-08-16 孤儿清理） | 上述「Sheet 内多级导航模式」的落地实现文件（`ui/widget/components/ManageScreenSheet.kt`，暂无页面引用） |
| **统计** | `HeatmapCalendar` | ✅ 已建（2026-08-16） | 自包含纯 Compose 阅读热力图（661 行无第三方依赖）：入参仅 `dailyReadCounts/dailyReadTimes`、COUNT/TIME 双模式、归一化基线 6 次/120min、周一起始 chunked(7)、`lerp(primaryContainer α0.42, primary, (value/max)²)` 二次方强度、月份 3 Pill 统计、5 格图例；后端 1 条 GROUP BY date SQL（getDailyStats）；from Legado_Max（2026-08-12 深挖，★ 强烈建议搬运）；**task 12.39** |
| | `SummaryCard+BookStackView` | ❌ 已删除（2026-08-16 孤儿清理，About 页私有卡已注释登记） | 书籍数+总时长+封面错位堆叠（rotate ±3°）成就卡，与 MetricGrid 互补；from Legado_Max（2026-08-12 深挖）；**task 12.3A** |
| **主题** | `CommonPageColors` 深色自适应 | 🆕 规范 | 统一深色观感：`background.luminance()<0.18f` 判暗 + lerp 向亮抬升（卡片暗=lerp(surface,onSurface,0.06) α0.98/亮=surface α0.95）；弹窗顶栏=secondary(pageTopBarContainerColor)、卡片底=surfaceVariant(pageCardContainerColor)；from Legado_Max（2026-08-12 深挖，MetricTile 当前硬用 surfaceVariant 无暗色处理需对齐） |
| **列表交互** | 拖拽排序模式 | 🆕 规范 | ReorderableItem+LaunchedEffect 持久化+触觉反馈+hapticFeedback+zIndex 提升被拖项；from Legado_Max SetListPage/HomepageModuleManageSheet（2026-08-12 深挖，S2 列表管理页样板） |
| **导航** | Nav3 全局路由+Route 壳层模式 | 🆕 规范 | 单 Activity+Navigation3 全局路由表（14 sealed route+backStack 手动栈管理），Route 壳层=副作用编排与渲染分离；底部 Tab 用 HorizontalPager 不嵌套 NavHost（避免双栈）；二级页回调 navigateToRoute 控栈深；from 325506（2026-08-12 深挖，S1 主框架+BookInfoActivity 改造范本） |
| **列表工具** | `ListScaffold<T>`+`ListUiState<T>` 泛型模板 | ✅ 已建（2026-08-16，模板待用） | 一屏统一 DynamicTopAppBar(搜索/下拉)+选中滑入 SelectionBottomBar+FAB；ListUiState(items,selectedIds,searchKey,isSearch,isLoading)；from 325506（2026-08-12 深挖，S2 列表页通用模板）；**task 12.30** |
| **Dialog 容器** | `AppAlertDialog`/`AppModalBottomSheet` 双引擎封装 | ✅ 已建（2026-08-16） | 统一弹窗容器：`AppAlertDialog` 含 show/data 双变体+data 缓存末值播放退出动画+18dp 圆角（container surfaceContainerHigh/title onSurface/text onSurfaceVariant）；本项目无 Miuix 依赖，双引擎退化为单 M3 引擎，入口已收敛便于未来接引擎；`AppModalBottomSheet` 已建 M3 版；from 325506（2026-08-12 深挖，Dialog 族容器范本）；**task 12.36** |
| **Dialog 工厂** | `AlertBuilder<D>` DSL | ✅ 已建（2026-08-16） | customView/okButton/cancelButton/yesButton/noButton/items/singleChoiceItems/multiChoiceItems 链式 DSL，Confirm/Select 类统一入口；from 325506 lib/dialogs（2026-08-12 深挖）；**task 12.37** |
| **导入弹窗** | 7 导入家族三处分叉模式 | 🆕 规范 | 导入类弹窗统一化：仅分叉 ①基类选择(居中/Sheet)②ViewModel 解析③菜单项，其余(导入执行/全选/空态/格式错)逐字相同；泛型 BatchImportDialog<T>(ImportState New/Update/Existing/Error)；from 325506（2026-08-12 深挖，对应目标书源/订阅源/净化/词典 4 导入对话框） |
| **搜索过滤** | `SearchBookFilter` 快照过滤引擎 | 🆕 规范 | 搜索/发现结果过滤：@Volatile 快照+惰性预编译(Regex+fields+scope)+@Synchronized ensure，规则字段 OR+多规则黑名单，scope 范围协议(空=全部/含::=单源/CSV=分组)；from huajideshutiao（2026-08-12 深挖，目标项目暂无此能力，数据模型+引擎+三套 UI 全可搬） |
| **搜索过滤** | `SourceFilterRule` 数据模型 | ✅ 已建（2026-08-16） | Room 实体：name/enabled/pattern(正则)/fields(NAME/AUTHOR/INTRO/KIND/WORD_COUNT 逗号分隔)/scope/order；Field enum 5 种+Scope sealed 4 态；from huajideshutiao（2026-08-12 深挖）；**task 12.3B** |

### 3.1 接线计划（孤儿组件 → 目标页）
| 组件 | 首个接线页 | 阶段 |
|------|-----------|------|
| PillNavigationBar | MainActivity | P1 |
| GlassTopAppBar | Explore/Rss/BookSource | P1 |
| SettingsSearchBar | Explore/Rss | P1 |
| AppModalBottomSheet | 阅读器浮层/BookSource 编辑 | P1 |
| BookTocBookmarkSheet | 阅读器目录/书签 | P1 |
| BadgeDot | 书架（替换页面私有 UnreadBadge） | ✅ 已接线（2026-08-11 书架网格+列表 2 处） |
| ShelfGridSkeleton | 书架加载态 | ✅ 已接线（2026-08-11 书架 loading 分支） |
| EmptyStatePlaceholder | 书架空态/错误态（本次沉淀） | ✅ 已接线（2026-08-11 书架空态+错误态） |
| ListLayoutMenu | BookSourceActivity（三视图+排序6，支干样板确立） | P1 里程碑 |
| ReadMenuGlassButtonSurface / ReadMenuSlider / ReaderBookSheet / ReaderMoreActionsSheet / ReaderViewport（阅读器族） | 阅读器浮层（P2-reader.md §五 R0-R4：桥接层→菜单壳→弹层单态→搜索层→选区/胶囊） | R0 起随阶段 |
| ConfirmDialog / AppEditDialog / AppSelectDialog / AppNumberPickerDialog / AppTextDialog / AppWaitDialog（Dialog 族） | 随各页 L2 弹窗收敛接线（首批：书源编辑校验/删除确认/分组选择） | P1 起随页 |
| AppMenuSheet / AppDropdownMenu（菜单族） | BookSourceActivity 条目长按/顶栏更多（S2 支干样板确立；SelectActionBar 为 View 存量组件，Compose 书源列表时迁移为受控批量栏） | P1 里程碑 |
| SwipeActionContainer（BookSourceItems 已接线） / ListScaffold（模板待用） | 对应页面改造时接线 | P2/P3 |

### 3.2 组件新增规范（防重复）
- 新组件必须：`camelCase` 命名 + 用途前缀（Settings/Pill/Glass/Shelf/Summary…）+ KDoc 标注设计来源（AD-xx 或借鉴 fork）+ 提交到 components 目录并登记本表。
- **页面私有组件禁止复制公共能力**（如书架 `UnreadBadge` 复制 `BadgeDot`）。发现即收敛：删私有实现改引公共组件，作为巡检项（P5 KPI：0 处私有重复）。

### 3.3 实施回执模板（Component Usage Receipt，强制）

> 用户要求（2026-08-11）：**每个页面 Compose 化实施完成后必须填写实施回执**，形成「组件复用自增长闭环」——后续开发新页面能快速知道"哪些组件可用、之前页面怎么用、能否继续复用"。回执是页面验收的前置条件（与第 9 步检查清单一同提交）。

**回执模板（每个页面一份，填完贴在 tasks.md 对应任务项后 + pages-inventory.md 该页状态栏）：**

```
### 页面回执：<页面名>（骨架 S? · 阶段 P?）
- 负责人/日期：AI / YYYY-MM-DD
- 【本次复用】公共组件清单：GlassTopAppBar, SettingsClickRow×N, BadgeDot, ...
- 【本次复用】骨架/样式：S2 列表骨架、卡 18dp、间距 16dp、colorScheme.primary
- 【本次沉淀】新增可复用资产：<新组件/新 Modifier/新模式> → 已登记 components 目录 + 本表（若无可写"无"）
- 【一致性】页面私有组件：<0 或列表>；硬编码色：<0>；三态齐全：<是/否>
- 【对后续页复用贡献】本页哪些部分后续页面可直接照抄复用（例：搜索过滤模式可复用到 RssSource）
- 【真机覆盖】功能点用例：① ② ③ ... 全部通过 ✅（测试时间/环境）
- 【遗留】未完成项/待理事项：
```

**回执价值**：① 强制页面开发者（含 AI）自我审计复用率与一致性；② 每页沉淀的"可复用资产"自动回流组件库 → 后续页越来越快（主干→支干→枝叶，见 §9）；③ 全仓可随时 grep 回执追踪"某个组件被哪些页用过、怎么用"。

### 3.4 组件规格真值表（精确规格书 · 唯一真值，2026-08-13 建立）

> **背景**：用户反馈另一 AI 产出「巨丑无比 / 丢三拉四」，审计发现根因=设计文档是「规范文本」而组件代码实现未对齐（卡 18dp 文档 vs SettingsCard 12dp 实现；注释「滑动胶囊 spring」vs 实际原地变色 tween）。本表是**组件级精确规格**——每个已建组件一行，圆角/间距/字号/颜色槽位/高度/触控逐项对账，实现必须与本表一致；标 🔴=当前代码违例（需修），🟡=待对齐，✅=已符合。**新组件实现前先在本表登记规格再写代码**。
>
> 全局基线（来自 §1）：卡 18dp / 按钮 12dp 圆角；间距 4dp grid（4/8/12/16/24/32）；触控 ≥48dp；页面边距 16dp；禁硬编码色/字号（用 colorScheme + MaterialTheme.typography）。

| 组件 | 容器/形状 | 内边距 | 字号（typography） | 颜色槽位 | 高度/尺寸 | 触控 | 状态 |
|------|-----------|--------|-------------------|----------|----------|------|------|
| `PillNavigationBar` | Row surface 背景 + 顶部 HorizontalDivider 0.5dp outlineVariant α0.4 | 垂直 4dp（Row）/ 垂直 2dp（Tab）/ SpaceEvenly | labelSmall Bold（选中）/ Regular（未选中） | surface / primary（选中图标/文字）/ onSurfaceVariant（未选中图标）/ onSurface（未选中文字） | Tab 图标 22dp + 图标区 26dp 高（无选中底胶囊） | Tab weight(1f) 均分，≥48dp | ✅ **2026-08-16 回填（D-13）**：组件 08-14 已按 bug① 简化——图标/文字变色 `animateColorAsState+tween(200)`（非 spring）、Row padding vertical 4dp、Tab padding vertical 2dp、**无选中底色胶囊**（注释自述）；本行此前「spring 弹性过渡 + α0.12 胶囊 36×30 RoundedCornerShape(15) + 垂直 6dp」为 08-13 未落地承诺，现回填为真实实现 |
| `GlassTopAppBar` | TopAppBar | 标准 M3 顶栏 | titleMedium | surface（实底） / onSurface | 标准 TopAppBar 高度 | — | ✅ **2026-08-13 修复（视觉效果分级封口）**：真磨砂需 RenderEffect/Haze 且 Modifier.blur 会连内容一起糊（不可用），**降级为 surface 纯色实底**；注释如实描述为「surface 纯色底」，不再自称 Glassmorphism；后续磨砂走独立容器方案 |
| `SettingsSection` | Column | top 12dp / 标题 h16 v6 | labelLarge Bold | primary | — | — | ✅ |
| `SettingsCard` | Card | 标题 h16 v12 | titleSmall（标题） | surfaceVariant / 1dp elevation | — | — | ✅ **2026-08-13 修复**：圆角 12→18dp（对齐设计基石卡 18dp）、水平内边距 12→16dp（对齐页边距） |
| `SettingsClickRow` | Row clickable | h16 v12 | bodyLarge（标题）/ bodySmall（副标）/ bodyMedium（尾值） | onSurface / onSurfaceVariant | 行高≥48dp | clickable 整行 | ✅ **2026-08-13 修复**：删除 :57 `Spacer(width(0.dp))` 垃圾代码，改 height(2.dp) 标题-副标间距 |
| `SettingsToggleRow` | Row clickable | h16 v12 | bodyLarge / bodySmall | checkedThumb primary / checkedTrack primaryContainer / checkedBorder primary | 行高≥48dp | 整行 + Switch | ✅ **2026-08-13 修复**：垂直内边距 v8→v12，与 ClickRow 同族行一致 |
| `SettingsSearchBar` | Row 背景 surfaceVariant + RoundedCornerShape(12.dp) | 水平 16dp / 垂直 8dp（外层 Row）；图标 start 12dp | bodyMedium（TextField 默认） | 容器 surfaceVariant / 图标 onSurfaceVariant / 光标 primary / 文字 onSurface / 占位符 onSurfaceVariant | TextField 默认高度（外层 v8 合计总高约 64dp≥48dp） | TextField 整行 | ✅ **2026-08-13 终审批补（已接线 S2 BookSource，2026-08-11）**：S2/S6 列表页统一搜索入口；受控组件（query+onQueryChange 由页面传），搜索词升 VM StateFlow |
| `RowIcon` | Box 36dp | — | — | primary α0.12 底 + RoundedCornerShape(10.dp) | 36dp 方块 + Icon 20dp | — | ✅（图标块规格：36dp/10dp/20dp，被 ClickRow/ToggleRow 复用） |
| `MetricGrid` | Column | h12 v4 / spacedBy 8 | value titleMedium Bold / label bodySmall | onSurface / onSurfaceVariant | MetricTile 圆角 12dp（卡规格） | — | 🟡 MetricTile 深色硬用 surfaceVariant **无暗色处理**（CommonPageColors 待对齐：暗=lerp(surface,onSurface,0.06)α0.98） |
| `BadgeDot` | Box CircleShape error 色 | 数字 h4 v1 / Text 10sp Bold | 10sp Bold（例外：徽标字号） | error 底 / badgeTextBright 黑或白字 | 纯点或数字胶囊 | — | ✅（count=0 隐藏 / -1 圆点 / >99 显示 99+） |
| `EmptyStatePlaceholder` | Column 居中 | Icon 48dp + Spacer16 + 标题 + Spacer24 | bodyLarge（标题）/ bodyMedium（副标） | outline（Icon）/ onSurfaceVariant / outline | Icon 48dp | 可选 Button | ✅ |
| `ShelfGridSkeleton` | 骨架屏卡片 | 呼吸动画 | — | surfaceVariant | 按网格列数 | — | ✅ |
| `SwipeActionContainer` | 左滑操作容器 | 操作区固定宽 | — | error（删除）/ primary | 行高匹配 | — | ✅（孤儿未接线） |
| `ConfirmDialog` | M3 AlertDialog 卡 18dp | M3 标准 | titleLarge / bodyMedium | primary 确认 / error destructive | M3 标准 | 按钮 ≥48dp | ✅（destructive=true 确认钮 error 色） |
| `AppEditDialog` | M3 AlertDialog | M3 标准 + EditField 列表间距 8dp | bodyMedium 输入 | primary 标签 / surfaceVariant 输入框 | M3 标准 | 按钮 ≥48dp | ✅（EditField 列表替代 DialogEditText 系） |
| `AppSelectDialog` | M3 AlertDialog | 列表项 h16 v12 | bodyLarge | RadioButton primary / 选中项 primary | M3 标准 | 列表项整行 | ✅ |
| `AppNumberPickerDialog` | M3 AlertDialog | Slider+输入框间距 8dp | bodyLarge | primary Slider | M3 标准 | Slider ≥48dp | ✅ |
| `AppTextDialog` | M3 AlertDialog | 内容滚动区 16dp | bodyMedium（Markwon 渲染） | onSurface / surfaceVariant 背景 | 内容 maxHeight 70% | 关闭按钮 | ✅ |
| `AppWaitDialog` | 裸 Dialog 居中 | 图标+文案间距 8dp | bodyMedium | primary 转圈 | 居中 | — | ✅ |
| `AppMenuSheet` | AppModalBottomSheet | 条目 h16 v12 | bodyLarge | 图标 primary / 文字 onSurface / destructive error | 条目≥48dp | 长按触发 | ✅ |
| `AppDropdownMenu` | M3 DropdownMenu | 条目 h12 | bodyMedium | checked 勾选 primary | 条目≥48dp | 点击项 | ✅（S4 B6 已接线 16 项） |
| `ImportSourceSheet` | AppModalBottomSheet 容器 | 顶部行 h56 / 列表项 h16 v12 / 底部 h48 | titleLarge（标题）/ bodyLarge（名称）/ labelSmall（状态徽标）/ bodyMedium（菜单） | 状态徽标 NEW=primaryContainer / UPDATE=tertiaryContainer / EXIST=secondaryContainer；底部全选-取消/取消/导入 12dp 圆角 48dp 高 | 列表 LazyColumn heightIn max440dp | 整行勾选+Checkbox+Edit 按钮 ≥48dp | ✅ **2026-08-13 接线（S6 ImportRssSourceDialog 样板）**；🔴 **审计3 定案（2026-08-13）**：列表项 content 内边距改 `padding(16,12)` 对齐 h16 v12，行高由内部 Row height(48dp) 保证，改后复核总高≥48dp 触控 |
| `AppModalBottomSheet` | M3 ModalBottomSheet | 顶部装饰条 + 圆角 16dp + navigationBarsPadding + bottom 16dp | 内容由调用方定 | surfaceVariant 底 / onSurface 内容 / tonalElevation 8dp | — | 拖拽关闭 + dragHandle | ✅ 已接线（Phase4 阅读器浮层/ImportSourceSheet/S6，2026-08-13 补真值行） |
| `BookTocBookmarkSheet` | AppModalBottomSheet 内双 Tab | Tab 区 h16 | Tab 标签 labelLarge / 列表项 bodyLarge | Tab 选中 primary / 未选中 onSurfaceVariant | 章节/书签列表 heightIn max440dp | 整行点击 | ✅ 已接线（Phase4 阅读器浮层，2026-08-13 补真值行；双 Tab=目录/书签，附「章节列表」TextButton 保留完整目录入口） |
| `ListLayoutMenu` | DropdownMenu 两区 | 布局区/排序区 | bodyMedium | 选中 primary | — | 点击项 | ✅（受控组件：当前值+onSelect 由页面传） |
| `GroupHeader` | Row | h16 v8 | titleSmall Bold | onSurface / outline | 行≥48dp | 整行折叠 + 组操作菜单 | ✅ |

**🆕 待建组件精确规格**（2026-08-13 收敛专项二升级，标 🔵=待建精确规格）。**来源=全局基线 §1（卡 18dp/按钮 12dp/间距 4dp grid/触控 ≥48dp）+ fork 源码推导 + 已接线同族组件规格参照**，四维（容器/圆角、内边距、字号、色槽）+ 高度/触控**已逐项给精确值**，后续 AI 可直接照此开发。**接线 task 见 tasks.md §13 待建组件清单（12.28-12.3C，已逐组件挂精确 task），实现后回填本表 🔵→✅ 并登记 §3 组件目录接线页。**

| 组件 | 容器/形状 | 内边距 | 字号（typography） | 颜色槽位 | 高度/尺寸 | 触控 | 状态 |
|------|-----------|--------|-------------------|----------|----------|------|------|
| `ReadMenuGlassButtonSurface`（阅读器按钮原语） | 圆形 IconButton（`RoundedCornerShape(50%)`）；玻璃态 `surface.copy(α0.8f)` + 1dp `outlineVariant` 描边；普通态透明无底 | 无（icon-only） | —（icon-only，无文字） | selected 高亮 `primary` / 常态 `onSurfaceVariant` / 玻璃态底色 `surface α0.8` | 玻璃 48dp / 普通 40dp 圆 | 48dp（普通态 `sizeIn(min=48dp)` 兜底，视觉 40dp 触控 48dp） | ✅ 已建（2026-08-16，task 12.28） |
| `ReadMenuSlider`（阅读器进度/亮度） | M3 `Slider`（`SliderDefaults`，轨道圆角默认） | Slider 轨道区默认 | — | `SliderDefaults.colors`：activeTrack `primary` / inactiveTrack `surfaceVariant` / thumb `primary` | 高度≥48dp（外层包 `heightIn(min=48dp)`） | 拖动时菜单 alpha≤30% 实时预览、松手 `onValueChangeFinished` commit | ✅ 已建（2026-08-16，task 12.29） |
| `ReaderBookSheet`（目录/书签/高亮 三 Tab） | `AppModalBottomSheet` 容器 + M3 `TabRow`（项目无 CardTabRow，沿用 BookTocBookmarkSheet 同款）+ `HorizontalPager`；Sheet 顶圆角 16dp、容器 `surfaceVariant` + `tonalElevation 8dp` | Tab 区 h16 / 列表项 h16 v12 | Tab 标签 `labelLarge` / 列表项 `bodyLarge` | Tab 选中 `primary` / 未选中 `onSurfaceVariant` / 容器 `surfaceVariant` / 内容 `onSurface` | 列表 maxHeight **72%** 屏高 | 整行点击 ≥48dp | ✅ 已建（2026-08-16，task 12.2A） |
| `ReaderMoreActionsSheet`（更多操作弹层） | `AppModalBottomSheet` 容器 + 4 列 `LazyVerticalGrid` + 分页 | 网格项 8dp 间距 / 容器 padding h16 | 动作 label `labelMedium` | 图标 `primary` / 文字 `onSurface` / destructive `error` | 网格项 ≥48dp（`sizeIn(min=48dp)`） | 点击动作 / 编辑模式长按 | ✅ 已建（2026-08-16，task 12.2B） |
| `ListCard`（含 BookListCardMetrics） | `Card` clip 圆角 **18dp**（默认 `RoundedCornerShape(18.dp)`）+ 背景 + heightIn | content 内边距由调用方 `metrics` 传（默认 h16） | 内容由调用方定（默认 bodyLarge 标题 / bodySmall 副标） | 容器 `surface` / `surfaceVariant`（暗色 lerp 见 §4.5） | heightIn 由调用方定 | combinedClickable（点击+长按由调用方回调） | ✅ 已建（2026-08-16，task 12.2F） |
| `ModernActionPopup`（通用弹层菜单） | `Popup` 弹层（`DropdownMenu` 风格容器） | 条目 h12 | 条目 `bodyMedium` | 图标 `primary` / 文字 `onSurface` / destructive `error` | 条目 ≥48dp | 点击项（Action(title,invoke) 数据驱动） | ✅ 已建（2026-08-16，task 12.31） |
| `AppConfirmDialog`（M3 AlertDialog 封装） | M3 `AlertDialog` 卡 **18dp** | M3 标准 | `titleLarge` / `bodyMedium` | 确认钮 `primary` / destructive 确认钮 `error` | M3 标准 | 按钮 ≥48dp | ✅ 已建（2026-08-16，task 12.34） |
| `MultiSelectDialog`（分组多选） | M3 `AlertDialog` 卡 **18dp** | 列表项 h16 v12 | 项 `bodyLarge` / 组头 `titleSmall` | 选中项 `primary` / 其余 `onSurface` | 内容 maxHeight **70%** | 项整行 ≥48dp | ✅ 已建（2026-08-16，task 12.35） |
| `HeatmapCalendar`（阅读热力图） | 自包含 `Column` 卡片（`Card` 18dp 圆角包裹） | 格间距 2dp / 月份 Pill 间距 8dp | 计数 `bodySmall` | `lerp(primaryContainer α0.42, primary, (value/max)²)` 强度 / 月份 Pill `primary` | 7 列网格（周一起始 chunked(7)） | 格 ≥8dp 可点 | ✅ 已建（2026-08-16，task 12.39） |
| ~~`SummaryCard`~~（成就卡，含 BookStackView，已删除 2026-08-16 孤儿清理） | `Card` **18dp** | h16 v12 | value `titleMedium` / label `bodySmall` | `surfaceVariant` / `onSurface` | 封面错位堆叠 rotate ±3°（BookStackView） | 卡片 ≥48dp 可点 | ❌ 已删除（2026-08-16，task 12.3A） |
| `AssistChip`（登录态辅助 chip，fork F2） | M3 `AssistChip`（chip **18dp** 圆角） | chip 内 h6 v6（M3 标准） | `labelMedium` | 已登录 ✓ `primaryContainer` / 未登录 `LockOpen` outlined（配 loginUrl 才显示，未配或未登录用 outlined） | M3 AssistChip 高度（≥32dp） | 点击区 ≥48dp | ✅ 已建（2026-08-16，task 12.3C） |
| `ListScaffold<T>` + `ListUiState<T>`（泛型列表模板） | `Scaffold`（`DynamicTopAppBar`+内容+`SelectionBottomBar`+FAB） | 内容区 h16 | 顶栏 `titleMedium` / 列表项 `bodyLarge` | 选中滑入 `SelectionBottomBar` `primary` | 一屏 | 项 ≥48dp | ✅ 已建（2026-08-16，task 12.30；ListUiState：items/selectedIds/searchKey/isSearch/isLoading） |
| `AppAlertDialog`/`AppModalBottomSheet` 双引擎容器 | M3 `AlertDialog` 卡 **18dp**（本项目无 Miuix 依赖，退化为单 M3 引擎；`AppModalBottomSheet` 已建 M3 版） | M3 标准 | M3 标准 | M3 用 colorScheme（container `surfaceContainerHigh`/title `onSurface`/text `onSurfaceVariant`） | M3 标准 | show/data 双变体，data 重载缓存末值播放退出动画 | ✅ 已建（2026-08-16，task 12.36；from 325506 规格，Miuix 分支按需未来接入） |
| ComposeDialog 家族 8 类（TextInput/TextForm/NumberPicker/MultiChoice/Confirm/SingleChoice/ActionList/FetchedModel） | 统一 `AppDialogStyle` 底框 + 卡 **18dp** | M3 标准 + 字段间距 8dp | `bodyMedium` 输入 / `bodyLarge` 选项 | `primary` 标签 / `surfaceVariant` 输入框 | M3 标准 | 按钮/项 ≥48dp | ✅ 已建（2026-08-16，task 12.32；TextInput/SingleChoice/ActionList 三子类落地，余 5 子类按需补） |
| `ManageScreenHost`/`ManageScreenHeader`（Sheet 内多级导航，补缺漏行） | `AppModalBottomSheet` 容器 + `AnimatedContent` 横向滑动 | 页面间 0（动画接管）/ 顶栏 h16 | 标题 `titleMedium` | 返回箭头 `onSurface` / 标题 `onSurface` | 内容 maxHeight **80%** 屏高 | 返回键 BackHandler 链 | ✅ 已建（2026-08-16，task 12.38；sealed `ManageScreen(depth)` 控动画方向） |
| `ReaderViewport`（正文尺寸接缝，补缺漏行） | `AndroidView` 桥接正文内核（N 不迁移，AD-02） | 内核原布局，Compose 侧不包 padding | 内核自绘（不适用） | 内核原色（不适用） | width/height/density 由 coordinator 回调 `ChapterProvider::upViewSize` + `awaitViewport` | 内核触摸 | ✅ 已建（2026-08-16，task 12.2C；纯桥接零 UI 规格） |
| `TextActionSelectionMenu`（阅读器选区工具条，补缺漏行） | `Popup` 弹层，`textMenuPosition` View 坐标锚点桥接 | 条目 h12 / 色板 2 行 6 色格间距 8dp | 动作 `bodyMedium` | 图标 `primary` / 文字 `onSurface` / destructive `error` | 色格 40dp×40dp、条目 ≥48dp | 点击动作；无二级菜单 | ✅ 已建（2026-08-16，task 12.2D） |
| `HighlightStyleDialog`（高亮选色，补缺漏行·存量升级） | 外层 `BottomSheetDialogFragment`（BottomSheet 化）+ `ComposeView` 承载 Column 内容 | 色板 3 列 2 行 6 色格间距 8dp / 容器 h16 | 预设标签 `labelMedium` / 通道标签 `bodyLarge` / 线型 `labelMedium` | 色格 6 语义预设色 / 选中描边 `primary` 2dp | 色格 40dp×40dp、通道行 ≥48dp | 点击即选即生效，无二级 | ✅ 已建（2026-08-16，task 12.2E；Compose 化升级，保留 StyleHost 桥接与 8 通道+线型+字体业务） |
| `SelectActionBarCompose`（多选批量栏，补缺漏行） | Row 底部栏（`surface` 底 + 顶部 `HorizontalDivider` 0.5dp） | 操作项 h16 | 操作 `bodyMedium` | 选中滑入 `surface` 底 / 图标 `onSurface` / 全选勾选 `primary` | 栏高 ≥48dp | 操作项 ≥48dp | 🔵 精确（from View `SelectActionBar` 迁移为受控批量栏，受控：selectedUrls+onSelect 由页面传；P5 已引用） |
| `ListLayoutMenu`（布局/排序切换，补缺漏行） | `DropdownMenu` 两区（布局区/排序区） | 条目 h12 | `bodyMedium` | 选中 `primary` | — | 点击项 ≥48dp | ✅（受控组件：当前值+onSelect 由页面传并持久化，P5 已接线） |

**设计模式（非组件规格，不入真值表；见对应章节）**：`BaseComposeDialogFragment` 宿主基类（§3 组件表，Dialog 族统一宿主）；`Sheet 内多级导航`（S6 弹窗多级页面，§3 组件表）；`CommonPageColors` 深色自适应（§1.1/§4.5）；`拖拽排序模式`（§2 S2）；`Nav3 全局路由+Route 壳层`（S1/§2）；`7 导入家族三处分叉`（S6）；`AlertBuilder<D>` DSL（Dialog 工厂）；`SearchBookFilter` 快照过滤引擎 + `SourceFilterRule` 数据模型（搜索过滤，§3 组件表）——这些以 fork 来源描述为准，开发时作为范式参考，不做圆角/间距精确对账。

**规格对账义务**：① 本表是唯一真值，组件实现与本表不符即 🔴 违例；② 页面实现引用组件后禁二次改样式（圆角/间距/字号/颜色槽位以本表为准）；③ 每完成一次组件修改，回填「状态」列 ✅；④ 新组件入表后方可写代码（§3.2 强制）。

---

## 4. 状态管理范式（Compose 页面）

### 4.1 受控组件模式（强制，from BookshelfScreen 最佳实践）
- **UI 组件 = 无状态**：`data class State`（data 字段）+ 回调注入（`onXxx`），state 全部提升到调用方。
- **数据源 = ViewModel + Room Flow**：`xxxDao.flowXxx()` → `collectAsStateWithLifecycle`（或 `produceState` 单次查询）。
- **Fragment 只做壳**：XML 壳（TitleBar/容器）+ `ComposeView`，订阅收敛到 ViewModel（禁止 style1/style2 各写一份 upConnect/booksJob）。
- 异步单发：用 `Coroutine.async{}...onSuccess{}...onError{}` 链（项目规范）；挂起函数 `xxxAwait()`。

### 4.2 页面生命周期规范
- `DisposableEffect` 清理 Flow/Job；`rememberSaveable` 保存轻量 UI 态（Tab 位置/搜索词/多选集 listSaver）。
- 避免 `produceState` + `LaunchedEffect` 同源死锁（AOAdapt 教训：永久 loading）。
- 主题切换：监听 `EventBus.REPAINT` / 配置变更重读 `ThemeStore`。

### 4.3 数据类去重陷阱（2026-08-11 fork 核验补证，from MoRealm BookSourceManageScreen）
- **陷阱**：Room 实体 `data class` 若 `equals` 只比较主键字段（如 `BookSource.equals` 只比 bookSourceUrl），对列表项做 toggle/更新后 **StateFlow/dedup 判定"结果没变"→ UI 不重组**（MoRealm 曾因开关不实时生效排查数日）。
- **规避**：① 列表项在 UI 层包成 **`Ui` 轻量模型**（把 enabled/选中态独立字段提出来），或在 Composable 参数层把易变字段（enabled）**单独拆成 primitive 参数**（Compose 100% 识别变化）；② 派生列表用 `derivedStateOf` + `referentialEqualityPolicy` 强制每次重算发新引用；③ 禁止依赖 Room 实体 `equals` 做 UI diff。
- 持久化枚举（排序/分组方式）用 **String key + fromKey fallback**（非 ordinal），增删枚举旧值不崩。

### 4.4 多选状态收敛（2026-08-12 fork 核验补证，from legado-archive）
- **多选态由选择集派生**：`isSelectMode = selectedUrls.isNotEmpty()`（源 Activity:638-639），**禁止独立 isSelecting 标志**——独立标志需手动同步（清空集合忘置位/置位忘清空都是回归源）。清空自动退出多选。
- **数据回流剪除脏选中**：每次数据回流后 `selectedUrls.filter { it in currentUrls }`（源 Activity:637-639），防已删除/已筛选掉的 URL 留残选中。
- **区间补选 checkSelectedInterval**：选中项 min~max index 区间全选（校验场景），批量操作入口需时提供。
- **批量操作栏 AnimatedVisibility**：按 selectedCount>0 整栏显隐，计数文本点击=全选，主危险操作（删除）外置，其余收 ⋮ 菜单（源 AppManagementScaffold:263-322）。
- 拖拽排序与长按多选共存：拖柄局部 draggableHandle（行本体 combinedClickable 不冲突），仅 Default 排序且非搜索/非分组态启用（源 BookSourceScreen.kt:56-136）。

### 4.5 主题撞色守卫（2026-08-12 fork 核验补证，from legado-archive）
- **toM3Scheme 生成后做对比度后处理 pass**：对 onSurface 系文字槽位按实际 surface 槽位校验 `MIN_FONT_SURFACE_CONTRAST=1.3`（防"完全不可读"，非 WCAG 合规），撞色时在日夜默认文字色中选最小对比度更高者兜底（可跨昼夜取色）；半透明前景先 composite 再算（源 ThemeConfig.kt:755-812）。
- **签名式重组合失效**：依赖键拼字符串签名 + `remember(signature)`，替代逐 token 观察（源 ThemeUiPalette.kt:149-183）。
- 背景资源变化用**版本号 bump 驱动 remember 失效**（事件+version++），比直接改 state 抗并发（源 MainActivity.kt:204,583）。

### 4.6 书架快照缓存（2026-08-12 fork 核验补证，from legado-archive，P1 后置）
- 列表渲染配置（style/group/sort/layout/margin 等 14 项+分组签名）拼 key → sha256 前 32 位 → 内存 LRU + 磁盘 JSON 双层快照，**切分组/改配置秒显旧数据**（collect 前先 restore，源 BookshelfSnapshotStore.kt）；刷新 dataVersion 防快照覆盖。

---

## 5. 三态规范（加载/空/错误，全站一致）

| 状态 | 组件 | 说明 |
|------|------|------|
| 加载中 | `ShelfGridSkeleton`（列表）/ 顶部 LinearProgress（详情） | 首次加载骨架屏；增量刷新用 PullToRefresh 指示 |
| 空态 | `EmptyStatePlaceholder`：图标 48dp + 主文案 + 次文案 + 可选操作按钮 | 文案风格一致（"还没有X，去添加"） |
| 错误态 | `EmptyStatePlaceholder` + "重试"按钮 | 重试走原逻辑；错误信息 `AppLog.put()` + 可选 Snackbar |

> 确认操作统一 `AppModalBottomSheet`。

---

## 6. 无障碍与质量
- 触控目标 ≥48dp；颜色对比度满足 WCAG（Error 用 M3 标准红）。
- 暗色模式：所有页面需过 `values-night`/isNight 分支，禁止暗色下不可见（P0 已修，保持）。
- 性能：长列表 `LazyColumn/LazyVerticalGrid` + `key`；图片统一 `BookCover.load`（Glide，AndroidView 桥接，免 glide-compose）；避免浮层触发 re-layout（正文零改动）。
- 命名：`camelCase` + 用途前缀 + KDoc 设计来源标注。

### 6.1 国际化（i18n，新增，2026-08-11 核验补证）
- **新文案一律进 `strings.xml`（values/ 英文 + values-zh/ 中文，双语必填）**，Compose 用 `stringResource(R.string.xxx)`，View 用 `getString(R.string.xxx)`。
- ❌ 禁止在代码/布局中硬编码中文文案。存量硬编码清零（实测残留：RegexTestScreen「匹配详情」、TimestampConvertScreen「日期格式」、SettingsSearchBar「搜索设置」、OpenUrlConfirmDialog「正在请求跳转链接/应用」、VideoPlayerActivity/VideoFragment「播放地址/暂无播放地址/线路」、SpeakEngineDialog「系统默认」等，随页面改造逐项迁移）。
- 🔴 **公共组件库硬编码中文 4 处（2026-08-11 v2.8 复审实测，接线页全部继承，优先级最高）**：`PillNavigationBar`（Tab label「书架/发现/历史/我的」）、`SettingsSearchBar`（「搜索设置」）、`BookTocBookmarkSheet`（Tab「目录/书签」）、`SummaryCard`（占位「书」）——公共组件 i18n 必须最先清，否则每个接线页都带中文。**【2026-08-12 已修复 1 处】**：`BookTocBookmarkSheet` Tab「目录/书签」→ `stringResource(R.string.source_tab_toc/bookmark)`（复用存量双语 key），剩 PillNavigationBar/SettingsSearchBar/SummaryCard 3 处待清。
- 🔴 **debug 工具族硬编码（2026-08-11 v2.8 复审实测，Compose 工具页 7 个）**：硬编码中文 60 处（EncodeTools 19/HttpDebug 16/TimestampConvert 8/CurlTest 6/PingTest 6/RegexTest 4/DebugTools 1）；硬编码色 11 处（CurlTest 2/PingTest 5/RegexTest 4）——均走 §7 检查清单（第 8 步国际化/第 13 步硬编码色），随页面改造迁移 strings.xml 与 colorScheme token。
- 带占位符文案用 `%1$s` 位置参数（如 `getString(R.string.xxx, url)`），禁止字符串拼接翻译。
- 文案一致性：同一概念全站同一 key（如"添加""删除""确定/取消""重试"已存在 key 优先复用，禁止同义多 key）。

### 6.2 动画与转场（新增，2026-08-11 核验补证）
- **封面 Hero 转场默认关**（AD-08，兼容低端设备；书架→详情/阅读器场景）。
- **浮层动画零打断**：浮层出现/消失不触发正文 re-layout（正文零改动红线）。
- 微交互用局部 `animateFloatAsState`/`animateColorAsState` + `spring(0.45,800)`（收藏心跳/加书架即时反馈）；骨架屏用呼吸动画（ShelfGridSkeleton 既有）。
- ❌ 禁止常驻全量平滑换肤动画（34 个 animateColor，recomposition 成本，AD-18 决策：即时切换 + 局部动效）。
- 列表增删/视图切换（网格↔列表↔紧凑）可加 `AnimatedVisibility`/`AnimatedContent` 轻过渡，但禁止影响滚动性能。

---

## 7. 页面改造检查清单（每个页面改造必过）

1. **功能核对**：对照 pages-inventory.md 该页功能点清单逐项核对——Compose 化后每个功能点有落点（Sheet/菜单/行/控件），**核心功能一个不漏**。
2. **骨架归类**：该页属于 S1-S6 哪一类？骨架结构是否与同类型页一致？
3. **组件复用**：grep 公共组件是否可覆盖（Settings* / BadgeDot / Skeleton / Sheet）？页面私有组件是否重复了公共能力？
4. **主题接入**：`LegadoTheme {}` 包裹？无硬编码色值？字号/圆角/间距用 token？
5. **状态管理**：ViewModel + Flow？受控组件？无 Fragment 散落重复订阅？
6. **三态 + 弹窗 + 菜单**：加载/空/错误三态齐全且用规范组件；页面内 Dialog 全部归入 S6 三层体系（L1 Sheet / L2 Dialog 族 / L3 透明窗壳），**无页面私有弹窗布局**；页面内长按/更多菜单全部归入菜单族（`AppMenuSheet`/`AppDropdownMenu`/`SelectActionBar`），**无页面私有 PopupMenu**。
7. **无障碍/暗色**：48dp、对比度、暗色分支？
8. **国际化**：新文案全部 `strings.xml` 双语（en/zh），页面无硬编码中文？（§6.1）
9. **方向与自适应**：新页面不写 requestedOrientation（跟随系统）；仅阅读器/WebView 内容/沉浸全屏三类既有场景保留方向控制；网格列数随宽度自适应。
10. **动画与转场**：Hero 转场默认关；浮层零打断；无常驻全量平滑换肤动画？（§6.2）
11. **真机功能点覆盖测试**：用 ai_tests 框架写真机用例覆盖该页全部功能点（参考 ai_e2e_testing_workflow），**通过才算完成**。
12. **文档同步**：pages-inventory.md 更新状态；tasks.md 勾选；updateLog.md 编译前更新。
13. **实施回执**：填 §3.3 实施回执（复用组件/沉淀资产/私有复制计数/后续复用贡献/真机覆盖/遗留）并附在 tasks.md 任务项后——**回执缺失 = 页面未完成**（AD-23，验收 KPI 第 5 项）。

---

## 8. 验收 KPI（统一性门禁）
- 每个 Compose 化页面：同类型骨架一致（视觉对比截图）。
- 全仓 grep：`Color(0x` 硬编码色值在非内核页面 = 0；页面私有重复组件 = 0。
- 组件库接线：孤儿组件全部有首个接线页。
- 真机：每页功能点覆盖用例全部通过；四入口（书架/我的/搜索/书源）≤2 步可达。
- **回执完成率 100%**：每个 Compose 化页面已填 §3.3 实施回执（无回执 = 未完成）。

---

## 9. 主干 → 支干 → 枝叶 全局构建策略（用户指定，2026-08-11）

> 用户明确指出开发节奏判断：「最难的是一开始，全局公共组件完成后，后续页面基本就是复用引用实现，所以会越来越快」。据此建立**分层构建策略**，杜绝逐页从头设计导致的进度瓶颈与风格漂移。

### 9.1 三层结构
| 层 | 含义 | 现状 | 命中页面 |
|----|------|------|---------|
| **主干** | 全局公共资产：主题（LegadoTheme/ThemeSpec）、组件库 19 文件、6 类骨架模板、状态管理范式 | ✅ 已完成（Phase0-3） | 无特定页 |
| **支干** | 每类骨架的**首个样板页（reference page）**：完整实现该类骨架的全部复用模式，作为后续同类页的抄写范本 | 🔄 待建设（Phase P1） | 下表 S1-S6 各一个 |
| **枝叶** | 同类剩余页面：**直接复用支干样板**的组件/布局/状态范式，只替换业务数据与功能点 | ⏳ 待进行（Phase P2+） | 全部其余页 |

### 9.2 支干样板页分配（每类骨架指定一个"首做页"，做完验收后冻结为范本）
| 骨架 | 样板页（首做） | 确立的复用模式（供枝叶抄写） |
|------|--------------|------------------------------|
| S1 主框架 | MainActivity | PillNavigationBar+BadgeDot+ViewPager 接线、双击回顶/压缩 |
| S2 列表管理 | BookSourceActivity（书源管理） | GlassTopAppBar+SettingsSearchBar+LazyColumn+滑选/拖拽/批量操作+三态+SwipeActionContainer+**ListLayoutMenu（三视图+排序 6 样板）**+**AppMenuSheet/AppDropdownMenu/SelectActionBar（菜单族样板）** |
| S3 表单编辑器 | BookSourceEditActivity | 6 Tab + 字段分组 SettingsCard + CodeView + KeyboardToolPop + 未保存拦截 + 回执模板示范 |
| S4 详情阅读 | BookInfoActivity | 共享折叠封面 + 底部操作栏 + AppModalBottomSheet（换源/分组等） |
| S5 全屏沉浸 | 阅读器浮层（ReadBookActivity 壳） | edge-to-edge + 3s 隐藏 + **单一 activeSheet 弹层单态 + BackHandler 优先级链 + ReadMenuGlassButtonSurface 按钮原语 + ReadMenuSlider 进度/亮度 + 磨砂降级方案（RenderEffect blur API31+/纯色）** + 专属手势保留（P2-reader.md §五 R0-R4） |
| S6 弹窗透明窗 | SourceLoginDialog / 导入 Dialog 族 | AppModalBottomSheet 统一化 + 透明窗壳保留流转确认 |

### 9.3 构建节奏（对应用户"越来越快"）
1. **主干阶段（已完成）**：先砸时间把公共库/主题/骨架/范式磨到工程级 —— 一次投入，全期受益。
2. **支干阶段（P1，每类骨架做 1 个样板页）**：把该类骨架所有复用模式在样板页走通并冻结验收 → 产出「这类页面就这么做」的范本。
3. **枝叶阶段（P2+，剩余同类页）**：逐页打开样板页 → 复制骨架结构 + 复用组件 → 替换功能点 → 填回执。支架完成得越充分，枝叶页实现越机械、越快、越一致。

**不变量**：任何阶段都逃不过 §7 检查清单与 §3.3 回执；枝干页验收后，同类页不得另起炉灶重写骨架。

---

## 10. 页面设计文档索引（每页独立详细设计文档 · 2026-08-13 建立）

> **每页（骨架级样板页）一份独立详细设计文档**（pages/ 下 `P{编号}-{页名}.md`），用 _template v2 模板编写。页面开发前**先建/读本文档 + §3.4 组件规格书**；本文档在 README「分页面设计文档」与下表双向登记；开发任务在 tasks.md 对应任务项引用本文档路径。
>
> 状态：✅ 已发布（可作为另一 AI 开发依据）/ 🚧 编写中 / 📋 待建（开发该页前必须补）。

### 10.1 分档规则（每页必归一档）

| 档位 | 模板 | 适用 | 文档产物 |
|------|------|------|---------|
| **完整 v2** | `pages/_template.md` | 骨架级样板页 / 已接线核心页 / 交互复杂或高风险页 | `pages/P{编号}.md` 十节完整文档 |
| **轻量** | `pages/_light-template.md` | 普通子页/枝叶页（继承族文档规格） | `pages/light/L{编号}-{页名}.md` 七节轻量文档 |
| **N 不迁移** | 无 | 内核/第三方控件/无 UI/可删 | 不做文档（pages-inventory 标 N 即覆盖） |

> 判断：查下表档位列 + pages-inventory 优先级；拿不准升一档。N 页被引用时以族文档/浮层规格覆盖。

### 10.2 完整 v2 文档索引（骨架级/已接线核心页）

| 文档 | 页面 | 骨架 | 状态 | 对应 task | 对应 fork 借鉴 |
|------|------|------|------|-----------|---------------|
| `pages/P9-main.md` | 主框架 MainActivity | S1 | ✅ v2 样板 | 12.20/12.21（已接线） | forks §9/§11 |
| `pages/P1-bookshelf.md` | 书架 Bookshelf | S2 | ✅ v2 | 12.16j（已接线） | forks §1/§9.2 |
| `pages/P5-booksource.md` | 书源管理 BookSource | S2 | ✅ v2 样板 | 12.16q/r（已接线）、V-1~V-4 | forks §7.1/§7.3/§11.3 |
| `pages/P4-my-config.md` | 我的/设置 My+Config | S2 | ✅ v2 | 12.16k（我的页） | four-fork §四 |
| `pages/P10-booksource-edit.md` | 书源编辑 BookSourceEdit | S3 | ✅ v2 样板 | 12.xx（待接线） | forks §7/§3 |
| `pages/P3-bookinfo.md` | 书籍详情 BookInfo | S4 | ✅ v2 | 12.23（已接线） | forks §11.1 |
| `pages/P2-reader.md` | 阅读器 ReadBook | S5 | ✅ v2 | 12.24（已接线 Phase4）、R0-R4 | forks §3 |
| `pages/P6-explore.md` | 发现 Explore | S2 | ✅ v2 | 12.16m A7 | forks §11 |
| `pages/P7-rss.md` | 订阅源 Rss | S2 | ✅ v2 | 12.16o A8 | forks §7.2 |
| `pages/P8-overlays.md` | 浮层/弹窗族 | S6 | ✅ v2 | 12.22 Dialog 族 | forks §10.2/§11.3 |
| `pages/P0-reader-migration.md` | 阅读器迁移路线 | S5 | 📋 待建 | P2-reader R0-R4 | — |

### 10.3 84 页档位矩阵（完整 84 页面类档位，含轻量文档清单）

> **口径说明**：本矩阵 64 行为「档位条目」，其中 A3/A4、C18、C20、D4、D5、D9 等行合并了多个页面类（pages-inventory 为 84 页面类权威基线，69 页面类 + 15 抽象/壳）。轻量文档 = `pages/light/L{编号}-{页名}.md`，继承对应「族文档」规格，只写差异点（继承族文档编号见下表）。F1/F2/F3 复用 `L-C20` 族、F6 复用 `L-D9` 族，不单独建文件。N 页不做文档。task 对应见 tasks.md 12.16 系列对应条目 + §13 轻量页 task 精确映射表（12.40-12.62）。

| 页 | 页面 | 档位 | 继承族文档 | 骨架 | task 对应 |
|----|------|------|-----------|------|-----------|
| A1 | MainActivity | 完整 v2 | — | S1 | 12.20/12.21 ✅ |
| A2 | MyFragment+ProfileScreen3Level | 完整 v2 | P4 | S2 | 12.16k ✅ |
| A3/A4 | 书架 style1/style2 | 完整 v2 | P1 | S2 | 12.16j ✅ |
| A5 | BaseBookshelfFragment | 轻量 L-A5 | P1 | S1 附属 | 12.16j |
| A6 | BooksFragment | N（可删） | — | S2 | — |
| A7 | ExploreFragment | 完整 v2 | P6 | S2 | 12.16m |
| A8 | RssFragment | 完整 v2 | P7 | S2 | 12.16o |
| B1 | ReadBookActivity | 完整 v2 | P2 | S4+S5 | 12.24 ✅ |
| B2 | TocActivity | 轻量 L-B2 | P2 | S2 | 12.16p |
| B3 | BookmarkFragment | 轻量 L-B3 | P2 | S2 | 12.16p |
| B4 | HighlightFragment | 轻量 L-B4 | P2 | S2 | 12.16p |
| B5 | AllBookmarkActivity | 轻量 L-B5 | P2 | S2 | 12.4F |
| B6 | BookInfoActivity | 完整 v2 | P3 | S4 | 12.23 ✅ |
| B7 | BookInfoEditActivity | 轻量 L-B7 | P3/P10 | S3 | 12.50 |
| B8 | BookshelfManageActivity | 轻量 L-B8 | P1/P5 | S2 | 12.41 |
| B9 | ImportBook/RemoteBook | 轻量 L-B9 | P1/P8 | S2 | 12.51 |
| B10 | CacheActivity | 轻量 L-B10 | P2 | S2 | 12.42 |
| B11 | Search/SearchContent | 轻量 L-B11 | P6/P7 | S2 | 12.16p |
| B12 | ReadMangaActivity | 轻量 L-B12 | P2 | S5 | 12.43 |
| B13 | AudioPlayActivity | 轻量 L-B13 | P2 | S5 | 12.44 |
| B14 | ExploreShowActivity | 轻量 L-B14 | P6 | S2 | 12.52 |
| B15 | StorageManageActivity | 轻量 L-B15 | P4 | S2 | 12.53 |
| B16 | TxtTocRuleActivity | 轻量 L-B16 | P2 | S2 | 12.54 |
| C1 | BookSourceActivity | 完整 v2 | P5 | S2 | 12.16q/r ✅ |
| C2 | BookSourceEditActivity | 完整 v2 | P10 | S3 | 12.16n |
| C3 | BookSourceDebugActivity | 轻量 L-C3 | P5/P10 | S3 | 12.45 |
| C4 | ReplaceRule/ReplaceEdit | 轻量 L-C4 | P5 | S2+S3 | 12.46 |
| C5 | HighlightRuleActivity | 轻量 L-C5 | P5 | S2 | 12.47 |
| C6 | DictRuleActivity | 轻量 L-C6 | P5 | S2+S3 | 12.55 |
| C7 | CodeEditActivity | N（sora 内核） | — | S3 | — |
| C8 | WebViewActivity | N（WebView 池） | — | S4 | — |
| C9 | FileManage/HandleFile | 轻量 L-C9 | P4 | S2+S6 | 12.56 |
| C10 | DownloadManageActivity | 轻量 L-C10 | P4 | S2 | 12.57 |
| C11 | UrlRecordActivity | 轻量 L-C11 | P4 | S2 | 12.58 |
| C12 | RecycleBinActivity | 轻量 L-C12 | P5 | S2 | 12.59 |
| C13 | SourceLoginActivity | 轻量 L-C13 | P8 | S6 | 12.48 |
| C14 | QrCodeActivity | N（camera-scan） | — | S6 | — |
| C15 | ImageGallery/ImageDetail | 轻量 L-C15 | P2 | S5 | 12.49 |
| C16 | AutoTask/AutoTaskEdit | 轻量 L-C16 | P5/P10 | S2+S3 | 12.5A |
| C17 | WelcomeActivity | 轻量 L-C17 | P4 | S6 | 12.5B |
| C18 | association 透明窗 | N（协议分发；Import Dialog 属 P8） | — | S6 | — |
| C19 | debug 7 工具 | 轻量 L-C19 | P4 | S3 | 12.16k ✅ |
| C20 | About/AboutFragment/ReadRecord | 轻量 L-C20 | P4 | S2 | 12.5C |
| D1 | RssSourceActivity | 完整 v2 | P7 | S2 | 12.16l |
| D2 | RssSourceEditActivity | 轻量 L-D2 | P7/P10 | S3 | 12.16n |
| D3 | RssSourceDebugActivity | 轻量 L-D3 | P7 | S3 | 12.5D |
| D4 | RssArticles/RssSort | 轻量 L-D4 | P7 | S2 | 12.40 |
| D5 | RssSearch/RssArticleInfo | 轻量 L-D5 | P7 | S2 | 12.16p |
| D6 | ReadRssActivity | 轻量 L-D6 | P2 | S4 | 12.4A |
| D7 | RssFavoritesActivity | 轻量 L-D7 | P7 | S2 | 12.5E |
| D8 | RuleSubActivity | 轻量 L-D8 | P8 | S2+S6 | 12.5F |
| D9 | VideoPlayerActivity | 轻量 L-D9 | P2 | S5 | 12.4B |
| E1 | BackupConfigFragment | 轻量 L-E1 | P4 | S2 | 12.4C |
| E2 | ThemeConfigFragment | 轻量 L-E2 | P4 | S2 | 12.16p |
| E3 | CoverConfigFragment | 轻量 L-E3 | P4 | S2 | 12.60 |
| E4 | OtherConfigFragment | 轻量 L-E4 | P4 | S2 | 12.4D |
| E5 | PreciseManageFragment | 轻量 L-E5 | P4 | S2 | 12.61 |
| E6 | WelcomeConfigFragment | 轻量 L-E6 | P4 | S2 | 12.62 |
| F1 | AboutActivity | 轻量 L-C20 族 | P4 | S2 | 12.5C |
| F2 | AboutFragment | 轻量 L-C20 族 | P4 | S2 | 12.5C |
| F3 | ReadRecordActivity | 轻量 L-C20 族 | P4 | S2 | 12.5C |
| F4 | WebViewLoginFragment | N | — | S6 | — |
| F5 | QrCodeFragment | N | — | S6 | — |
| F6 | VideoFragment | 轻量 L-D9 族 | P2 | S5 | 12.4E |

> 规范：① 每页文档必须含验收标准（完整 v2 见 _template §8，轻量见 _light-template §6，另一 AI 交付门禁）；② 已接线页升级 v2 时用「对齐现状+登记违例」方式；③ 新页 Compose 化前，文档状态须从 📋→🚧→✅ 走完，缺文档不准动工；④ 轻量文档继承族文档规格，差异点登记在轻量文档 §2 与 pages-inventory 对应条目，task 对应见 tasks.md 对应条目。

## 11. 变更记录
- 2026-08-11：建立工程规范（骨架 6 类/组件六族接线计划/状态范式/三态/检查清单/验收 KPI）。
- 2026-08-11：实施者复盘补证——§1.1 增「封面视觉定色」豁免登记（GeneratedCover 8 色 + 内核 N 页）；提示 §3.1 接线计划「阶段」列采用 Phase 语义，与 frontend-synthesis/implementation-spec 统一（随 Phase4 开工时修订）。
- 2026-08-11 v2：新增 §3.3 实施回执模板（用户要求回执校验机制，见 AD-23）；新增 §9 主干→支干→枝叶全局构建策略（用户指定开发节奏，见 AD-24）。
- 2026-08-11 v2.1：§7 检查清单增至 10 步（新增第 10 步实施回执）；§8 验收 KPI 加「回执完成率 100%」。（后经 v2.5 增至 11 步：插入「方向与自适应」为第 8 步）
- 2026-08-11 v2.2：§2 S2 补「搜索（统一 SettingsSearchBar）+ 布局切换+排序（统一 `ListLayoutMenu`，待建）」——覆盖四模块（书架/书源/订阅源/搜索/发现）共性功能，消灭各页私有布局切换实现；§3 组件表登记 `ListLayoutMenu`（🆕 待建）+ 接线计划 P1 里程碑（首接线 BookSourceActivity 确立三视图+排序 6 样板）。
- 2026-08-11 v2.3：§6 S6 升级为「弹窗统一三层体系」——L1 浮层面板 `AppModalBottomSheet` / L2 语义 Dialog 族（ConfirmDialog/AppEditDialog/AppSelectDialog/AppNumberPickerDialog/AppTextDialog/AppWaitDialog 共 6 个，🆕 待建，替代全仓几十处 DialogEditText/NumberPicker/TextDialog/WaitDialog 等私有弹窗）/ L3 透明窗壳保留；§3 组件表新增 Dialog 族 + 接线计划；§7 检查清单 6 步补「弹窗收敛」门禁（无页面私有弹窗布局）。
- 2026-08-11 v2.3：§3 组件表登记 `EmptyStatePlaceholder`（🆕 沉淀，统一空态/错误占位，20 文件）；`BadgeDot`/`ShelfGridSkeleton` 由孤儿转「✅ 在用」（书架 P0 收敛实施落地，见 tasks.md 11.9/14.2/14.3）；§5 三态表空态/错误态列补充组件名。
- 2026-08-11 v2.4：新增「菜单族」统一方案（用户追问"弹框/菜单是否有统一组件化"核验延伸）——全仓 20+ 私有 PopupMenu 收敛为 `AppMenuSheet`（长按条目 BottomSheet 富操作）+ `AppDropdownMenu`（顶栏/条目更多下拉，均 🆕 待建）；`SelectActionBar` 登记为公共组件（ui/widget/SelectActionBar.kt 存量 View，10+ 页在用，Compose 化时迁移受控批量栏）；§2 S2 手势行/§3 组件表/§3.1 接线计划/§7 检查清单 6 步/§9.2 S2 样板同步更新。
- 2026-08-11 v2.5：新增 §1.4「方向与自适应」统一策略（核验缺口）——阅读器方向走 AppConfig.screenOrientation（0-5，BaseReadBookActivity 统一）；WebView 内容方向由书源 JS 控制（portrait/landscape/any 映射）；沉浸页全屏按 VideoPlay.isPortraitVideo 切换；新页面一律跟随系统不写 requestedOrientation；configChanges 已声明 + rememberSaveable 保活；网格列数随宽度自适应（BoxWithConstraints 断点 480/840dp）。
- 2026-08-11 v2.6：新增 §6.1 国际化（i18n）规范（核验补证：新文案双语 strings.xml、禁硬编码中文、存量硬编码残留清单）与 §6.2 动画与转场规范（Hero 默认关 AD-08 / 浮层零打断 / 局部 spring 微交互 / 禁常驻全量换肤动画）；§7 检查清单扩至 13 步（插入「国际化」第 8 步、「动画与转场」第 10 步，原 8-11 顺延 9/11/12/13）。
- 2026-08-11 v2.7：书源/订阅源管理页 fork 布局深挖补证（用户追问后逐源码核验 HapeLee BookSourceScreen/RssSourceScreen + MoRealm BookSourceManageScreen，见 forks-deep-dive §7）——S2 骨架新增「分组列表 GroupHeader」（折叠箭头+组名+启用数/总数徽标+组操作，from MoRealm）+「ListLayoutMenu 排序交互」（下拉首行升降序、点同维度翻转、String key 持久化）+「多选列表」规范（BackHandler 优先退多选、选中集 rememberSaveable listSaver、滑选覆盖层）；§3 组件表登记 `GroupHeader`（🆕 待建）；新增 §4.3 数据类去重陷阱（Room 实体 equals 只比主键 → toggle 不重组，MoRealm 教训；规避：UI 轻量模型/易变字段拆 primitive 参数/derivedStateOf+referentialEqualityPolicy/String key fromKey fallback）。
- 2026-08-11 v2.8：**阅读页整体框架设计定稿**（用户重点要求补强，推翻早期"Compose 化回归风险大不动"保守结论；3 fork 验证：HapeLee AndroidView 桥接、MoRealm 仿真翻页退 View）——S5 骨架扩写「壳-核分离」架构（正文 ReadView/page/ 29 文件零改动 AD-02 + UI 壳 read_menu/search_menu/config 弹窗族渐进 Compose 化）；pages/P2-reader.md 全面重写为权威版（三层架构/叠放布局树/单一 activeSheet 三类渲染/BackHandler 优先级链/顶底栏磨砂降级方案 RenderEffect API31+/纯色 不引第三方/滑块拖动 alpha≤30% 实时预览/配置驱动工具按钮/ReaderViewport 尺寸接缝/R0-R4 迁移路径/红线 6 条）；§3 组件表新增「阅读器」族 5 组件（ReadMenuGlassButtonSurface/ReadMenuSlider/ReaderBookSheet/ReaderMoreActionsSheet/ReaderViewport，均 🆕 待建 from HapeLee）+ §3.1 接线计划。
- 2026-08-11 v2.9：**`ListLayoutMenu` 组件落地**（P1 里程碑首个待建组件）——§3 组件表 `ListLayoutMenu` 🆕待建→✅已建（`ui/widget/components/ListLayoutMenu.kt`）：布局区横向图标+label 高亮当前项、排序区首行升降序切换+维度列表（点同维度翻转/点新维度保留方向）按 v2.7 MoRealm 交互落地；字符串 `list_layout`/`sort_asc`/`list_layout_menu`/`list_layout_menu_switch_hint` 双语入库；updateLog 已记；**下一步按 §3.1 接线 BookSourceActivity（P1 里程碑）**。
- 2026-08-11 v2.10：**公共组件库 + debug 工具族 v2.8 规范符合性复审**（用户指令继续审查剩余已 Compose 化部分）——① 公共组件库接线实测：✅ 已接线 8 个（MetricGrid/SettingsSection/ClickRow/ToggleRow/ShelfGridSkeleton/EmptyStatePlaceholder/BadgeDot/RowIcon），❌ 孤儿 11 个（PillNavigationBar/GlassTopAppBar/SettingsSearchBar/AppModalBottomSheet/BookTocBookmarkSheet/VerticalScrollbar/SwipeActionContainer/SplicedColumnGroup/SummaryCard/ThemedSnackbarHost/ListLayoutMenu，其中 ListLayoutMenu 已建未接线、SettingsSearchBar 规划接管四模块搜索未接线）；§3.1 接线计划维持现状（P1/P2/P3 阶段），孤儿接线为 P1 里程碑前置。② §6.1 存量清零清单补充公共组件库硬编码中文 4 处（接线页继承，优先级最高）+ debug 工具族硬编码中文 60 处/硬编码色 11 处。③ 审查方法论：ui-standards §7 检查清单 13 步逐条，公共组件库重点是 §3 组件目录对齐 + i18n，debug 工具族重点是 i18n + 硬编码色 + 回执缺失。
- 2026-08-12 v2.11：**阅读 Archive（legado-archive，Rimchars 私有仓）深挖补证**（用户指令「继续学习其他开源阅读的细节，补充到我们的设计文档中」，3 个 explore 子代理并行，见 forks-deep-dive §9）——新增 §4.4 多选状态收敛（**isSelectMode 由选择集派生**禁独立标志/数据回流剪除脏选中/区间补选/批量栏 AnimatedVisibility/拖柄与长按多选共存，from legado-archive BookSourceActivity）+ §4.5 主题撞色守卫（toM3Scheme 后处理对比度 pass MIN 1.3/签名式重组合失效/背景版本号 bump，from ThemeConfig/ThemeUiPalette）+ §4.6 书架快照缓存（14 项配置签名 sha256 key + 内存 LRU/磁盘 JSON 双层秒显，P1 后置）；§3 组件表新增 `ListCard`（布局交互解耦卡片）/`ModernActionPopup`（通用弹层菜单）/ComposeDialog 家族 8 类（对齐 6 待建清单扩展）；我的页收录 Preference XML 深度搜索深链 + 区块级 ComposeView 渐进式浸润范式；书源收录智能导出（<30% 仅选中）。
- 2026-08-12 v2.12：**Legado_Max（Suml-1/Legado_Max，Compose 128 文件）深挖补证**（3 个 explore 子代理并行，见 forks-deep-dive §10）——§3 组件表新增 8 行：`BaseComposeDialogFragment` 基类（31 行 ComposeView 宿主，**Dialog 族 6 统一基类，优先于自造骨架**）、`AppConfirmDialog`（M3 AlertDialog+destructive error 色，14 处实战直接改造成 ConfirmDialog）、`MultiSelectDialog` 内容模型（分组多选，覆盖 Dialog 族「多选类」缺口）、**Sheet 内多级导航模式**（sealed ManageScreen+AnimatedContent+BackHandler 返回链，单 Sheet 承载 7 页面 = S6 多级弹窗统一方案）、`HeatmapCalendar`（★ 自包含纯 Compose 661 行无第三方：入参仅 2 个 Map、COUNT/TIME 双模式、`lerp(primaryContainer α0.42, primary, (value/max)²)`、后端仅需 1 条 GROUP BY date SQL）、`SummaryCard+BookStackView`（书籍数+总时长+封面错位堆叠成就卡）、`CommonPageColors` 深色自适应规范（`luminance()<0.18f` 判暗+lerp 向亮抬升+弹窗顶栏 secondary+卡片底 surfaceVariant）、拖拽排序模式（ReorderableItem+LaunchedEffect 持久化+hapticFeedback+zIndex 提升）；**关键决策**：① HeatmapCalendar 为统计卡页高价值低成本增量（1 条 DAO SQL）；② BaseComposeDialogFragment+AppConfirmDialog 直接指导 Dialog 族 6 落地；③ 模块化首页作为发现/书架页交互模型参考（同 ViewPager 框架可嵌）；④ FlowLog 规则可视化需 41 处埋点侵入规则引擎，仅增量接入（开关默认关+书源自测回归）；⑤ **教训：fork AppDialogScaffold 骨架全仓零引用=抽象骨架不接线即负债，Dialog 族以实际共性为准不先造骨架**；MetricTile 深色硬用 surfaceVariant 无暗色处理需对齐 CommonPageColors。
- 2026-08-12 v2.13：**legado-with-MD3-DIY（325506，kt=1106 compose≈126 全量 Compose 仓）深挖补证**（3 个 explore 子代理并行，见 forks-deep-dive §11）——§3 组件表新增 5 行：**Nav3 全局路由+Route 壳层模式**（单 Activity+Navigation3 14 sealed route+backStack 手动栈管理，壳层=副作用编排与渲染分离，底部 Tab 用 HorizontalPager 不嵌套 NavHost 避免双栈，S1 主框架+BookInfoActivity 改造范本）、`ListScaffold<T>`+`ListUiState<T>` 泛型列表模板（一屏统一 DynamicTopAppBar 搜索/下拉+选中滑入 SelectionBottomBar+FAB）、`AppAlertDialog`/`AppModalBottomSheet` 双引擎封装（Miuix WindowDialog vs M3 AlertDialog 按引擎切换+data 重载退出动画，Dialog 族容器范本）、`AlertBuilder<D>` DSL（链式 customView/okButton/items 等，Confirm/Select 统一入口）、7 导入家族三处分叉模式（仅分叉基类选择/VM 解析/菜单项，泛型 BatchImportDialog<T>）；新增 §11.2 主题引擎借鉴点（14 模式预置定义化+种子色/风格/对比度三维覆写+Opaque/Transparent 双通道，供 AD-18 参考但不全量搬）；**关键决策**：① BookInfoRoute 壳层+ListScaffold 泛型模板为 P1 书源/书架改造直接范本；② AppAlertDialog 双引擎（data 重载缓存末值播放退出动画）+AppModalBottomSheet 是 Dialog 族可直接搬范本；③ 7 导入家族三处分叉=目标书源/订阅源/净化/词典 4 个导入对话框统一化样板；④ 主题引擎 48×2 硬编码维护成本高，仅借鉴组织方式保留 AD-18/撞色守卫。
- 2026-08-12 v2.14：**huajideshutiao/legado 深挖补证**（净化规则源三件套为全 fork 独有，本次前台直读源码深挖，见 forks-deep-dive §12）——新增 §3 组件表 2 行：`SearchBookFilter` 快照过滤引擎（★ @Volatile 快照+惰性预编译 Regex+@Synchronized ensure，apply 返回丢弃数，rulesInScope 列生效规则，scope 范围协议 空=全部/含::=单源/CSV=分组）+ `SourceFilterRule` 数据模型（Room 实体，Field enum 5 种 NAME/AUTHOR/INTRO/KIND/WORD_COUNT，Scope sealed 4 态，规则字段 OR+多规则黑名单）；**关键决策**：① 目标项目暂无「搜索/发现结果过滤」能力，huajideshutiao 给出完整闭环（数据模型+快照引擎+Activity/EditDialog/ImportDialog 三件套），可完整借鉴——引擎性能快照模式与 §4.6 书架快照缓存同思路；② 导入三态判定（新增/更新/已有 比较 pattern/fields/scope）复用 Import 家族模式；③ 编辑弹窗作用范围复用 SearchScopeDialog（与搜索范围选择同源），是「弹窗复用既有选择器」的范例。
- 2026-08-13 v2.15：**8 页族设计文档全部升级 v2 模板 + 84 子页面归属登记**（用户 m0088 要求每页独立详细设计文档，m0171 确认批量升级后交付另一 AI 实施）——pages/ 下 P1 书架/P2 阅读器/P3 书籍详情/P4 我的设置/P6 发现/P7 订阅源/P8 浮层全部按 _template v2 十节模板重写（0 身份/1 意图/2 布局框图+区块表/3 组件选型引用 §3.4/4 交互/5 状态/6 三态/7 i18n/8 验收标准 7 条/9 绘图 Prompt/10 变更记录）；P5 保持 v2 样板；§10 索引表 8 行状态更新（P1-P8 ✅ v2），新增「84 子页面归属登记」子表（pages-inventory A-F 六域 84 页按族文档三级覆盖：族文档规格 + pages-inventory 条目差异点 + tasks.md task 对应，子页不重复建完整文档）。
- 2026-08-13 v2.16：**设计文档收敛专项二（用户要求暂停实施，确保文档可指导后续 AI 开发）**——① **轻量页 task 精确化**：§10.3 矩阵中所有标 P1/P2/P3 阶段号的轻量文档收编为精确 `12.4x` task 号（tasks.md 新增「轻量页 task 精确映射表」12.40-12.62，35 项，映射到 V-7/V-8/V-9 真机 task），矩阵 task 列全部精确；② **§1.4 网格断点维度澄清**：网格列数档位（400/600/800）为内容自适应档位，独立于骨架断点；③ **审计 3 处 🔴 定案**（audit-wired-components.md 违例汇总表已改为「已定案收敛」）：SourceCover:357 删硬编码字号改 displaySmall / GlassTopAppBar:44-48 补 titleMedium / ImportSourceSheet:267 改 padding(16,12) 并复核触控；④ **§3.4 ImportSourceSheet 行状态同步**为定案。
- 2026-08-13 v2.17：**设计文档终审（用户要求再做一轮独立交叉核验确认真实完整度）**——独立核验 5 维度：①§3.4 规格书精确性（逐项对账）②84 页矩阵 vs pages/ 目录一致性 ③轻量 task 精确映射 vs tasks.md 一致性 ④5 项已接线审计定案 ⑤主文档引用齐全性。核验通过，补 2 处收敛：① **§3.4 补 `SettingsSearchBar` 真值行**（2026-08-13 终审批补，已接线 S2 BookSource 却缺规格行，本次从源码取证补入：Row surfaceVariant 底+RoundedCornerShape(12.dp)/h16 v8/图标 onSurfaceVariant/光标 primary/总高约64dp）；② **§10.3 矩阵口径说明**：标注 64 行为「档位条目」含合并行（A3/A4、C18、C20、D4、D5、D9），实际覆盖 84 页面类（pages-inventory 为权威基线），F1/F2/F3 复用 L-C20 族、F6 复用 L-D9 族不单独建文件。矩阵/README/light 目录 43 文件三分一致，映射表 35 项与矩阵 task 列逐项一致。
- 2026-08-13 v2.18：**轻量页 task 占位符清零（用户要求每页设计文档有明确 task 子任务对应）**——对 pages/light/ 全部 43 份轻量文档逐份审计（audit-lightweight-docs.md），发现 16 份页面身份残留 `tasks.md 12.xx` 占位符 + 6 份标 `task 待接线` + 11 份仅 pages-inventory 引用无 task 号。按 tasks.md「轻量页 task 精确映射表」（12.40-12.62）统一回填：34 份页面身份「对应 task」+「变更记录」双处补/换精确 task 号（L-B5→12.4F、L-B7→12.50、L-B8→12.41、L-B9→12.51、L-B10→12.42、L-B12→12.43、L-B13→12.44、L-B14→12.52、L-B15→12.53、L-B16→12.54、L-C3→12.45、L-C4→12.46、L-C5→12.47、L-C6→12.55、L-C9→12.56、L-C10→12.57、L-C11→12.58、L-C12→12.59、L-C13→12.48、L-C15→12.49、L-C16→12.5A、L-C17→12.5B、L-C20→12.5C、L-D3→12.5D、L-D4→12.40、L-D6→12.4A、L-D7→12.5E、L-D8→12.5F、L-D9→12.4B、L-E1→12.4C、L-E3→12.60、L-E4→12.4D、L-E5→12.61、L-E6→12.62）。核验：light/ 目录 Grep `12.xx` 0 残留，每份轻量文档均含精确 task 号可定位实施/验证任务。
- 2026-08-16 v2.19：**§3 组件目录表全量回填 59 文件**——审计回填：新增 AppShapes/EmptyStatePlaceholder/TagChip/SettingsSelectableRow/ReaderMenuSheet/HighlightStyleSheet/MenuLayer/LazyListFastScroller/ManageScreenSheet 共 9 行登记；原标「32 文件」修正为实际 59 文件；ListScaffold 补充孤儿状态标注；§11 变更记录追加本行。
- 2026-08-16 v2.20：孤儿组件清理——删除 SummaryCard/ThemedSnackbarHost/SplicedColumnGroup/ManageScreenSheet 4 个无消费场景孤儿组件；VerticalScrollbar 接线到 DownloadManageScreen；ListScaffold 登记为模板待用（task 12.30）。
- 2026-08-17 v2.21：**主题架构 v2 落地（theme-architecture-v2 spec）**——§3 组件表新增 ThemeSync/ColorPickerSheet/SettingsColorRow 3 行；主题设置页（L-E2）重设计为全 Compose（瓦片网格+色盘活预览）；AppNumberPickerDialog 增 neutralText/onNeutral；PillNavigationBar 选中色 accent→primaryColor（对齐 View 语义）；BaseActivity 统一 RECREATE 订阅（沉浸页/设置宿主页 recreateOnThemeChange=false 豁免）+onResume 令牌懒同步；ThemeSpec 增 withContrastGuard 撞色守卫。
