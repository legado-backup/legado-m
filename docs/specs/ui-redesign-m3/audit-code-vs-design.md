# 待提交代码改造 vs 设计文档一致性审查报告

> 审查对象：另一 AI 在 master 分支的全部待提交改动（40+ kt / 30+ xml / 新增 untracked）。
> 审查基准：`ui-standards.md §3.4`（组件规格唯一真值）+ `pages/` 族文档 v2 + `pages-inventory.md` + `tasks.md`。
> 审查方式：git diff 逐项核对 + Grep 违规扫描 + 源码读码。**本审查只改文档不改代码**。
> 日期：2026-08-15。供另一 AI 继续实施前必读。

---

## 〇、总体结论

**方向正确，偏差率低，但存在 9 项需修正/决策的偏差 + 2 项范围外改动需确认。** 全部新增/重构点中大部分符合设计文档，9 项需处理（详见下）。

符合设计文档的高质量改造（✅）：
1. **LegadoTheme → ThemeSpec.toM3Scheme 重构**（LegadoTheme.kt -73）——语义等价（primary=accent/secondary=primaryColorValue/lerp 三件套 surface 0.04-0.10 surfaceVariant 0.05-0.14 outline 0.12-0.24/outlineVariant α0.75-0.8/error 亮 #E53935 暗 #FF5252），`remember(6 参)` 缓存正确，符合 **AD-18 单一推导入口**。ThemeSpec.kt 已复核 107 行。
2. **Import 族 8 文件统一 ImportSourceSheet**（7 文件 890+/1060-，ImportRssSource 为样板）——符合 12.25 评估/12.26 样板方案，dialog_import_sheet.xml 独立宿主未动共享 dialog_recycler_view.xml。
3. **阅读器浮层 reader-overlay-compose spec 四文档**——引用 P2-reader v2 + ui-standards §3.4，阶段1-4 完成，正文零改动红线守住（git status page/ 零变更），ReaderUiState/MenuLayer/ReaderMenuSheet 设计合理。
4. **Menu 3 文件删除有承接**——backup_restore/theme_config 迁 ConfigActivity `setTopBarMenu(MenuAction)`，video_play 迁 VideoPlayerActivity Compose 顶栏，非功能丢失。
5. **另一 AI 自建审计（audit-wired-components.md）3 处定案违例已修复落地**——BookSourceItems:354 displaySmall / GlassTopAppBar:46 titleMedium / ImportSourceSheet:267 padding h16v12，BUILD SUCCESSFUL。
6. **S1 PillNavigationBar / S2 书源页 / S6 Import 样板全部符合 §3.4**（另一 AI 审计已逐维度对账）。

---

## 一、🔴 偏差需修正（10 项）

### 偏差 1：`VideoPlayerActivity.kt:1251,1272` 存量 `Log.d("VideoFS", ...)` 未清理

- **事实**：git diff 证实为存量日志，另一 AI 仅改写 message（`titleBarNew gone`→`composeTopBar gone`），未删除。违反 AGENTS「任务完成前 grep 无 `android.util.Log.d/e` 残留」。
- **决策**：改造该文件时应收敛为 `AppLog.put()` 或删除。**不属于本次审查修正范围（禁动代码），已登记为新子任务 D-1 交另一 AI 处理。**

### 偏差 2：rssSort 排序偏好 no-op 仅限 RssFragment 主列表层（P7 V4，已精确定位）

- **事实（第二阶段核码定案）**：
  - **管理页 RssSourceActivity 已消费 rssSort**：菜单 `:212-235` 写入 AppConfig.rssSort 0-6，`sortSources():587-597` 按 rssSort 排序（1 名称/2 启用/3 类型/4 分组/5 URL/6 更新时间）+ sortAscending 反转。**本页 no-op 不成立。**
  - **RssSortActivity +252 行**：主要为代码重排/查询跳转参数，菜单 GridView 为 `switchLayout`（RssSortViewModel:39-48 articleStyle 0-4 循环持久化，**消费方是 RssArticlesViewModel 文章列表风格，已真实生效**，与 sourceLayout 属不同机制）。
  - **RssFragment 主列表仍 no-op**：数据源 `:379-419` 六分支 flow 全部 `RssSourceDao` 查询（恒 `order by customOrder`）；`RssViewModel:13-33` 仅 top/bottomSource 操作 customOrder；**无任何 AppConfig.rssSort 消费**。文件夹配置对话框写 rssSort（SourceFolderAdapter:119-120）但主列表不读。
- **结论**：P7 V4 缺陷**未关闭**，精确定位为 **RssFragment 主列表**（非管理页）。
- **决策**：D-2 改为「RssFragment 主列表接入 rssSort 排序偏好」（排序偏好传 DAO 查询参数或 upRssFlowJob 分支内存排序）。

### 偏差 3：sourceLayout no-op 仅限 RssFragment 主列表层（P7 V5，已精确定位）

