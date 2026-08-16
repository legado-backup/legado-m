# 页面全景清单 · pages-inventory（全量 84 页面类功能点核对表）

> 本文件是 ui-redesign-m3 的**页面级基线**，回答两个硬约束：**「核心功能一个不漏」**与**「每个页面是否从外到里分析清楚」**。
> 每一页 = 功能点清单（源码探针佐证）+ 当前技术栈 + 归属骨架类型 + 迁移优先级 + 真机覆盖状态。
> 新增/优化页面时**必须先在此登记**，再进 ui-standards.md 套骨架、选组件、写真机用例。

## 0. 总览（84 页面类 · 按功能域）

| 功能域 | 页面数 | 已 Compose | 未 Compose |
|--------|-------|-----------|-----------|
| A 主框架/我的 | 8 | 3（书架1/2、MyFragment） | 5 |
| B 阅读器核心 | 16 | 0 | 16 |
| C 书源/规则/工具 | 20 | 7（debug 工具族） | 13 |
| D RSS/订阅 | 13 | 0 | 13 |
| E 配置子页 | 6 | 0 | 6 |
| F 其它（about/透明窗） | 6 | 0 | 6 |
| **合计** | **69 页面类 + 15 抽象/壳 = 84** | **10.7%** | **89.3%** |

> 技术栈术语：`View`=纯 XML View（VMBaseActivity/BaseActivity + ViewBinding）；`Compose`=纯 Compose 渲染；`混血`=XML 壳内嵌 ComposeView。
> 骨架类型：`S1 主框架Tab` `S2 列表管理页` `S3 表单/编辑器页` `S4 详情/阅读页` `S5 全屏沉浸页` `S6 弹窗/透明窗`（详见 ui-standards.md）。
> 迁移优先级：`P0 已改造` `P1 高优核心` `P2 次优高频` `P3 长尾低频` `N 不迁移（内核/无UI）`。

---

## A. 主框架 / 我的（8 页面类）

### A1. MainActivity（主框架 4Tab）
- 路径 `ui/main/MainActivity.kt` + `activity_main.xml`｜技术 **View**｜骨架 S1｜优先级 P1
- 功能点：① ViewPager 托管 4 Tab（offscreenPageLimit=3）② Tab 可见性开关（`upBottomMenu` 按 showDiscovery/showRSS）③ 默认首页切换 `upHomePage` ④ 书架上新角标（Compose `PillNavTab.badgeCount`←onUpBooksLiveData）⑤ 双击返回退出（2s）⑥ 隐私协议弹窗（拒绝 finish）⑦ 版本更新/更新日志 `upVersion` ⑧ 首次设本地密码 ⑨ 崩溃提示 CrashLogsDialog ⑩ WebDav 自动备份检查 ⑪ 自动更新书源/书籍（延时1/2/3s）⑫ 外部导入统一入口 `openImportUi`（书源/订阅源/替换 3 Dialog）⑬ 书架样式切换重建 recreate（Tab 位置保活）⑭ 回收池
- 手势：底部导航单击切 Tab；Tab 重选（书架双击回顶/发现收起）；ViewPager 滑动同步选中态；返回键先回书架再退出
- ✅ **v2.11 接线完成（2026-08-12，本窗口，tasks.md 12.20）**：PillNavigationBar 已接线（ComposeView 桥接，LegadoTheme 包裹）+ defaultTabs() 废弃 + badgeCount 接管 + Tab 保活 + 全 i18n。→ 骨架 **S1 主框架壳部分(底栏) Compose 已落地**，ViewPager/Fragment 架构保留。**状态：接线 ✅ / FR-11 真机 ✅（tasks.md 12.21，MEmu 验证通过）**
- 设计要点：底部导航改 `PillNavigationBar`（AD-17），4 Tab 保留，Tab 可见性逻辑保留
- 🔎 **v2.8 预审（2026-08-11，explore 深审 MainActivity 509 行+XML+ThemeBottomNavigationVIew+PillNavigationBar+MainViewModel，见 tasks.md 12.16o）**：骨架判定 **S1 主导航壳**（正确）。**已符合 12 项（✅1-✅12）**：configChanges 声明旋转不重建/pagePosition 天然存活/无 requestedOrientation 跟随系统/沉浸式（VMBaseActivity fullScreen）/无硬编码色（grep 0+@color/background 昼夜双值）/可隐藏 Tab（upBottomMenu:392-412 realPositions 重映射）/Tab 重选手势（onNavigationItemReselected:172-190 gotoTop+compressExplore 300ms 双守卫）/返回键优先级链（:101-121 非首页回书架→bookshelf2 back→双击退出）/换肤走 RECREATE 即时切换（AD-18 合规，EventBus.REPAINT 不存在实际用 RECREATE）/底部 inset 处理（:202-206 windowInsetsListener）/路由决策不引 Nav3 一致/功能点 14 项逐一有落点（openImportUi:495-507 三 Dialog+postLoad/ruleSubsUp/upAllBookToc 延时链:139-151）。**违例 10 项（V1-V10）**：V1 **PillNavigationBar 零接线**（孤儿，grep 全仓仅自文件引用；现状用 BottomNavigationView activity_main.xml:16-24）——S1 样板首接线点即本页；V2 硬编码中文（:301 崩溃提示正文「检测到阅读发生了崩溃…」未走 R.string）；V3 硬编码 hint（:279 `"password"` 字面量非资源）；V4 **PillNavigationBar 自身硬编码中文+结构失真**（:171,176,181,186 defaultTabs() 写死「书架/发现/历史/我的」且「历史」与真实四 Tab「书架/发现/订阅/我的」不符已过期失真+:156 fontSize=10.sp 写死字号违反 §1.1）——接线前必须废弃 defaultTabs() 改接线页显式传真实 tabs+stringResource；V5 无 §3.3 回执；V6 **Tab 位置跨 recreate 不保活**（onSaveInstanceState:331-336 仅存 isAutoRefreshedBook，recreate:351-356 后 upHomePage:414-427 无条件按 defaultHomePage 覆盖——用户在「我的」页切主题回来被打回默认首页；修复=savedInstanceState 存 pagePosition+recreate 已存则跳过 upHomePage，Compose 化等价 rememberSaveable）；V7 私有弹窗布局（setLocalPassword:277-293 DialogEditTextBinding+alert/notifyAppCrash:301 alert/backupSync:321 alert/upVersion:252-263 TextDialog 非 L2 族）；V8 角标用 View BadgeView 未用公共 BadgeDot（:359-364 ThemeBottomNavigationVIew:50-58 addBadgeView(0) 手工 inflate，PillNavigationBar 接线后由 PillNavTab.badgeCount 接管，BadgeView 可退役）；V9 S1 壳未包 LegadoTheme（底栏 View 走 ThemeStore 旧 5 色+recreate 重建，M3 34 槽位未接入本壳）；V10 弃用 API+勾选同步 hack（L1 @file:Suppress(DEPRECATION)+FragmentStatePagerAdapter @Deprecated+:441 `menu[realPositions[position]].isChecked=true` 把 ID 值当菜单下标+返回 false 监听器与 onPageSelected 二次纠正隐形耦合——PillNavigationBar 受控组件接线后天然消除）。**PillNavigationBar 接线方案（S1 样板首接线，低风险序）**：① activity_main.xml 底栏槽位换 ComposeView+setContent{LegadoTheme{PillNavigationBar(...)}}（ViewPager 不动）② 受控映射 selectedTab←pagePosition/onTabSelect←viewPagerMain.setCurrentItem(index,false) ③ tabs 动态构建按 showDiscovery/showRSS 过滤+badgeCount←onUpBooksLiveData.value ④ BackHandler 双击退出链:101-121 原样保留 ⑤ insets 用 windowInsetsPadding(WindowInsets.navigationBars) 对齐 :202-206 ⑥ 前置清理：V4 defaultTabs 硬编码/失真/V5 回执/V6 Tab 保活 ⑦ 遗留映射：menu_bnv 四 id→四个 PillNavTab（RSS 图标需替换 History 语义）。风险：PillNavigationBar 未包 LegadoTheme（读 MaterialTheme.colorScheme:61-65）调用方必须提供主题；badgeCount=-1 纯圆点语义与现有 setBadgeCount 计数角标需对齐。**fork 差距**：PillNavigationBar 为简化版（缺滑动指示圆点 4dp spring+radial glow/combinedClickable 长按/tabExtras 插槽/state 读下沉防整树重组/1dp 顶白高光，MoRealm 有）；导航安全缺 Tab 切换连点节流（MoRealm navigateToReader 500ms 节流，本仓仅 reselect 300ms）

### A2. MyFragment + ProfileScreen3Level（我的页）
- 路径 `ui/main/my/`｜技术 **混血（XML 壳 + ComposeView）**｜骨架 S2｜优先级 **P0 已改造**
- 功能点（Compose `ProfileScreen3Level` 276行）：① 统计卡 MetricGrid（真实 Room：阅读数/总时长/书签数/书源数）② 高频功能卡 8 行（备份恢复/主题/其他/书源管理/替换净化/词典/TXT目录/自动任务）③ 服务开关 2（Web服务/自动任务服务）④ 低频 6 行（书签/阅读记录/文件管理/精准管理/关于/退出）
- ✅ 符合项（v2.8 复审，2026-08-11）：组件复用率最高（全页 import 设置族：MetricGrid/SettingsSection/SettingsCard/SettingsClickRow×14/SettingsToggleRow×2，页面几乎无私有实现）；LegadoTheme 包裹 ✅；无硬编码色/字号走 typography ✅；文案全走 getString ✅；骨架 S2 归类正确；主题/换肤由 Fragment 壳 TitleBar 承接
- ⚠️ 遗留（v2.8 复审新增 4 项 + 旧 3 项）：
  1. **回执缺失**（§3.3/AD-23 违例，KPI 第 5 项）：我的页无实施回执（书架 A3 已有），待补填「页面回执：我的页 MyFragment」
  2. **formatDuring 硬编码中文**（§6.1 i18n 违例）：`"${d}天"` / `"小时"` / `"分钟"` / `"秒"` / `"0秒"` 需迁 `strings.xml` 双语（formatDuring 是唯一私有工具函数）
  3. **三态不全**（§7 第 6 步）：仅有加载态（`CircularProgressIndicator` 居中）——应换顶部 LinearProgress 或轻骨架；**无错误态**——stats 查询 `withContext(IO)` 无 `runCatching`，Room 异常会闪崩/永久 loading（§4.1 单 produceState 可保留，但须补 kotlin.runCatching + 错误占位/重试）
  4. **服务开关状态不同步**（§4.2）：`remember { mutableStateOf(WebService.isRun) }` 仅初始值，不观察 `EventBus.WEB_SERVICE`/`AUTO_TASK` 事件——若在 ConfigActivity 子页启停 Web 服务返回，开关不回读（MyPreferenceFragment:111-120 有 observeEventSticky 但 Compose 版未接）
  5. （旧）`MyPreferenceFragment` 死代码与 Compose 重叠（frontend-synthesis 红线 D，可清类）
  6. （旧）退出行 `(context as? Activity)?.finish()` 硬转类型（应经壳回调/`runCatching`）
  7. （旧）工具栏"帮助"菜单仍在 XML 壳（main_my.xml menu_help）
- 设计要点：替换壳内 TitleBar 为 GlassTopAppBar；清死代码；补回执/三态/i18n（四项属 P1 或 P4 收尾队列，见 tasks.md 12.16i）

### A3. BookshelfFragment1（style1 分组 Tab 书架）
- 路径 `ui/main/bookshelf/style1/`｜技术 **Compose**｜骨架 S2｜优先级 **P0 已改造**
- 功能点：① 分组 Tab（`BookGroupTabs` ScrollableTabRow）② 书列表 ③ 下拉刷新 `PullToRefreshBox` ④ 空态/加载态 ⑤ `upGroup()` LiveData ⑥ `flowByGroup`+`sortedByBook` ⑦ `saveTabPosition` 记忆 ⑧ `gotoTop()` 回顶
- ⚠️ 遗留：style1/style2 各写一份 upConnect/loading/booksJob 数据订阅未收敛（Phase4 收敛到 ViewModel）；加载态已用 ShelfGridSkeleton、`UnreadBadge` 已收敛为公共 `BadgeDot`、三态已补全（2026-08-11 11.9 落地）
- 📋 回执：见 tasks.md「页面回执：书架 BookshelfScreen」（2026-08-11，§3.3）——复用 BadgeDot×2/ShelfGridSkeleton/EmptyStatePlaceholder×2，沉淀 EmptyStatePlaceholder，私有组件 0，三态齐全，真机 BadgeDot 渲染+阅读器打开已验，14.8 复核待办
- 🔎 **v2.8 复审（2026-08-11，见 tasks.md 12.16j）4 新违例 + 2 已知**：
  1. **易变 Config 值 `remember{}` 首帧快照**（BookshelfScreen:81-85 bookshelfLayout/showBookname/showUnread/showBookshelfReadProgress/showLastUpdateTime 5 项）——§4.2 违例，改设置在其它页后回书架不刷新（configBookshelf 靠 `postEvent(RECREATE)` 强制重建 Fragment 兜底，证明快照失效）；修复=P1 队列换 `AppConfigFlow`/`collectAsState` 或观察 EVENTBUS
  2. **网格列数 `GridCells.Fixed(spanCount)`**（BookshelfScreen:262）——§1.4「网格列数随宽度自适应」违例；但列数由 `AppConfig.bookshelfLayout`（1-4 用户显式选择）驱动，属用户控制，需登记为 §1.4 例外（与 GeneratedCover 8 色同类豁免）或大屏自适应叠加
  3. **i18n 硬编码**（§6.1 违例）：BookshelfItems.kt:125 GeneratedCover 徽章 `"本地"/"在线"` 直接渲染 UI；BookshelfViewModel 业务 toast 5 处（"添加网址失败"/"添加网址出错"/"导出书籍出错"/"格式不对"/"书籍不能为空"）；BaseBookshelfFragment waitDialog `"添加中..."`×2——存量清零清单登记，随改造迁移
  4. **configBookshelf 对话框为页面私有弹窗**（DialogBookshelfConfigBinding，A5）——§7 第 6 步「无页面私有弹窗布局」违例；但 Phase3 用户红线「12 菜单+configBookshelf 对话框全量保留为 View 壳」冲突，登记为红线保留例外（Compose 化 L2 Dialog 族时合并）
  - 已知遗留（非本轮新增）：style1/2 upConnect 重复订阅（§4.1，Phase4 收敛）、grid `Fixed` 列数 vs §1.4 自适应

