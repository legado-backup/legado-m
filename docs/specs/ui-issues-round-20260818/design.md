# design.md — UI 问题综合整改批次设计（2026-08-18）

> 本批次承接 `docs/specs/ui-redesign-m3/`（UI Compose 化改造，含 `ui-standards.md` 前端 UI 工程规范）的存量遗留问题整改。9 大用户反馈 UI 问题的根因已由主代理确认（本文所有代码行为引用均与根因分析一致，经源码核对）。设计规范对齐点：组件目录 `app/src/main/java/io/legado/app/ui/widget/components/`、协程 `Coroutine.async{}` 链式、Room Flow `collectAsStateWithLifecycle`、Compose 页包 `LegadoTheme{}`、禁止 `Color(0x..)` 硬编码、字符串进 `strings.xml`、圆角 token 4/8/12/16dp、间距 4dp grid、触控 ≥48dp。

## 问题清单 → 修复阶段映射

| # | 问题 | 根因（源码核对） | 修复阶段 |
|---|------|-----------------|---------|
| 1 | 书架标签头部异常 | `MainActivity.getFragmentId` 按 `bookGroupStyle==1` 返回 style2(Folder)/style1(Tab)；`BaseBookshelfFragment.configBookshelf()` 切换 `bookGroupStyle` 只 `notifyMain=true`（postEvent `NOTIFY_MAIN`）不 recreate → fragment 不重建；style1 头部为 Compose `BookGroupTabs`（ScrollableTabRow），与原版 Toolbar+TabLayout 结构不同（固定 Tab 全部/本地缺失、位置差异） | P0 |
| 2 | 沉浸式操作栏 | `PreferKey.immNavigationBar` 只控制底部导航栏（`BaseActivity.upNavigationBarColor` / `ComposeActivitySupport.setupLegadoComposeSystemBar`），`transparentStatusBar` 单独控制顶部状态栏；用户期望 immNavigationBar 打开后头部（状态栏/顶栏）一起沉浸 | P0 |
| 3 | 启动界面缩减 + 我的页子页面 Compose 化不完整 | `WelcomeScreen.kt` 仅 `showTitle/showSubtitle/showIcon/showSlogan`；`ui/config/` 下 ThemeConfigFragment、CoverConfigFragment、WelcomeConfigFragment、PreciseManageFragment 已 Compose 化（有对应 Screen），OtherConfigFragment、BackupConfigFragment 仍为 XML View | P3 |
| 4 | 发现/订阅无批量分组设置 | 书架有 `GroupManageDialog`、`BookshelfManageActivity`；发现/订阅仅 `SourceFolderAdapter.showConfigDialog`（文件夹外观配置），无批量分组管理入口 | P1 |
| 5 | 发现/订阅默认应为标签、分组模式隐藏搜索框且搜索限当前文件夹 | `ExploreFragment.kt` / `RssFragment.kt` 用 View `com.google.android.material.tabs.TabLayout` + `SettingsSearchBar`（搜索框固定显示在标签上方）+ `AppDropdownMenu`；配置 key 为 `AppConfig.sourceGroupStyle` / `AppConfig.sourceGroupMode` | P1 |
| 6 | 发现/订阅右上角分组弹框可去掉 | `ExploreFragment.buildMenuActions` / `RssFragment.buildMenuActions` 含 `Groups` header + 动态分组列表 | P1 |
| 7 | 书源编辑页被改丑 | `BookSourceEditActivity.initComposeQuickToolbar` 用 `FlowRow`+`Checkbox`+`DropdownMenu` 紧凑风格（S3 阶段3 产物）；`RssSourceEditActivity` 仅顶栏 GlassTopAppBar，保留原 XML 表单 | P2 |
| 8 | 长按书架书进详情 book is null | `BookshelfFragment1/2.onBookLongClick` 只 `startActivity<BookInfoActivity>{ putExtra("name"); putExtra("author") }` 不传 `bookUrl`；`BookInfoViewModel.initData` 先 `getBook(name, author)`（书架库），匹配失败后才走 `bookUrl` 分支 | P0 |
| 9 | 弹框体系统一 | 已有三类弹框：`AppDropdownMenu`（右上角下拉）/ `AppModalBottomSheet`（底部）/ Dialog 族 `AppEditDialog`/`AppSelectDialog`/`ConfirmDialog`（悬浮居中）；设置项应统一 `SettingsToggleRow`（M3 Switch）；功能裁剪回溯（对比 8 月 4 号前版本）；除阅读详情页外全部 Compose 化 | P2 / P3 |

## 调研结论（2026-08-18 源码核实）

> 本批次在设计阶段即完成「全页面 Compose 化现状」与「功能裁剪/降级证据」调研，防止实施阶段偷懒漏项。基线 commit：`897b42f95`（2026-08-02，8 月 4 号前最新）。

### A. 全页面 Compose 化现状清单（三分类，逐页源码核实）

> 调研统计（84 页面类，逐页代码位置证据见 `docs/temp-analysis/compose-status-inventory.md`）：**① 纯 Compose 7 页（8.3%）**；**② View+Compose 壳 62 页（73.8%）**——其中「内容区全 Compose 渲染（composeHost 双轨壳）」约 20 页、「仅顶栏/菜单 Compose 其余主体 View（composeTopBar，即"只改头部"）」约 42 页；**③ 纯 View 15 页（17.9%）**。

**① 纯 Compose（完整，7 页）**：debug 工具族 7 页（CurlTest/HttpDebug/PingTest/EncodeTools/RegexTest/TimestampConvert/DebugTools，全部 `ui/debug/*Activity.kt:13` `setLegadoContent { XxxScreen() }`）。

**②a View+Compose 壳 — 内容区全 Compose（composeHost 双轨，~20 页）**：`binding.composeHost.setContent { XxxScreen() }` 渲染全内容区，View 壳仅留生命周期/Intent/系统回调。书架 style1/2（`BookshelfScreen`）、我的页（`ProfileScreen3Level`）、书源管理（`BookSourceScreen`）、高亮规则、关于、阅读记录、全部书签、书籍信息编辑、自动任务列表/编辑、词典、TXT目录、回收站、URL记录、下载管理、文件管理、存储管理、发现分页、欢迎页、导入书籍本地/远程。**缺口 = 各页私有 Dialog 族**（如高亮规则 Dialog、关于 CrashLogsDialog、全部书签 BookmarkDialog、书籍信息编辑 ChangeCoverDialog、远程导入 ServersDialog）。

**②b View+Compose 壳 — 仅顶栏/菜单 Compose，主体仍 View（composeTopBar，~42 页，"只改头部"重点）**：顶栏 `GlassTopAppBar` + 菜单 `AppDropdownMenu` + 搜索 `SettingsSearchBar` 已 Compose，内容区仍是 View `RecyclerView`/`TabLayout`/`WebView`。**迁移缺口 Top 页**（按用户高频，见 `compose-status-inventory.md` §5）：

| 排名 | 页面 | 文件 | 已 Compose | 仍 View 主体 | 建议骨架 |
|------|------|------|-----------|-------------|---------|
| 1 | **发现页** | `ui/main/explore/ExploreFragment.kt:226` | GlassTopAppBar+菜单 | **TabLayout**、RecyclerView(ExploreAdapter)、SourceFolderAdapter、6 私有弹窗 | S2 |
| 2 | **订阅页** | `ui/main/rss/RssFragment.kt:233` | GlassTopAppBar+菜单 | **TabLayout**、RecyclerView(RssAdapter)、ReadRecordDialog | S2 |
| 3 | **订阅源编辑** | `ui/rss/source/edit/RssSourceEditActivity.kt:168` | GlassTopAppBar+菜单 | 4 Tab 字段 RecyclerView、6 私有弹窗 | S3 |
| 4 | **书源编辑** | `ui/book/source/edit/BookSourceEditActivity.kt:187,388,421,518,530` | 5 处 Compose 桥接 | 字段区 RecyclerView+EditText、KeyboardToolPop、6 私有弹窗 | S3 |
| 5 | **搜索/全文搜索** | `ui/book/search/SearchActivity.kt:121`、`ui/book/searchContent/SearchContentActivity.kt:100` | GlassTopAppBar+搜索+菜单 | SearchAdapter RecyclerView、搜索历史、ScopeDialog | S2 |
| 6 | **目录页** | `ui/book/toc/TocActivity.kt:111` | GlassTopAppBar+TabRow+搜索 | ChapterListFragment/BookmarkFragment/HighlightFragment RecyclerView | S2 |
| 7 | **订阅源管理** | `ui/rss/source/manage/RssSourceActivity.kt:153` | GlassTopAppBar+搜索+菜单 | RecyclerView 三视图、SelectActionBar、8 私有弹窗 | S2 |
| 8 | **书籍详情** | `ui/book/info/BookInfoActivity.kt:298,325` | GlassTopAppBar+底部按钮+菜单 | 封面/简介/标签/目录/分组全 View、6 私有弹窗 | S4 |
| 9 | **RSS 文章列表** | `ui/rss/article/RssArticlesFragment.kt` | 无 Compose | 5 样式 RecyclerView(StaggeredGrid/Grid)、LoadMoreView | S2 |
| 10 | 缓存/书架管理 | `ui/book/cache/CacheActivity.kt:160`、`ui/book/manage/BookshelfManageActivity.kt:175` | GlassTopAppBar+菜单 | RecyclerView、SelectActionBar | S2 |
| 11 | 视频/音频/图片 | `ui/video/VideoPlayerActivity.kt:573`、`ui/book/audio/AudioPlayActivity.kt:148`、`ui/image/ImageGalleryActivity.kt:199` | GlassTopAppBar+菜单 | 播放内核（保留）、ViewPager2、章节列表 | S5 |
| 12 | 替换规则 | `ui/replace/ReplaceRuleActivity.kt:117` | ReplaceRuleTopBar+搜索 | RecyclerView、拖拽排序、滑选 | S2 |
| 13 | 配置子页 | `ui/config/ThemeConfigFragment.kt:73` 等 | ComposeView 顶栏 | PreferenceFragment 主体 | S2 |