- **事实（第二阶段核码定案）**：
  - **管理页 BookSourceActivity/RssSourceActivity 已完整消费 sourceLayout**：两页 `applyListView:576-590/314-340` 按 0=列表/1=紧凑/2-6=网格 切换 layoutManager；`currentSelectionAdapter`/`currentGetItems` 按布局选适配器；RssSourceActivity:337 布局 0 才允许拖拽。
  - **RssFragment 主列表仍恒 4 列**：`applyListView():241-245` `GridLayoutManager(context,4)` 硬编码，**不读 AppConfig.sourceLayout**；`applyView():295-310` 仅按 isShowingFolder/isTagMode 二分支。RssFragment 不在本次改动清单（未改）。
- **结论**：P7 V5 缺陷**未关闭**，精确定位为 **RssFragment 主列表**（非管理页）。
- **决策**：D-3 改为「RssFragment applyListView 读 AppConfig.sourceLayout 三态转 layoutManager」（列表→LinearLayoutManager / 紧凑→Grid(2) / 网格→复用 applyFolderView 的 calculateSpanCount 逻辑）。

### 偏差 4：HighlightRuleScreen/ReplaceRuleScreen 顶栏菜单用裸 DropdownMenu 非 AppDropdownMenu（新增发现）

- **事实**：两个新增 Screen 文件（`HighlightRuleScreen.kt:115-139` 顶栏 MoreVert 5 项；`ReplaceRuleScreen.kt:85-103` 分组菜单 + `:121-146` 顶栏 MoreVert）直接用 `material3.DropdownMenu`+`DropdownMenuItem` 手写，**未复用 §3.4 菜单族 `AppDropdownMenu`**（MenuAction 数据驱动+48dp 高+checked 态）。违反 ui-standards §7 第 6 步门禁「禁页面私有 PopupMenu/下拉菜单，统一 AppMenuSheet/AppDropdownMenu」+ L-C5 §1/L-C4 复用声明（明确列 AppDropdownMenu）。
- **对照**：本次改动同批 BookInfoActivity:307/ReadRssActivity:312/RssSortActivity 顶栏均正确用 AppDropdownMenu，说明另一 AI 具备该组件认知，此两处属遗漏。
- **决策**：登记 D-8 交另一 AI 将两文件裸 DropdownMenu 替换为 AppDropdownMenu（MenuAction 数据驱动，功能等价）。

### 偏差 5：BookshelfScreen 私有 ShelfUnreadBadge vs P1 文档 BadgeDot 接线声明不符（新增发现）

- **事实**：
  - **代码**：`BookshelfScreen.kt:332-350` 私有 `ShelfUnreadBadge`（primary 底 + `Color.White` 硬编码字，:345/:401；`:393` `Color.Black.copy(alpha=0.55f)` 封面文字遮罩）被 :382/:518 调用。**全仓 BadgeDot 仅 PillNavigationBar:126 引用**，书架页零引用。
  - **P1 文档**：§2 区块表:38 + §3:46 声称「未读角标 `BadgeDot`（error 底/10sp/99+）BookshelfItems.kt:323/:449 已接线 ✅」+ :50「本页私有组件 0」——**与代码矛盾**（BookshelfItems.kt 实际仅 124 行，无 :323/:449；角标在 BookshelfScreen 私有实现）。
  - **用户需求冲突**：2026-08-14 用户 b6 反馈「书架 99+ 角标丑→主题色圆角数字」（ai_memory 记录），即用户要 **primary 主题色** 角标；而 P1 文档 BadgeDot 规格是 **error 色**——设计文档与用户需求本身冲突。
- **决策**：登记 D-9：①P1 文档需回填角标真实实现（BookshelfScreen ShelfUnreadBadge 私有 primary 底，响应 b6 用户主题色需求），BadgeDot 接线声明改回「仅 PillNavigationBar」；②ShelfUnreadBadge 硬编码 Color.White/Black 建议收敛 colorScheme 或复用 BadgeDot 亮度自适应逻辑（badgeTextBright）。**✅ 已定案（2026-08-15 用户决策）：色槽取主题色 primary（响应 b6 需求），P1 文档回填真实实现。**

### 偏差 6：MenuLayer 顶栏「换源/更多」菜单裸 DropdownMenu（P2 阅读器浮层，新增发现）

- **事实**：新文件 `MenuLayer.kt`（git 未跟踪，被 ReadBookActivity:1417 setupTocSheet 使用）`MenuTitleBar`:222-426——换源菜单 :298-320、更多菜单 :331-418 直接用 `material3.DropdownMenu`+`DropdownMenuItem` 手写，checked 态用 leadingIcon Check 手写（:437-446），**未复用 AppDropdownMenu 数据驱动+action.checked**。违反 ui-standards §7 门禁（与偏差 4/8 同类）。注：顶栏本体为自定义 48dp Row（:234-238）非 GlassTopAppBar，但 P2 spec §2/§3 明确定义阅读器顶栏为 `MenuTitleBar`（surface α0.86 玻璃降级），与 §3.4 GlassTopAppBar 属两套组件——此处为 P2 页级设计，**不作违例，但 P2 spec §3 表 :54「更多操作 → AppMenuSheet」与实现（下拉菜单）不符**，需裁决。
- **对照**：同批 MangaMenu（ReadMangaActivity:484-668 buildMangaMenuActions + :305-309 AppDropdownMenu）完全合规，可作样板。
- **决策**：登记 D-10 交另一 AI：MenuLayer 换源/更多菜单改 AppDropdownMenu（MenuAction 数据驱动）。**✅ 已定案（2026-08-15 用户决策）：菜单形态取下拉菜单，P2 spec「更多操作→AppMenuSheet」描述同步更新为下拉。**