### A4. BookshelfFragment2（style2 文件夹书架）
- 路径 `ui/main/bookshelf/style2/`｜技术 **Compose**｜骨架 S2｜优先级 **P0 已改造**
- 功能点：① IdRoot 显示 FolderGroupList 分组列表 ② 选中子分组 `upTitle` 改标题"书架(组名)" ③ 下拉刷新（XML SwipeRefreshLayout）④ `back()` 返回键子分组回根 ⑤ onlyUpdateRead 跟随组
- 🔎 v2.8 复审：与 style1 共用 BookshelfScreen，**无独立实施回执**（§3.3 违例，A3 回执仅覆盖 style1/公共组件）；同一批违例（Config remember 快照/i18n/Fixed 列数）同 style1 修复队列，见 tasks.md 12.16j

### A5. BaseBookshelfFragment（书架抽象基类，View 壳）
- 路径 `ui/main/bookshelf/BaseBookshelfFragment.kt`｜技术 **View**｜骨架 S1 附属｜优先级 P1
- 功能点：① 12 项菜单挂载（远程导入/搜索/更新目录/书架布局/分组管理/本地导入/URL添加/书架管理/缓存导出/书架导出/导入/日志）② 3 个 HandleFileContract ③ WaitDialog ④ `configBookshelf()` 对话框（分组样式/排序/显示书名/未读/进度/更新时间/等待更新数/FastScroller 开关+间距，变更发 EventBus.BOOKSHELF_REFRESH/RECREATE/NOTIFY_MAIN）⑤ `showAddBookByUrlAlert()` ⑥ `importBookshelfAlert()`
- ⚠️ Compose 化时 **12 菜单 + configBookshelf 对话框必须全量保留**（Phase3 已验证保留）
- 🔎 v2.8 复审：configBookshelf（DialogBookshelfConfigBinding）为**页面私有弹窗布局**（§7 第 6 步违例），但受 Phase3 用户红线「保留 View 壳」约束——登记为红线保留例外，Compose 化 L2 Dialog 族时合并进 `AppSelectDialog` 体系；waitDialog `"添加中..."` 硬编码中文入 §6.1 存量清零清单

### A6. BooksFragment（书架旧 View 实现，已无引用）
- 路径 `ui/main/bookshelf/style1/books/BooksFragment.kt`｜技术 **View 遗留**｜骨架 S2｜优先级 N（被 Compose 书架替换，可删）
- 能力：RecyclerView+SwipeRefreshLayout、6 种排序、FastScroller、30s 轮询更新时间——**均已由 Compose 书架覆盖**，确认无外部实例化后清理

### A7. ExploreFragment（发现页）
- 路径 `ui/main/explore/`｜技术 **View**｜骨架 S2｜优先级 P1
- 功能点：① 搜索框实时过滤 ② 分组 6 分支查询 ③ TabLayout 标签模式（isTagMode：按类型5 Tab/按分组动态 Tab）④ 文件夹视图（动态列数）⑤ 文件夹点击临时切列表 ⑥ 菜单：文件夹配置 Dialog + 动态分组子菜单 ⑦ Item 展开 flexbox 探索控件（rotateLoading）⑧ Item 长按 PopupMenu（编辑/置顶/搜索/登录/刷新/删除）⑨ 探索控件 5 种（url/button/text防抖600ms/toggle/select，均支持 JS evalUiJs/evalButtonClick）⑩ compressExplore 收起 ⑪ 返回键子目录回退
- 设计要点：搜索顶栏 → SettingsSearchBar；探索控件动态 UI 保留原逻辑（内核红线）
- 🔎 **v2.8 预审（2026-08-11，explore 深审 8 文件，见 tasks.md 12.16m）**：骨架判定 **S2 列表管理页**。**已符合 7 项（✅1-✅7）**：无硬编码色（grep 0）/数据源全 Room Flow+flowWithLifecycleAndDatabaseChange/文件夹网格自适应/主文案全 @string/顶栏+列表+空态三件套/协程 execute 链/返回键层级合理。**违例 17 项（V1-V17）**：V1 SearchView 非 SettingsSearchBar+搜索词不升 StateFlow（ExploreFragment:94-96,170-184，view_search.xml 17 页共享）；V2 私有配置 Dialog（dialog_source_folder_config.xml 223 行承载 sourceGroupStyle/Mode/sourceLayout/bookSourceSort/sourceMargin）非 ListLayoutMenu；V3 条目私有 PopupMenu（ExploreAdapter:641-664 explore_item.xml 6 项）非 AppMenuSheet；V4 删除私有 alert（:478-485）；V5 TextDialog ERROR（Adapter:195,214）非 AppTextDialog；V6 状态未收敛（ExploreViewModel 26 行零数据流+Fragment 私有态 currentGroup/currentType/isShowingFolder+Adapter 持 exIndex/scrollTo/lastClickTime/sourceKinds 五份运行时状态）；V7 英文 strings.xml 中文值（type_text..type_video 5 key+source_group_mode*+layout_list_compact，被类型 Tab/文件夹/Dialog 消费）；V8 view_search.xml:19 搜索硬编码（共享 17 页继承）；V9 日志中文（发现界面更新数据出错 :380）；V10 无 GroupHeader 折叠渲染（分组只有 Tab/文件夹两种，无徽标无折叠）；V11 无多选批量（fork 已采纳规范，本页未实现，归 P2）；V12 空态裸 TextView 非 EmptyStatePlaceholder（fragment_explore.xml:35-47）；V13 文件夹列数像素除法非 BoxWithConstraints 断点+页面级无骨架屏；V14 触控目标不足（item_find_book.xml:34,43 20dp 图标+Dialog tools:ignore 掩盖）；V15 冗余（SourceFolderAdapter:106-110 rgLayout 可改 sourceLayout 但发现页列表不消费=半无效配置）；V16 无回执；V17 顶栏 TitleBar 非 GlassTopAppBar。**内核红线**：探索控件 JS 双求值链（evalUiJs/evalButtonClick）/InfoMap LruCache(99) 被 WebBook+BookSourceExtensions 跨模块引用/sourceKinds 缓存/SourceLoginJsExtensions 桥四条**逐字平移**；FlexboxLayout→Compose FlowRow 但 FlexChildStyle.layout_justifySelf 语义保留；**ExploreKind.equals 只比 title/type/url/action/default 不含 chars/viewName/style**——§4.3 陷阱适用，Compose 化需 Ui 轻量模型或拆易变参数。**P1 接线前置序**：V8（view_search 中文 hint）→ V1（SettingsSearchBar+StateFlow）→ V17（GlassTopAppBar）→ V2（ListLayoutMenu）→ V3/V4/V5（菜单/Dialog 族）→ V10（GroupHeader）→ V7/V12/V16（i18n/空态/回执门禁）

### A8. RssFragment（订阅页）
- 路径 `ui/main/rss/`｜技术 **View**｜骨架 S2｜优先级 P1
- 功能点：① 搜索过滤 + **提交跳 RssSearchActivity** ② 分组 6 分支查询 ③ Tab 标签模式（网页/图片/视频 3 Tab）④ 文件夹视图 ⑤ 菜单 5 项（文件夹配置/阅读记录 Dialog/订阅收藏/RSS 配置）⑥ 头部规则订阅入口（RuleSubActivity）⑦ Item 单击 openRss 智能分发（singleUrl→ReadRss 或浏览器；否则取 HTML）⑧ Item 长按 PopupMenu（编辑/置顶/登录/删除/禁用）⑨ 返回键子目录回退
- 🔎 **v2.8 预审（2026-08-11，explore 深审 3 kt+SourceFolderAdapter+4 布局+2 菜单+ReadRecordDialog+接线核查，含 fork 基线 4c3935cf5 diff 对比，见 tasks.md 12.16o）**：骨架判定 **S2 列表管理页**（正确）。**已符合 12 项（C1-C12）**：骨架归类正确/用户可见文案全 R.string（:204,230,271-274,279-280,345-352+两菜单全 @string）/Kotlin 硬编码色 0（全走 primaryTextColor/primaryColor/accentColor）/搜索提交跳全局 RssSearchActivity（rss-unified-search 落点 :206-215）/分组筛选 6 分支 DAO+F-01 解耦 searchView（currentGroup 独立状态 :383-408）/文件夹网格列数随屏宽动态（min90dp 卡宽 min2 列 SourceFolderAdapter:140-145）/返回键子目录回退完整（:137-159）/方向跟随系统/ViewModel 动作走 execute 协程链+timeout（RssViewModel:13-106）/列表触控 ≥48dp（item_rss.xml:15）/暗色安全（token @color/secondaryText）/菜单项标题全资源化。**违例 16 项（V1-V16）**：V1 顶栏 TitleBar 非 GlassTopAppBar（fragment_rss.xml:9-16）；V2 搜索用私有 SearchView 非 SettingsSearchBar+query 未升 VM（RssFragment:97-99,200-224+view_search.xml:2-19）；V3 布局切换+排序私有（showFolderConfig:313-338+SourceFolderAdapter:74-133 私有 alert 对话框 7 布局 RadioButton+6 排序+间距 SeekBar）ListLayoutMenu 零接线；**V4 功能性缺陷：rssSort 排序 no-op**（AppConfig:370-374 rssSort: Int，RssSourceDao:62,74,86,100,102,116,127,137 全部 `order by customOrder`——排序设置在本页完全不生效；RssSourceSort enum 死代码:3-5；rssSortAscending 定义后全仓无读写=死配置，与 D1 预审 V5 同款）——P1 优先修复；**V5 功能性缺陷：sourceLayout no-op**（rgLayout 保存 AppConfig.sourceLayout 但 applyListView 恒 GridLayoutManager(context,4) 列表/紧凑/网格选项保存后不生效 :241-245）；V6 分组无 GroupHeader（TabLayout 横滚:258-292+文件夹卡片无数量徽标 SourceFolderAdapter:25 注释自认不显示数量）；V7 状态管理违规（Fragment 12 私有态:77-105+2 个 Flow Job:102-103+Room Flow collect 在 Fragment:357-419，RssViewModel 零状态零 StateFlow 仅 6 动作方法，旋转丢筛选态无 onSaveInstanceState）；V8 三态缺失（fragment_rss.xml:37-49 tv_empty_msg 死控件零引用；:360-361,413-414 仅 AppLog.put 无占位无重试）；V9 弹窗族全私有 3 处（:499-506 del 确认 alert+SourceFolderAdapter:79-133 配置 alert+ReadRecordDialog:59-68 清空确认）；V10 菜单族（RssAdapter:64-79 PopupMenu 5 项+Fragment:162-186 OptionsMenu+动态分组 SubMenu 未下沉）；V11 i18n 硬编码 6 处（:361 订阅界面获取分组数据失败/:414 订阅界面更新数据出错/view_search.xml:19 搜索/strings.xml:1752,1754,1755 type_image 等英文文件中文值/1761-1763 source_group_mode 同款/RssSourceDao:71,102 SQL `like '%未分组%'` 数据层硬编码中文需迁移方案/g type_web/image/video 与 rss_article_type_web 同义双 key §6.1 禁止）；V12 XML 硬编码色 3 处（item_source_folder_grid.xml:54 shadowColor="#80000000"+:58 @android:color/white；:82 md_dark_primary_text 为 token 豁免）；V13 无障碍（view_search.xml:9 SearchView height=30dp<48dp+dialog_source_folder_config.xml 17 处 tools:ignore=TouchTargetSizeCheck）；V14 网格列数固定不随宽度（RssFragment:243 GridLayoutManager(context,4)+fragment_rss.xml:33-34 spanCount=4）；V15 无 §3.3 回执；V16 无视图切换轻过渡（P2 非阻塞）。**fork 差距**：相对 fork 基线已领先 +280 行（统一搜索跳转/文件夹视图 F-P1-8/Tab 标签 D1/类型分组 D2/子目录回退/按 Activity 区分 rssSort）；相对审定 3 fork 缺失——RuleListScaffold 壳+FastScroll（VerticalScrollbar 孤儿零接线）/GroupHeader 折叠+徽标/统计条+空态 CTA/BackHandler 退多选/ListLayoutMenu/左滑 SwipeActionContainer（P7-rss 设计收藏/置顶/删除无任何左滑）。**P1 开工序**：先修 V4/V5 功能性缺陷（否则 ListLayoutMenu 接线后依然不生效）→ BookSourceActivity S2 支干样板冻结后本页照抄（V1-V3/V6-V15）→ V16 入 P2。六公共组件（GlassTopAppBar/SettingsSearchBar/ShelfGridSkeleton/EmptyStatePlaceholder/ListLayoutMenu/SwipeActionContainer）本页全零接线

---

## B. 阅读器核心（16 页面类）