**③ 纯 View（15 页，P3 收尾目标）**：`BackupConfigFragment`、`OtherConfigFragment`（PreferenceFragment 无 Compose）、`RssArticlesFragment`（文章列表）、`VideoFragment`、`ReadMangaActivity`（漫画引擎）、`HandleFileActivity`（系统文件选择）、旧 `BooksFragment`（被 Compose 书架替代，可删）+ 阅读正文引擎族（`ui/book/read/page/` 29 文件，AD-02 红线 N）+ 关联透明窗族 + QR 扫码（第三方库 N）。

### B. 功能裁剪/降级证据清单（源码核实）

> 审计基线 `897b42f95`（2026-08-02）→ HEAD `aa1170a08`，只读 `git diff`，完整证据见 `docs/temp-analysis/regression-diff.md`。判定三态：❌ 不存在（CUT）/ ⚠️ 降级（DEGRADED）/ ✅ 存在（PRESERVED）。

**❌ 明确裁剪（CUT，5 项）**：

| # | 功能 | 基线（8/2） | 现状 | 证据 | 优先级 |
|---|------|------------|------|------|-------|
| C1 | **主题模式四态选择器**（跟随系统/日间/夜间/**墨水屏**） | `pref_main.xml` themeMode NameListPreference 4 选项（arrays theme_mode 0-3） | `PreferKey.themeMode`/`AppConfig.themeMode`/`AppContextWrapper` 读取逻辑仍在，但**全工程无 UI 入口**；`ThemeConfigFragment` 仅日/夜二态 toggle；**墨水屏模式入口完全丢失**、"跟随系统"不可选 | `ui/config/ThemeConfigFragment.kt:186-194`；`help/config/AppConfig.kt:46,56`；`base/AppContextWrapper.kt:33-42` | 🔴 高 |
| C2 | **欢迎页文字/图标显隐 4 开关** | `pref_config_welcome.xml`：日 `welcomeShowText`/`welcomeShowIcon` + 夜 `welcomeShowTextDark`/`welcomeShowIconDark`（显示时长/自定义欢迎/日/夜背景图已保留） | `WelcomeConfigScreen` 仅 显示时长 Slider/自定义欢迎/日/夜背景图 4 项，**4 个显隐开关 UI 被注释裁剪**（代码自认"留空，未实现"）；`WelcomeActivity` 仍读 key（默认 true）→ 用户无法再控制 | `ui/config/WelcomeConfigScreen.kt:40-55,64-143`；`ui/welcome/WelcomeActivity.kt:92-105`；`AppConfig.kt:1099-1126` | 🟠 中 |
| C3 | **书源排序「最近更新/自动/响应时间」** | `book_source.xml` 排序子菜单 7 项（倒序/手动/自动/名称/地址/最近更新/响应时间/启用） | `BookSourceScreen.kt:161-168` 仅 6 项 `ListSortOption("0".."5")`；**`menu_sort_time` 排序逻辑仍在**（`sortSources` 中 `bookSourceSort==6 -> lastUpdateTime`）**但 UI 无入口**；自动/响应时间仅留旧回退分支 | `BookSourceScreen.kt:161-168`；`BookSourceActivity.kt:567-607` | 🟠 中 |
| C4 | **切换桌面图标（launcherIcon）** | `pref_config_theme.xml` launcherIcon IconListPreference + `LauncherIconHelp.changeIcon()` | 字符串/数组资源仍在，**无任何 UI/代码引用**，`LauncherIconHelp` 无调用方 | `ThemeConfigScreen.kt` 无该行；Grep `launcherIcon` 仅命中资源 | 🟡 低 |
| C5 | **捐赠入口（DonateActivity）** | `activity_donate.xml` + DonateActivity + DonateFragment | 布局与类全删，Grep `Donate` 0 命中 | `git show 897b42f95:res/layout/activity_donate.xml` | 🟡 低 |

**⚠️ 被降级（DEGRADED，5 项）**：

| # | 功能 | 基线 | 现状 | 证据 | 优先级 |
|---|------|------|------|------|-------|
| D1 | 书源管理文件夹视图 | 可切换文件夹视图 | `isFolderViewMode` 硬编码 `false`（注释指向 spec AD-03 决策），`folderItems` 恒空，配置弹窗 `showGroupStyle=false` | `BookSourceActivity.kt:133-134,166,195,463-471,640,944-951` | 🟠 中（与 AD-03 复核） |
| D2 | 书源管理拖拽滑选 | 长按进入滑选拖动区间 | `DragSelectTouchHelper/ItemTouchHelper` 移除（注释"纯死接线"），现为点击/长按单点多选 | `BookSourceActivity.kt:387,296-305` | 🟡 低-中 |
| D3 | 书架 style2 快速索引条 FastScroller | `setFastScrollEnabled(showBookshelfFastScroller)` | style1 `BooksFragment.kt:189-192` 保留 ✅；**style2 Compose `BookshelfScreen` 无 FastScroller 覆盖层** | `style2/BookshelfFragment2.kt:67,103`；`BookshelfScreen.kt:141,314,525` | 🟠 中 |
| D4 | 文件管理入口 | `pref_main.xml` 一级入口 | `ProfileScreen3Level`「其他」组无文件管理行；改为 我的→精准管理→文件管理（深一层） | `ProfileScreen3Level.kt:211-247`；`PreciseManageScreen.kt:76-77` | 🟡 低 |
| D5 | 书源筛选（启用/禁用探索） | `book_source.xml` 分组子菜单 | `BookSourceMoreMenu` 无此项，降为搜索框快捷词 `enabled_explore`/`disabled_explore` | `BookSourceScreen.kt:416,428`；`BookSourceViewModel.kt:205` | 🟡 低 |

**✅ 已核实无裁剪（PRESERVED，15 项）**：底部导航 4 Tab、书架 12 项菜单、发现页菜单、订阅页菜单、书源管理主菜单、书源批量操作、书源编辑 15 项菜单、订阅源编辑页、订阅源管理页、视频播放页、音频播放页、关于页、主题设置页、备份恢复/其他设置入口、高亮样式/背景图模糊（详见 `regression-diff.md` §四）。

> 优先级恢复清单：**墨水屏模式（高）→ 欢迎页 4 开关 + 书源排序（中）→ 桌面图标 + 文件管理入口（低）**。

### C. git 基线功能裁剪回溯范围

- 对比基线：`897b42f95`（2026-08-02，8 月 4 号前最新），HEAD `aa1170a08`。
- 回溯对象：问题 3/9 用户点名功能（启动界面、发现/订阅布局选项、书源/订阅源布局设置、我的页开关）+ C1-C5/D1-D5 全部证据项。
- 产出物：`docs/specs/ui-issues-round-20260818/regression-inventory.md`——**设计阶段已产出**（不再推给 P3），逐功能三态核对（✅ 存在 / ⚠️ 降级 / ❌ 不存在），由 B 节证据汇总而来，实施阶段仅做恢复与回执。

### D. 用户点名疑点核实结论（源码证据，详见 `docs/temp-analysis/user-suspicion-check.md`）

| 疑点 | 根因结论 | 修复方向 | 阶段 |
|------|---------|---------|------|
| 1 我的页开关/滑动不生效 | `ProfileScreen3Level` 全公共组件；**唯一缺陷 `SettingsToggleRow` 整行无 `clickable`，仅 M3 Switch 本体（48dp）可点**，点标题/图标/空白无效；本页无 RadioButton/Slider | `SettingsToggleRow` 的 Row 加 `Modifier.clickable(enabled){ onCheckedChange(!checked) }`，整行 60dp 可切换 | P2 |
| 2 sourceLayout 是否消费 | key 读写链完整，但**发现页/订阅页完全不消费**；书源管理页网格列数被屏幕宽度硬编码覆盖（`BookSourceScreen.kt:377-382`），且 `applyListView` 操作的是 `visibility=gone` 的死 RecyclerView；仅订阅源管理页精确生效 | 书源管理页列数改读 `currentLayout`（2-6）`GridCells.Fixed(currentLayout)`；删除 gone recyclerView 死接线；发现页如需布局切换需 ExploreAdapter 加 sourceLayout 分支 | P1/P3 |
| 3 启动界面展示 | 展示元素（标题/副标题/图标/标语）+ 日/夜背景图齐全可用；**4 个显隐开关 key/读写/消费逻辑都在，但 UI 入口被裁剪**（`WelcomeConfigScreen` 无入口，`WelcomeConfigFragment.kt:68` 注释自认裁剪）；`showSlogan` 与标题共用 `welcomeShowText` 无法独立控制 | `WelcomeConfigScreen` 补日/夜 4 个开关行（SettingsToggleRow 读写 `welcomeShowText/Dark`、`welcomeShowIcon/Dark`）；保持 `customWelcome=false` 时不生效语义 | P3 |
| 4 书源/订阅源布局设置项 | **未被裁剪**：共用 `sourceLayout` key（无独立 key）；书源在顶栏 ListLayoutMenu、订阅源在更多菜单→布局设置、发现页在文件夹配置对话框均有入口；订阅源精确生效，书源列数失真（同疑点2） | 无需新增 key；修书源管理页列数跟随 `currentLayout`；发现页书源列表是否布局切换需决策 | P1/P3 |
| 5 弹框三样式盘点 | 公共弹框组件 16+ 已建（AppDropdownMenu/AppModalBottomSheet/AppAlertDialog/AppConfirmDialog/AppEditDialog/TextInputDialog/AppSelectDialog/MultiSelectDialog/AppNumberPickerDialog/AppTextDialog/AppWaitDialog 等）；**两对功能重叠冗余**：`ConfirmDialog↔AppConfirmDialog`、`AppSelectDialog↔SingleChoiceDialog`；Compose 私有弹框残留 8 文件；View 体系 `alert{}`/`PopupMenu` 残留约 25+ 文件 50+ 调用点 | 合并冗余对（保留 ConfirmDialog/AppSelectDialog 为唯一实现）；8 个 Compose 私有弹框收敛到公共族；View alert/PopupMenu 列第二轮收敛范围 | P2/P3 |

> 新增设计要点：**书源管理页「文件夹视图」被硬编码禁用（D1，指向 AD-03 决策）与「发现/订阅批量分组设置（问题4）」存在设计冲突**——D1 关闭了书源管理页文件夹入口，而问题 4 要求发现/订阅批量分组。需在 P1 阶段一并复核：批量分组入口应基于「分组」维度（不依赖文件夹视图开关）。

## Technical Approach

分 **P0 → P3** 四阶段实施，每阶段可独立编译、真机验证、交付。阶段顺序 = 影响面（用户日常使用频率）× 风险（回归面）加权。

### P0：Bug 修复（问题 1 / 8 / 2）

#### P0-1 书架标签头部（问题 1）

**关键实现思路**
- `BaseBookshelfFragment.configBookshelf()` 的 okButton 逻辑中，将 `bookGroupStyle` 变化从「仅 `notifyMain = true` → `postEvent(NOTIFY_MAIN, false)`」改为「并入 `recreate` 分支 → `postEvent(EventBus.RECREATE, "")`」（与 showBookname/bookshelfLayout 等其他布局项变化同路径）。`NOTIFY_MAIN` 仅用于切换主界面 Tab（`MainActivity.observeLiveBus` 中 `upBottomMenu` + `setCurrentItem`），不能触发 fragment 重建。
- `MainActivity` 侧无需改动重建机制：`FragmentStatePagerAdapter.getItemPosition` 已对「fragmentId 与实例类型不匹配」（`fragmentId == idBookshelf1 && any is BookshelfFragment2` 等）返回 `POSITION_NONE`，RECREATE 事件 → `BaseActivity.recreate()` → adapter 判定类型不匹配 → 重建 style1/style2 fragment。
- 头部 Tab 样式修复：style1 的 `BookshelfScreen.BookGroupTabs`（`ScrollableTabRow`，置于内容区顶部）对齐原版「Toolbar 内 TabLayout」（legado-E 的 `view_tab_layout_min.xml` + `setupWithViewPager`）结构——分组 Tab 与标题同区，并补齐原版固定 Tab（全部/本地）能力。实现上优先在 `BaseBookshelfFragment.initComposeTopBar()` 的 `GlassTopAppBar` 内容区下方内嵌 Tab 行（`Column{ GlassTopAppBar; BookGroupTabs }`），或抽独立头部组件，保持「标题 + 分组 Tab + 搜索/菜单」一体的 Toolbar 布局。

**涉及组件**：`BookshelfScreen.BookGroupTabs`（复用 ScrollableTabRow 渲染逻辑，可提取为公共组件）、`GlassTopAppBar`。

**验收要点**
- 切换书架的「标签 / 文件夹」分组样式后，主界面书架页 fragment 立即重建，头部切换为对应样式，无需重启或手动刷新。
- style1 头部：标题 + 分组 Tab 同区显示，含「全部 / 本地」固定 Tab，位置与原版一致；Tab 可横向滚动、支持长按分组编辑。
- 回归：主题切换（RECREATE）不受影响；`NOTIFY_MAIN` 行为（切到我的 Tab）不变。

#### P0-2 长按书架书进详情（问题 8）

**关键实现思路**
- `BookshelfFragment1.kt` / `BookshelfFragment2.kt` 的 `onBookLongClick` 回调中，向 `BookInfoActivity` 的 Intent 补传 `bookUrl`（保留 `name`/`author` 双 extra 兼容）：
  `startActivity<BookInfoActivity>{ putExtra("name", book.name); putExtra("author", book.author); putExtra("bookUrl", book.bookUrl) }`。
- `BookInfoViewModel.initData` 已支持：`getBook(name, author)` 失败 → `bookUrl` 非空 → `getBook(bookUrl)`（书架库）→ `getSearchBook(bookUrl)`（搜索库）逐级兜底，无需改动 ViewModel。
- 注意：onClick 走的 `startActivityForBook(book)`（`ContextExtensions.kt`，进 `ReadBookActivity`/视频/音频）与长按进 `BookInfoActivity` 是两条不同路径，本次只修长按路径。

**涉及文件**：`BookshelfFragment1.kt`、`BookshelfFragment2.kt`（`BookInfoActivity.kt`/`BookInfoViewModel.kt` 仅核对，不改）。

**验收要点**
- 长按书架任意书（含书架中 name/author 为空或重复的书）→ 详情页正常加载 book 数据，非空态。
- 回归：单击进阅读、长按分组编辑、style1/style2 两书架行为一致。

#### P0-3 沉浸式操作栏联动（问题 2）

**关键实现思路**
- 统一沉浸语义：`immNavigationBar=true` 时，不仅底部导航栏用 `ThemeStore.navigationBarColor`，顶部状态栏也进入沉浸（与 `transparentStatusBar` 联动，二者不再独立解释）。
- 改动点：
  - `BaseActivity.upNavigationBarColor()` / `onResume` 的 `setStatusBarColorAuto` 逻辑：读取 `AppConfig.immNavigationBar`，为 true 时状态栏同样调用 `setStatusBarColorAuto(ThemeStore.statusBarColor(this, true), isTransparentStatusBar=true, fullScreen)` 走透明沉浸路径。
  - `ComposeActivitySupport.setupLegadoComposeSystemBar()`：与 BaseActivity 同步，immNavigationBar 联动状态栏沉浸。
- 兜底：`ThemeConfigFragment` 的 `onImmNavigationBarChange` / `onTransparentStatusBarChange` 均保持 `recreateActivities()`，改动即时生效；沉浸页（阅读器/视频/音频，`recreateOnThemeChange=false`）由 `setupSystemBar()` 兜底刷新。

**涉及文件**：`BaseActivity.kt`、`ComposeActivitySupport.kt`、`ThemeConfigFragment.kt`（文案/开关说明同步，可选）。

**验收要点**
- 设置中打开「沉浸导航栏」，顶栏/状态栏随页面内容沉浸（透明叠加），关闭后恢复实色。
- 日/夜主题切换、横竖屏旋转后沉浸状态保持正确。
- 阅读器/视频播放器等 `recreateOnThemeChange=false` 页不受影响。

### P1：发现/订阅 标签 + 搜索 + 分组设置（问题 5 / 6 / 4）

#### P1-1 默认标签模式 + 搜索框显隐（问题 5）

**关键实现思路**
- 默认展示模式（**默认值变更，否则"默认标签"不生效**）：`AppConfig.sourceGroupStyle` 默认值由 `0`（列表平铺）改为 **`1`（按类型分组）**、`sourceGroupMode` 默认 `0`（标签平铺）——满足用户"默认标签展示 + 默认按类型分组"要求（`AppConfig.kt:271` `getPrefInt(key, 0)` 改 `1`，新装/未改设置生效）。标签展示判定沿用现成 `isTagMode = sourceGroupStyle != 0 && sourceGroupMode == 0`（`ExploreFragment.kt:148`）；**`sourceGroupStyle==0`（用户主动选"列表平铺"）时不显示标签行、普通列表**。分组模式（`sourceGroupMode == 1`，文件夹）作为用户主动切换的形态——对齐书架「标签 / 文件夹」双维度正交设计（`sourceGroupStyle`=数据归类、`sourceGroupMode`=展示形态）。
- 标签组件替换：`ExploreFragment.kt` / `RssFragment.kt` 的 View `TabLayout`（`com.google.android.material.tabs.TabLayout`，布局 `binding.tabLayout`）替换为 Compose 标签行（复用/对齐书架 `BookshelfScreen.BookGroupTabs` 的 `ScrollableTabRow` 思路，新增分组 Tab 填充逻辑：全部 / 未分组 / 动态 `groups`，按 `sourceGroupStyle==1` 时为类型 Tab）。移除 `initTabLayout()`/`upTabLayout()`/`tabSelectedListener`（View 实现），状态沿用 `currentGroup`/`currentType` 与现有 DAO Flow 分支（`upExploreData` / `upRssFlowJob` 的 6 分支不变）。
- 搜索框显隐逻辑：`SettingsSearchBar` 由「固定显示」改为「按模式显隐」——分组模式（文件夹视图 `isShowingFolder=true`）隐藏搜索框；进入文件夹内（子目录列表，`isShowingFolder=false`）显示搜索框，且搜索范围限定 `currentGroup`/`currentType`（现有 DAO 分支已天然支持 `flowGroupSearchExact(currentGroup, searchKey)` / `flowByTypeSearch`，无需新增 DAO）。

**涉及文件**：`ExploreFragment.kt`、`RssFragment.kt`、新增公共标签组件（`ui/widget/components/`，如 `GroupTabRow`）。

**验收要点**
- 发现/订阅默认展示标签平铺；分组模式进入文件夹时搜索框隐藏，进入文件夹内恢复且搜索仅命中当前文件夹/类型。
- 标签样式与书架视觉对齐（M3 `ScrollableTabRow` + `SecondaryIndicator`，无硬编码色）。

#### P1-2 去掉右上角分组弹框（问题 6）

**关键实现思路**
- `ExploreFragment.buildMenuActions()` / `RssFragment.buildMenuActions()` 删除 `Groups` header + 动态分组列表段（分组切换能力由头部标签行 / 文件夹视图承担，不再重复入口）。保留「文件夹配置」等其余菜单项。
- `groups` 状态仍保留（驱动标签行与文件夹视图数据），仅菜单项移除。

**验收要点**：右上角更多菜单不再出现分组列表；通过头部标签/文件夹仍可切换分组。

#### P1-3 发现/订阅批量分组设置（问题 4）

**关键实现思路**
- 现状核实（2026-08-18 源码确认）：书源分组管理 Dialog **已存在**（`ui/book/source/manage/GroupManageDialog.kt`，分组增删改 CRUD，入口 `BookSourceActivity.kt:243`）；书架 `ui/book/group/GroupManageDialog.kt` 存在；RSS 侧 `ui/rss/source/manage/GroupManageDialog.kt` 存在。
- 实施反哺（2026-08-18 P1 执行后修正，修正设计文档与源码的不符点）：
  - ⚠️ 原设计文档称「`BookSourceViewModel` 无基于选中源列表的批量分组方法，为能力缺口」——**与源码不符**。实际 `BookSourceViewModel.selectionAddToGroups/selectionRemoveFromGroups`（`BookSourceViewModel.kt:107/118`）与 `RssSourceViewModel.selectionAddToGroups/selectionRemoveFromGroups`（`RssSourceViewModel.kt:106/115`）**已存在**，入参即 `List<BookSourcePart>`/`List<RssSource>`，底层走 `BookSourceDao.upGroup(List)`（`BookSourceDao.kt:402`，已存在）与 `RssSourceDao.update(*array)`（已存在，`RssSourceDao.kt:158`）。**无需新增 DAO 方法**。
  - ⚠️ 原设计文档隐含"发现/订阅页直接复用管理页多选交互"——**不适用**：发现页 `ExploreAdapter`（复杂 flexbox 布局）、订阅页 `RssAdapter`（网格布局）均**不支持多选**，且发现/订阅页用 `ExploreViewModel`/`RssViewModel`（非管理页的 `BookSourceViewModel`/`RssSourceViewModel`）。
- 本批次实施范围（P1-3a，已交付）：
  - 入口：发现/订阅右上角菜单新增「分组管理」项（替换 P1-2 移除的动态分组列表位置）。
  - 分组 CRUD：复用已存在的 `ui/book/source/manage/GroupManageDialog.kt`（书源，`ExploreFragment.kt` 引入）/ `ui/rss/source/manage/GroupManageDialog.kt`（订阅源，`RssFragment.kt` 引入），不重复造轮子。
- 后续批次（P1-3b，**已实施交付，非待排期**）——实施决策（2026-08-18 执行后反哺）：
  - **方案选型**：采用设计文档推荐的**方案 B**（风险隔离，不动 ExploreAdapter/RssAdapter 的多选交互）。
  - **新增公共对话框 `ui/widget/BatchGroupDialog.kt`**（非 dialog_recycler_view 直用，独立封装）：`BaseDialogFragment(R.layout.dialog_recycler_view)` + checkbox 多选列表（`RecyclerAdapter<String, ItemBatchGroupBinding>`）+ 工具栏 4 菜单项（全选 `menu_select_all`/反选 `menu_revert_selection`/移入分组 `menu_add_group`/移出分组 `menu_remove_group`）。选中态 `linkedSetOf<Int>` 存**列表索引**，回调 `CallBack.addToGroups/removeFromGroups(selected: List<Int>, group: String)`，由调用方映射回真实数据。
  - **新增资源**：`res/layout/item_batch_group.xml`（`ThemeCheckBox` 单行）、`res/menu/batch_group.xml`（4 菜单项）、`strings.xml` 新增 `batch_group`/`please_select_first`。
  - **ViewModel 批量方法**：`ExploreViewModel.selectionAddToGroups/selectionRemoveFromGroups`（内部 `BookSourcePart.addGroup/removeGroup` + `BookSourceDao.upGroup(List)`，`ExploreViewModel.kt:27/38`）、`RssViewModel.selectionAddToGroups/selectionRemoveFromGroups`（内部 `RssSource.addGroup/removeGroup` + `RssSourceDao.update(*array)`，`RssViewModel.kt:42/51`）——**已新增**（设计文档原本判断"能力缺口"，实施时确认管理页 `BookSourceViewModel`/`RssSourceViewModel` 已有同名方法，但发现/订阅页用的是 `ExploreViewModel`/`RssViewModel`，故在两 VM 各补一份）。
  - **菜单入口**：`ExploreFragment.kt:315-319`/`RssFragment.kt:339-343` 各新增 `Icons.Default.List` + `batch_group` 菜单项 → `showBatchGroupDialog()`。
  - **批量分组入口补充说明（相对设计文档的差异）**：除「分组管理（CRUD）」外，**批量改分组已一并交付**，用户可在发现/订阅右上角菜单直接多选源批量移入/移出分组。
- **P1-1 实施差异反哺（相对设计文档）**：
  - `AppConfig.sourceGroupStyle` 默认值 **0→1**（按类型分组），`migrateSourceConfigIfNeeded()` 迁移映射同步调整（旧「文件夹+按分组」→ 新默认按类型），保证存量用户升级后默认「标签+按类型」。
  - 标签行组件 **`GroupTabRow` 已交付**（`ui/widget/components/GroupTabRow.kt`，M3 `ScrollableTabRow` + `SecondaryIndicator`，入参 `groups: List<String>/selectedIndex/onTabSelect/modifier`）——原设计放 P3-3a，因 P1 需要提前到 P1 交付，P3-3a 标记为已由 P1 覆盖。
  - `fragment_explore.xml`/`fragment_rss.xml` 已删除 View `TabLayout`，标签行在 `compose_top_bar` 的 `setContent` 内 `Column` 中渲染（`GlassTopAppBar` 之下、`SettingsSearchBar` 之下），搜索框按 `isShowingFolder` 显隐（`initComposeTopBar` 内 `if (!isShowingFolder)`）。
  - 搜索框显隐（问题5）已实现：分组文件夹根视图（`isShowingFolder=true`）隐藏搜索框与标签行；进入文件夹（`onFolderClick` 置 `isShowingFolder=false`）显示搜索框且 `upExploreData`/`upRssFlowJob` 走现有 6 分支 DAO Flow（含 `flowGroupSearchExact`/`flowExploreByTypeSearch`）限定当前分组/类型。
  - 菜单移除动态分组列表（问题6）已实现：`buildMenuActions()` 保留「文件夹配置 + 分组管理 + 批量改分组」（发现页）+ 阅读记录/收藏/设置（订阅页），不再含分组列表段。

**涉及文件**：`ExploreFragment.kt`、`RssFragment.kt`、`ExploreViewModel.kt`、`RssViewModel.kt`、`ui/book/source/manage/GroupManageDialog.kt`（复用核对入口）、`ui/rss/source/manage/GroupManageDialog.kt`（复用）、新增 `ui/widget/BatchGroupDialog.kt`、新增 `res/layout/item_batch_group.xml`、新增 `res/menu/batch_group.xml`、新增 `ui/widget/components/GroupTabRow.kt`、`AppConfig.kt`、`fragment_explore.xml`、`fragment_rss.xml`、`strings.xml`。

**验收要点**：书源/订阅源右上角菜单出现「分组管理」（CRUD）+「批量改分组」（多选移入/移出）；分组变更后标签行与文件夹视图即时刷新；发现/订阅默认标签+按类型分组；搜索框文件夹根视图隐藏、进文件夹恢复且限定范围。P1 已编译通过（`assembleAppDebug` BUILD SUCCESSFUL），真机 L2 验证见交付阶段。

### P2：弹框体系统一 + 组件风格 + 书源编辑页还原（问题 9 前半 / 7）

#### P2-1 弹框体系统一（问题 9）

**关键实现思路**
- 三类弹框收敛为公共组件族（均在 `ui/widget/components/`，已存在）：
  - 右上角操作菜单 → `AppDropdownMenu`（`MenuAction` 数据驱动，含 `header`/`checked` 语义，定义于 `AppMenuSheet.kt`）。
  - 底部操作面板 → `AppModalBottomSheet`（列表/多选/编辑统一走底部面板）。
  - 悬浮居中确认/编辑/单选 → Dialog 族 `AppEditDialog` / `AppSelectDialog` / `ConfirmDialog`。
- 设置项开关统一 `SettingsToggleRow`（M3 `Switch`），替换页面内散落的 Checkbox 开关（如书源编辑页 `initComposeQuickToolbar` 的内联 `Checkbox+Row`）。
- 新页面/改造页面强制走弹框族，禁止页面私有弹框实现（对齐 ui-redesign-m3 AD-21「组件复用强制规范」）。

**涉及文件**：`ui/widget/components/` 弹框族（核对补缺）、各调用页。

**验收要点**：全局弹框三样式可枚举、样式一致；无页面私有弹框实现残留（grep 核对）。

#### P2-2 书源编辑页还原（问题 7）

**关键实现思路**
- `BookSourceEditActivity.initComposeQuickToolbar()`：由 `FlowRow`+`Checkbox`+`DropdownMenu` 紧凑风格还原为贴近原版 XML 表单风格（`ThemeCheckBox` 朴素横排 + 类型 Spinner 布局），类型选择改用 `AppSelectDialog`（悬浮选择）而非内联 `DropdownMenu`，开关统一 `SettingsToggleRow`/对齐原版 CheckBox 视觉。**尊重原样式而非重新设计**（AD-04）。
- `RssSourceEditActivity`：保持顶栏 `GlassTopAppBar` + 原 XML 表单主体（`tabLayout`/`spType`/`cbIsEnable` 等）不动，仅核对顶栏/底部与全局风格一致性（无需大改）。
- 保留既有已验收能力：`PrimaryScrollableTabRow` 字段 Tab、底部保存/取消栏、`KeyboardToolPop` 软键盘辅助。

**涉及文件**：`BookSourceEditActivity.kt`、`RssSourceEditActivity.kt`（核对）。

**验收要点**：书源编辑页头部信息密度与可读性还原（类型/启用/发现/Cookie 等开关不换行拥挤）；真机编辑保存流程回归（ANR 历史问题不复现）。

### P3：功能裁剪回溯 + 子页面 Compose 化补全（问题 9 后半 / 3）

#### P3-1 功能裁剪回溯（问题 9「对比 8 月 4 号前版本」）

**设计阶段已完成调研（2026-08-18，详见 `docs/temp-analysis/regression-diff.md`）**，以下为裁剪清单实施要点：

1. **恢复主题选择器（C1，高优先级）**：`ThemeConfigFragment` 日/夜二态 toggle 改为四态 NameListPreference（跟随系统/日间/夜间/墨水屏），复用 `PreferKey.themeMode`/`AppConfig.themeMode`/`AppContextWrapper` 现有逻辑。墨水屏模式 `isEInkMode` 判定逻辑已存在，仅需 UI 接线。
2. **恢复欢迎页 4 开关（C2，中优先级）**：`WelcomeConfigScreen` 补 `welcomeShowText`/`welcomeShowTextDark`/`welcomeShowIcon`/`welcomeShowIconDark` 四个 `SettingsToggleRow`（日/夜两组），`WelcomeActivity` 消费逻辑已存在。
3. **恢复书源排序「最近更新/自动」（C3，中优先级）**：`BookSourceScreen.kt:161-168` 的 `ListSortOption` 补 `"6"`（最近更新）+ `sortSources` 逻辑已有 `bookSourceSort==6 -> lastUpdateTime`，纯 UI 补入口。
4. **恢复桌面图标切换（C4，低优先级）**：`ThemeConfigScreen` 补一行 `SettingsClickRow` 调用 `LauncherIconHelp.changeIcon()`，资源已就绪。
5. **D1-D5 降级项复核**：D1（书源管理文件夹视图）硬编码禁用与问题 4（批量分组）设计冲突，需 P1 阶段一并决策；D3（style2 FastScroller）列为 Compose 增强项，非回归；D2/D4/D5 低优先级暂不处理。
6. **红线（AD-06）**：只恢复不新增；恢复项逐条真机回归并登记；禁止借机添加新功能。

**验收要点**：裁剪清单关闭率 100%；恢复项真机验证通过；无新增功能越界。

#### P3-2 我的页子页面 Compose 化补全（问题 3）

**关键实现思路**
- **我的页开关不生效修复（疑点1，源码已核实）**：`SettingsToggleRow.kt:33-39` 整行无 `clickable`，仅 Switch 本体（48dp）可点。修复：`SettingsToggleRow` 的 `Row` 增加 `Modifier.clickable(enabled){ onCheckedChange(!checked) }`，使整行 60dp 均可切换；`MetricTile`（`MetricGrid.kt:60-71`）当前为纯展示非 bug，不加点击。
- **sourceLayout 消费修复（疑点2，源码已核实）**：`BookSourceScreen.kt:377-382` 网格列数被屏幕宽度硬编码覆盖，`applyListView` 操作 `visibility=gone` 死 RecyclerView。修复：① 书源管理页列数改读 `currentLayout`（`GridCells.Fixed(currentLayout)`），菜单补 2-6 列细分；② 清理 `BookSourceActivity.kt:396-421` 对 gone recyclerView 的死接线；③ 发现/订阅页是否消费 `sourceLayout` 属产品决策（当前设计为 flexbox 标签式），本批次不做布局切换、仅修书源管理页列数失真。
- 待 Compose 化页面清单（按「调研结论 A」③ 纯 View 类 + ② 壳类未完成部分）：
  - **配置子页**：`OtherConfigFragment`、`BackupConfigFragment`（新 `OtherConfigScreen.kt`/`BackupConfigScreen.kt` + 原 Fragment 托管，对齐 ThemeConfigScreen/CoverConfigScreen/WelcomeConfigScreen/PreciseManageScreen 范式，复用 `SettingsCard`/`SettingsToggleRow`/`SettingsClickRow`/`SettingsSection` 公共组件）。
  - **发现/订阅内容区**：ExploreFragment/RssFragment 的 View `TabLayout` → Compose 标签行（P1 已含）；RecyclerView 列表保留（探索控件 JS 双求值链内核红线，逐字平移 Compose FlowRow）。
  - **P3 长尾页**（pages-inventory §G + compose-status-inventory §5）：导入/存储/文件/下载/记录/回收站/自动任务/词典/TxtToc/BookInfoEdit/About/ReadRecord/URL记录/SS阅读、RSS 文章列表+排序、RssSearch/RssArticleInfo、缓存/书架管理/替换规则——按调研矩阵 P1/P2/P3 优先级与「②b 表」排名逐页推进（见 P3-3 逐族矩阵），每页填 §3.3 实施回执。
- 启动界面：`WelcomeScreen.kt` 保持纯展示职责；补齐文字/图标显隐（P3-1 C2）；欢迎页配置收敛到 `WelcomeConfigScreen`。
- 除阅读详情页（`BookInfoActivity`，正文/书签/目录等内核对，维持混合态）外，本批次涉及页面全部 Compose 化。

**涉及文件**：`SettingsToggleRow.kt`、`BookSourceScreen.kt`、`BookSourceActivity.kt`、`OtherConfigFragment.kt`、`BackupConfigFragment.kt`、新增 `OtherConfigScreen.kt`/`BackupConfigScreen.kt`、`WelcomeConfigScreen.kt`/`WelcomeScreen.kt`、`ExploreFragment.kt`/`RssFragment.kt`（内容区）、P3 长尾页。

**验收要点**：我的页开关整行可点、开关生效；书源管理页网格列数与设置一致；我的页子页面全部 Compose 化（阅读详情页豁免）；设置项可迁移、功能点无丢失；启动界面配置（含文字/图标显隐）生效。

#### P3-3 顶栏/局部 Compose 主体仍 View 的页面完整迁移设计

> 现状：15 族页面为「View+Compose 壳」（顶栏/局部已 Compose，列表/表单/内容主体仍 View），分布在发现/订阅/RSS 文章/搜索/替换/漫画/视频/目录/详情编辑/书源管理/订阅源管理等。本设计按 **OpenSpec 骨架类型（ui-standards §2 S1-S6）+ 公共组件复用（§3 组件目录）+ 优先级依赖序** 逐族展开，避免实施时"改了顶栏主体还是 View"的半吊子状态。

**设计原则（对齐 ui-standards §7 页面改造检查清单 + §9 主干→支干→枝叶）**：
- 每页改造 = **壳（Fragment 托管 composeView）+ 内容区（Compose）** 双轨，一次性到位，不再停留在"只改顶栏"。
- 复用已接线的公共组件（GlassTopAppBar/SettingsSearchBar/AppDropdownMenu/AppModalBottomSheet/ListScaffold/GroupHeader/SwipeActionContainer），禁止页面私有复制（AD-21 门禁）。
- 内核红线（逐字平移）：探索控件 JS 双求值链 / InfoMap LruCache / SourceLoginJsExtensions 桥 / FlexboxLayout→Compose FlowRow 语义；RecyclerView 可保留为 Compose 内 `LazyColumn`/`LazyVerticalGrid` 或 `AndroidView` 桥接（依页面）。
- 每族迁移遵循依赖序（先公共组件 → 再样板页打个样 → 同族复用），迁移后填 §3.3 实施回执（回执缺失=未完成）。

**逐族迁移矩阵**：

| 族 | 骨架 | 已 Compose | 待 Compose 主体 | 复用公共组件 | 改造策略 | 优先级 |
|----|------|-----------|----------------|-------------|---------|--------|
| **E1 发现页 Explore** | S2 | 顶栏+搜索+菜单 | View `TabLayout` → Compose 标签行；RecyclerView 探索控件列表 | `GroupTabRow`（新增，对齐 BookGroupTabs）、`SettingsSearchBar`、`AppDropdownMenu`、`ListScaffold` | 见 **P3-3a**（标签行替换 TabLayout 槽位） | P1 |
| **E2 订阅页 Rss** | S2 | 顶栏+搜索+菜单 | View `TabLayout` → Compose 标签行；RecyclerView 卡片网格 | 同 E1 | 同 P3-3a | P1 |
| **E3 书源管理 BookSourceActivity** | S2 | BookSourceScreen/Items | RecyclerView 壳（双轨已建） | `ListLayoutMenu`、`SwipeActionContainer`、`GroupHeader`、`SortActionMenu` | 壳层交付，列表 LazyColumn 收敛 | P1 |
| **E4 书源编辑 BookSourceEditActivity** | S3 | 5 处 compose | 字段表单主体 | `SettingsCard` 字段分组、`AppSelectDialog`（类型）、`KeyboardToolPop` | 见问题7（P2 已含头部还原） | P2 |
| **E5 订阅源管理 RssSourceActivity** | S2 | 顶栏 | RecyclerView 列表 + 布局切换 | `RssSourceAdapterCompact/Grid` → LazyLayout、`ListLayoutMenu` | 同型页照抄 BookSource 样板 | P1 |
| **E6 订阅源编辑 RssSourceEditActivity** | S3 | GlassTopAppBar | **XML 表单主体（保留，被用户认可，不迁移）** | — | 仅核对风格一致性，不迁移主体 | N |
| **E7 书籍信息编辑 BookInfoEditActivity** | S3 | BookInfoEditScreen | 壳 | — | 已基本完成，收尾回执 | P3 |
| **E8 搜索 SearchActivity/SearchContentActivity** | S2 | GlassTopAppBar | 搜索列表 + 历史 | `SettingsSearchBar`、`ListScaffold` | 同型页照抄 Sample | P2 |
| **E9 替换 ReplaceRuleActivity** | S3 | Compose 顶栏 | 规则编辑列表 | `AppEditDialog`、`SettingsToggleRow` | 同型页照抄 | P2 |
| **E10 漫画 ReadMangaActivity** | S5 | composeHost | 画布内核（保留 View） | titleBar 浮层 | 内核红线，仅壳 Compose | N |
| **E11 视频 VideoPlayerActivity** | S5 | View+Compose 壳 | 播放内核（保留 View） | titleBar 浮层 | 内核红线，仅壳 Compose | N |
| **E12 目录 TocActivity** | S2 | BookTocBookmarkSheet | 目录列表主体 | `BookTocBookmarkSheet`、`AppModalBottomSheet` | 目录列表 LazyColumn 收敛 | P2 |
| **E13 配置子页（Backup/Other）** | S2 | 无 Screen | PreferenceFragment 全迁移 | `SettingsSection/Card/ClickRow/ToggleRow` | 见 **P3-3b** | P3 |
| **E14 主题/封面/精准/欢迎配置** | S2 | 对应 Screen | Fragment 壳 | Settings 族 | 壳层交付，回执收尾 | P1 |
| **E15 MainActivity** | S1 | PillNavigationBar | ViewPager/Fragment 壳 | `PillNavigationBar`、`BadgeDot` | 壳保留（Tab 架构），已接入 | P1 |

**P3-3a 发现/订阅 Compose 标签行（已由 P1 提前交付，本节仅作归档参考）**
- **实施状态**：已交付（P1-1 + P1-2 于 2026-08-18 完成，编译通过 `assembleAppDebug`）。
- 涉及工作：`GroupTabRow` 公共组件已创建（`ui/widget/components/GroupTabRow.kt`）、`fragment_explore.xml`/`fragment_rss.xml` 中 View `TabLayout` 已删除、标签行在 `compose_top_bar` 的 `setContent` 内 `Column` 中渲染、搜索框按 `isShowingFolder` 显隐、标签选中 6 分支 DAO Flow 不变。
- 验收通过标准：发现/订阅标签与书架视觉一致（M3 token 无硬编码色）；搜索框显隐规则符合（分组隐藏/进文件夹限定）；点标签切换分组即时刷新。**P3-3a 视为已闭合，P3 阶段不再重复处理。**

**P3-3b 配置子页迁移（BackupConfig/OtherConfig）**
- **实施反哺（2026-08-18，OtherConfig 已完成交付）**：
  - `OtherConfigFragment` 已完成 Compose 化：PreferenceFragment → Fragment + ComposeView（对齐 CoverConfigFragment 双轨范式），内容区全 Compose（[`OtherConfigScreen.kt`](../ui-issues-round-20260818/../../../../app/src/main/java/io/legado/app/ui/config/OtherConfigScreen.kt)，Main Activity 组 + 其他设置组 8 卡片，全部设置项零裁剪迁移）。
  - 与设计文档差异点（实施决策反哺）：① Screen 用 `onToggleChange(key, value)` 通用回调（key 即 PreferKey 常量值）+ `onItemClick(key)` + 三个单选回调（`onLanguageSelect`/`onHomePageSelect`/`onVariantSelect`），语言/默认首页/更新渠道三项 NameListPreference 用 `AppSelectDialog`（悬浮单选）呈现，非底部面板；② 副作用统一收敛策略：开关副作用（recordLog 日志链/debugLogFloatingBall 悬浮球/processText 组件开关/showDiscovery·showRss 主 Tab 通知）全部由 `onSharedPreferenceChanged` 统一处理（与 PreferenceFragment 原行为一致），`onToggleChange` 只写偏好+更新状态，避免双重执行；③ NumberPicker 全部点击项（线程数/缓存/端口等）保留原 Fragment 副作用；④ `pref_config_other.xml` 已确认无代码引用后删除；⑤ 语言切换 restart 由 `listView.postDelayed` 改 `view?.postDelayed`。
  - 保留的隐藏项：`threadCount`（旧线程数迁移隐藏项，XML `isPreferenceVisible=false`）无 UI 入口，迁移 toast（`migratedThreadCountJustDone`）保留。
- 现状：**P3-2b 已交付（2026-08-18）**，`BackupConfigFragment` 已完成 Compose 化：`PreferenceFragment` → Fragment + ComposeView（对齐 OtherConfigFragment 双轨范式），内容区全 Compose（`BackupConfigScreen.kt`：WebDAV 设置组 + 备份与恢复组，全部设置项零裁剪迁移）。`pref_config_backup.xml` 已确认无代码引用后删除。
- **P3-2b 实施反哺（相对设计文档）**：
  - ① Screen 桥接状态：`webDavUrl/webDavAccount/webDavPassword/webDavDir/webDavDeviceName/syncBookProgress/syncBookProgressPlus/backupPath/onlyLatestBackup/autoCheckNewBackup` 10 项，全部在 `onCreateView` 延迟初始化（构造期 `requireContext` 未 attach，直接用 `mutableStateOf("")` 默认值会崩），`onSharedPreferenceChanged` 统一刷新（对齐 PreferenceFragment 原行为）。
  - ② 副作用收敛：开关项（`syncBookProgress/syncBookProgressPlus/onlyLatestBackup/autoCheckNewBackup`）由 `onToggleChange` 写偏好 + 更新状态，副作用经 `onSharedPreferenceChanged` 统一处理避免双重执行；点击项（WebDAV 编辑/备份/恢复/备份路径/导入旧数据/备份忽略）保留原 Fragment 全部副作用（`showEditTextDialog`/`backup()`/`restore()`/`backupIgnore()`/`restoreOld`）。
  - ③ 隐藏功能保留：「恢复」行长按 → 本地恢复（原版 `web_dav_restore` Preference 的 `onLongClick` 隐藏功能），`SettingsClickRow` 新增可选 `onLongClick` 参数（`combinedClickable`，`SettingsClickRow.kt:46`）。
  - ④ WebDAV 5 个编辑项（地址/账户/密码/子目录/设备名）用原 `alert{}` + `DialogEditTextBinding` 编辑框（保留密码 `inputType` 语义），未改 `AppEditDialog`（跨 View/Compose 边界，密码框语义需谨慎）。
  - ⑤ 顶栏菜单迁移：原 `menu_backup_restore`（帮助/日志）迁移至 `ConfigActivity.setTopBarMenu`（`MenuAction` 数据驱动），与 L-E1 S2 改造一致。
- 迁移范式（对齐 ThemeConfigFragment→ThemeConfigScreen、CoverConfigFragment→CoverConfigScreen 已验证模式）：
  1. 新增 `BackupConfigScreen.kt`/`OtherConfigScreen.kt`：内容区全 Compose，复用 `SettingsSection`（分组标题）+ `SettingsCard`（卡片）+ `SettingsClickRow`（点击项含打开/选择文件/输入框）+ `SettingsToggleRow`（开关项）。`BackupConfigFragment`/`OtherConfigFragment` 壳改为 `binding.composeContent.setContent { LegadoTheme { BackupConfigScreen(...) } }`。
  2. 桥接：Fragment 持有各行状态（读写 AppConfig/PreferenceManager），传到 Screen 的 `value`/`onChange` 回调；文件选择（HandleFileContract）、WebDAV 弹窗、权限申请等副作用保留在 Fragment（Compose 只做 UI 与回调上抛）。
  3. 设置项逐条迁移（Backup：备份目录/自动备份周期/WebDAV 地址-账户-密码/本地备份/恢复；Other：可核对后按实际 XML pref 表逐项迁移），**功能项不漏**（红线）。
- 验收：两子页全 Compose；所有设置项可见可操作；功能点与迁移前一致。

**P3 阶段真机验证反哺（2026-08-18 新增）**
- **真机发现 Bug（BookSourceActivity BackHandler 递归）**：书源管理页按返回键后 logcat 出现 2200+ 行 `StackOverflowError` 堆栈（FATAL=0 未崩溃，但属真实回归）。根因：Compose `BackHandler`（BookSourceScreen.kt:180）回调 → `onBack()` → `BookSourceActivity.onBackPressed()`（BookSourceActivity.kt:595）→ 默认分支 `super.onBackPressed()` → `OnBackPressedDispatcher` 重新分发返回事件 → 再次进入同一 `BackHandler` → 无限递归。
  - **修复决策**：`onBackPressed()` 默认分支由 `super.onBackPressed()` 改为 `finish()`（`finish()` 已有覆写处理搜索词清空逻辑，行为完整），避免 dispatcher 重入。修复后按返回键 AndroidRuntime E 行数降为 0，验证通过。
  - **设计文档未覆盖点**：原设计未预见 Compose `BackHandler` 与 Activity `onBackPressed()` 覆写的递归风险；本 bug 仅在真机验证（进入书源管理页按返回键）时暴露，静态分析不可见。教训：凡 Compose `BackHandler` 与 Activity `onBackPressed()` 覆写并存时，回调须走 `finish()` 而非 `super.onBackPressed()`，避免 dispatcher 重入。

**P3-3c 全量巡检门禁（对齐 AD-21）**
- grep 页面私有弹框/私有组件清零：无页面自建 `Dialog`/`DropdownMenu`/`Checkbox` 开关，全部走公共组件族。
- 除 N 类页（阅读详情/漫画/视频/订阅源编辑/WebView/代码编辑器/扫码/透明窗，`N 不迁移`）外，本批次涉及页面均为 Compose。
- 每页填写 §3.3 实施回执，回执缺失=未完成。

---

### P4：全页面 Compose 化优先级依赖序（汇总）

> 页面迁移顺序 = 用户高频 × 公共组件就绪度 × 内核红线边界，与 ui-redesign-m3 §9 树枝叶策略一致。

```
P0（本批次）  P1（本spec P1-3）      P2（本spec P2）          P3（本spec P3-3）
问题1/8/2   │  发现/订阅标签+搜索   │  书源编辑头还原          │  配置子页 Backup/Other
           │  书源/订阅源管理壳     │  弹框/开关统一           │  目录/搜索/替换列表
           │  批量分组             │                        │  长尾页增量
            └──────────────┬───────┴────────────────────────┴── 全量巡检门禁
                          └────────► 每阶段独立编译 + 真机 L2 验证 + 回执
```

## Architecture Decisions

> 使用 ADR Y-Statement 模板（Context / Concern / Decision / Goal / Tradeoff / Status / Superseded-by）。

### AD-01: 书架分组样式切换用 RECREATE 重建 fragment，而非改 Compose 内部状态
- **Context**: `MainActivity.getFragmentId` 按 `AppConfig.bookGroupStyle` 返回 style1(BookshelfFragment1, Tab)/style2(BookshelfFragment2, Folder) 两类不同 fragment；`BaseBookshelfFragment.configBookshelf()` 切换 bookGroupStyle 时仅 `postEvent(NOTIFY_MAIN)` 刷新底部菜单与 Tab 切换，fragment 类型未变 → 头部样式不更新。`FragmentStatePagerAdapter.getItemPosition` 已对「fragmentId 与实例类型不匹配」返回 `POSITION_NONE`，RECREATE 会触发重建。
- **Concern**: 若改为在 Compose 内部做 style1/style2 双态渲染，需在单个 fragment 内维护两套头部/数据订阅状态（style1 分组 Tab vs style2 文件夹），与现有 `getItemPosition` 类型判定机制冲突，且引入双份状态同步成本与回归面。
- **Decision**: `configBookshelf()` 中 bookGroupStyle 变化并入 `recreate=true` 分支，`postEvent(EventBus.RECREATE, "")`；由 `BaseActivity.recreate()` → adapter 类型不匹配 → 重建对应 fragment。Compose 内部不改双态逻辑。
- **Goal**: 复用现有 fragment 生命周期与 ViewPager 重建机制，改动最小、行为与原版一致。
- **Tradeoff**: RECREATE 会重建整个 Activity（含其他 Tab），成本略高于局部刷新；但频次极低（仅用户手动切换分组样式时），可接受。
- **Status**: Proposed
- **Superseded-by**: —

### AD-02: 长按书架书进详情改传完整 book 关键字段（补传 bookUrl）
- **Context**: `BookshelfFragment1/2.onBookLongClick` 仅 `putExtra("name"/"author")`；`BookInfoViewModel.initData` 先用 `getBook(name, author)` 从书架库匹配，name/author 为空或重复时匹配失败 → book 为 null。`onBookClick` 的 `startActivityForBook`（`ContextExtensions.kt`）是进阅读页路径，与长按进详情路径不同。
- **Concern**: 只加 `getBook(name, author)` 兜底无法覆盖空/重名场景；直接复用 `startActivityForBook` 会错误进入阅读页而非详情页。
- **Decision**: 长按回调保持 `startActivity<BookInfoActivity>`，补传 `bookUrl` extra（保留 name/author 兼容），复用 `initData` 已有「`getBook(bookUrl)` → `getSearchBook(bookUrl)`」兜底链。
- **Goal**: 任意书架书长按均可稳定进入详情；最小改动、零 ViewModel 变更。
- **Tradeoff**: 多传一个 extra 无副作用；`getBook(bookUrl)` 书架库主键查询路径需真机验证（含本地书/URL 书）。
- **Status**: Proposed
- **Superseded-by**: —

### AD-03: 发现/订阅标签样式复用并对齐书架 BookGroupTabs
- **Context**: 发现/订阅目前用 View `TabLayout`（`com.google.android.material.tabs.TabLayout`）+ 固定 `SettingsSearchBar`；书架 style1 已是 Compose `ScrollableTabRow`（`BookshelfScreen.BookGroupTabs`）。
- **Concern**: View TabLayout 与书架 Compose 标签视觉/行为割裂，且搜索框固定显示与「分组模式隐藏、进文件夹限定范围」需求冲突。
- **Decision**: 发现/订阅标签替换为 Compose 标签行（复用/对齐 `BookGroupTabs` 的 ScrollableTabRow + SecondaryIndicator 渲染思路，按 `sourceGroupStyle` 填充分组/类型 Tab，新增为公共组件供两页共用）；搜索框按模式显隐。
- **Goal**: 发现/订阅/书架三处标签视觉一致（M3 token，无硬编码色），搜索行为符合「分组隐藏、进文件夹限定」预期。
- **Tradeoff**: 替换 View TabLayout 需移除 `initTabLayout`/`upTabLayout`/`tabSelectedListener` 及 XML `binding.tabLayout` 引用，改动面集中在两 Fragment；DAO 6 分支查询无需改。
- **Status**: Proposed
- **Superseded-by**: —

### AD-04: 书源编辑页头部还原为贴近原版 XML 表单风格（尊重原样式而非重新设计）
- **Context**: `BookSourceEditActivity.initComposeQuickToolbar` 在 S3 阶段3 被改为 `FlowRow`+`Checkbox`+`DropdownMenu` 紧凑风格，用户反馈「被改丑」；`RssSourceEditActivity` 仅顶栏 Compose 化、主体保留原 XML 表单。
- **Concern**: 重新设计会再次偏离用户认知的既有表单布局，且与订阅源编辑页风格不一致。
- **Decision**: 书源编辑页头部还原为贴近原版 XML 表单风格（朴素 CheckBox 横排 + 类型选择 `AppSelectDialog`），不做主观再设计；开关对齐 `SettingsToggleRow` 视觉。
- **Goal**: 书源/订阅源两编辑页头部观感一致、接近原版，可读性提升。
- **Tradeoff**: 放弃已实现的紧凑排版（为还原回退部分 S3 样式），但保住用户熟悉的表单结构与操作效率。
- **Status**: Proposed
- **Superseded-by**: —

### AD-05: 弹框三样式统一为公共组件族（AppDropdownMenu / AppModalBottomSheet / Dialog 族）
- **Context**: 项目已有三类弹框组件：`AppDropdownMenu`（右上角下拉）、`AppModalBottomSheet`（底部面板）、Dialog 族 `AppEditDialog`/`AppSelectDialog`/`ConfirmDialog`（悬浮居中）；各页面存在页面私有弹框/内联 Checkbox 开关。
- **Concern**: 无统一约定则每页各自弹框，token/圆角/间距漂移，与 ui-redesign-m3 AD-21「组件复用强制规范」冲突。
- **Decision**: 弹框按语义三选一收敛为公共组件族；设置开关统一 `SettingsToggleRow`（M3 Switch）；改造页禁止私有弹框实现。
- **Goal**: 全局弹框可枚举、视觉一致、复用率收敛（对齐 AD-21 验收 KPI）。
- **Tradeoff**: 首期需清理存量私有弹框（grep 排查收敛）；对已验收页面有一定改动量。
- **Status**: Proposed
- **Superseded-by**: —

### AD-06: 功能裁剪回溯只恢复不新增（红线清单）
- **Context**: Compose 化改造（ui-redesign-m3 多阶段）中可能存在被裁剪/降级的功能（对比 8 月 4 号前版本），用户要求回溯。
- **Concern**: 回溯若同时允许新增功能，范围失控、回归面扩大；只列缺失不恢复则问题悬置。
- **Decision**: 以 8 月 4 号前版本为基线做 `git diff` 裁剪清单，**只恢复缺失功能、禁止新增**；恢复项逐条真机回归并登记。
- **Goal**: 用户既有功能无感回归，杜绝「改 UI 丢功能」。
- **Tradeoff**: 回溯恢复会回退少量「为简化而裁剪」的 UI 状态，需在还原与极简之间取用户原行为为准。
- **Status**: Proposed
- **Superseded-by**: —

## Data Flow

1. **书架分组样式切换**：用户「书架布局」弹框选「标签/文件夹」→ `configBookshelf()` 检测 `bookGroupStyle` 变化 → 置 `recreate=true` → `postEvent(EventBus.RECREATE, "")` → `BaseActivity` 订阅（`recreateOnThemeChange=true`）→ `recreate()` → `FragmentStatePagerAdapter.getItemPosition` 判定 fragmentId 与实例类型不匹配（`idBookshelf1 vs BookshelfFragment2` 等）返回 `POSITION_NONE` → 书架 fragment 重建 → style1 头部（GlassTopAppBar + 分组 Tab）/style2（文件夹）按新样式重渲染。
2. **发现/订阅搜索范围**：默认标签模式（`sourceGroupMode==0`）→ 显示头部标签行 + 搜索框；分组模式（`sourceGroupMode==1`）文件夹视图（`isShowingFolder=true`）→ 隐藏搜索框；点击文件夹进入列表（`isShowingFolder=false`，`currentGroup`/`currentType` 已设置）→ 显示搜索框，输入触发 `upExploreData(query)` / `upRssFlowJob(query)` → 走 6 分支 DAO Flow（含 `flowGroupSearchExact(currentGroup, searchKey)` / `flowByTypeSearch(currentType, searchKey)`）→ `flowWithLifecycleAndDatabaseChange` → 列表仅含当前分组/类型结果。
3. **长按书架书进详情**：长按 → `onBookLongClick(book)` → `startActivity<BookInfoActivity>` 携带 `name`/`author`/`bookUrl` → `BookInfoViewModel.initData(intent)` → `getBook(name, author)`（书架库）命中即展示；未命中 → `bookUrl` 非空 → `getBook(bookUrl)`（书架库主键）→ `getSearchBook(bookUrl)`（搜索库）→ 逐级兜底 → `upBook()` 发布 `bookData` → 详情页渲染，book 非空。
4. **沉浸式操作栏**：`AppConfig.immNavigationBar=true` → `BaseActivity.upNavigationBarColor()` / `ComposeActivitySupport.setupLegadoComposeSystemBar()` 联动 → 底部导航栏 `setNavigationBarColorAuto(ThemeStore.navigationBarColor)` + 顶部状态栏走透明沉浸（`setStatusBarColorAuto(ThemeStore.statusBarColor(this, true), true, fullScreen)`）→ 顶栏随内容沉浸；`ThemeConfigFragment` 开关变更 → `recreateActivities()` 即时生效。

## File Changes

| 文件 | 类型 | 变更内容说明 |
|------|------|-------------|
| `app/src/main/java/io/legado/app/ui/main/bookshelf/BaseBookshelfFragment.kt` | 修改 | `configBookshelf()` 中 bookGroupStyle 变化并入 `recreate=true` 分支（postEvent `RECREATE`）；`initComposeTopBar()` 支持头部内嵌分组 Tab（如适用） |
| `app/src/main/java/io/legado/app/ui/main/MainActivity.kt` | 修改 | 核对 `getFragmentId`/`getItemPosition`（已支持类型不匹配重建，无需大改；仅按需调整头部 Tab 联动） |
| `app/src/main/java/io/legado/app/ui/main/bookshelf/BookshelfScreen.kt` | 修改 | `BookGroupTabs` 渲染逻辑对齐原版固定 Tab（全部/本地）+ 可提取为公共组件 |
| `app/src/main/java/io/legado/app/ui/main/bookshelf/style1/BookshelfFragment1.kt` | 修改 | `onBookLongClick` 补传 `bookUrl` extra（问题 8） |
| `app/src/main/java/io/legado/app/ui/main/bookshelf/style2/BookshelfFragment2.kt` | 修改 | `onBookLongClick` 补传 `bookUrl` extra（问题 8） |
| `app/src/main/java/io/legado/app/ui/book/source/edit/BookSourceEditActivity.kt` | 修改 | `initComposeQuickToolbar` 还原为贴近原版 XML 表单风格；类型选择改 `AppSelectDialog`；开关对齐 `SettingsToggleRow`（问题 7） |
| `app/src/main/java/io/legado/app/ui/rss/source/edit/RssSourceEditActivity.kt` | 核对/微调 | 顶栏 `GlassTopAppBar` + 原 XML 表单主体保留，核对全局风格一致性（问题 7） |
| `app/src/main/java/io/legado/app/ui/main/explore/ExploreFragment.kt` | 修改 | View `TabLayout` 替换为 Compose 标签行（问题 5）；`SettingsSearchBar` 按模式显隐（问题 5）；`buildMenuActions` 移除分组弹框段 + 新增「分组管理」「批量改分组」入口（问题 6/4）；搜索限当前分组/类型 |
| `app/src/main/java/io/legado/app/ui/main/rss/RssFragment.kt` | 修改 | 同 ExploreFragment：标签 Compose 化 + 搜索框显隐 + 菜单分组项移除 + 分组管理/批量改分组入口（问题 5/6/4） |
| `app/src/main/java/io/legado/app/ui/main/explore/ExploreViewModel.kt` | 修改 | 新增 `selectionAddToGroups`/`selectionRemoveFromGroups` 批量分组方法（问题 4，`BookSourceDao.upGroup(List)`） |
| `app/src/main/java/io/legado/app/ui/main/rss/RssViewModel.kt` | 修改 | 新增 `selectionAddToGroups`/`selectionRemoveFromGroups` 批量分组方法（问题 4，`RssSourceDao.update(*array)`） |
| `app/src/main/java/io/legado/app/help/config/AppConfig.kt` | 修改 | `sourceGroupStyle` 默认值 0→1（按类型分组）+ `migrateSourceConfigIfNeeded()` 迁移映射调整（问题 5/P1-1） |
| `app/src/main/java/io/legado/app/base/BaseActivity.kt` | 修改 | `upNavigationBarColor()` / 状态栏设置联动 `immNavigationBar`（问题 2） |
| `app/src/main/java/io/legado/app/ui/theme/ComposeActivitySupport.kt` | 修改 | `setupLegadoComposeSystemBar()` 联动 `immNavigationBar` 状态栏沉浸（问题 2） |
| `app/src/main/java/io/legado/app/ui/config/ThemeConfigFragment.kt` | 核对/微调 | 开关说明文案同步（问题 2）；`recreateActivities()` 保留 |
| `app/src/main/java/io/legado/app/ui/book/info/BookInfoActivity.kt` | 核对 | `initData` 的 bookUrl 兜底分支已存在，确认不改（问题 8） |
| `app/src/main/java/io/legado/app/ui/book/info/BookInfoViewModel.kt` | 核对 | `initData` 兜底链（getBook(name,author) → getBook(bookUrl) → getSearchBook(bookUrl)）确认，不改（问题 8） |
| `app/src/main/java/io/legado/app/ui/widget/components/`（弹框族） | 核对/补缺 | `AppDropdownMenu`/`AppModalBottomSheet`/`AppEditDialog`/`AppSelectDialog`/`ConfirmDialog`/`SettingsToggleRow` 已存在，核对签名与调用一致性（问题 9） |
| 新增 `app/src/main/java/io/legado/app/ui/widget/components/GroupTabRow.kt` | 新增 | 发现/订阅/书架共用的 Compose 标签行（对齐 `BookGroupTabs`，`ScrollableTabRow` + 分组/类型 Tab 填充）（问题 5/AD-03，P1 已交付） |
| 新增 `app/src/main/java/io/legado/app/ui/widget/BatchGroupDialog.kt` | 新增 | 批量改分组对话框（checkbox 多选 + 全选/反选 + 移入/移出分组菜单），回调索引由调用方映射（问题 4/P1-3b） |
| 新增 `app/src/main/res/layout/item_batch_group.xml` + `res/menu/batch_group.xml` | 新增 | 批量改分组对话框的列表项布局与工具栏菜单（问题 4/P1-3b） |
| 复用 书源/订阅源分组管理 Dialog | 复用 | 复用已存在 `ui/book/source/manage/GroupManageDialog.kt`/`ui/rss/source/manage/GroupManageDialog.kt`（分组 CRUD，P1-3a 已交付）+ 批量改分组 Dialog（P1-3b 已交付，见上） |
| 新增 `app/src/main/java/io/legado/app/ui/config/OtherConfigScreen.kt` | 新增 | `OtherConfigFragment` 的 Compose 化内容（问题 3/P3-2） |
| 新增 `app/src/main/java/io/legado/app/ui/config/BackupConfigScreen.kt` | 新增 | `BackupConfigFragment` 的 Compose 化内容（问题 3/P3-2） |
| `app/src/main/java/io/legado/app/ui/config/OtherConfigFragment.kt` | 修改 | 托管 Compose 内容，清理/迁移 XML 布局（问题 3） |
| `app/src/main/java/io/legado/app/ui/config/BackupConfigFragment.kt` | 修改 | 托管 Compose 内容，清理/迁移 XML 布局（问题 3） |
| `app/src/main/java/io/legado/app/ui/welcome/WelcomeScreen.kt` | 核对/微调 | 保持四显隐开关纯展示职责；配置收敛 `WelcomeConfigScreen`（问题 3） |
| `docs/specs/ui-issues-round-20260818/regression-inventory.md` | 新增 | P3 功能裁剪回溯清单（8 月 4 号前基线 diff 产物） |
| `app/src/main/res/values/strings.xml` | 修改 | 新增「分组管理」等新入口字符串（禁止硬编码） |

> 说明：`RssSourceEditActivity.kt`、`BookInfoActivity.kt`、`BookInfoViewModel.kt` 列为「核对」项——本批次对它们的目标是不引入不必要的改动，仅确认行为符合根因预期；实际变更集中在书架两 Fragment、发现/订阅两 Fragment 与公共组件/配置页。