### 偏差 7：BookSourceScreen/BookSourceItems 裸 DropdownMenu + 硬编码中文/英文关键词（P5 书源，新增发现）

- **事实**：
  - `BookSourceScreen.kt:699` `DropdownMenu`（BookSourceMoreMenu 16 项更多菜单 :700-832）+ `:915-918` `DropdownMenu`（SelectActionBarCompose 批量菜单 :920）——均裸手写，违反 §3.4 菜单族门禁（同偏差 4/8 类）。
  - `BookSourceScreen.kt:402-403` QuickFilterWords 硬编码英文关键词 `"enabled"/"disabled"/"need_login"/"no_group"/"enabled_explore"/"disabled_explore"`——View 侧对应关键词走 `getString(R.string.enabled)` 等本地化（BookSourceActivity:500-505，中文环境为「已启用」等），中文环境下 chip 筛选会落入名称搜索，**功能不一致**；且该区 showTopBar=false 下不渲染，属**死代码**。
  - `BookSourceItems.kt:287` `checkMessage.contains("成功")` 硬编码中文 UI 判断（照搬存量 BookSourceAdapter:45 `Regex("成功|失败")`，但仍属新增侧）。
  - `BookSourceItems.kt:338` `Color.White`（封面首字符，primary 渐变上，语义用途但未登记豁免）；`:363-366` SourceTypeBadge 4 色 `Color(0xFF4CAF50) 等`——**P5 §7 已登记豁免**。
- **决策**：登记 D-11：①BookSourceScreen 两处裸 DropdownMenu→AppDropdownMenu；②QuickFilterWords 关键词走 getString 或删死代码；③BookSourceItems:287「成功」判断收敛（复用存量 Regex 或 message 资源化）。

### 偏差 8：MyFragment 内部类 MyPreferenceFragment 已成死代码（P9 我的页，本次改动副作用）

- **事实**：MyFragment:63-76 已改为 View 壳+ComposeView 桥接，onFragmentCreated 不再实例化 `MyPreferenceFragment`（原 childFragmentManager replace 已删），但类体 L92-202 **完整保留**（含存量硬编码中文 L103「复制地址/浏览器打开」+ 未迁移的 observeEventSticky 逻辑）。非功能丢失，属遗留死代码。
- **决策**：登记 D-12 交另一 AI 清理死代码（保留时需确认无反射/无 ID 引用）。

### 偏差 9：PillNavigationBar 组件代码 vs §3.4/P9 文档漂移（底栏，新增发现）

- **事实**：§3.4 真值表（ui-standards.md:220）与 P9-main.md §3 写明「spring 弹性过渡 + primary α0.12 选中底胶囊 36×30 RoundedCornerShape(15) + Row 垂直 6dp」，但 `PillNavigationBar.kt` 实际：:66 Row padding 仅 vertical 4dp、:95-104 `animateColorAsState+tween(200)`（非 spring）、**无选中胶囊底色**（注释 :41 自述「2026-08-14 按 bug① 简化…无底色胶囊动画」）。即 08-14 简化后 §3.4/P9/本报告此前「全部符合 §3.4」断言均未同步回填。
- **决策**：登记 D-13：PillNavigationBar 规格或文档回填其一（组件简化已落地，建议回填 §3.4 状态列+检查点描述）；MainActivity 接线本身合规。

### 偏差 10：ConfigActivity 启动即 NPE 崩溃（真机验证新增，P0）

- **事实（2026-08-15 真机验证）**：`ConfigActivity.kt:32` `private var composeTitle by mutableStateOf(getString(R.string.setting))`——**属性初始化在 Activity 构造阶段执行，此时 Context 尚未 attach**，`getString()` 抛 `NullPointerException: Attempt to invoke virtual method 'getResources()' on a null object reference`（crash 栈指向 `ConfigActivity.<init>`）。真机 am start ConfigActivity 直接崩溃退回 launcher。
- **范围核对**：全仓同模式 `by mutableStateOf(getString(...))` 仅此一处；其余 6 处（Cache:110/AudioPlay:100/RssSort:78/VideoPlayer:148/ReadRss:146/BookshelfManage:102）均用 `""` 空串初始（安全），但同样依赖 `setTitle()`/`onActivityCreated` 后续赋真实值。
- **根因**：Compose 顶栏改造把标题状态提升为属性初始化，违反「Activity 属性初始化禁调 context 依赖 API」约束（构造阶段无 attach）。
- **决策**：登记 D-15（P0 优先）：`ConfigActivity.kt:32` 改 `mutableStateOf("")`（与其余 6 处一致）+ setTitle() 兜底赋真实值；或将 composeTitle 惰性初始化（onActivityCreated 后再建状态）。**此缺陷直接阻断 ConfigActivity 全部子页入口（设置/主题/备份/封面/欢迎/精准管理）**。