### B1. ReadBookActivity + BaseReadBookActivity（阅读器，最大页面）
- 路径 `ui/book/read/`（1875 + 406 行）｜技术 **View**｜骨架 S4+S5 混合｜优先级 P1（浮层优先，正文不迁移）
- `activity_book_read.xml` 浮层清单：read_view（ReadView 翻页核心）/text_menu_position 选词锚点/cursor_left+cursor_right 选词光标/read_menu（ReadMenu）/search_menu（SearchMenu）/navigation_bar 底部占位
- **view_read_menu.xml 顶栏**：tv_chapter_name（点击开章节URL/长按设浏览器）/tv_chapter_url/tv_custom_btn（书源自定义按钮点击长按 SourceCallBack）/tv_source_action（PopupMenu：登录/章节购买payAction/编辑书源/禁用书源）
- **亮度条**：iv_brightness_auto 跟随 toggle + seek_brightness（VerticalSeekBar 0-255，ContentObserver 高亮环境适配）+ vw_brightness_pos_adjust 位置调整
- **浮动钮**：fabSearch（→SearchContentActivity）/fabAutoPage（自动翻页）/fabReplaceRule（→ReplaceRuleActivity）/fabNightTheme（日夜切换）
- **底栏**：tv_pre/seek_read_page（ThemeSeekBar，page/chapter 可配，章节跳转确认框）/tv_next + 四入口 ll_catalog（→TocActivity）/ll_read_aloud（点击朗读/长按 ReadAloudDialog）/ll_font（→ReadStyleDialog）/ll_setting（→MoreConfigDialog）
- **顶栏菜单 R.menu.book_read**：换书源/章节换源/刷新（当前/本章之后/全部）/离线缓存下载/添加书签/高亮规则管理/模拟阅读 DatePicker/编辑内容/更新目录/启用替换/重新分段/删Ruby与H标签/翻页动画（覆盖滑动仿真滚动无）/日志/txt目录正则/反转内容/字符集/图片样式/WebDav获取上传进度/去重复标题/生效替换
- **配置弹窗类**：ReadStyleDialog（字号/行距/字间距/缩进/字体/边距/Tip样式/文字背景）/MoreConfigDialog（PreferenceScreen：隐藏状态栏导航栏/刘海适配/防息屏/选择/双页/进度条行为/触控阈值）/ReadAloudDialog+Config（TTS）/AutoReadDialog/ClickActionConfigDialog（9宫格）/BgTextConfigDialog/PaddingConfigDialog/PageKeyDialog/TxtTocRuleDialog
- **9宫格点击**（ReadView.onTouchEvent）：0显菜单/1下一页/2上一页/3下章/4上章/5-6朗读段落/7加书签/8编辑内容/9切换替换/10目录/11搜索/12同步进度/13朗读暂停恢复
- **长按600ms选词** → 光标拖拽 → TextActionMenu（复制/分享/浏览器搜索/朗读/书签/替换/全文搜索/词典 + PROCESS_TEXT）
- **翻页**：Cover/Slide/Simulation/Scroll/NoAnim 五种 PageDelegate + 滚动模式；按键（音量/方向/PgUp/PgDn/空格/自定义 prev/next）+ 鼠标滚轮 + MENU + MEDIA_BUTTON
- 返回键链：搜索结果→恢复进度→暂停朗读→停自动翻页→finish；退出"加入书架"确认
- 设计要点：**正文引擎 0 改动**（AD-02）；浮层 Sheet 化（AD-06/FR-6）；阅读设置 Sheet 可拉伸；高亮样式沿用 HighlightStyleDialog
- 📋 回执：见 tasks.md「页面回执：S5 阅读器浮层」（2026-08-14，§3.3 AD-23）——S5 骨架四阶段完成：MenuLayer 菜单层 Compose 化 + activeSheet 单态收敛 + ReaderMenuSheet 阅读设置 Sheet（更多设置保全原对话框）+ Back 链/i18n/无障碍；复用 AppModalBottomSheet/SettingsCard/BookTocBookmarkSheet，私有组件 0，正文 page/ 零改动（git status 零变更）；FR-11 真机交用户回归（2026-08-14 用户自测 3.26.081411）

### B2. TocActivity + ChapterListFragment（目录）
- 路径 `ui/book/toc/`｜技术 **View**｜骨架 S2｜优先级 P1
- 功能点：SearchView 搜索章节/书签；menu_book_toc：txt目录正则/拆分长章节/反转目录/目录UI替换/加载字数/导出书签/导出MD/导出Obsidian/日志；Tab 动态菜单组；ChapterListFragment（顶部 llChapterBaseInfo 定位当前章/置顶/置底；item 点击回传 index/chapterChanged；长按 toast 替换后标题；ivChecked 云朵/✓缓存状态；卷名/字数/VIP锁/缓存文件监听）
- 设计要点：目录改 ReaderBookSheet 三 Tab（目录/书签/高亮，AD-06）
- 🔎 **v2.8 预审（2026-08-11，explore 深审 13 kt+BookTocBookmarkSheet+6 布局+菜单+4 Dialog，见 tasks.md 12.16p）**：骨架判定 **S2 列表管理页（现状）+S5 浮层（蓝图目标）**——短期按 S2 治理（S2 样板确立后枝叶），中期迁入阅读器浮层 ReaderBookSheet 三 Tab（P2-reader R2），双归类并行。**已符合 14 项（C1-C14）**：功能点齐全（目录搜索/反转/替换标题/字数/拆分长章/正则/导出书签/MD/Obsidian/日志：TocActivity:128-174）/双 Tab Room Flow 实时订阅（flowByBook/flowSearch+flowOn(IO)）/协程 execute 链合规/菜单全 @string/Tab 标题 getString/EventBus.SAVE_CONTENT 缓存云精确更新（ChapterListFragment:102-119）/DiffUtil 逐字段比较规避 §4.3/长列表性能（DiffRecyclerAdapter+payload+ConcurrentHashMap 标题缓存）/Kotlin 硬编码色 0（高亮 chip 色来自用户样式=豁免）/返回键层级/frame 文件导出 HandleFileContract/高亮 Tab 复用 fragment_bookmark 布局/全 @color token+派生色/目录功能超越 fork（卷名/字数/VIP锁/缓存态/替换标题）。**违例 14 项（V1-V14）**：V1 顶栏 TitleBar 非 GlassTopAppBar（activity_chapter_list.xml:9-14）；V2 appcompat SearchView 非 SettingsSearchBar+searchKey 可变普通字段未升 StateFlow+menu_search 无 queryHint（TocActivity:74-105+TocViewModel:29+book_toc.xml:7-11）；V3 目录/书签用 TabLayout+ViewPager+FragmentPagerAdapter 与 BookTocBookmarkSheet（孤儿）零接线（:56-62,199-221）——中期随 R2 收敛；V4 状态未收敛（VM 仅 MutableLiveData<Book>+3 回调接口反注册靠手动，Fragment 散落 durChapterIndex/chapterList/mLayoutManager/adapter 私有态无 onSaveInstanceState）；V5 搜索词驱动链非受控（onQueryTextChange 直接调回调扩散 :84-98）；V6 i18n 硬编码 9 处（TocViewModel:97,99,121,123 导出失败/成功+BookmarkFragment:64+HighlightFragment:77+TxtTocRuleActivity:114+TxtTocRuleDialog:119+TxtTocRuleEditDialog:81,88,161,164）；V7 占位符规范（ChapterListFragment:88 ${book.durChapterTitle}(${index+1}/${total}) 拼接非 %1$s 不可翻译）；V8 硬编码色 item_highlight.xml:16 background="#80FFF176" 绕过 token（高亮默认色）；V9 弹窗族全私有（WaitDialog L3/TxtTocRuleDialog 0.9/0.8 全屏/BookmarkDialog/HighlightNoteDialog 全屏/alert+DialogEditTextBinding，L2 Dialog 族 6 组件零接线）；V10 菜单族（book_toc.xml:13-77 OptionsMenu 手写显隐:109-126+条目 PopupMenu 未下沉 AppMenuSheet/AppDropdownMenu）；V11 三态全缺（目录加载无骨架屏/空态裸空白/错误态仅 AppLog，ChapterListFragment:121-137/BookmarkFragment:63-77/HighlightFragment:76-91）；V12 无障碍（fragment_chapter_list.xml:32,45,56 当前章信息栏+置顶/置底按钮 36dp<48dp）；V13 无回执；**V14 高亮 Tab 未接线**（HighlightFragment 已建 108 行但 TabFragmentPageAdapter getCount()==2 :210-212 不含高亮；highlightCallBack 定义 :28,140-142 但搜索分发无高亮分支 :90-98；updateLog:484 声称「目录页新增标注 Tab」与现状代码不符=功能被回退或未完成接线）——P1 高优先止血。**BookTocBookmarkSheet 接线评估**：组件仅 99 行双 Tab 纯 String 列表渲染，能力覆盖 TocActivity 功能面不足 20%（无搜索/当前章高亮/缓存卷/VIP/书签编辑/高亮三 Tab）——**不能直接接线本页否则功能回归**；正确路径=定位为阅读器浮层双 Tab 雏形，R2 增强演进 ReaderBookSheet 三 Tab（HorizontalPager 72% 高+CardTabRow+当前章态数据驱动，from HapeLee），TocActivity P1 先治理为 S2 枝叶页，功能点随后作为 ReaderBookSheet 数据源（Book/BookChapter/Bookmark/BookHighlight Flow）迁移，最终独立 Activity 收敛进阅读器浮层。组件内硬编码中文「目录/书签」（:58,64）接线前必须清。**fork 差距**：fork 相对原版新增（高亮规则系统 F-P1-2/Obsidian 导出/TxtTocRule 独立页/tocUiUseReplace 等 4 增强配置）属正向；蓝图差距（ReaderBookSheet 三 Tab 未建/高亮 Tab 未接线 V14/GlassTopAppBar+SettingsSearchBar+三态+回执零接线/当前章定位带进度条百分比仅文本 36dp）。**P1 开工序**：V14 高亮 Tab 接线（止血 updateLog 与现状不符）→ V1/V2（随 S2 样板冻结）→ V11/V6/V7/V8（三态+i18n+色）→ V4/V5（状态收敛）→ V9/V10/V12（随 Dialog/菜单族归 P2）→ V13（回执）；ReaderBookSheet 收敛 R2 与 S2 治理并行

### B3. BookmarkFragment / B4. HighlightFragment
- 路径 `ui/book/toc/`｜技术 **View**｜骨架 S2｜优先级 P2
- 功能点（书签）：flowByBook/flowSearch 实时列表/自动滚动定位/点击跳转/长按 BookmarkDialog（编辑/删除）；搜索由 TocActivity 驱动
- 功能点（高亮）：bookHighlightDao 流/点击跳章节/长按 HighlightNoteDialog/**当前未挂载（F-P1-2 注释），真实入口在 HighlightRuleActivity**

### B5. AllBookmarkActivity（全部书签）
- 路径 `ui/book/bookmark/`｜技术 **View**｜骨架 S2｜优先级 P3
- 功能点：flowAll+分组头/点击查书跳读（书删则 BookmarkDialog）/长按 BookmarkDialog/导出 MD

### B6. BookInfoActivity（书籍详情，1189行）
- 路径 `ui/book/info/`｜技术 **View（壳层 Compose 桥接）**｜骨架 S4｜优先级 P1
- **状态：S4 支干壳层接线 ✅（2026-08-12，tasks.md 12.23）｜FR-11 真机 ✅（部分功能点）**
- 功能点：封面（点击 ChangeCoverDialog/长按 PhotoDialog）；书名/作者（点击长按→SearchActivity）；**简介四渲染** `<useweb>`WebView池/`<usehtml>`setHtml+GlideImageGetter/`<md>`Markwon/纯文本；图片点击执行书源JS/长按 PhotoDialog；标签点击长按书源回调+搜索；分组 tvChangeGroup→GroupSelectDialog；目录 tvTocView→TocActivity；书架增删；阅读 tvRead（按类型分发）；Web文件下载导入 showWebFileDownloadAlert；菜单：自定义按钮/编辑/分享/刷新/登录/置顶/源变量/书籍变量/复制URL×2/允许更新/清缓存/日志/拆分长章/删除确认/WebDav上传；下拉刷新
- 设计要点：共享折叠封面（P3-page 设计大纲）；多 Tab 信息流
- 🔎 **v2.8 预审（2026-08-11，explore 深审 4 文件+5 XML+5 Dialog，见 tasks.md 12.16m）**：骨架判定 **S4 详情/阅读页**（正确）。**已符合 8 项（C1-C8）**：骨架归类正确/功能点零遗漏（四渲染+换源+分组+目录+书架+阅读分发+WebFile+16 菜单）/Kotlin 层零硬编码色（grep 0 命中）/方向跟随系统+双布局自适应/底部主操作 ≥48dp/协程 execute 链合规/封面背景图 contentDescription 齐备/简介 minHeight 48dp+textIsSelectable。**违例 13 项（V1-V13）**：V1 顶栏 TitleBar（activity_book_info.xml:24-30 themeMode=dark）非 GlassTopAppBar；V2 底部操作栏纯 TextView 50dp 非规范圆角按钮组（:383-405）+换源/分组是小 accent 文本（:218-227/:297-306）非下沉操作栏；V3 无共享折叠封面（:55-88 静态 CardView，Hero 决策 AD-08 默认关未落地）；V4 无多 Tab 信息流/目录预览/相似推荐（目录仅 1 行跳全屏 TocActivity :311-353/:1006-1010）；V5 状态未收敛（VM 两 LiveData+可变公有字段 inBookshelf/hasCustomBtn/bookSource+Activity 直写 VM 字段 :160/:204-206/:502，7 私有态散落）；V6 i18n 硬编码 15 处（上传中...../未配置webDav/下载中.../书源不存在×2/源变量注释/书籍变量注释/Unexpected webFileData/Loading...../未找到书籍/webDav没有配置/下载远程书籍失败/LoadTocError/已下载/清理缓存出错+EditVM 2 处）；V7 layout-land 硬编码色 #50000000（:24 绕过 color token）；V8 6 类弹窗全私有（删除确认自定义 CheckBox/WebFile selector/ChangeBookSourceDialog 全屏/GroupSelectDialog 0.9f/ChangeCoverDialog/VariableDialog/WaitDialog 非 L2 族）；V9 顶栏 OptionsMenu 16 项+手写显隐状态机未下沉 AppDropdownMenu（onMenuOpened :268-285）；V10 三态不齐（加载=文字「章节:加载中」/失败仅 toast 无占位/无 EmptyStatePlaceholder）；V11 无障碍错位（ic_book_last/ic_groups/ic_folder_open 复用 @string/read_dur_progress=Origin 语义错误+换源/分组/目录触控约 20dp<<48dp）；V12 加书架/删除无微交互动画（§6.2 MoRealm 心跳未落地，upTvBookshelf 纯文本切换 :735-742/:783-797）；V13 无回执。**fork 差距**：MoRealm 收藏心跳 spring(0.45,800)/加架过渡/HapeLee 封面 Hero 共享转场/ReaderBookSheet 三 Tab/磨砂顶栏+双圆角按钮全缺失（设计已入文档未落地）。**S4 样板首接线**：遵循 §9.2 S4 范式（共享折叠封面+底部操作栏+AppModalBottomSheet 换源/分组+GlassTopAppBar+三态+Dialog/菜单族），一次走通 13 项后冻结为枝叶范本（RssArticleInfo/About/ReadRecord P2/P3 复用）。**✅ 已修（12.23，tasks.md 12.23）**：V1 顶栏 GlassTopAppBar（ComposeView 桥接）；V2 底部 Compose 圆角按钮组（OutlinedButton 加/删书架+Button 阅读，12dp 圆角 48dp 高）；V6 i18n 18 处→16 key 双语；V7 transparent50 token；V9 16 项菜单全下沉 AppDropdownMenu（MenuAction.checked 勾选态）；V11 AccentBgTextView 48dp+；V13 回执。**⬜ 后续**：V3 折叠封面（AD-08 默认关）、V4 多 Tab、V5 状态收敛、V8 业务弹窗（L2 族待枝叶接线）、V10 三态、V12 动画。

### B7. BookInfoEditActivity（书籍信息编辑）
- 路径 `ui/book/info/edit/`｜技术 **View+Compose 壳**（BookInfoEditScreen 全 Compose 内容区+ComposeView 桥接，2026-08-15 12.50 实施；换封面三途径/保存逻辑保留 Activity，View 状态上抛）｜骨架 S3｜优先级 P3
- 功能点：改书名/作者/类型（文本/音频/图片/视频）/封面URL/简介；换封面三途径（ChangeCoverDialog/本地 selectCover/刷新 tvRefreshCover）；保存 BookHelp.updateCacheFolder

### B8. BookshelfManageActivity（书架管理，多选）
- 路径 `ui/book/manage/`（430行）｜技术 **View**｜骨架 S2｜优先级 P2
- 功能点：进入即滑选多选 + ItemTouchCallback 拖拽（仅自定义排序）；SearchView；4 排序；SelectActionBar"移动到分组"；选择菜单（删除带"删除原文件"CheckBox/启用停用更新/加移分组/批量换源 SourcePickerDialog+WaitDialog/清缓存/区间选）；菜单（分组管理/详情开关/导出所用书源/分组切换）；item 点击→BookInfoActivity
- ⚠️ 与 Compose 书架排序一致性需回归

### B9. ImportBookActivity / BaseImportBookActivity / RemoteBookActivity（导入）
- 路径 `ui/book/import/`｜技术 **View**｜骨架 S2｜优先级 P3
- Base：首次 setBookStorage 强制选 SAF 目录；压缩包点击（单文件直导/多文件 selector/重导入确认）；startReadBook
- 本地：目录导航（nextDoc/tvGoBack/back）；菜单（选择文件夹/扫描子文件夹/导入文件名JS/排序）；"加入书架"/删除；文件点击 startRead
- 远程 WebDav：目录浏览/服务器配置 ServersDialog/日志/帮助/排序；"加入书架"；startRead 未下载→showRemoteBookDownloadAlert；addToBookShelfAgain

### B10. CacheActivity（缓存管理，665行）
- 路径 `ui/book/cache/`｜技术 **View**｜骨架 S2｜优先级 P2
- 功能点：按分组加载（flowByGroup+4排序）；菜单（下载当前章起/全部/停止/导出全部/启用替换/自定义导出开关/不带章节名/导出WebDav/导出图片/并行导出/导出文件夹/导出文件名JS/导出类型 txt|epub/导出字符集/缓存并发率 Dialog/日志/缓存分项统计 buildStorageBreakdown 逐项删除）；自定义导出 Dialog（全部或章节范围+验证/每卷章数/epub文件名JS实时解析）；ExportBookService 进度；事件 UP_DOWNLOAD/UP_DOWNLOAD_STATE/SAVE_CONTENT；item 长按下载菜单

### B11. SearchActivity + SearchContentActivity（搜索/全文搜索）
- 路径 `ui/book/search/` + `ui/book/searchContent/`｜技术 **View**｜骨架 S2｜优先级 P1
- 搜索页：SearchView 提交→viewModel.search；结果 SearchAdapter 滚动自动加载；书架内模糊搜索 Flexbox；历史关键字 Flexbox+清空+删除+回填；fbStartStop；输入帮助；菜单（精准搜索/搜索范围 Dialog/书源管理/日志/动态分组）；空结果 alert；单条→BookInfoActivity
- 全文搜索页：SearchView→逐章搜本地/已缓存（IO协程+ensureActive+fbStop+进度）；结果列表（章节名/行号/命中/缓存标记）；点击→postEvent(SEARCH_RESULT)+IntentData 回传阅读器定位；菜单（启用替换/正则）；ivSearchContentTop/Bottom
- 🔎 **v2.8 预审（2026-08-11，explore 深审 18 kt+12 布局+5 菜单+2 实体，含 SearchContent/RssSearch/RssArticleInfo 三关联页，见 tasks.md 12.16p）**：骨架判定 **S2 列表管理页**（B11 一致；**归类疑点：D5 将 RssArticleInfoActivity 混归 S2，源码实为仿 BookInfoActivity 的 S4 详情页**——ArcView+CardView 封面/多源列表/底部操作栏 RssArticleInfoActivity:39-45 自述仿书源，P1 开工前需裁决）。**已符合 14 项（C1-C14）**：三搜索包 Kotlin 硬编码色 0（布局全 @color token）/方向跟随系统/暗色安全（applyThemeColors 修复暗色白块 :118-136）/DiffUtil payload 规避 §4.3（SearchAdapter:23-52 areContentsTheSame 恒 false 强制刷新绕开 SearchBook equals 只比主键/RssSearchAdapter:41-82 同款）/日志规范 AppLog.put/协程 execute 链/菜单项全资源化/搜索历史类型隔离（type=0 书源:132-149/type=1 订阅源 RssSearchViewModel:147-164）/搜索防抖（ConflateLiveData(1000)+onQueryTextChange 触发 stop）/搜索范围持久化（SearchScope:148-155 save→AppConfig.searchScope/searchGroup）/空结果引导闭环（:438-459 alert 引导关精准搜索/切分组）/结果缓存安全（SearchBookStoragePolicy 512KB 行预算防 CursorWindow 崩溃）/触控 ≥48dp（110dp 封面撑行高）/订阅源搜索为 fork 正向资产。**违例 21 项（V1-V21）**：V1 三页顶栏全私有 TitleBar 非 GlassTopAppBar（activity_book_search.xml:9-16/activity_rss_search.xml:9-16/activity_search_content.xml:8-14）；V2 用 androidx SearchView 私有子类（SearchView.kt 110 行）搜索词不升 VM（view_search.xml:2-19 17 页共享+SearchActivity:86-88,186-218）SettingsSearchBar 孤儿零接线；V3 搜索历史 FlexboxLayoutManager 原生容器非 Compose FlowRow（SearchActivity:224,227/RssSearchActivity:231）；V4 状态未收敛（Activity 6 私有态:89-94+2 Flow Job:91-92，VM 5 LiveData+可变公有 searchKey/hasMore:26-33，Room Flow collect 在 Activity:311/381/394）；V5 SearchScope stateLiveData 非 StateFlow（SearchScope.kt:32）；**V6 全文搜索配置存 companion object 静态可变**（SearchContentViewModel:17-27 6 公有可变字段+Activity 直写 companion:87-101 进程内全局共享，三搜索页均无 onSaveInstanceState/rememberSaveable 旋转丢全丢）；V7 三态全缺（仅 2dp 线性条 RefreshProgressBar activity_book_search.xml:18-22/空结果 alert 弹窗非占位:440/错误仅 toast:58 无重试按钮）；V8 4 处私有弹窗（SearchScopeDialog 自绘 RadioGroup+FastScrollRecyclerView dialog_search_scope.xml 114 行/alertClearHistory:524-532/空结果 alert/ChangeRssArticleSourceDialog）非 L2 族；V9 OptionsMenu+手写动态分组状态机（SearchActivity:110-156 onMenuOpened removeGroup+动态 add+setGroupCheckable/RssSearchActivity:109-164 类型+分组双动态菜单/menu.transaction{} 每开必重建）非 AppDropdownMenu；V10 用户可见硬编码中文 7 处（SearchActivity:440,444,452 搜索结果为空/分组空结果/activity_book_search.xml:16 标题搜索/activity_rss_search.xml:16 订阅源搜索）；V11 日志硬编码中文 6 处（AppLog）；V12 view_search.xml:19 defaultQueryHint="搜索" 硬编码共享 17 页接线页全部继承（M1 前置）；V13 公共组件 SettingsSearchBar.kt:53 "搜索设置" 硬编码中文（接线即继承 M1 前置）；V14 英文 strings.xml 中文值 strings.xml:1447 search_result="搜索结果:"；V15 占位符规范（SearchContentActivity:160-171,193-241 @SuppressLint(SetTextI18n) 拼接非 %1$s）；V16 私有 BadgeView 复制 BadgeDot 能力（item_search.xml:36-43+item_rss_search.xml:43-50）+FAB 停止图标手写显隐；V17 无障碍（item_fillet_text.xml:6-18 chip 高约 27dp<48dp padding4dp+14sp/activity_search_content.xml:29 tools:ignore=SpeakableTextPresentCheck/item_search.xml:22 UnusedAttribute 掩盖）；V18 无 GroupHeader/分组 Chips/徽标（分组筛选仅菜单动态组）；V19 无多选批量（搜索场景可论证低优先级归 P2）；V20 三页未包 LegadoTheme（M3 34 槽位未接入）；V21 三搜索页+详情页均无回执。**fork 差距**：功能面完整超 fork（流式聚合/书架模糊搜索/历史双类型隔离/精准搜索/分页/搜索范围多选/rss 统一搜索为 fork 独有）；缺 MoRealm SearchResultCard 加架动画+字数/状态/收藏心/HapeLee RuleListScaffold 壳/MoRealm GroupModeChips+统计条。**P1 开工序**（对齐 C1 样板）：M1（V12/V13 共享布局+公共组件 i18n 清零）→ M2（GlassTopAppBar+SettingsSearchBar+Dialog 族+AppDropdownMenu+EmptyStatePlaceholder 接线 V1/V2/V7/V8/V9/V18/V20）→ M3（StateFlow 状态收敛 V4/V5/V6）→ M4（i18n/无障碍/BadgeDot/回执 V10-V17/V21）

### B12. ReadMangaActivity（漫画，862行）
- 路径 `ui/book/manga/`｜技术 **View**｜骨架 S5｜优先级 P2
- 功能点：横/竖翻页（MangaLayoutManager+PagerSnapHelper）；自动翻页/自动滚动（速度 NumberPicker）；Glide 预加载（mangaPreDownloadNum）；加载层/重试；信息栏 MangaFooterConfig（章节/页码/章节/进度%可配置）；LoadMoreView footer；漫画菜单（亮度/页码进度 fastBinarySearch/自定义按钮）；菜单：换源/目录/刷新/预下载数量/禁用缩放/禁用点击滚动/横屏切换/颜色滤镜/电子纸/灰度/隐藏标题/底部信息栏配置/禁用页吸附/禁用页动画/自动翻页速度
- 手势：onTouchMiddle 开菜单/翻页、双指缩放、音量键、滚动驱动进度跨章

### B13. AudioPlayActivity（音频播放器）
- 路径 `ui/book/audio/`（416行）｜技术 **View**（+LyricViewX 第三方）｜骨架 S5｜优先级 P2
- 功能点：播放/暂停 FAB（长按停止）；上一章/下一章；播放模式循环；进度条+缓冲+时间；倍速 SliderPopup；定时停止 SliderPopup；歌词 LyricViewX（章节变量 lyric/durLyric，点击跳转）；封面+模糊背景；章节→TocActivity；菜单：自定义按钮/换源/登录/保持唤醒/复制音频URL/编辑源/跳过片头片尾/日志；事件 AUDIO_STATE/SUB_TITLE/SIZE/PROGRESS/BUFFER/SPEED/DS/MEDIA_BUTTON；退出未入书架询问

### B14. ExploreShowActivity（发现页分页）
- 路径 `ui/book/explore/`｜技术 **View**｜骨架 S2｜优先级 P3
- 功能点：滚动到底加载下一页/顶部上翻上一页（LoadMoreView 错误重试）；跳页 NumberPicker（1-999，跳页 isClearAll）；exploreName 标题；点击→BookInfoActivity（判入架）

### B15. StorageManageActivity（书库存储管理）
- 路径 `ui/book/storage/`｜技术 **View**｜骨架 S2｜优先级 P3
- 功能点：分项存储统计（名称+大小+清除）；点击 alert 详情；清除确认；菜单（刷新/清空全部逐项删除）；视频播放中删除保护

### B16. TxtTocRuleActivity（txt 目录规则）
- 路径 `ui/book/toc/rule/`（273行）｜技术 **View**｜骨架 S2｜优先级 P3
- 功能点：规则列表+滑选多选+拖拽排序；SelectActionBar 删除；选择菜单（启用停用/导出JSON）；菜单（添加 TxtTocRuleEditDialog/导入本地/在线导入/二维码导入/导入默认/帮助）；item 点击编辑/长按删除；置顶置底

---

## C. 书源 / 规则 / 工具（20 页面类）

### C1. BookSourceActivity（书源管理列表）
- 路径 `ui/book/source/manage/`｜技术 **View+Compose 壳**（BookSourceScreen 1006 行/BookSourceItems 430 行 Compose 化，ComposeView 桥接双轨，2026-08-11 v2.11 实施；View 顶栏/批量栏保留过渡）｜骨架 S2｜优先级 **P1（frontend-synthesis 红线 C 明确优先）**
- 功能点：① 三视图（列表/紧凑/网格 2-6）+ 文件夹视图（SourceFolderAdapter 按类型/分组）② 搜索+快捷筛选词（enabled/disabled/need_login/no_group/enabled_explore/disabled_explore）③ 类型/分组子目录（currentType/currentGroup/inSubDirectory）④ 排序（6 选项+升降序）⑤ 域名分组 groupSourcesByDomain ⑥ 滑选多选+批量（启用/停用/探索/置顶/置底/加移组/导出/分享/检查源）⑦ 检查源 CheckSource.start+进度 Snackbar+300ms 刷新 ⑧ 拖拽排序 ⑨ 菜单（添加/二维码/本地/在线 ACache/分组管理/帮助/回收站）⑩ 返回键层级回退
- 设计要点：SwipeActionContainer 左滑操作（P5-page）；角标改小圆点信息不丢；**布局切换+排序统一 `ListLayoutMenu`**（S2 支干样板页，见 ui-standards §9.2）
- 🔎 **v2.8 预审（2026-08-11，explore 深审 7 文件+2 XML，见 tasks.md 12.16l）**：骨架判定 **S2 列表管理页**（规范 §2 S2 样板页指定本页）。**已符合 10 项**：SelectActionBar 批量栏（唯一接线公共组件）/DragSelectTouchHelper 滑选/DiffUtil 规避 §4.3 去重陷阱/主题 token 主配色/返回键层级/方向跟随系统/文件夹网格宽度自适应/检查源进度反馈/三视图超越 fork 单列表。**违例 14 项（V1-V14）**：V1 顶栏私有 TitleBar 非 GlassTopAppBar；V2 SearchView 非 SettingsSearchBar+搜索词不升 VM；V3 ListLayoutMenu 零接线+三套排序逻辑并存（顶栏菜单 7 维 book_source.xml:18-67 / 配置对话框 6 维 dialog_source_folder_config / 旧 BookSourceSort enum 6 维，menu 项重置 bookSourceSort=0 后走 enum，交互非首行升降序+点同维翻转）；V4 文件夹子目录替代 GroupHeader 折叠渲染+domain 头不可折叠无徽标；V5 VM 零数据流（14 私有状态+4 adapter 散落 Activity，Room Flow collect 在 Activity）；V6 多选集普通 set 不持久化+onBackPressed 不优先退多选；V7 i18n 硬编码 8 处（L545 日志/L864-866 失效筛选+toast/L728 search word hint/L821 url hint/L259 校验失败/L45 成功|失败正则/view_search.xml:19 搜索）+strings.xml:1761-1763 英文文件存中文值；V8 硬编码色 3 处（Adapter:237 GREEN/243 RED/Grid:66 argb 蓝）；V9 8 类弹窗全私有 alert 布局+GroupManageDialog 非 L2 族；V10 条目私有 PopupMenu+顶栏 OptionsMenu 未下沉；V11 三态缺失（无骨架屏/空态/错误态，裸 Snackbar）；V12 view_search.xml:19 defaultQueryHint 硬编码；V13 网格固定 2-6 非 BoxWithConstraints 断点；V14 无 §3.3 回执（tasks 12.19 未勾选）。**fork 差距**：GroupHeader 折叠/分组 Chips/统计条/空态 CTA/卡片 SourceItem 选中描边+评分 N4+登录 AssistChip/BackHandler 退多选/导入剪贴板嗅探均缺失。**P1 开工依赖序**：ListLayoutMenu 接线（V3）→ GlassTopAppBar+SettingsSearchBar（V1/V2）→ Dialog/菜单族建成并收敛（V9/V10）→ GroupHeader 建成（V4）→ 状态收敛 VM（V5）→ i18n/色/三态/多选工程（V6-V8/V11）→ 回执（V14）
- ✅ **v2.11 实施审查增量（2026-08-11，另一 AI 窗口 ComposeView 桥接双轨实施，见 tasks.md 12.16q）**：已符合：GlassTopAppBar/ListLayoutMenu/SettingsSearchBar/EmptyStatePlaceholder/SwipeActionContainer 组件接线（showTopBar=false 过渡期 ListLayoutMenu 隐于 View 顶栏，可接受）；BookSourcePart.equals 仅比主键（data class:54）+LazyColumn key={bookSourceUrl} 规避 §4.3；三视图断点 400/600/800dp；左滑复用 SwipeActionContainer（编辑/调试/复制URL）；i18n 快捷筛选词已资源化；检查源状态实时回传。**新违例 5 项（待修）**：① 多选批量被架空（isSelecting=false 写死 BookSourceActivity:208+onItemLongClick 改弹 PopupMenu :259+recyclerView gone 但 DragSelectTouchHelper/ItemTouchHelper/SelectActionBar 挂死列表→滑选多选+批量全失效）；② 硬编码色 2 处未登记豁免（BookSourceItems.kt:294-303 palette 8 色+ :363-368 SourceTypeBadge 4 色）；③ i18n 硬编码中文「源」兜底（:335）；④ 空态文案语义错位（BookSourceScreen.kt:225 用 bookshelf_empty 书架文案，应书源专用）；⑤ 搜索词未升 StateFlow 双轨。修复路径：composeIsSelecting/selectedIds 升 Activity→SelectActionBarCompose 接线+长按进多选+选中高亮；硬编码色走 ThemeSpec/登记豁免；新增 book_source_empty_title。
- ✅ **v2.11 复审增量 R1（2026-08-12，见 tasks.md 12.16r）**：另一 AI 修复 R1 多选批量——Activity 升 composeIsSelecting/composeSelectedUrls(:137)+composeSelection 计算属性；onItemClick 多选时 toggleSelect(:269)、onItemLongClick=enterSelect(:271)；onSelectAll/onRevertSelection/onDeleteSelection/onBatchAction 全接线(:277-284)；SelectActionBarCompose 完整实现（BookSourceBatchAction enum 12 项+批量菜单 SelectActionBarCompose:917-1005）；View selectActionBar visibility=GONE(:937)；onBackPressed 双分支(:870-892)；checkComposeSelectedInterval/exportSelection/shareSelection 齐全；BookSourceScreen isChecked=selectedUrls.contains 选中高亮接线(:321/342/367/576/587)。**R1 遗留**：DragSelectTouchHelper 滑选死接线未清理(:567-572 attach 到 gone recyclerView)+无滑选等效/降级声明。R2-R5 未动。

### C2. BookSourceEditActivity（书源编辑，核心编辑器）
- 路径 `ui/book/source/edit/`｜技术 **View+Compose 壳**（composeTopBar/composeTabBar/composeQuickToolbar/composeFields/composeBottomBar 5 处 Compose 接线，2026-08-16 12.19 核验；View 内核字段区保留）｜骨架 S3｜优先级 P1
- 功能点：**6 Tab**（基本/搜索/发现/详情/目录/正文）字段总数 13+11+10+11+10+11；**顶部快捷工具条**（类型 Spinner 默认/音频/图片/文件/视频 + 5 个 ThemeCheckBox）；**规则自动补全** RuleComplete.autoComplete（type 1/2/3）+ CodeView addLegadoPattern/addJsonPattern/addJsPattern；**正文 Tab replaceRegex 净化替换**；**KeyboardToolPop**（URL参数/教程/选文件/sendText/undo/redo+光标滚动 smoothScrollBy）；菜单（全屏编辑→CodeEditActivity 带回光标/保存/调试/清Cookie/复制粘贴源/扫码/分享文本+二维码/日志/帮助/登录/源变量）；保存校验（URL/名称非空+URL 变更书架迁移弹窗）；未保存拦截 finish；全屏编辑光标恢复 360ms
- 设计要点：**净化替换二级页**（红线 C 要求净化独立页功能相等）；6 Tab → 保留但 Sheet 化子面板
- 🔎 **v2.8 预审（2026-08-11，explore 深审 3 kt+3 布局+菜单+关联内核，见 tasks.md 12.16n）**：骨架判定 **S3 表单/编辑器页**（正确，且是 ui-standards §9.2 指定的 S3 支干样板页；命中 S3 共性：KeyboardToolPop/全屏编辑跳 CodeEditActivity/未保存拦截 finish）。**已符合 7 项（C1-C7）**：功能点一一对应（6 Tab 13+11+10+11+10+11 字段/快捷工具条/自动补全/KeyboardToolPop/全屏编辑 360ms 光标恢复/保存校验+URL 变更书架迁移/未保存拦截）；未保存全字段对比 `BookSource.equal` 26 字段（非 equals 只比主键，天然规避 §4.3）；保存校验抛 NoStackTraceException；全包 grep `Color(0x/hexColor/#RRGGBB` 0 命中全走主题 token；无 requestedOrientation+insets 双轨；RuleComplete.autoComplete 调用链完整+CodeView 三 pattern 每项注册；段评 Tab 已裁剪且布局 gone 一致。**违例 13 项（V1-V13）**：V1 顶栏私有 TitleBar 非 GlassTopAppBar（xml:9-13）；V2 菜单 15 项全走 OptionsMenu+onMenuOpened 手写显隐未下沉 AppDropdownMenu（source_edit.xml:1-86+Activity:118-127/162-205）；V3 **非 ViewPager**——TabLayout+单 RecyclerView onTabSelected 整体换数组（Activity:247-249/280-292），Compose 选型 TabRow(6)+LazyColumn vs HorizontalPager 需开工前裁决；V4 状态散落（6 个 EditEntity 私有数组 Activity:75-80+TextWatcher 直写 editEntity.value Adapter:89-91+VM 无 Flow/StateFlow bookSource 仅内存字段）；V5 无 rememberSaveable/onSaveInstanceState——旋转/进程死亡丢未保存编辑（Activity:103-109）；V6 6 类弹窗全私有（退出确认 alert/迁移确认/分组 selector/UrlOptionDialog/VariableDialog/KeyboardAssistsConfig）；V7 i18n 硬编码 12 处（L647-663 五个 SelectItem/L740,755 日志/L779 源变量注释/VM:91,138 剪贴板为空|格式不对/L327 "jsLib" hint 字面量）；V8 资源层英文文件存中文值 3 key（strings.xml:1124 variable_comment/:1469 is_event_listener/:1472 custom_button，values-zh 缺）；V9 无障碍（item_source_edit.xml:14 tools:ignore=TouchTargetSizeCheck+TabLayout SpeakableTextPresentCheck+KeyboardToolPop 图标按钮无 contentDescription）；V10 顶部快捷工具条两行 HorizontalScrollView 未分组拥挤（xml:15-107）+cb_is_enable_review 死字段；V11 净化无独立二级页（replaceRegex 仅正文 Tab 内联字段，功能存在度待产品确认）；V12 **文档冲突**：pages/P5-booksource.md:40「编辑页暂不 Compose 化」vs ui-standards §9.2 指定本页为 S3 样板——开工前裁决（倾向 §9.2 权威）；V13 无 §3.3 回执。**内核红线**：RuleComplete.kt 零 UI 依赖纯函数（type 1/2/3 映射表 Activity:464-601 逐行原样搬迁+autoComplete 作为 VM 持久态）；CodeView addLegadoPattern 等 6 Pattern（CodeViewExtensions.kt:12-31）Compose 用 **AndroidView 桥接原样实例**+每 CodeView 只注册一次+TextWatcher 回写桥接受控输入；KeyboardToolPop（PopupWindow，5+ 页复用）原样保留，仅复刻 insets 接线否则键盘弹出工具条错位。**fork 差距**：fork 均无书源编辑页（S3）Compose 样板，仅管理页外推——MoRealm 校验 N/4 展开 error 行/导入剪贴板嗅探可借鉴（P2）；登录态可视化 AssistChip（P2）。**P1 开工建议序**：开工前裁决（V12/V3/V11）→ 里程碑1 骨架壳（V1 GlassTopAppBar→V2 AppDropdownMenu→V10 工具条收敛 SettingsCard 分组+删死字段）→ 里程碑2 状态收敛（V4/V5 EditState+StateFlow+rememberSaveable+getSource() 规则补全映射移入 VM）→ 里程碑3 弹窗族（V6）→ 里程碑4 i18n/无障碍（V7-V9）→ 回执（V13）
- 路径 `ui/book/source/debug/`｜技术 **View**｜骨架 S3｜优先级 P2
- 功能点：调试搜索+快捷前缀（++目录/--正文/text_my/xt/fx/info）；发现调试 initExploreKinds（标题::URL 长按 selector 切分类）；流式输出 observe{state,msg}；菜单（扫码/查看搜索/书籍/目录/正文 HTML 源码 TextDialog/刷新发现/帮助）；帮助面板焦点显隐

### C4. ReplaceRuleActivity + ReplaceEditActivity（替换净化）
- 路径 `ui/replace/`｜技术 **Compose 顶栏/菜单/底部（ReplaceRuleTopBar + ReplaceEdit 顶栏菜单底部栏 Compose，2026-08-14，tasks.md 12.46）**｜骨架 S2+S3｜优先级 P2
- 列表页：搜索（enabled/disabled/no_group/group:xxx）；菜单（添加/分组管理/启用停用筛选/删除选中/在线/本地/扫码导入/帮助）；多选（启用停用/置顶置底/导出JSON）；onDestroy 全局刷新 ContentProcessor.upReplaceRules；拖拽排序滑选
- 编辑页：字段 name/group/**pattern**/cb_use_regex/replacement/scope_title/scope_content/scope/excludeScope/timeout(3000)；菜单（全屏编辑/保存/复制粘贴）；KeyboardToolPop+正则帮助
- ✅ **v2 实施（2026-08-14，tasks.md 12.46）**：列表页（ReplaceRuleActivity）顶栏/搜索/菜单 Compose 化（ReplaceRuleTopBar + SettingsSearchBar + 快捷筛选），列表内核（RecyclerView 拖拽排序/滑选多选/SelectActionBar 批量）View 保留（AD-20 内核桥接）；编辑页（ReplaceEditActivity）顶栏 GlassTopAppBar + 菜单下沉 AppDropdownMenu（全屏编辑/保存/复制规则/粘贴规则）+ 底部保存/取消栏（12dp 圆角 48dp），字段区 View 内核保留（EditText 行内编辑 + KeyboardToolPop + 正则帮助）；VM 数据逻辑零改动，全量功能保留（红线合规）；FR-11 真机验证归 V-8（待统一验证）