---

## 二、🟡 范围外改动需用户确认（2 项）

### 项 1：App 图标被改（无设计依据）

- **事实**：`mipmap-anydpi-v26/ic_launcher.xml` foreground `@drawable/ic_launcher0`→`@mipmap/ic_launcher_foreground`，并新增 5 个 `ic_launcher_foreground.png`（hdpi~xxxhdpi）。**设计文档体系无任何图标改版记录**。
- **风险**：正式包图标被替换为未经验证的新图标，可能偏离品牌设计。
- **决策**：**✅ 已授权（2026-08-15 用户决策）：保留新图标 ic_launcher_foreground。另一 AI 补设计依据（图标改版文档），D-14 ③ launcherIcon 代码侧残留一并收尾。**

### 项 2：ai_tests 新增 ai-llm-testing 体系 + 独立 spec

- **事实**：新增 `docs/specs/ai-llm-testing/` + `ai_tests/lib/llm_client.py/llm_server.py/ai_agent.py/ai_verifier.py/ai_experience.py` 等 6 文件+5 测试。**不在 ui-redesign-m3 范围内**（属新能力建设）。
- **决策**：属合理扩展但需确认独立立项（已单独 spec 目录，结构合规）。

---

## 三、✅ 观察项确认（无动作，仅记录）