### C5. HighlightRuleActivity（高亮规则）
- 路径 `ui/highlight/`｜技术 **Compose（HighlightRuleScreen 全 Compose，2026-08-14，tasks.md 12.47）**｜骨架 S2｜优先级 P2
- 功能点：列表+拖拽排序；**数据存 SharedPreferences**（HighlightRuleStore 非 Room）；菜单（添加/分组管理/预设 HighlightPresetRuleDialog/恢复默认 MERGE|OVERWRITE 双确认/导入剪贴板JSON去重/导出）；item 编辑删除置顶置底开关；onDestroy 同步 ReadBook.upHighlightRules
- ✅ **v2 实施（2026-08-14，tasks.md 12.47）**：Compose 混合架构（activity_highlight_rule.xml 单 ComposeView + HighlightRuleScreen.kt 全 UI），复用公共组件 GlassTopAppBar/SettingsSearchBar/EmptyStatePlaceholder/AppMenuSheet，新增搜索过滤（按规则名即时筛选）；VM 数据逻辑零改动，Dialog 族（编辑/分组/预设/恢复/导入/导出）全量保留，无功能删减（红线合规）；FR-11 真机验证归 V-8（待统一验证）

### C6. DictRuleActivity（词典规则）
- 路径 `ui/dict/rule/`｜技术 **View**｜骨架 S2+S3｜优先级 P3
- 功能点：列表+滑选+拖拽；菜单（添加/本地在线扫码导入/**导入默认**/帮助）；多选（启用停用/导出）；编辑全屏 Dialog 三字段 name/urlRule/showRule（带规则补全）；全屏编辑；dismiss 未保存拦截

### C7. CodeEditActivity（代码编辑器，sora 内核）
- 路径 `ui/code/`｜技术 **View**（外壳）+ **sora CodeEditor 第三方**｜骨架 S3｜优先级 **N（sora 内核不迁移，壳可换）**
- 功能点：语法高亮 TextMateColorScheme2+主题；字号/自动补全/自动换行/非打印字符；搜索替换 EditorSearcher（正则/普通+RegexBackrefGrammar+搜索结果 n/total）；格式化 formatCode；保存回传 text+cursorPosition；光标恢复 360ms；KeyboardToolPop undo/redo；只读模式
- ⚠️ sora 为第三方 View 控件，**保留原样**（换肤仅调主题色）

### C8. WebViewActivity（网页浏览）
- 路径 `ui/browser/`｜技术 **View**（WebViewPool 池化）｜骨架 S4｜优先级 N（WebView 池不迁移，壳可换）
- 功能点：loadUrl/loadDataWithBaseURL+JS 接口（WebJsExtensions nameJava/WebCacheManager nameCache/lockOrientation/onCloseRequested）；网页全屏 customWebView+按钮全屏；进度；长按图片保存/选目录；下载监听 Download.start；Cookie setCookie；scheme 拦截（legado/yuedu→OnLineImport）；SSL proceed；console 日志；**Cloudflare 挑战检测 `window._cf_chl_opt`**；**源验证模式 saveVerificationResult**；菜单（刷新/浏览器打开/复制URL/完成/全屏/网页日志/禁用删除源）；返回键三级回退