1. **网格断点 400/600/800 vs §1.4 的 480/840**：两者不同维度（网格列数自适应 vs 骨架断点），保留现状正确（另一 AI 审计已定案）。
2. **SettingsSearchBar 已被 BookSourceScreen:215 接线**：组件表状态应从 ⚠️孤儿更新为 ✅ 已接线（另一 AI 审计已登记）。
3. **AppModalBottomSheet/BookTocBookmarkSheet 已在 §3.4 补真值行**：规格缺口封闭正确。
4. **reader-overlay 推迟项**：3s 无操作自动淡出 / 滑块 alpha≤30% 预览 + conflate 串行，已在 tasks.md 注明「P2 收尾评估」——需在 P2-reader.md §8 验收中补登记为待办（见下 D-5）。
5. **轻量文档 16 份 task 占位符**（audit-lightweight-docs 已列）：L-B14/B15/B16/C3/C4/C5/C6/C9/C10/C11/C12/C13/C15/C16/C17/C20 待回填精确 task 号（D-6）。
6. **debug 7 Screen 存量 `titleLarge.copy(fontSize=20.sp)`**：存量未改，入存量清零清单，不属本次偏差。
7. **SourceLoginDialog 壳层 Compose 化**（2026-08-15 二阶段核码）：顶栏 Toolbar→`initComposeTopBar()`（GlassTopAppBar+Check 确定+MoreVert 3 菜单：查看登录头/删除/日志），表单引擎内核（rowUiBuilder/loginUi/动态 JS 表单）保留 View——属 AD-02 壳层 Compose 化合规。12.25「属 N 不迁移」判定需更新（见 D-7）。
8. **switchLayout vs sourceLayout 是两套机制**（2026-08-15 核码）：RssSortViewModel:39-48 switchLayout 循环 articleStyle 0-4 持久化，消费方 RssArticlesViewModel（文章列表风格，已生效）；sourceLayout 是源列表布局（AppConfig.sourceLayout）。P7 V4/V5 登记的是后者，与 switchLayout 无关。
9. **BookshelfFragment1/2 重构合规**（2026-08-15 核码）：两文件净删 375 行（类声明/方法签名移动重构），新增 ViewPager 内嵌 Compose BookshelfContent；功能点保留（点击开书 startActivityForBook/分组 onGroupSelected/排序 upSort/搜索跳 SearchActivity）；grep 无硬编码中文/色（仅 AppLog.putDebugWithTag 日志 1 处）。删除侧无 `startActivity/.show()/.start(` 功能丢失。
10. **BookInfoActivity/ReadRssActivity 顶栏合规**（2026-08-15 核码）：均 GlassTopAppBar + AppDropdownMenu（BookInfo:307 / ReadRss:312），无硬编码中文/色（book/info 仅 AppLog.put 日志 2 处；ReadRssViewModel/RssJsExtensions 中文 toast 5 处经 diff 证实存量非本次）。
11. **ProfileScreen3Level formatDuring 硬编码中文**（2026-08-15 核码）：`formatDuring():260-274` 硬编码「天/小时/分钟/秒/0秒」5 处，但 **P4-my-config.md §7 V2 已登记**（「需迁 strings.xml 双语」）——属已知遗留非新偏差，D-9 不重复登记。
12. **BookshelfScreen Color.White/Black 上下文**：ShelfUnreadBadge primary 底白字（onPrimary 语义）+ 封面文字 Black 0.55 遮罩白字，均属语义用途但硬编码（见 D-9）。
13. **ReadMangaActivity 中文 3 处**（没有更多了/加载失败，请重试/请选择书籍加载来源）：经 diff 证实为存量（不在 + 新增侧），归存量清零清单。
14. **P2 阅读器族核码**（2026-08-15 四阶段）：ReadBookActivity 顶栏经 MenuLayer 承载（:1417），新增侧无硬编码中文/色（L1560 还主动修复了存量 `toastOnUi("未找到可移除的重复标题")`→getString，属改进）；L745 `LogUtils.d` 为 java.util.logging 文件日志非 android.util.Log，合规；BaseReadBookActivity 仅 +5 行（menuOverlayVisible）；activity_book_read.xml 仅 +7 行（compose_sheet_host）；MangaMenu/ReaderUiState 完全合规（可作样板）。**轻微惯例违例**：ReadBookActivity:1288 loadTocSheetData + :1551 onMoreSameTitleRemoved 用 `lifecycleScope.launch` 而非 Coroutine.async 链（无 try/catch，风险低）。
15. **P5 书源族核码**（2026-08-15 四阶段）：BookSourceActivity applyListView:577-602 三态消费完整合规（0 列表/1 紧凑/2-6 网格）+ 网格断点 <400→2/<600→3/<800→4/≥800→6 与 P5 §2 逐行一致；BookSourceEditActivity 顶栏（GlassTopAppBar:189+AppDropdownMenu:201 buildMenuActions 12 项）完全对齐 P10 §2/§3；BookSourceDebugActivity（GlassTopAppBar:84+AppDropdownMenu:101+SettingsSearchBar:109）合规；activity_source_debug.xml 帮助面板硬编码中文带 `tools:ignore` 且 diff 证实存量。**边界**：BookSourceEditActivity:460-472 类型下拉用裸 DropdownMenu（非顶栏菜单，属字段选择器 Spinner，标准①未限定范围，建议确认）；Tab 内容区用单 View RecyclerView 换数组（setEditEntities:631）非 V3 裁决的 when 切 6 独立 LazyColumn——功能等价（RecyclerView 换数组不触发 CodeView 重建，AD-02 红线未破），属规格字面偏差。
16. **P9 主页族核码**（2026-08-15 四阶段）：MainActivity PillNavigationBar 接线（:196-201）+ 4 Tab ViewPager 保留 + Tab 保活 V6 修复（:105-110）+ 重选双守卫 300ms + i18n 修复（password/crash_detected_prompt）+ BadgeView 退役全部落地；ConfigActivity setTopBarMenu(MenuAction):58-60 接口存在、空列表隐藏 MoreVert、BackupConfigFragment:150-163/ThemeConfigFragment:108-119 注册，无 titleBar 残留引用、已删菜单 XML 无悬空引用。ProfileScreen3Level 4 项偏差（formatDuring 硬编码中文/无 runCatching/服务开关不观察 EventBus/加载态居中转圈）**P4 §7 V2 已登记**，非遗漏。
17. **Import 族 8 文件 + 杂项核码**（2026-08-15 四阶段）：7 个 ImportDialog 全部绑定 dialog_import_sheet.xml + 调 ImportSourceSheet（grep BottomSheet/Color(0x 零残留），WebViewLoginFragment（GlassTopAppBar:60）、SourceLoginDialog（:664/:682）、CacheActivity（:163 顶栏 + :177/191/205 三处 AppDropdownMenu）、BookshelfManageActivity（:178/:202）、ReplaceEditActivity（:125/:137）全部合规；AppContextWrapper uiMode 强制（:41-52 themeMode 1/3→NIGHT_NO 2→NIGHT_YES else 跟随）与 AppConfig.isNightTheme 一致；Restore.kt 仅删 LauncherIconHelp.changeIcon 调用；SwitchPreference accentColor→primaryColor；LegadoTheme→ThemeSpec.toM3Scheme 语义等价（error 色逐位一致）。**存量死代码 2 处**：CacheActivity:94/409 PopupMenu 接口+onMenuItemClick（HEAD 已有，本次删实例化成死代码）、Restore.kt:7 无用 BuildConfig import，非门禁项建议顺手清理。
18. **图片/音频/漫画族 + VM/宿主核码**（2026-08-15 五阶段）：ImageGallery（GlassTopAppBar:201+AppDropdownMenu:231 buildMenuActions）、ImageDetail（:161 无菜单）、AudioPlay（:146+:176 buildAudioPlayMenuActions 6 项）、ReadManga（顶栏在 MangaMenu.kt:276/305 样板一致，buildMangaMenuActions:484 16 项）全部合规；4 Activity 零新增中文（旧「图片浏览」硬编码还修正为 getString(R.string.image_browse)）、零硬编码色、零 Log.d/e。BookInfoViewModel 8 处字符串全迁 strings.xml（book_not_found/webdav_not_configured_alarm/download_remote_book_fail/load_toc_error/downloaded/clear_cache_error 等双语齐备），BookInfoEditViewModel 2 处（book_info_save_fail_duplicate/fail）、HighlightRuleActivity 8 处（highlight_rule_preset_added_toast/_import_*/_export_*）、ReplaceRuleActivity 8 处（enabled/disabled/no_group）全迁；Compose 宿主 3 文件（HighlightRule L44-45 / ReplaceRule L117-118 / ReplaceEdit L123,151）全部包 LegadoTheme；HighlightRuleAdapter 删除无悬空引用；P3 §5 V5 状态管理违例（LiveData+可变字段）为已知存量。**死资源 1 处**：`menu/image_gallery.xml` 未随菜单迁移删除（全仓 R.menu.image_gallery 零引用），建议清理。
19. **RSS 域 + 剩余 XML + 双语核码**（2026-08-15 六阶段）：RssSortActivity（GlassTopAppBar:286+AppDropdownMenu:298）顶栏合规，D-2 switchLayout articleStyle 消费链路已闭环确认（RssSortViewModel:39-50 循环落库 → upFragments 重建 → RssArticlesFragment:61/74/92-124 重读）；ReadRssActivity 原 10 项菜单全部下沉无遗漏；RSS 域全目录 Log.d/e 零残留。**新副作用 3 处**：①`activity_rss_artivles.xml:23` 残留 `@id/title_bar` 死引用（约束属性，LinearLayout 内无害）；②`menu/rss_articles.xml`+`menu/rss_read.xml` 成孤儿资源（onCompatCreateOptionsMenu 已删零引用）；③`pref_config_theme.xml` 删除 launcherIcon 后代码侧残留（LauncherIconHelp:15/IconListPreference:138/BackupConfig:63 仍引用 change_icon）。**双语缺失 2 key**：`about_description_sigma`+`contributors_summary_sigma`（values:1518/1519 有但 values-zh 无，且中文内容错放默认 values）——疑似 D-4 图标相关未完成迁移。fragment_video.xml 5 处存量硬编码中文 contentDescription 无 tools:ignore（存量非本次）。
20. **真机+VLM 全面验证**（2026-08-15 七阶段）：接入本地视觉模型 Qwen3VL-8B（`ai_tests/scripts/ui_visual_check.py`，LlmServerManager 自动拉起/复用服务），**12 个页面全部 VLM 审查通过**——RssSourceActivity(88)、书架 BookshelfScreen(98)、我的 ProfileScreen3Level(98)、书源管理 BookSourceActivity(98)、书源编辑 BookSourceEditActivity(98)、高亮规则 HighlightRuleActivity(98)、替换净化 ReplaceRuleActivity(98)、发现页 ExploreFragment(98)、订阅 tab RssFragment(98)、阅读器正文(85)、阅读器菜单层(85)、更多菜单(85)。阅读器 85 分系 VLM 建议加常驻 TopAppBar，但沉浸式阅读器设计刻意无常驻顶栏（顶底栏按需弹出）属设计意图非缺陷。**启动验证**：composeTitle 改造 6 Activity（Cache/AudioPlay/RssSort/ReadRss/BookshelfManage/VideoPlayer）全部安全启动无崩溃（VideoPlayer 无 bookUrl 参数时 initData error→finish 属设计内行为，logcat 零 AndroidRuntime）；SourceLoginActivity 无 sourceUrl 时 error→finish 同属正常。**唯一 P0 缺陷：ConfigActivity 启动 NPE 崩溃**（D-15）——编译通过≠功能正确，真机验证不可省。

---

## 四、📋 新增子任务（已写入 tasks.md 13.1 节，供另一 AI 执行）

| 子任务 | 内容 | 优先级 | 归属 |
|--------|------|--------|------|
| D-1 | VideoPlayerActivity 存量 Log.d("VideoFS") 收敛为 AppLog.put 或删除 | P1 | 改造文件内清理 |
| D-2 | 核实并修复 rssSort 排序偏好 no-op（**RssFragment 主列表层**，管理页已消费；upRssFlowJob 接入 rssSort 排序）| P1 | Rss 页 |
| D-3 | 核实并修复 sourceLayout no-op（**RssFragment applyListView 读 sourceLayout 三态转 layoutManager**，管理页已消费）| P1 | Rss 页 |
| D-7 | SourceLoginDialog 壳层 Compose 化定案（12.25「N 不迁移」更新为「壳层化合规」，复核通过）| 已定案 | Rss 源 |
| D-8 | HighlightRuleScreen/ReplaceRuleScreen 裸 DropdownMenu→AppDropdownMenu（§3.4 菜单族门禁）| P2 | 高亮/替换页 | ✅ 已完成（2026-08-16 核码确认） |
| D-9 | 书架角标：P1 文档回填 ShelfUnreadBadge 真实实现 + BadgeDot 接线改回仅 PillNavigationBar + 硬编码色收敛（**已定案主题色 primary**，用户 2026-08-15 决策，响应 b6 需求）| P2 | 书架 | ✅ 已完成（2026-08-16 核码确认） |
| D-4 | App 图标改版：**已授权**（用户 2026-08-15 决策，保留 ic_launcher_foreground）；设计依据已补（`app-icon-design.md`），D-14 launcherIcon 残留已一并收尾 | 已定案 | 图标 | ✅ 已完成（2026-08-16，设计依据文档 + PreferKey/BackupConfig 两处清理） |
| D-5 | P2-reader.md §8 验收补登记：3s 淡出 + 滑块 alpha≤30% 预览为「P2 收尾待办」（与 reader-overlay tasks 2.4/4.2 对齐）| P2 | 阅读器 | ✅ 已完成（2026-08-16，§8:109 已登记） |
| D-6 | 16 份 light 轻量文档回填精确 task 号（audit-lightweight-docs 16 清单）| P3 | 文档 | ✅ 已完成（2026-08-16，Grep 零残留） |
| D-10 | MenuLayer 换源/更多菜单裸 DropdownMenu→AppDropdownMenu + P2 spec「更多→AppMenuSheet」描述更新为下拉（**已定案下拉菜单**，用户 2026-08-15 决策）| P2 | 阅读器 | ✅ 已完成（2026-08-16 核码确认） |
| D-11 | BookSourceScreen 裸 DropdownMenu×2→AppDropdownMenu + QuickFilterWords 英文关键词 i18n/删死代码 + BookSourceItems:287「成功」硬编码收敛 | P2 | 书源页 | ✅ 已完成（2026-08-16） |
| D-12 | MyFragment 内部类 MyPreferenceFragment 死代码清理（保留需确认无反射/ID 引用）| P3 | 我的页 | ✅ 已完成（2026-08-16，含 pref_main.xml 孤儿资源删除）|
| D-13 | PillNavigationBar 规格或文档回填（组件 08-14 已简化：tween+无胶囊，§3.4:220/P9 §3 描述滞后）| P2 | 底栏 | ✅ 已完成（2026-08-16，取「回填文档匹配代码」） |
| D-14 | 残留清理批次（2026-08-15 六阶段）：①activity_rss_artivles.xml:23 残留 `@id/title_bar` 死引用（改 compose_top_bar 或删）；②menu/rss_articles.xml+menu/rss_read.xml 孤儿资源删除；③pref_config_theme.xml 删 launcherIcon 后代码侧残留确认（LauncherIconHelp/IconListPreference/BackupConfig 仍引用 change_icon，与 D-4 图标相关）；④双语缺失 2 key（about_description_sigma/contributors_summary_sigma，values-zh 无且中文内容错放默认 values）| P3 | 清理 | ✅ ①②④ 已完成（2026-08-16），③ 待 D-4 联动 |
| D-15 | **ConfigActivity 启动 NPE 崩溃修复**（P0，2026-08-15 真机验证新增）：ConfigActivity.kt:32 属性初始化调 getString 在构造阶段抛 NPE，阻断设置/主题/备份/封面/欢迎/精准管理全部子页入口。修复：改 `mutableStateOf("")` + setTitle() 兜底（与其余 6 处一致）| P0 | 配置页 | ✅ 已修复（2026-08-15 模拟器验证） |
| D-16 | **书源管理页分组视图下 sourceLayout 网格 no-op**（P1，2026-08-15 横向扩展真机验证新增）：BookSourceScreen 分组视图（`isFolderViewMode && isShowingFolder`，即 sourceGroupStyle≠0）走 GroupedSourceList 恒 `LazyColumn`（BookSourceScreen.kt:548），layout 参数仅 :594 区分 0/1，**layout>=2 网格被忽略**；切「列表平铺」（sourceGroupStyle=0）后走 :313 三态分支网格生效（真机对照：分组视图切网格四列仍单列 → 切列表平铺后变 3 列自适应网格）。修复：GroupedSourceList 支持 layout>=2 网格（分组 header + 网格 items）或分组视图禁用网格选项 | P1 | 书源页 | ✅ 已完成（2026-08-16） |

> **D-2/D-3 真机验证证据（2026-08-15 全面测试阶段）**：RssSourceActivity 管理页已完整消费两偏好——布局设置对话框切 sourceLayout=4 后管理页单列→4 列网格（每行 4 卡片，序号 x=106/356/606/856），切回 sourceLayout=0 恢复单列列表；排序菜单切 rssSort=1（名称排序）后管理页顺序变 @91porn/牛h影视/Chentai-c/丝瓜（按名）。**但 RssFragment 订阅 tab 主列表在两偏好切换前后恒 4 列网格、顺序恒 customOrder**（sourceLayout=0+rssSort=1 下仍「一牛影视/©h牛影视/日鲍/xxxx 黑料」按行），确认 D-2/D-3 no-op 仅存于主列表层，与偏差 2/3 定位一致。
>
> **补充验证（2026-08-15 追问验证）**：管理页 rssSort 各值 + 反序全部生效——①名称排序+反序后首项变「xxxx 黑料」（正序首项 @91porn，反转正确）；②更新时间排序（rssSort=6+反序）后首项变 Papa线路(seji50.cfd)/秘密线路(ikanxm51.cfd)/桃花视频(seji51.cfd)（最近更新在前）；③是否启用排序（rssSort=2）顺序与手动不同且受反序影响（sortSources:589 `sortedByDescending { enabled }` 后 :596 `sortAscending` 反转，逻辑正确）。核码确认 sortSources():586-597 六分支全实现。

---

## 五、变更记录

- 2026-08-15：本审查报告建立（另一 AI 待提交代码 vs 设计文档一致性审查，用户指示「审查补全设计文档和子任务项，确保审查结果告知另一 AI」）。
- 2026-08-15（第二阶段）：偏差 2/3 精确定位为 RssFragment 主列表层（管理页已消费）；SourceLoginDialog 壳层化复核通过（D-7 登记）；switchLayout 部分生效且与 sourceLayout 分属两机制；VideoPlayer 两 toast 为位置移动非新增。
- 2026-08-15（第二阶段·继续核实）：新增 D-8（HighlightRuleScreen/ReplaceRuleScreen 裸 DropdownMenu）；BookshelfFragment1/2 重构合规（功能保留+零硬编码）；BookInfoActivity/ReadRssActivity 顶栏合规；ReadRss 域 5 处中文 toast 为存量。
- 2026-08-15（第三阶段）：新增 D-9（书架私有 ShelfUnreadBadge vs P1 BadgeDot 声明矛盾 + 硬编码色，含 b6 用户主题色需求冲突）；P4 formatDuring 硬编码中文为已登记遗留（V2）；BookshelfScreen/BookshelfItems 角标全仓 BadgeDot 仅 PillNavigationBar 引用。
- 2026-08-15（第四阶段）：4 并行子代理核码 32 文件（P2 阅读器族/P5 书源族/P9 主页族/Import 族+杂项）。新增 D-10（MenuLayer 裸 DropdownMenu+P2「更多→AppMenuSheet」裁决）、D-11（BookSourceScreen 裸 DropdownMenu×2+QuickFilterWords i18n+BookSourceItems「成功」）、D-12（MyFragment MyPreferenceFragment 死代码）、D-13（PillNavigationBar 规格/文档漂移）。零新增偏差确认：Import 族 8 文件统一 ImportSourceSheet、杂项 9 文件全合规、P5 applyListView 三态完整、P9 MainActivity 接线全落地。存量清理建议：CacheActivity PopupMenu 死接口+Restore 无用 import。观察项 14-17 补充。
- 2026-08-15（第五阶段）：2 并行子代理核码 11 文件（图片/音频/漫画族 4 Activity + VM/宿主族 4 Activity+3 XML）。**零新增偏差**：4 Activity 顶栏全 AppDropdownMenu（ImageGallery:231/AudioPlay:176/ReadManga 经 MangaMenu:305）、16+4 处字符串迁 strings.xml 双语齐备、3 Compose 宿主全包 LegadoTheme、HighlightRuleAdapter 删除无悬空引用。死资源 1 处（menu/image_gallery.xml 未删）。观察项 18 补充。
- 2026-08-15（第六阶段）：2 并行子代理核码 RSS 域+剩余 XML+双语。**零新增硬编码违规**（RssSortActivity/ReadRssActivity 顶栏全合规，D-2 articleStyle 消费链路闭环确认）；新副作用 3 处登记 D-14（activity_rss_artivles.xml:23 title_bar 死引用 + rss_articles/rss_read 孤儿菜单 + launcherIcon 代码侧残留）。双语缺失 2 key（about_description_sigma/contributors_summary_sigma）。观察项 19 补充。
- 2026-08-15（三待办定案）：用户决策完成——**D-4 授权新图标**（保留 ic_launcher_foreground，补设计依据）；**D-9 角标色槽取主题色 primary**（响应 b6 需求）；**D-10 菜单形态取下拉菜单**（P2 spec「更多→AppMenuSheet」描述更新为下拉）。全部已回填 audit 偏差节+子任务表+tasks.md。审查收尾，可交另一 AI 执行 D-1/D-2/D-3/D-5/D-6/D-8/D-10/D-11/D-12/D-13/D-14。
- 2026-08-15（真机+VLM 验证阶段）：接入本地视觉模型 Qwen3VL-8B（ui_visual_check.py）审查 RssSourceActivity(88)/书架(98)/我的(98) 全部通过。**真机实测发现 ConfigActivity 启动 NPE 崩溃**（P0），登记 D-15：ConfigActivity.kt:32 属性初始化调 getString 构造阶段崩溃，阻断配置页全子页。此缺陷说明**编译通过≠功能正确**，需真机验证兜底。观察项 20 补充。