### C9. FileManageActivity + HandleFileActivity（文件管理/选择）
- 路径 `ui/file/`｜技术 **View**｜骨架 S2+S6｜优先级 P3
- FileManage：路径导航条 PathAdapter（root+逐级跳）；文件列表（上级/文件夹/文件）；搜索过滤；长按删除；返回键回上级
- HandleFile：mode 分发（DIR_SYS/DIR/FILE/EXPORT/IMAGE）；系统目录选择器/应用内 FilePickerDialog/**手动输入目录**（校验 isExternalStorage）/系统文件选择器/图片选择/**手动输入图片链接**；EXPORT 上传 URL 或存本地；统一 Intent 回传；存储权限

### C10. DownloadManageActivity（下载管理）
- 路径 `ui/download/`｜技术 **View**｜骨架 S2｜优先级 P3
- 功能点：**5 Tab**（全部/运行中/暂停/完成/失败）；**500ms 轮询** DownloadState.queryAllTaskStatus；过滤+startTime 倒序；任务点击状态菜单（删除/重试/打开+复制路径+删除）；清除完成失败任务

### C11. UrlRecordActivity（URL 记录）
- 路径 `ui/urlrecord/`｜技术 **View**｜骨架 S2｜优先级 P3
- 功能点：搜索；**四维过滤**（domain/sourceName/method/status+清除）；菜单（开关记录/过滤/清除7天/30天/全部）；item 着色（method GET蓝/POST紫/status 2xx绿/4xx橙/错误红）；点击详情复制URL

### C12. RecycleBinActivity（源回收站）
- 路径 `ui/source/recycle/`｜技术 **View**｜骨架 S2｜优先级 P3
- 功能点：sourceRecycleBinDao.flowAll；SelectActionBar 主按钮**恢复**；恢复冲突检测 hasConflict 覆盖确认；菜单（清空回收站/帮助）；选择模式删除选中；item 恢复/删除

### C13. SourceLoginActivity（登录）
- 路径 `ui/login/`｜技术 **View**｜骨架 S6｜优先级 P2
- 功能点：loginUi 空→WebViewLoginFragment（WebViewPool+登录Cookie）；非空→SourceLoginDialog；**loginUi 规则引擎**：JSON 数组或 @js:/<js> 求值（evalUiJs→RowUi 列表）；**RowUi.Type 渲染**（text/password/select/button 点击长按>666ms/toggle）；viewName（null→name/'xxx'引号/JS求值）；action（绝对URL openUrl/JS handleButtonClick 注入 java/result/book/chapter/isLongClick）；输入防抖 600ms；style.layout_justifySelf（center/flex_start/flex_end）；菜单（确定 login()/查看删除 loginHeader/日志）；onDismiss 自动保存 loginInfo；upUiData/reUiView 回调更新

### C14. QrCodeActivity + QrCodeFragment（扫码）
- 路径 `ui/qrcode/`｜技术 **View**（camera-scan+zxing）｜骨架 S6｜优先级 N
- 功能点：相机扫码（仅二维码 QR_CODE_HINTS+全区域+0.8f）；相册选图；回调返回扫描文本；扫描后停止连续识别

### C15. ImageGalleryActivity + ImageDetailActivity（图片浏览）
- 路径 `ui/image/`｜技术 **View**（V4 垂直画布架构）｜骨架 S5｜优先级 P2
- Gallery：垂直长画布扁平化所有文章图；分页加载（PAGINATION_THRESHOLD+isInitialScrollDone）；智能预加载（速度阈值2.0px/ms+150ms 去抖）；快滚 Glide pause/resume；**WebView 串行预热**（Cloudflare 403→I-P0-2 降级重载 5s 兜底）；降级链回调（onWebViewFallback/onWebModeFallback）；**横向大图模式**（ViewPager2 全屏淡入/平滑回滚）；旋转工具栏；沉浸式；页码双显（横向 n/total+画布右下悬浮）；长按保存/分享/复制URL；工具栏（收藏/刷新/浏览器打开/日志）；返回键退横向
- Detail：独立大图页 ViewPager2+共享元素过渡；onSaveInstanceState 存 index

### C16. AutoTaskActivity + AutoTaskEditActivity（自动任务）
- 路径 `ui/autoTask/`｜技术 **View**｜骨架 S2+S3｜优先级 P3
- 列表页：搜索；菜单（添加/本地在线导入/日志）；多选（启用停用/导出JSON/**批量设置 cron** CronSchedule.parse 校验）；item 点击编辑/开关/日志/拖拽
- 编辑页：字段（cb_enable/cb_cookie/name/cron 频率 Spinner 每天|每小时|自定义/comment/script minLines4/header/jsLib/concurrentRate/loginUrl/loginUi/loginCheckJs）；菜单（保存校验/调试任务 TODO toast/登录/复制粘贴/帮助）；未保存拦截

### C17. WelcomeActivity（欢迎页）
- 路径 `ui/welcome/`｜技术 **View**｜骨架 S6｜优先级 P3
- 功能点：显示时长 PreferKey.welcomeShowTime（0 直接跳转）；FLAG_ACTIVITY_BROUGHT_TO_FRONT 防重复；**自定义欢迎图** customWelcome+welcomeImage(Dark)（.9.png decodeNinePatchDrawable/普通位图按窗口解码）；文字图标显隐（日/夜两套）；startMainActivity+defaultToRead 直达阅读器；图标标题 setColorFilter(accent)

### C18. association 系（透明窗，4 页面类）
- 路径 `ui/association/`｜技术 **View**（共享 activity_translucence.xml）｜骨架 S6｜优先级 N
- FileAssociationActivity：dispatchIntent 分发关联文件；书籍导入复制到目录（SAF/File+lastModified 比较）；存储权限；successLive 按类型弹 Import*Dialog；openBookLiveData→startActivityForBook；不支持类型强制导入
- OpenUrlConfirmActivity：读 intent→OpenUrlConfirmDialog
- OnLineImportActivity：**协议分发** legado://import/{path}?src={url}（bookSource/rssSource/replaceRule/textTocRule/httpTTS/dictRule/theme/readConfig/addToBookshelf/importonline/未知 determineType）
- VerificationCodeActivity：验证码识别 VerificationCodeDialog
- 附属 Dialog：ImportBookSource/ImportRssSource/ImportReplaceRule/ImportHttpTts/ImportTheme/ImportTxtTocRule/ImportDictRule/AddToBookshelf

### C19. debug/ 7 工具（已 Compose）
- 路径 `ui/debug/`｜技术 **纯 Compose**（AppCompatActivity+setLegadoContent+LegadoThemeWithBackground）｜骨架 S3｜**P0 已改造**
- CurlTest/HttpDebug/PingTest/EncodeTools/RegexTest（带 startIntent 外部初始值）/TimestampConvert/DebugTools 总入口
- 🔎 **v2.8 复审（2026-08-11，见 tasks.md 12.16k）3 违例**：① **硬编码中文 60 处**（§6.1 i18n 违例，实测分布 EncodeTools 19/HttpDebug 16/TimestampConvert 8/CurlTest 6/PingTest 6/RegexTest 4/DebugTools 1——工具文案/占位符/输出格式标签）② **硬编码色 11 处**（§7 第 13 步，CurlTest 2/PingTest 5/RegexTest 4）③ **实施回执缺失**（§3.3，工具族 7 Screen 均无回执模板）。修复归入 P4 一致性巡检（工具页为枝叶，非 P1 支干样板）。

### C20. AboutActivity + AboutFragment + ReadRecordActivity
- 路径 `ui/about/`｜技术 **View**（PreferenceFragmentCompat/RecyclerView）｜骨架 S2｜优先级 P3
- About：公众号文字高亮；菜单（市场评分/分享）
- AboutFragment：开源贡献者/更新日志 MD Dialog/**检查更新** giteeUpdate+UpdateDialog/发邮件/license/disclaimer/privacyPolicy MD/复制公众号/crashLog CrashLogsDialog/saveLog zip 打包/crashLog/logcat/**createHeapDump 堆转储**
- ReadRecord：搜索实时过滤；排序子菜单（书名/时长/最近，持久化）；menu_enable_record 开关；顶部总时长+"清除"确认；item 单击查书（存在跳读/不存在跳搜索）；行内删除单条

---

## D. RSS / 订阅（13 页面类）

### D1. RssSourceActivity（订阅源管理）
- 路径 `ui/rss/source/manage/`｜技术 **View+Compose 壳**（顶栏 GlassTopAppBar/SettingsSearchBar/AppDropdownMenu Compose 化，列表/批量栏保留 View）｜骨架 S2｜优先级 P1
- 功能点：搜索+快捷筛选词；三视图+文件夹视图（SourceFolderAdapter）；排序 rssSort 6 选项+升降序；类型筛选 menu_type_all/0/1/2；域名分组；分组操作（加/移组 DialogEditText+setFilterValues+动态分组子菜单）；滑选多选（DragSelectTouchHelper 16-50px）+批量（启用/停用/加移组/置顶置底/导出 saveToFile+HandleFileContract/分享/校验 CheckRssSource.start/删除）；拖拽排序（isCanDrag=rssSort==0&&layout==0）；菜单（文件夹配置/添加/本地导入/在线导入 ACache URL历史/二维码/导入默认）；条目（ivEdit 编辑/ivMenuMore PopupMenu 置顶置底删除/swtEnabled 开关/cbSource）；返回键三级
- 设计要点：**布局切换+排序统一 `ListLayoutMenu`**（与书源 C1 同款，枝叶复用）
- 🔎 **v2.8 预审（2026-08-11，explore 深审 7 文件+5 布局+3 菜单，见 tasks.md 12.16l）**：骨架判定 **S2 列表管理页**。**已符合 12 项（C1-C12）**：三视图超越 fork/滑选+Selection 接口+区间选择/SelectActionBar 批量 11 项超 fork 6/拖拽排序语义正确/快捷筛选词全 string 资源/方向跟随系统/主题 token/文件夹网格自适应/DAO 查询面齐备/返回键三级/DiffUtil payload+§4.3 手动规避。**违例 20 项（V1-V20）**：V1 顶栏 TitleBar 非 GlassTopAppBar；V2 SearchView 非 SettingsSearchBar+query 不升 VM；V3 ListLayoutMenu 零接线；V4 排序维度三套不一致（菜单 5/对话框 6/代码 7）；V5 升降序不持久化（AppConfig.rssSortAscending 已定义但全仓无读写=死配置）；V6 rssSort 用 Int 非 String key+RssSourceSort enum 死代码；V7 分组无 GroupHeader/Chips，文件夹视图私有；V8 10 私有状态散落 Activity+VM 零 UI 态；V9 多选无 BackHandler 优先退多选+不持久化；V10 三态缺失；V11 view_search.xml:19 搜索硬编码；V12 ImportRssSourceDialog.kt:272-274 新增/更新/已有 硬编码；V13 英文 strings.xml 中文值 9 key（type_text/audio/image/file/video/web+source_group_mode*）；V14 网格选中遮罩 argb 蓝硬编码色；V15 8 类弹窗全私有；V16 条目 PopupMenu+SelectActionBar 内部 PopupMenu；V17 触控目标 <48dp 被 tools:ignore 掩盖（13 处）；V18 网格固定列数非断点自适应；V19 无轻过渡动画（中性）；V20 无回执（P1 完成门禁）。**fork 差距**：RuleListScaffold 壳/GroupHeader/分组 Chips/统计条/空态 CTA/BackHandler 退多选/ListLayoutMenu 交互全缺失。**迁移路径**：以 C1 书源样板为范本，本页作 S2 枝叶复用，逐项清 V1-V20 后补回执

### D2. RssSourceEditActivity（订阅源编辑）
- 路径 `ui/rss/source/edit/`｜技术 **View**｜骨架 S3｜优先级 P1
- 功能点：**4 Tab**（基础17字段/启动/列表 ruleArticles 等/WebView enableJs等+Routes+Episodes 视频 textVideoOnly 等）；顶部快捷（cbIsEnable/cbSingleUrl/cbIsEnableCookie/cbIsEnablePreload+spType rss_type 0/1/2 切换显隐 textVideoOnly+lyType articleStyle+editParseConcurrency 0=继承全局）；**规则补全 ruleComplete**（Title/PubDate/Description/Link 补自 Articles/Image/NextPage）；菜单（保存/全屏编辑→CodeEditActivity/调试/登录/源变量/清cookie/自动补全/复制粘贴JSON/扫码/分享/日志/帮助）；KeyboardToolPop；退出未保存拦截；光标滚动跟随
- 🔎 **v2.8 预审（2026-08-11，explore 深审 3 kt+3 布局+2 菜单+debug 页+共享内核，见 tasks.md 12.16n）**：骨架判定 **S3 表单/编辑器页**（正确，4 Tab+KeyboardToolPop+未保存拦截命中）。**已符合 9 项（C1-C9）**：S3 骨架归类/硬编码色 0（3 kt+3 布局全 @color 资源）/方向跟随系统（manifest configChanges 声明）/字段 label 全 R.string（upSourceView 30+ 字段 :322-396）+menu 15 项全资源/菜单动态显隐正确（menu_login :136+menu_auto_complete checkable :137）/未保存拦截语义正确（getRssSource vs rssSource.equal，exit_no_save 确定=留页）/无违规动画/暗色全主题资源色/全页无私有 PopupMenu。**违例 20 项（V1-V20）**：V1 顶栏 TitleBar 非 GlassTopAppBar（xml:9-15）；V2 无 SettingsCard 分组表单容器+无底部保存/取消条（HorizontalScrollView 快捷条+TabLayout+RecyclerView 裸字段流 xml:17-144）；V3 Activity:225 `text="WEB_VIEW"` 第 4 Tab 文案硬编码；V4 :401 shouldOverrideUrlLoading 字段 hint 硬编码中文；V5 :501 getDisplayVariableComment 默认文案硬编码；V6 :521-525 helpActions 5 项硬编码中文；V7 VM:93 toastOnUi("格式不对")；V8 :337 "jsLib" EditEntity label 非资源（P2）；V9 资源缺双语（values/strings.xml:1425 source_tab_start=「启动」中文落英文文件+arrays.xml:16-28 layout_type/rss_type 仅中文，Spinner 全语言显示中文）；V10 source_parse_concurrency 无 values-zh（P2）；V11-13 关联 debug 页（D3）硬编码中文 3 处（:82 我的/:123 获取发现出错/:132 选择分类/:157 未获取到书源）+布局 xml 7 处+TextDialog.kt:102/KeyboardToolPop.kt:133/KeyboardAssistsConfig.kt:115 共享组件（debug P3 迁移时清）；V14 状态散落（VM 仅 autoComplete/rssSource 2 var 无 StateFlow+Activity 私有 4 ArrayList :74-77+Adapter editEntities/currentSourceType+TextWatcher 写回 :118-120）；**V15 真实功能缺陷：parseConcurrency 双源冲突**（顶栏 editParseConcurrency 读 0..32 coerce :418-419，被 sourceEntities 旧值覆盖 0..20 :435-436，顶栏编辑值保存时被静默覆盖丢失，上下限 32/20 不一致）——P1 修复；V16 死菜单项 menu_search（onCompatOptionsItemSelected 无处理分支 source_edit.xml:30-33）；V17 弹窗 6 类全存量私有（退出确认 alert/KeyboardToolPop selector/KeyboardAssistsConfig/VariableDialog/UrlOptionDialog/TextDialog）；V18 触控目标 <48dp tools:ignore 掩盖（xml:36,44,52,60 4 CheckBox+:91,106 2 Spinner+:125 60dp 宽输入）D1 V17 同款；V19 debug 页三态不合规（RotateLoading 非骨架屏+无空/错态 P2）；V20 无 §3.3 回执（完成门禁）。**内核红线**：RuleComplete.kt 纯正则零 UI 依赖零改动，7 个保存时调用点（:455-482 type 2/1/1/1/1/3/1）原样搬入 Compose VM；KeyboardToolPop 为 PopupWindow 强依赖 View 体系（IME 高度探测+undo/redo 走 EditText API）——**中高风险，建议 CodeView 走 AndroidView 桥接保留整条 View 栈，KeyboardToolPop 原样保留，P1 不重写 IME 探测**；CodeView 语法色 R.color.md_* 豁免登记。**fork 差距**：fork 无编辑页 Compose 样板，与 base 同构，无差距（本仓新增仅 Issue-1 并发继承显示+Issue-5 引入 V15 双源冲突）。**P1 必清 13 项**（V1-V7/V9/V14-V18/V20），P2 随行 4 项（V8/V10-V13 归 D3），完成门禁 V20 回执。**文档修正**：pages-inventory 原记「基础17字段」实测 sourceEntities 为 16 项（:322-337）

### D3. RssSourceDebugActivity（订阅源调试）
- 路径 `ui/rss/source/debug/`｜技术 **View**｜骨架 S3｜优先级 P3
- 功能点：调试搜索 startDebug；辅助面板快捷词（我的/系统/分类 URL initSortKinds 首个非空分类错误 ERROR 提示/内容页）；**分类切换 textFl onLongClick→selector**；流式输出 observe；菜单（查看列表/内容 HTML TextDialog）；搜索提交按钮模式+焦点显隐面板

### D4. RssArticlesFragment + RssSortActivity（文章列表+排序）
- 路径 `ui/rss/article/`｜技术 **View（顶栏 Compose，2026-08-14，tasks.md 12.40）**｜骨架 S2｜优先级 P1
- RssSortActivity：**多分类多行标签**（setupMultiLineTabs 按数量1/2/3行分块+横屏减1行+updateTabSelection/ensureTabVisible）；sortUrl 解析（JSON map/单URL/sortUrls）；搜索（仅配置 searchUrl 显示）→RssSearchActivity；翻页 menu_page→NumberPickerDialog（按 ruleNextPage 配置显隐）；登录/刷新/源变量/编辑源回调刷新/切换布局/阅读记录/清空文章；返回键搜索态回列表
- RssArticlesFragment：**5 种文章样式**（0列表/1/2/4网格 2/2/3列/3瀑布流 StaggeredGrid 2/3列）；下拉刷新 loadArticles；滚动加载更多 LoadMoreView；预加载模式 isPreload（阈值5提前触发）；DiffUtil 增量更新（payload read/title，areItemsTheSame=link）；分页跳转+位置记忆（VideoPlay/ImagePlay lastPlayedArticleLink）；点击→readRss 按 type 路由网页/图片/视频+携带分页上下文
- ✅ **v2 实施（2026-08-14，tasks.md 12.40）**：RssSortActivity 顶栏 Compose 化（activity_rss_artivles.xml title_bar→compose_top_bar + GlassTopAppBar + 菜单下沉 AppDropdownMenu），菜单全量迁移（搜索/翻页/登录/刷新分类/设置源变量/编辑源/切换布局/阅读记录/清空，搜索改 AppEditDialog 输入框弹窗），翻页菜单显隐由 pageMenuTitle 状态驱动；多行标签/ViewPager/文章列表（5 样式+预加载+DiffUtil+位置记忆）View 内核保留（AD-20 内核桥接）；VM 数据逻辑零改动，全量功能保留（红线合规）；FR-11 真机验证归 V-7（待统一验证）

### D5. RssSearchActivity + RssArticleInfoActivity（RSS 搜索/详情）
- 路径 `ui/rss/search/`｜技术 **View**｜骨架 S2｜优先级 P2
- RssSearch：统一搜索 searchRssLiveData 流式无分页；搜索历史 searchKeywordDao type=1（与书源隔离）Flexbox+点击即搜+长按删除+清空；fbStartStop 停止（红色图标）+进度条；类型筛选+动态分组；**搜索范围筛选**（已选组勾选/全部源/全部组，变更重搜）；空结果 alert 切全部；条目点击→showArticleInfo 写入 RssSearchSourceHolder→详情页
- RssArticleInfo：仿书源详情（ArcView+CardView 封面 Glide+OkHttpModelLoader referer/标题/时间/类型/来源数）；**多源列表** rv_source_list 点击某源→setSelected+立即跳阅读；底部"阅读"按钮 tvRead+“返回”tvCancel；**主题动态适配 applyThemeColors**

### D6. ReadRssActivity + ReadRss（RSS 网页阅读）
- 路径 `ui/rss/read/`｜技术 **View**（WebViewPool PooledWebView）｜骨架 S4｜优先级 P2
- 功能点：**工具栏菜单**（刷新 refreshNameList 去重重开/收藏 RssFavoritesDialog 编辑标题分组/分享/朗读 TTS 抓 outerHTML+Jsoup textArray/登录/浏览器打开/阅读记录/换源仅多源/编辑源/日志）；WebView 三通道渲染（contentLiveData clHtml+style/urlLiveData UA+header+Cookie/htmlLiveData loadWithBaseUrl）；网页拦截（preloadJs 注入 JS_URL+白黑名单 SourceContentFilter.filterUrl+legado/yuedu scheme→OnLineImport+其他外部打开）；JS 接口 nameBasic/nameJava/nameSource/nameCache；全屏视频 customWebView+toggleSystemBar+keepScreenOn；网页日志；智能返回（refreshNameList 跳过刷新页）；图片长按保存/选目录+下载监听
- **ReadRss 路由**：type 2→VideoPlayer/1→ImageGallery/0→ReadRss；历史入口

### D7. RssFavoritesActivity + RssFavoritesFragment（订阅收藏）
- 路径 `ui/rss/favorites/`｜技术 **View**（复用 fragment_rss_articles）｜骨架 S2｜优先级 P3
- 功能点：分组 Tab（rssStarDao.flowGroups 动态+单组隐藏）；ViewPager 滑动切换；菜单跳转分组 setCurrentItem；onResume 定位；删除整组 deleteByGroup；删除全部 deleteAll；条目点击→ReadRss.readRss；条目长按→delStar 确认

### D8. RuleSubActivity（规则订阅/分组）
- 路径 `ui/rss/subscription/`｜技术 **View**｜骨架 S2+S6｜优先级 P3
- 功能点：ruleSubDao.flowAll+空提示；点击 openSubscription 按 type→ImportBookSourceDialog(0)/ImportRssSourceDialog(1)/ImportReplaceRuleDialog(2)；菜单（新增/条目编辑 DialogRuleSubEditBinding：spType+名称+URL+autoUpdate+silentUpdate+interval **联动 interval=0 禁用两者/开自动更新默认24h**+URL 查重）；删除；拖拽排序 upOrder

### D9. VideoPlayerActivity + VideoFragment（视频播放器）
- 路径 `ui/video/`（1702+1392 行）｜技术 **View+Compose 壳**（顶栏 `initComposeTopBar()` Compose 化 + VideoSettingsPanel 设置面板 ComposeView 承载；ViewPager2 垂直+GSYVideoPlayer+ExoPlayer+WebView 降级播放内核保留 View）｜骨架 S5｜优先级 P2
- 功能点：**三播放模式**（文章模式上下滑动/集数模式/书源单URL 禁滑）；文章分页加载（滑到末篇 loadMoreArticles+80% 预缓冲 preloadNextArticleHtml 5s 轮询）；线路/集数选择（tvRouteSelector PopupMenu+rv_episodes+底部 chapters/volumes 横向）；播放控制（倍速 Spinner 1x/2x/3x/5x/10x+快进退-30/-10/+10/+30s+调试面板+播放地址复制）；收藏/设置/全屏悬浮按钮（VideoSettingsPanel BottomSheet：线路/倍速/悬浮窗/编辑源/日志）；全屏（isPortraitVideo 旋转+titleBarNew gone 真全屏+onUserLeaveHint 画中画+双指缩放）；**四级降级链**（L1 Exo→L2 重试→L3 WebView→L4 系统浏览器；playerType=2 自动降级不弹窗；ErrorMapper+FirstFramePreloader）；播放历史 PlayHistoryStore.save/load（10s 定时+onPause 保存+>10s 延时 seekTo）；**状态快照**（8 实例快速切换防串扰）；书源模式（封面简介 useweb/usehtml/md+目录 showToc+卷 showVolumes+菜单 自定义按钮/换源/登录/复制URL/浏览器打开/外部播放器）；订阅源菜单（收藏/刷新 recreate/换源对话框）；悬浮窗 startFloatingWindow→VideoPlayService（overlay 权限先检后启）；finish 清理位置记忆
- **手势**（VideoFragment 核心）：单击切 PURE↔NORMAL 显隐；双击播放暂停（GSY 失效重实现）；长按倍速（松手恢复）；左右滑动 seek（dx/屏宽×时长+overlay 预览）；垂直滑动放权 ViewPager2 切文章；双指外拉>1.2 触发全屏；双指左右滑隐藏控件（阈值100px）；3s 自动隐藏；触摸事件挂 GSY surface_container 替换 GSY 监听

---

## E. 配置子页（6 页面类，均在 ui/config/）

### E1. BackupConfigFragment
- 技术 **View**（PreferenceFragment，pref_config_backup）｜骨架 S2｜优先级 P2
- 功能点：WebDav 配置（URL/账号/密码掩码"*"repeat/目录/设备名，变更实时 upWebDavConfig）；备份路径选择；web_dav_backup 备份（权限+可写检查）；web_dav_restore 恢复（WebDav 文件选择器+**长按备份名删除/重命名**）；import_old 导入旧数据；restore_ignore 忽略项 multiChoice；长按→本地 zip 恢复；菜单（帮助/日志）

### E2. ThemeConfigFragment
- 技术 **View**（PreferenceFragment，pref_config_theme）｜骨架 S2｜优先级 P1
- 功能点：主题色 6 项（日/夜 主色/强调/背景/导航栏，ColorPreference 明暗校验）；bgImage/bgImageN 背景图（选图/模糊 SeekBar/删除三选）；barElevation/fontScale NumberPicker；**themeList 主题列表 Dialog**；saveDayTheme/saveNightTheme 保存；coverConfig/welcomeStyle 跳子配置；launcherIcon 换图标；状态栏/导航栏切换重建
- ⚠️ 主题权威源为 ThemeStore+ThemeSpec（AD-01），此页为唯一改主题入口，**34 槽位只在运行时推导，不改 themeConfig.json 格式**
- 🔎 **v2.8 预审（2026-08-11，explore 深审 ThemeConfigFragment+ConfigActivity 壳+ColorPreference+ThemeListDialog+ThemeConfig/ThemeSpec/ThemeStore，见 tasks.md 12.16p）**：骨架判定 **S2 配置列表页**（E2 一致，等价 SettingsClickRow/SettingsToggleRow 组合语义；无搜索需求可豁免 SettingsSearchBar）。**已符合 12 项（C1-C12）**：骨架归类正确/**主题权威源迁移红线完全合规零越界**（34 槽位只在运行时推导 LegadoTheme:41-49→ThemeSpec:34-93 toM3Scheme 无写入动作；themeConfig.json 格式不改 Config 保持 9 历史字段 ThemeConfig.kt:511-521 save 写 GSON 原格式 :146-150 validateConfig 旧字段 :226-236；SharedPreferences 旧 key 不改 applyTheme 直读 cPrimary 等 :427-473）/换肤即时切换无全量 animateColor（postEvent(RECREATE) ThemeConfig.kt:69-74）/明暗校验功能正确（onSaveColor 白天禁太暗/夜间禁太亮 :89-108）/页面层硬编码 UI 色 0（listView.setEdgeEffectColor(primaryColor):114 走 token+XML 全 @color）/无页面私有 PopupMenu（顶栏仅 menu_theme_mode 1 项 MenuProvider 注入 :115,128-142）/Pref listener 注册注销配对+runCatching 链（:118-126/:350-386）/方向跟随系统/无障碍部分达标（图标 48dp+contentDescription item_theme_config.xml:19-42）/资源层双语主体合规（pref_config_theme 18 title/summary 全 @string+values-zh 补齐）/阅读器红线未越界（主题切换仅 SharedPreferences+EventBus 不碰数据库，未改 ReadBookConfig 每书配色）/背景图下载逻辑正确（url→Content-Type 判扩展名→MD5 文件名 :347-411）。**违例 15 项（V1-V15）**：V1 顶栏私有 TitleBar 非 GlassTopAppBar（activity_config.xml:8-13+ConfigActivity:30-33 setTitle）；V2 页面零 Compose 未包 LegadoTheme（PreferenceFragmentCompat 纯 View 体系 M3 34 槽位未接入本页）；V3 状态管理无 ViewModel+Flow（SharedPreferences 直读直写+onSharedPreferenceChanged 散落 :80-121，ConfigViewModel:16-51 为占位未被本页使用）；V4 themeList 私有全屏 Dialog（ThemeListDialog:23-120 BaseDialogFragment+setLayout(0.9f,0.9f)+RecyclerView+VerticalDivider，§6 S6 L2 明确 AppSelectDialog 替代主题列表）；V5 4 类私有弹窗布局（保存主题 DialogEditTextBinding:223-244/背景图三选 selector:246-282/模糊 SeekBar DialogImageBlurringBinding:284-310/删除确认 alert ThemeListDialog:73-81）；V6 NumberPicker 非 L2 族（io.legado.app.ui.widget.number.NumberPickerDialog :177-203）；V7 i18n 硬编码中文 7 处（:351 下载背景图片中.../:383 设定成功/ThemeListDialog:65 格式不对,添加失败/:85 主题分享/theme_list.xml:7 剪贴板导入/ThemeConfig.kt:120 未缓存在线背景图/278/290）；V8 硬编码英文字面量 :226 editView.hint="name"；V9 主题子系统 toast/日志硬编码中文 4 处（ThemeConfig.kt:120,278,290,321 AppLog.put 设置主题出错）；V10 硬编码色 ColorPreference.kt:28 Color.BLACK/:135 getPersistedInt(-0x1000000)/:261 取色器默认值非 UI 色建议登记豁免（巡检项）；V11 ThemeListDialog 三态不齐（RotateLoading 私有/空态裸 tv_msg/无错误态 dialog_recycler_view.xml:29-45）；V12 无 §3.3 回执；**V13 AD-01/AD-04 内置 4 套 ThemeSpec 未落地**（ThemeSpec.kt 仅 data class 无预设表，全仓 grep 米白|暖黄|纯黑 0 命中，themeConfig.json 17 套含暗夜紫 :91 但缺米白/暖黄/纯黑 3 套新内置）——功能范围问题非格式问题，**需用户裁决归 P1 或 P2**；V14 选主题双重重建隐患（ThemeConfig.applyConfig applyDayNight→RECREATE ThemeConfig.kt:319+onSharedPreferenceChanged 再触发 upTheme :150-156 两次 applyTheme+RECREATE，recreate 幂等无功能错误 P1 优化项）；V15 无障碍缺口（dialog_recycler_view.xml:27 tools:ignore=SpeakableTextPresentCheck+selectBgAction 三选弹窗触控未确认 ≥48dp）。**fork 差距**：MoRealm 用 Room themes 表+6 内置主题——**不引 Room 表（生态/风险），补内置 4 套预设待裁决 V13**；MoRealm readerBackground/readerText 随主题实体——**不学**（ReadBookConfig 每书配色红线）；ThemeSpec.toM3Scheme 已采纳背景锚定中性面思路（surface=lerp(bg,White/Black,0.04/0.10) ThemeSpec.kt:43-45）；HCT 引擎不引（受限）；RECREATE 即时切换已采纳。**P1 通用五件套**：V1 GlassTopAppBar→V2 零 Compose→V3 状态收敛→V4-V6 弹窗族收敛→V7-V9 i18n 11 处+裁决 V13

### E3. CoverConfigFragment
- 技术 **View**（PreferenceFragment，pref_config_cover）｜骨架 S2｜优先级 P3
- 功能点：默认封面图日/夜（选图/删除）；coverRule 封面规则→CoverRuleConfigDialog；coverShowName(N)/coverShowAuthor(N) 联动（作者依赖书名 enabled）；变更 BookCover.upDefaultCover

### E4. OtherConfigFragment
- 技术 **View**（PreferenceFragment，pref_config_other）｜骨架 S2｜优先级 P2
- 功能点：大量 NumberPicker（预下载/线程/搜索线程/缓存线程/RSS并发/图片并发/Web端口/位图缓存/图片保留/编辑最大行）；userAgent/customHosts(JSON 校验)；videoSetting→SettingsDialog；默认书目录 TreeUri；cleanCache/clearWebViewData/shrinkDatabase（确认框）；localPassword；checkSource→CheckSourceConfig；uploadRule→DirectLinkUploadConfig；debug_tools→DebugToolsActivity；开关（记录日志/调试浮球/processText 文本选择分享/显示发现-RSS/语言重启/自动刷新）

### E5. PreciseManageFragment
- 技术 **View**（PreferenceFragment，pref_precise_manage）｜骨架 S2｜优先级 P3
- 功能点：聚合入口 4 项（URL记录/存储管理/下载管理/文件管理）

### E6. WelcomeConfigFragment
- 技术 **View**（PreferenceFragment，pref_config_welcome）｜骨架 S2｜优先级 P3
- 功能点：欢迎页图片日/夜（选图/删除，支持 http 下载 AnalyzeUrl+BitmapUtils.cropBitmapToAspectRatio 屏幕比例裁剪）；文字/图标开关已注释留空

---

## F. 其它（6 页面类）

| 页面 | 骨架 | 优先级 | 一句话功能 |
|------|------|--------|-----------|
| AboutActivity | S2 | P3 | 公众号高亮+市场评分/分享 |
| AboutFragment | S2 | P3 | 贡献者/更新日志/检查更新/邮件/license/崩溃日志/堆转储 |
| ReadRecordActivity | S2 | P3 | 搜索+排序+启用开关+总时长+清除+跳读 |
| WebViewLoginFragment | S6 | N | WebView 登录+登录Cookie |
| QrCodeFragment | S6 | N | 相机扫码 |
| VideoFragment | S5 | P2 | 视频播放（见 D9） |

---

## G. 迁移路线图（主干 → 支干 → 枝叶 · 全 Compose 边界：正文/内核保留 View）

> 策略依据（AD-24）：主干 = 公共资产（已完成 Phase0-3 的组件库/主题/骨架/状态范式）；支干 = 每类骨架 S1-S6 的样板页（首做并冻结验收）；枝叶 = 同类剩余页直接复用样板。样板页分配见 `ui-standards.md` §9.2。

| 层/阶段 | 目标 | 页面清单 | 验收 |
|---------|------|---------|------|
| **主干 已改造** | 公共资产地基 | 书架1/2、MyFragment、debug 7 工具（组件库 19 文件/主题 34 槽位/骨架/状态范式全部建立） | 已真机验证 |
| **支干 P1 样板页** | 每类骨架冻结范本 | S1→MainActivity（PillNav）、S2→BookSourceActivity、S3→BookSourceEditActivity、S4→BookInfoActivity、S5→阅读器浮层 Sheet 化、S6→登录/导入 Dialog 族 | 样板页功能点全过 + 回执模板示范（FR-11） |
| **枝叶 P2 次优高频** | 复用支干样板 | Explore、Rss、Search、Toc、BookSourceDebug、Replace、Highlight、SourceLogin、BookManage、Cache、ReadManga、Audio、ImageGallery、Video、Config 3 子页（Backup/Theme/Other） | 同型页骨架一致（照抄样板）+ 真机覆盖 + 回执 |
| **枝叶 P3 长尾低频** | 收尾全量 | 其余所有 View 页（导入/存储/文件/下载/记录/回收站/自动任务/词典/TxtToc/BookInfoEdit/Welcome/About/ReadRecord/URL记录/SS阅读） | 全量页面 Compose + 巡检 0 私有重复 + 回执 |
| **N 不迁移** | 内核/第三方 | 阅读器正文（AD-02）、CodeEdit（sora）、WebView（WebViewPool）、QrCode（camera-scan）、透明窗（协议分发） | 壳换 Compose 浮层即可 |

> 逐页真机功能点覆盖测试为**每页 Compose 化强制门禁**（见 ui-standards.md §7 与 tasks.md），使用 `ai_tests\venv\Scripts\python.exe` + MEmu；每页完成必须填 §3.3 实施回执。

---

## H. 变更记录
- 2026-08-16 v2.12：深化迭代 12.19 收尾 C4 技术标注核对（2026-08-16，源码核验）——C1 BookSourceActivity 技术 **View→View+Compose 壳**（BookSourceScreen/BookSourceItems Compose 化，ComposeView 桥接双轨）；C2 BookSourceEditActivity 技术 **View→View+Compose 壳**（composeTopBar/TabBar/QuickToolbar/Fields/BottomBar 5 处 Compose 接线）；B7 BookInfoEditActivity 技术 **View→View+Compose 壳**（BookInfoEditScreen 全 Compose+ComposeView 桥接）；D1 RssSourceActivity/D9 VideoPlayerActivity 复核维持 **View+Compose 壳** 标注正确。
- 2026-08-11：建立全量 84 页面类功能点核对表（4 路源码探针佐证）；登记技术栈/骨架/优先级/真机状态。
- 2026-08-11 v2：§G 改为「主干→支干→枝叶」三阶段路线图，每类骨架 S1-S6 指定样板页（AD-24）；每页实施回执为强制门禁（§3.3/AD-23）。
- 2026-08-11 v2.1：C1/D1 功能点标注「布局切换+排序统一 `ListLayoutMenu`」；D4（RSS 文章 5 样式）归入 S2 ListLayoutMenu 覆盖范围。
- 2026-08-11 v2.9：C2/D2 条目标注 v2.8 预审（书源编辑 S3 样板页 7 符合+13 违例+内核红线 AndroidView 桥接方案；订阅源编辑 9 符合+20 违例+parseConcurrency 双源冲突功能缺陷登记）。
- 2026-08-11 v2.10：A1/A8 条目标注 v2.8 预审（MainActivity S1 样板 12 符合+10 违例+PillNavigationBar 孤儿接线点确认+S1 首接线方案；RssFragment S2 枝叶 12 符合+16 违例+rssSort/sourceLayout 双 no-op 功能性缺陷）。
- 2026-08-11 v2.11：B2/B11/E2 条目标注 v2.8 预审（TocActivity 14 符合+14 违例+高亮 Tab 未接线 V14 止血+BookTocBookmarkSheet 接线评估为 R2 浮层雏形；搜索页族 14 符合+21 违例+SearchContent companion 静态配置缺陷+D5 RssArticleInfo 归类疑点；ThemeConfigFragment 12 符合+15 违例+主题权威源红线合规+AD-04 内置 4 套主题未落地 V13 待裁决）。
