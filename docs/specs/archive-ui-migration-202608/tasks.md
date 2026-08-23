# Archive 前端 UI 迁移整合 — 任务清单（tasks.md）

> 修订 v2（2026-08-19）：基于最新 tag `archive-v3-3.26.08172114` 深度分析（rev2 五份报告）与用户调整意见重写。
> 状态标记：`- [ ]` 待办 / `- [x]` 完成（⚠️ 代码完成 / ✅ 功能验证）。编译门禁 = `./gradlew assembleAppDebug`（测试包 `io.legado.miss.app.debug`）。
> 查漏补缺（2026-08-21）：对两端 `ui/` 文件集合做差集复核，发现 Archive 有而本项目缺 55 个 UI 文件（编译门禁通过 ≠ 运行时已引用 Archive UI），补充为 §7.11（A/B/C/D 类：管理页缺失/旧实现未对齐/增强组件/全面再审查），对应 `spec.md` §Scope-12/FR-14、`design.md` §1.7 缺口总表 + §1.8 全面再审查（默认对齐 Archive 基调）。
> 子页面内部实现再审查（2026-08-21 深层）：用户指出"很多子页面仅头部 Compose 化、内置仍是 View"。逐目录比对实测本项目旧 RecyclerView/Adapter 文件 50 个（Archive 32）、旧 `lib.dialogs` 弹框文件 95 个（Archive 77），补充为 §7.11 E 类（E1 弹框/E2 列表/E3 半迁移壳/E4 特色统一外观/E5 骨架补缺，7.11aa~an2），对应 `design.md` §1.9、`spec.md` §Scope-13/FR-15，明细见 `docs/temp-analysis/archive-gap-*.md`。
> 跨任务一致性审计（2026-08-21）：修正 11 项矛盾 + 8 项悬空引用 + 发起 §9/§10/§11 联动（明细见 `docs/temp-analysis/task-consistency-audit.md`）：已回标 7.1c/7.1d（被 7.11x/7.11y 覆盖）、7.2/7.7 完成态收窄（其对应用到 7.11h/u/v + E3）；去重 7.11g/7.11o/8.9；统一完整文件名（ExploreShow/DiscoverySuite）；补 7.11an2（video/image/urlrecord 弹框）+8.11 特色入口（UrlRecord/MetricGrid/AITool）；§9.5 弹框壳层规范、§10.3 依赖 7.11w、§10.4 署名范围扩大、§11.2 以 8.12 为前置。

## 0. 前置准备
- [x] 0.1 需求分析（范围/方向/影响面/边界，含用户 4 项调整意见：阶段划分/特色功能范围/迁移基座方向/差异分析质疑）— 已完成
- [x] 0.2 获取 Rimchars/legado 最新 tag `archive-v3-3.26.08172114` 源码并解压至 `archive-ref/legado-08172114/` — 已完成
- [x] 0.3 基于最新 tag 四维度深度差异分析（后端核心/数据库/主题/UI 接口契约 + 特色接线）— 已完成，5 份 rev2 报告见 `docs/temp-analysis/`
- [x] 0.4 当前 Compose 迁移 WIP 快照分支 `test_compose_self_20260818` 提交并推送远端 — ✅ 已完成（commit 86ac9a802，53 文件）
- [x] 0.5 四文档修订 v2（README/spec/design/tasks 基于 rev2 分析 + 用户调整意见）— ✅ 已完成，**检查点 1 已通过**（用户确认：文档通过 + AI 完整搬入 + EPub 搬入 + 迁移分支确认 + 单元测试门禁）
- [x] 0.6 从 master 干净点（aa1170a08）创建迁移分支 `migration-archive-ui` 并推送远端 — ✅ 已完成（cherry-pick 设计文档 429168283 + .gitignore 忽略 archive-ref/temp-analysis 1bd1e94a0）
- [ ] 0.7 登记迁移 UI 标准基线（组件清单初版）到 `docs/project-flow/ui-standards/`

## 1. Cronet 升级（子任务 1，方案 1 `cronet-bundled` 已确认）
- [x] 1.1 确认 `500.0.1` 构件结构（`cronet` / `cronet-bundled` / `play-services-cronet` 在 Google Maven 坐标与大小）— 已完成
- [x] 1.2 确认打包策略：**方案 1 `cronet-bundled:500.0.1`（用户已确认）** — ✅
- [x] 1.3 修改 `gradle.properties`：`CronetVersion=500.0.1`、`CronetMainVersion=500.0.0.0` — 已完成
- [x] 1.4 删除 `app/cronetlib/` 本地 6 jar 与 `fileTree` 依赖，改 `cronet-bundled:500.0.1` Maven 构件 — 已完成
- [x] 1.5 适配 `app/build.gradle`（media3-datasource-cronet 排除项按新构件调整）— 已完成
- [x] 1.6 更新 `app/cronet-proguard-rules.pro`（keep 规则适配 500.0.1）— 已更新；release 正式适配验证待 Phase 末
- [x] 1.7 验证 `CronetHelper.kt`/`CronetInterceptor.kt`/`DohDns.kt` 对 500.0.1 API 兼容（编译通过；真机网络/嗅探验证推迟 Phase 末）— 编译已过
- [x] 1.8 编译 `assembleAppDebug` + 对比 APK 体积（验证减包效果；编译通过）— ✅
- [ ] 1.9 真机验证 Cronet 网络请求与视频播放/嗅探能力不退化（Phase 末集中）

## 2. 地基补齐（Phase 0，编译硬约束先行）
- [x] 2.1 `gradle/libs.versions.toml` 新增 4 个 Compose 生态依赖：miuix 0.8.8 / reorderable 3.1.0 / LazyColumnScrollbar 2.2.0 / liquidglass 1.0.3 — 已完成
- [ ] 2.2 composeBom 对齐 ARCHIVE 版本（2025.10.00，评估与现有代码兼容性）— **暂缓**：当前保持 2025.04.01（bump 需评估对存量 Compose 代码兼容性，避免回归）
- [x] 2.3 复制 `utils/SearchBookMergeUtils.kt`（从 ARCHIVE，ExploreShow 结果合并去重）— 已落地
- [x] 2.4 复制 `ui/video/VideoBookPreloader.kt`（从 ARCHIVE，SearchViewModel 依赖）— 已落地
- [x] 2.5 `help/webView/WebViewPool.kt` 补 `Scope` 枚举（GLOBAL/DISCOVERY/RSS）— 已落地
- [x] 2.6 `model/webBook/WebBook.kt` `exploreBook/exploreBookAwait` 补 `webViewPoolScope`/`shouldBreak` 参数 — 已落地
- [x] 2.7 编译门禁 `assembleAppDebug` 通过 — 已通过（各 Phase 编译门禁均验证）

## 3. 后端支撑搬入（Phase 1）
- [x] 3.1 `model/ReadBook.kt` 补 10 个新方法（reloadCurrentContent / invalidateParagraphRuleLayout / refreshCurrentParagraphRuleResult / invalidateEpubResource / markRecentRead / markReadAloudUserNavigation / stopReadAloudForBookSwitch / clearLastBookProgress / relayoutCurrentContent / upToc 同步）与 5 方法加参（moveToNextPage/moveToPrevPage/skipToPage/setPageIndex/saveRead/contentLoadFinish）— P1 完成
- [x] 3.2 `data/dao/BookDao.kt` 补 `flowShelf*`/`BookShelfDisplay`/`BookShelfIdentity`/`getDisplayInfosByUrls` 系列（书架/订阅/发现列表数据源）— P1 完成
- [x] 3.3 搬入 `help/AppCloudStorage.kt` + `lib/cloud/`（云存储抽象，被 ReadBookViewModel 等 20 文件引用）— P1 完成
- [x] 3.4 搬入 EPub Core 引擎 `model/localBook/epubcore/`（16 文件）+ `EpubBox/EpubLayoutEngine` 系列（**用户已确认搬入**，随 Archive 阅读页 UI 完整接入）— P1-D 完成
- [x] 3.5 搬入 `model/MediaTocRefresh.kt`、`ParagraphBubbleRenderer.kt` — P1-D 完成
- [x] 3.6 搬入 `help/config/` 新类（AppearanceKitManager/TopBarConfig/MainBottomNavConfig/NavigationBarIconConfig 等，随 UI 引用）— P1-E 完成
- [x] 3.7 搬入 **AI 全量业务后端** `help/ai/*`（AI 助手 / AI 记忆 / AI Agent / AI 绘图 / 角色 / 朗读 BGM / 段落规则，**用户已确认完整搬入，不做裁剪**）— P1-F 完成
- [x] 3.8 编译门禁 `assembleAppDebug` 通过 — 已通过
- [x] 3.9 单元测试门禁：`ReadBook` 新方法 / `WebBook.exploreBook` 新参数 / `BookDao.flowShelf*`（Room in-memory）单测通过 — P1-G 已过（181/186，5 项 AnalyzeRuleTest 为既有环境问题与本次无关，补跑待登记）；**✅ 2026-08-21 补跑 `./gradlew test` 9m32s：186 完成/181 通过/5 项 AnalyzeRuleTest 失败=既有 Android 环境 JVM mock 问题（AppConfig 初始化 / LruCache not mocked），与 P1-G 基线一致无回归**

## 4. 主题系统整合（Phase 2）
- [x] 4.1 升级 `help/config/ThemeConfig.kt` 为 32 字段（含 AtomicTextFileStore 原子写 + configSnapshot 缓存 + 背景图安全校验 + 字体-表面撞色守卫）
- [x] 4.2 新增 `constant/PreferKey.kt` ~50 个主题 key（日夜双键）
- [x] 4.3 搬入 `lib/theme/ThemeRuntimeKeys.kt` + 执行一次性夜间迁移 `migrateLegacyNightValues`（App.attachBaseContext 钩子）
- [x] 4.4 搬入 `lib/theme` 六件套：ThemeUiPalette / UiCorner / ComposeUiCorner / UiTypography / LegadoComposeTheme / TopBarSearchStyle
- [x] 4.5 搬入 `ui/widget/compose/ComposeThemeImageLayer.kt`、`AppUiTokens.kt`
- [x] 4.6 搬入 `help/config/ThemePackageManager.kt`、`AppearanceKitManager.kt`（主题包/外观套件子系统）
- [x] 4.7 统一 `themeMode` 默认值语义：**跟随 Archive（"0"跟随系统，用户已确认）**
- [x] 4.8 搬入 `ui/config/ThemeManageActivity.kt`、`AppearanceKitActivity.kt`、`ui/config/compose/ComposeSettingFragment.kt`、`lib/prefs/fragment/ComposePreferenceScreen.kt`
- [x] 4.9 保留 OURS `ThemeSync`/`LegadoTheme` 驱动存量页面，验证两套 Compose 主题共存
- [x] 4.10 编译门禁 `assembleAppDebug` 通过（纵深连带搬入 WebDavTask*、ImageCrop 链、PackageSyncTaskDialog 等编译依赖后 BUILD SUCCESSFUL）
- [ ] 4.11 主题切换/日夜间/背景图真机验证

## 5. 数据库实体合并（Phase 3）
> 实际落地：Phase 1（P1-B/P1-F）已完成实体+DAO+迁移的搬入，最终版本 **v106**（104→105 建 6 表；105→106 建 19 表含 2 张 FTS4）。与原计划"v104→v108 五批迁移"有差异：P1-F 一次性合并了 AI 绘图/角色/摘要/朗读 BGM/朗读发言人/AI Agent/AI 记忆等全部子表。本阶段做一致性校验 + 编译门禁收尾。
- [x] 5.1 盘点 Archive 25 独有实体 + 14 DAO 清单（参照 rev2-sa2 报告）— 已确认全部注册
- [x] 5.2 搬入 Archive 25 实体 + DAO 到 `data/entities` / `data/dao`（含 2 个 FTS4 实体 AiMemoryItemFts/AiMemoryFragmentFts）— 已在 P1 完成
- [x] 5.3 保留 OURS 9 特色实体（BookHighlight/CoverGallery*/PlayHistory/ReadRecordDetail/SourceRecycleBin/UrlRecord/AutoTaskRule/SourceGroupCover）— v106 全部保留
- [x] 5.4 `AppDatabase.kt` 迁移链：104→105（6 表）+ 105→106（19 表含 AI Agent/记忆/绘图/角色/摘要/朗读语音与 2 FTS4）— 已在 DatabaseMigrations.kt 实现并注册
- [x] 5.5 FTS4 虚拟表手动 `CREATE VIRTUAL TABLE`（ai_memory_items_fts / ai_memory_fragments_fts）— runCatchingSql 包裹
- [x] 5.6 生成 schema 快照：105.json / 106.json 已在 `app/schemas/`
- [ ] 5.7 覆盖安装回归：旧库（v104 含特色数据）→ 新库（v106）不崩溃、数据保留（真机，Phase 末集中做，已按用户要求跳过当前）
- [x] 5.8 编译门禁 `assembleAppDebug` 通过（迁移 SQL ↔ 25 实体 + HttpTTS + FTS4 schema 一致性校验无差异；BUILD SUCCESSFUL 5m36s）

## 6. UI 基建搬入（Phase 4）
> 实际落地：`ui/widget/compose` 20 个组件文件已在 P1-E/P1-F/Phase 2 纵深连带搬入时全部落盘，与 Archive 目录逐文件镜像（L 核对两目录完全一致）＋多轮 assembleAppDebug 编译通过。本阶段做存在性核验 + R.color 兜底色核对 + 编译门禁收尾。
- [x] 6.1 搬入 `ui/widget/compose/*` 全量组件库（AppManagementScaffold/ComposeDialogFragment/AppComposeDialogs/AppSettingComponents/ComposeFastScroller/LegadoComposeTheme/ComposeViewOwners/BookCoverImage/SearchBookListItem/LegadoMiuixComponents 等）— 20 文件已全部落盘，与 Archive 逐文件一致
- [x] 6.2 核对 R.color 兜底色资源（background_card/background_menu/bg_divider_line 等）是否存在，缺失补齐 — 均存在（colors.xml）
- [x] 6.3 编译门禁 `assembleAppDebug` 通过（77 up-to-date 51s BUILD SUCCESSFUL）— ✅

## 7. 核心页面逐模块替换（Phase 5）
- [x] 7.1 管理页先行：书源管理 / 订阅源管理 / 配置页 / 主题管理替换为 Archive 版 — ✅ 完成
  - 7.1a 书源管理 `BookSourceActivity`：Archive 版覆盖（Activity/Screen/GroupManageDialog/ViewModel），删 4 个自研 adapter（BookSourceAdapter/Compact/Grid/Items），补 `select_action_bar` PopupMenu 签名适配（改类实现接口）、`DirectLinkUpload.getExpiryDate()`（返回0=永久，对齐 Archive 默认）、`activity_book_source.xml` 布局、`AnimDialogFade`+dialog_fade enter/exit、`ShibbolethCodec`+`showShibbolethDialog`+`rss_source`菜单等资源 — 编译过（assembleAppDebug BUILD SUCCESSFUL）
  - 7.1b 订阅源管理 `RssSourceActivity`：Archive 版覆盖（+新增 RssSourceScreen/升级 Compose GroupManageDialog），删 3 自研 adapter（RssSourceAdapter/Compact/Grid）+RssSourceSort，补 RssSourceDao.upOrder 两种方法、`rss_source` 菜单、PopupMenu 签名适配 — 编译过
  - 7.1c 配置页 `ConfigActivity`：保留当前更先进 GlassTopAppBar 顶栏（不回退 Archive 顶栏），补 `ConfigTag.DISCOVERY/DISCOVERY_SUBSCRIPTION/SUBSCRIPTION_CONFIG` + 分支 + 3 个 Compose 子页 Fragment（Discovery/DiscoverySubscription/SubscriptionConfigFragment）+ res 资源（34 条）；**AiConfigFragment 及其 AI 管理 Activity 推迟到 7.8**（依赖 AiImageGallery/AiProviderManage 等 AI UI 未就绪）— 编译通过；**因用户对齐 Archive 要求，7.11x 已覆盖本行顶栏决策（回退 ConfigTopBar+MenuProvider），本项顶栏以 7.11x 为准**
  - 7.1d 主题管理 `ThemeManageActivity`：两版**字节级一致**，无操作；当前 ThemeConfigScreen（色板/背景下载/即时换肤）为更先进自研特色，本项原定"不回退 Archive 简单 DSL 版（Archive 会引入 6 处缺失）"— 已完成；**因用户对齐 Archive 要求，7.11y 已覆盖本项决策（ThemeConfigScreen 改 Archive ComposeSettingFragment），最终形态以 7.11y 为准**
- [x] 7.2 主界面替换：MainActivity（可配置底部导航）/ 书架（style1/2 + compose）/ 发现（含现代发现套件）/ 我的 / 订阅 / 阅读记录 — ✅ 编译+打包通过（assembleAppDebug BUILD SUCCESSFUL）**；仅骨架/壳层替换完成，现代发现套件（7.11h）·我的页（7.11u）·头部顶栏（7.11v）对齐归档 7.11，此 7.2 完成态不代表已对齐 Archive 实际页面**
  - 7.2a `MainActivity`+`activity_main.xml`：Archive 版整体覆盖（可配置底部导航/侧滑/顶栏状态栏沉浸适配/AI 悬浮球）。补 `LockableViewPager`、`ActivityExtensions.isHuaweiSystemDevice`+`setHuaweiDisplayCutoutShortEdgesCompat`、`ContextExtensions.clearClip`、`EventBus.NAVIGATION_BAR_CHANGED/TOP_BAR_CHANGED`、ViewExtensions 系工具、主题/更新工具函数；`RssFragment.gotoTop()`、`BookshelfFragment1/2.switchToGroupId()`
  - 7.2b 书详情 `BookInfoComposeActivity`（7.5 前置）：Archive 覆盖整套 `ui/book/info/*`（Navigator/ComposeRoute/ViewModel/Edit），补 `BookCloudEntryMode/Store`（help/book）、`book_info_*` 字符串、`book_info_useweb_popup_host` id；移除对项目缺失的 `CacheManageActivity` 音频缓存页依赖（云端备份改为仅设模式，对偶 onOpenLibraryContainer）
  - 7.2c AI 聊天页 `ui/main/ai/*`（7.8 前置）：Archive 整包搬入（AiChatActivity/AiChatViewModel/speech/imagemarkdown/compose 等），补 `AnalyzeUrl` 语音参数+evalJS/getResponseAwait/getErrResponse、`AI_CONFIG`/`AI_CONFIG_CHANGED`/`EXTRA_PREPARE_BOOK_INFO` 常量、角色管理页（BookCharacter*+compose）、`SpeechVoiceRoutePicker`（语音路由选择弹窗）、mawkwon markdown 插件（strikethrough/tasklist/linkify）、4 个 AI 布局+ai_* 字符串+`ic_close_x`
  - 7.2d 阅读记录：Archive 版 `activity_read_record.xml` 组件化面板布局 + `ReadRecordComponents/WidgetUi/OverviewCard/ConfigDialog` 覆盖 + `ReadHeatmapView`，配套 `applyMainBottomBarPadding`/`applyModernWindowStyle`/`StatusBarInsetAware`；`ReadRecordActivity` 作 Compose 壳层（composeHost）与 Fragment 共用绑定
- [x] 7.3 书源相关：书源列表 / 编辑 / 调试 / 分组替换 — ✅ 编译+打包通过（assembleAppDebug BUILD SUCCESSFUL）
  - 7.3a 书源列表：7.1a 已完成（manage/BookSourceActivity Archive 版可配置多源列表/分组/批量/排序）
  - 7.3b 书源编辑 `BookSourceEditActivity`：Archive 标准 TabLayout 版覆盖（6 Tab + RecyclerView + 单行规则项），连带 `activity_book_source_edit.xml`、`source_edit.xml` 菜单；**保留本项目"书源 URL 迁移书架"数据安全特性**（bookDao.hasBookByOrigin/updateOrigin + migrate_book_origin_* 字符串已回填，5 处保存入口统一走 saveSource()）
  - 7.3c 书源调试 `BookSourceDebugActivity`：Archive 版覆盖（TitleBar+SearchView+menu），连带 `activity_source_debug.xml`、`book_source_debug.xml` 菜单；分组插入走 `alertGroups()` selector（self-contained）
  - 7.3d BookSourceEditAdapter/ViewModel、BookSourceDebugAdapter/Model：与 Archive 一致，无需变更；无废弃自研独立文件需删
- [x] 7.4 搜索相关：搜索页 / 结果页（SearchResultScreen）/ 搜索范围替换 — ✅ 编译+打包通过（assembleAppDebug BUILD SUCCESSFUL）
  - 7.4a 搜索页 `SearchActivity`：Archive 完整 Compose 版覆盖（SearchView 顶栏 + Compose 结果列表 + Compose 输入帮助），沿用 `SearchBookOpenHelper` 打开书籍/视频；`activity_book_search.xml`、`book_search.xml` 菜单替换；历史 DAO 调用补 `type=0` 适配
  - 7.4b `SearchViewModel`：以目标为基底合并 Archive 的 `VideoBookPreloader` 视频封面预载增强；**保留本项目搜索历史 type 区分**（书源=0/订阅源=1）
  - 7.4c 结果页 `SearchResultScreen`、输入帮助 `SearchInputHelpScreen`：**新增**（Archive 版）
  - 7.4d 搜索范围：`SearchScope` 补 `getSingleBookSourcePart()`；`SearchScopeDialog` 覆盖为 Archive Compose 版
  - 7.4e 遗留：旧 `BookAdapter/HistoryKeyAdapter/SearchAdapter` 现无引用（Archive Activity 不再用），暂留死代码，Phase 7.10 清理
- [x] 7.5 详情/目录：BookInfoComposeActivity / TocComposeScreen 替换 — ✅ 编译+打包通过（assembleAppDebug BUILD SUCCESSFUL）
  - 7.5a 书详情 `ui/book/info/*`：**7.2b 前置已搬入**（BookInfoComposeActivity/ViewModel/UseWebHost/Navigator/Activity，与 Archive 文件集合一致）
  - 7.5b 目录 `toc`：Archive 纯 Compose 版替换（TocComposeScreen 新增 + TocActivity 改容器型 + TocViewModel 改精简型 + activity_chapter_list.xml 改纯 ComposeView）
  - 7.5c `isChapterCached`：Archive 对 `ExoPlayerHelper.isMediaCached`/`BookHelp.getChapterCacheFileNames` 的依赖改写为当前项目 API（音频/图片降级 cacheFileNames.contains，文本用 BookHelp.hasContent）；保留 item_chapter_list（换源 ChangeChapterTocAdapter 复用）
  - 7.5d 清理废弃：ChapterList/Bookmark/Highlight 六类 Fragment+Adapter 删除 + 孤儿布局（fragment_chapter_list/fragment_bookmark/item_bookmark/item_highlight）删除；TocActivityResult 保留（被详情/音频/阅读/漫画/视频多处调用）
  - 7.5e 遗留：Archive 的 `TxtTocRuleEditComposeDialog`（规则 Compose 对话框增强）未搬入，当前 TxtTocRuleActivity 用旧版 EditDialog 已编译闭合，**归 7.11af 统一搬入**
- [x] 7.6 阅读页：BaseReadBookActivity / ReadBookActivity 按 Archive 版替换（含 **EPub Core 引擎接入，用户已确认搬入**）— ✅ 编译+打包通过（assembleAppDebug BUILD SUCCESSFUL）
  - 7.6a read/ 目录整包覆盖 Archive 版（100 文件哈希对齐）：BaseReadBookActivity/ReadBookActivity/ReadBookViewModel/ReadMenu/SearchMenu/TextActionMenu + config/ 全部对话框 + page/(api/delegate/entities/provider/epub) 分页引擎，含 EPubReadView
  - 7.6b 漫画同步 Archive：ReadMangaActivity/ReadMangaViewModel 替换 + view_manga_menu.xml 布局对齐（工具栏/翻页/更换书源/目录/刷新）
  - 7.6c 高级标题管理页补齐：AdvancedTitleManageScreen（Compose）新增 + utils 相关 readBytes 重载 + manga_config/advanced_title_* strings
  - 7.6d 遗留：P0 高亮体系（Highlight*/ReaderUiState 等 13 文件）为 OURS 定制保留，Archive 版阅读页不引用，后续评估回写
- [x] 7.7 其余页面：缓存 / 下载 / 备份 / 我的信息 — ✅ 部分对齐（仅 Cache/Download/MyFragment 壳与 Archive 共享组件库，编译门禁通过）
  - 7.7a 现状核实：缓存（CacheActivity Compose 顶栏 + B11 分项统计 + B12 并发率）、下载（DownloadManageScreen 全 Compose + Tab 聚合轮询）、备份（BackupConfigFragment 接入 ConfigActivity setTopBarMenu，见 **7.11al 纠正：实际为纯 PreferenceFragment 未 Compose 化**）
  - 7.7b 决策：不盲覆盖 Archive（避免回退丢失 OURS 缓存分项统计/并发率、下载 Tab 聚合等增强）；该类模块以"对齐组件库 + 编译闭合"为目标；**备份 BackupConfigFragment/OtherConfigFragment 已归 7.11 E3（7.11al）升级 ComposeSettingFragment**
  - 7.7c 编译门禁：assembleAppDebug BUILD SUCCESSFUL（2026-08-21）
- [x] 7.8 AI UI 页面完整搬入 — ✅ 已搬入（compileAppDebugKotlin BUILD SUCCESSFUL，2026-08-21）
  - 7.8a config 系 AI 页全量落盘：AiConfigFragment / AiProviderEdit(+AiProviderEditScreen) / AiProviderManage / AiImageProviderEdit(+Screen) / AiImageProviderManage / AiWorldBookManage（与 help/ai/* 业务打通的配置入口）；辅助 management 页（AiImageGallery、character、朗读 BGM/段落规则管理页等）均已于前序 P1-F 后端接线时连带搬入
  - 7.8b 本次补齐编译残留：FileManageActivity EXTRA_ROOT_PATH/EXTRA_TITLE 常量 + onActivityCreated 读取经 setRoot 应用（openAiWorkspace 依赖）、FileManageViewModel rootDoc 改 var + setRoot（对齐 Archive）、AppComposeDialogs ComposeFetchedModelDialog 完整实现（此前为裁剪注释占位，依赖 ui/config.FetchedModelSelectorContent 已就位）
  - 7.8c 编译门禁：compileAppDebugKotlin BUILD SUCCESSFUL（2026-08-21），主代理直接执行（不再委派机械迁移子代理）
- [x] 7.9 每模块编译门禁 + 冒烟验证 — ✅ 完成（逐模块标记）
  - 2026-08-21 已清理根目录临时构建日志（16 个）+ 核对 git diff 无矛盾态/无残留调试日志 + compileAppDebugKotlin BUILD SUCCESSFUL
  - **4.11 主题真机冒烟完成**（测试包 io.legado.miss.app.debug，MEmu 127.0.0.1:21503）：① 主题设置页两种入口均正常导航进入（直接 intent `ConfigActivity` + `configTag=themeConfig`、真实导航"我的→主题设置"）；② 主题列表正常渲染（默认/典雅蓝/黑白/A屏黑/绿意/莫兰迪/海洋/薰衣草/琥珀/暗夜绿/蓝/紫/护眼绿/黄/牛皮纸/暗夜护眼/墨绿 + 剪贴板导入）；③ 切换"黑白"主题即时生效且无崩溃；④ 日/夜分组色板齐全（白天/夜间各含主色调/强调色/背景色/底栏色，"夜间（当前）"标识正确识别当前日夜态）；⑤ 背景图片/背景图片虚化/选择图片入口存在，点击无崩溃；⑥ 沉浸式操作栏/状态栏/导航栏设置齐全；⑦ 全程 logcat 无 FATAL/AndroidRuntime 异常
  - 遗留（非阻塞）：夜间"模式切换动作"（跟随系统/手动切）未在本轮做单独动作级验证，已在主题页正确反映当前日夜态；Cronet 真实 HTTPS 正向数据受模拟器网络限制采集不完整（见 §1.9，标记待公网复核）
- [ ] 7.10 清理本项目废弃 XML 资源与废弃自研 Compose 壳层（被 Archive 版替代的）
- [ ] 7.11 **查漏补缺：Archive 未搬入 UI 复核（2026-08-21 新增，基于两端 ui/ 文件清单差集：Archive 550 个 UI 文件 / 本项目 673 个，Archive 有而本项目缺 55 个）**
  - 背景：Phase 5 各模块编译门禁通过＝"能编译"，但运行时大量子页面/管理入口仍是本项目自研或缺失，未真正引用 Archive UI。以下按 **A/B/C/D（+E）类**罗列，均为"Archive 有"而本项目缺/未对齐，需逐项判定【搬入 Archive 版 / 本项目增强保留 / 缺口需补功能】。
  - **A-1 类：Archive 完整管理页缺失（后端已搬/函数已就位，但 UI 管理 Activity 没搬，无入口）**
    - [x] 7.11a 云存储容器管理：`config/LibraryContainerManageActivity`+`Screen`（后端 `help/book/library/*` 已搬）；`config/S3ContainerManageActivity`+`Screen`（后端 `lib/cloud/S3*` 已搬）→ 无 UI 无法配置容器
    - [x] 7.11b 封面图库管理：`config/CoverCollectionManageActivity`+`Screen`+`CoverCollectionDetailActivity`（后端 `help/config/CoverCollectionManager` 已搬）
    - [x] 7.11c 书籍信息管理：`config/BookInfoManageActivity`+`Screen`
    - [x] 7.11d 导航栏管理：`config/NavigationBarManageActivity`（MainActivity 可配置 5 tab 依赖此管理页）
    - [x] 7.11e 顶栏管理/编辑：`config/TopBarManageActivity`+`TopBarEditDialog`（配合已搬 `help/config/TopBarConfig`）
    - [x] 7.11f 中转设置：`config/RelaySettingsActivity`
    - [x] 7.11g 在线导入对话框：`config/PackageManageUi`（已落盘，编译可达）；`ComposeDirectLinkUploadDialog` 迁移归 **E1 7.11ad**（此处不再双列）
  - **A-2 类：功能模块整体缺失（无任何等价入口）**
    - [x] 7.11h 现代发现套件：`main/explore/DiscoverySuiteManageActivity`+`DiscoverySuiteHomeScreen`+`DiscoverySuiteConfig`+`DiscoveryCachePolicy`+`DiscoverTagAdapter`+`ExploreModernListScreen`（tasks §7.2 声言的"发现含现代发现套件"未真正落地）；`widget/WaterfallCardMetrics` 瀑布流组件同批（唯一搬入 owner）
    - [x] 7.11i 书架标签管理：`main/bookshelf/BookshelfTagManageActivity`+`Screen`+`BookshelfConfigDialog`
    - [x] 7.11j 我的设置聚合屏：`main/my/MySettingsScreen`
    - [x] 7.11k 在线导入/协议导入体系：`association/OnlineImportDownloader`+`OnlinePackageImportRoute`+`ImportDialogComponents`+`ImportRedThemeDialog`+`ImportResponseLimits`+`ParagraphRuleOnlineImportDialog`+`ParagraphRulePackageImporter/Parser/Models`（本项目仅 `VerificationCodeDialog`，协议/主题包在线导入缺失）
    - [x] 7.11l 关于页：`about/AboutFragment`+`UpdateAcceleratorDialog`（本项目 `about/AboutScreen` 为自研 Compose）→ **最终决策见 7.11w（回退 Archive）**
  - **B 类：Archive 有 Compose 新版，本项目仍为旧 View/自研未对齐**
    - [x] 7.11m 规则订阅：Archive `rss/subscription/RuleSubScreen`+`RuleSubEditComposeDialog`；本项目仍 `RuleSubActivity`+旧 `RuleSubAdapter`（即 task 8.9 未做，已复核确认为旧版）
    - [x] 7.11n 详情 ExploreShow：Archive `book/explore/ExploreShowComposeScreen`+`ExploreShowBookCallback`+`ExploreShowWaterfallAdapter`；本项目自研 `ExploreShowScreen`
    - [x] 7.11o 目录规则：Archive `book/toc/rule/TxtTocRuleEditComposeDialog`（task 7.5e 已标记，确认未补）→ **并入 7.11af 统一实施**
    - [x] 7.11p 换源对话框：`book/changesource/ChangeSourceDialogTheme`
    - [ ] 7.11q RSS 文章搜索：Archive `rss/article/RssSearchActivity`（与本项目特色 `ui/rss/search/RssSearchActivity` 属两套，需判别是否并入）
  - **C 类：Archive 增强组件/适配器缺失（供引用/增强，作用域复核）**
    - [ ] 7.11r 书籍导入：`book/import/local/ImportBookAdapter`+`remote/RemoteBookAdapter`（与本项目 `ImportBookScreen` 判别）
    - [x] 7.11s 音频缓存增强：`book/cache/AudioCacheActionReceiver`+`AudioCachePackage`+`AudioCacheTaskManager`+`CacheChapterAdapter`+`CacheChapterDialog`+`CacheManageActivity`+`CacheManageAdapter`（本项目 `CacheActivity` 为增强 Compose 替代，评估是否仍需 Archive 音频缓存任务管理；`CacheManageActivity` 作为 7.11u 我的页依赖的缓存管理入口，本项为唯一落点）
    - [x] 7.11t 组件：`widget/SourceSelectDialog`
  - **C 类登记说明（最终补漏核验 2026-08-21，明细见 docs/temp-analysis/archive-gap-final.md）：**Archive 独有 UI 文件全集 55 项逐项对照 A/B/C/D/E 全部命中，无实质遗漏；`book/changecover/`（两端 3 文件同名已对齐）/`MySettingsScreen` 依赖入口缓存管理均已覆盖，此处仅为登记完整性说明，不再新增条目。
  - **D 类：全面再审查（2026-08-21 用户定调"除本项目特有功能外完全对齐 Archive"，详见 design §1.8）**
    - [x] 7.11u 「我的」页回退 Archive：`MyFragment`+`MySettingsScreen`（搜索栏+内容/外观/同步/工具 4 分组+themeMode 快速切换+webService 弹窗），删/停用自研 `ProfileScreen3Level`（**纠正 7.7a「我的信息已对齐」表述**）；**显式补齐用户点名的五大入口**：订阅源管理（RssSourceActivity）→ 应用主题（ThemeConfigScreen）→ 界面设置（ConfigActivity）→ AI 设置（AiConfigFragment）→ 设置（ConfigActivity），并同步补依赖页 `CacheManageActivity`（缓存管理，1.1s 为唯一落点）/`RelaySettingsActivity`（网络中转，7.11f）/`FileManageActivity`（文件管理）；每入口到达后真机核对可跳转（⚠️ 骨架+入口代码均落地，含 2026-08-22 补的特色入口高亮/UrlRecord/RSS全局搜索；真机跳转核对待 §11 全量测试）
    - [x] 7.11v 头部布局对齐 Archive：书架/订阅/发现三 tab 顶栏改用 `MainTopBarView(Mode.{BOOKSHELF,DISCOVERY,RSS})`（书架/订阅置顶分组标签栏、订阅搜索/星标/刷新/登录常驻按钮），删除各 Fragment 自研 `GlassTopAppBar` 顶栏；现代发现 `ExploreModernListScreen`/`DiscoverySuiteHomeScreen` 接入以 **7.11h** 为唯一搬入 source（此处不重复搬入措辞，仅接线）
    - [x] 7.11w 关于页回退 Archive：`AboutScreen` → `AboutFragment`（继承 ComposeSettingFragment，含内测/更新加速入口）
    - [x] 7.11x 配置页顶栏回退 Archive：`GlassTopAppBar` → 专有 `ConfigTopBar` + `MenuProvider` 菜单机制（**纠正/覆盖 7.1c「保留更先进 GlassTopAppBar 不回退」决策**，按用户现要求对齐 Archive 顶栏，避免 7.1c/7.11x 自相矛盾）
    - [x] 7.11y 主题配置页改 Archive：保留 `ThemeManageActivity`（两端同构）；`ThemeConfigScreen` 自研 → `ComposeSettingFragment`/`SettingPageSpec` 声明式组件库（**纠正/覆盖 7.1d「不回退 Archive」决策**，最终形态以此项为准）
    - [x] 7.11z 清理书架旧死适配器：`style1/2/BooksAdapter*`+`BooksFragment`（旧 RecyclerView，已无运行时引用）
  - **E 类：子页面内部实现再审查（2026-08-21 深层审查，用户指出"很多子页面仅头部 Compose 化、内置仍是 View"；对应 `design.md` §1.9，明细见 `docs/temp-analysis/archive-gap-*.md`）**
    - **E1 弹框层对齐 Archive（旧 `BaseDialogFragment`/`lib.dialogs` → `ComposeDialogFragment`）**
    - [x] 7.11aa 分组弹框：`book/group/GroupEditDialog`+`GroupSelectDialog`+`book/group/GroupManageDialog` + `replace/GroupManageDialog` → Compose（复用 `GroupManageComposeDialog`）
    - [x] 7.11ab 导入弹框：association `ImportBookSource/ImportDictRule/ImportHttpTts/ImportReplaceRule/ImportRssSource/ImportTheme/ImportTxtTocRule`（7 个）+`OnLineImportActivity` → Compose（配套 7.11k 在线导入体系）
    - [x] 7.11ac 阅读相关弹框：`manga/config/MangaColorFilterDialog`+`MangaEpaperDialog`+`MangaFooterSettingDialog`、`import/remote/ServerConfigDialog`、`bookmark/BookmarkDialog`、`audio/config/AudioSkipCredits` → Compose
    - [x] 7.11ad 配置/字典弹框：`config/CheckSourceConfig`+`CoverRuleConfigDialog`+`DirectLinkUploadConfig`、`dict/rule/DictRuleEditDialog` → Compose
    - [x] 7.11ae 关于弹框：`about/UpdateDialog` → Compose；补 `UpdateAcceleratorDialog`（含于 7.11l）
    - [x] 7.11af 目录规则弹框：补 `toc/rule/TxtTocRuleEditComposeDialog`（替代旧 `TxtTocRuleEditDialog`）
    - **E2 列表/主内容对齐 Archive（旧 `RecyclerView`/`Adapter` → `LazyColumn`/`AppManagementScaffold`）**
    - [x] 7.11ag `replace/ReplaceRuleActivity` 列表 → `AppManagementScaffold` 全 Compose；删 `ReplaceRuleAdapter` 死代码
    - [x] 7.11ah `book/search/SearchActivity` 结果列表去除残留 `RecyclerView`+`SearchAdapter`+`AlertDialog` 段；清理 `BookAdapter`/`HistoryKeyAdapter` 死代码
    - [ ] 7.11ai `book/cache/CacheActivity` 去除残留旧 `RecyclerView`/`AlertDialog` 段
    - [ ] 7.11aj `explore/ExploreFragment` 主列表接入现代/套件模式（并入 7.11h，唯一搬入 owner 于 7.11h）
    - **E3 半迁移壳层升级（`Fragment` 壳 → `ComposeSettingFragment`）**
    - [x] 7.11ak config `CoverConfigFragment`/`ThemeConfigFragment`/`WelcomeConfigFragment` 升 `ComposeSettingFragment`
    - [ ] 7.11al config `BackupConfigFragment`/`OtherConfigFragment`（纯 `PreferenceFragment`，差异最大）→ `ComposeSettingFragment`（**纠正 7.7a「备份已对齐」表述：实测 OtherConfigFragment 已升 ComposeSettingFragment，BackupConfigFragment 仍为 PreferenceFragment 未 Compose 化**）
    - **E4 特色功能旧弹框统一外观（功能保留，仅升级组件库）**
    - [x] 7.11am `highlight/` 旧弹框（GroupManage/Edit/PresetRule）→ `GroupManageComposeDialog`/`AppEditDialog`
    - [ ] 7.11an `autoTask/`（AutoTaskLogDialog/ImportAutoTaskDialog）+`widget/dialog/TextListDialog`+`config/CheckRssSourceConfig` 统一外观
    - [ ] 7.11an2 `video/`（播放器内部旧弹框）+`image/`（图片浏览旧弹框）+`urlrecord/`（访问记录旧弹框）→ 统一到 widget/components（8.1/8.4 标注的落点）
    - **E5 骨架/弹框补缺（Archive 有 Compose 版本项目缺）**
    - [x] 7.11ao 补 `bookshelf/BookshelfConfigDialog` 替换 `BaseBookshelfFragment` 旧弹框
    - [x] 7.11ap 作用域复核：`widget/SourceSelectDialog`（并入 7.11t）；`widget/WaterfallCardMetrics`（并入 7.11h 瀑布流批）
  - 门禁：A/B/D/E 类每项补完 = 编译 `assembleAppDebug` + 运行可达性核对（入口能打开该管理页/顶栏/弹框正常）；A 类"后端已搬仅缺 UI"、D 类「我的页」、E1 弹框优先，可批量并行。**C 类（7.11r/s/t）为"作用域复核判定项"，需先判别再定搬入/保留，不单独设编译门禁，与 B/E 类判定位区分。**

## 8. 特色功能整合（Phase 6，P0/P1/P2 分级）
> **2026-08-21 联动修订（因任务 7 查漏补缺新增而调整）**：任务 7 的 D 类（我的页/头部/关于/配置回退 Archive）与 E 类（弹框/子页面统一外观）会置换大量 UI 骨架，特色功能接线点必须**重新注入 Archive Compose 壳**，否则回退会丢特色入口。本阶段修订要点：
> - **重叠去重**：8.9「RuleSub 用 Archive 版」与 7.11m（规则订阅 RuleSub→RuleSubScreen）**重复**，RuleSub 主体已归 7.11m，8.9 仅保留分组封面适配
> - **依赖衔接**：8.5 全局搜索入口依赖 7.11v 订阅顶栏对齐；8.6 分组入口依赖 7.11a-p 管理页 + 7.11v 顶栏；8.1/8.4 特色弹框外观统一归 7.11 E4
> - **新增 8.11/8.12**：特色入口 Archive 壳再注入 + 接线点回归验证
- [ ] 8.1 **P0 视频播放器**：保留 `ui/video/*`（11 文件）+ `model/VideoPlay` 增强版 + `help/video` + `help/exoplayer` 增强层（✅ 全部保留，2026-08-22 核实）；`model/VideoPlay` 合并 ARCHIVE `chapterLinkCache` 预加载优化；接入 Archive 组件库统一外观（内部旧弹框统一走 7.11 E4/widget/compose）— 保留完成，外观统一待 7.11an2
- [ ] 8.2 P0 视频滑动切换链路真机验证（上下滑动切换下一内容 + 自动加载下一页 + WebView 降级触摸拦截）
- [ ] 8.3 P0 前置嗅探链路真机验证（JS 覆写 fetch/XHR + WebView 拦截 + MIME 嗅探 + M3U8/HLS 加固）
- [ ] 8.4 **P0 图片播放器**：保留 `ui/image/*`（11 文件）+ `help/image`（✅ 全部保留），接入新 UI 入口（ReadRss type=1 分派保留）— 保留完成，外观统一待 7.11an2
- [x] 8.5 **P0 RSS 订阅源全局搜索**：保留 `ui/rss/search/*`（8 文件）+ `model/rss/RssSearchModel`；订阅 tab 搜索栏=全局搜索入口（ARCHIVE 单源搜索保留）— **依赖 7.11v 订阅顶栏对齐后，在 Archive `MainTopBarView(Mode.RSS)` 保留本项目全局搜索入口，防被 Archive 单源搜索覆盖**（2026-08-22 核实：RssFragment topBar.searchButton/searchEntry 均已跳 RssSearchActivity 且经 RssSearchModel 接线 ✅）
- [x] 8.6 **P1 分组编辑**：发现页/订阅 tab 重新注入分组入口 + `GroupTabRow` + `SourceGroupCover` + 批量分组；订阅源管理页补分组管理入口（复用 ARCHIVE 通用分组组件）— **依赖 7.11v 顶栏 + 7.11a-p 管理页，分组入口在 Archive 顶栏重新注入**（2026-08-22 核实：RssFragment/ExploreFragment 均经 setPrimaryItems 注入 SourceGroupCover 分组 ✅）
- [x] 8.7 **P1 高亮体系**：保留 `help/Highlight*`（8 文件）+ `ui/highlight/*` + `BookHighlight` 实体 + ReadBook/备份接线（✅ 全部保留；2026-08-22 补高亮入口断链修复：MyFragment 工具分组注入 HighlightRuleActivity）**高亮弹框外观统一归 7.11 E4（7.11am）**
- [x] 8.8 **P2 漫画**：复用 ARCHIVE `ui/book/manga/` + 回填 OURS Webtoon/ScrollTimer/Gesture/嗅探兜底增量（✅ 全部保留：ReadMangaActivity + WebtoonRecyclerView/ScrollTimer/GestureDetectorWithLongTap）
- [x] 8.9 **P2 分组封面**：`SourceFolderAdapter` 分组封面适配主题（存在，位于 `ui/adapter/`）**RuleSub 主体由 7.11m 承接，此处不再重复；仅做分组封面外观对齐**（RuleSub 主体已完成 7.11m）
- [ ] 8.10 特色功能全量真机端到端验证（L1/L2）
- [x] 8.11 **P0/P1 特色入口 Archive 壳再注入（2026-08-21 新增；部分完成）**：任务 7 D 类回退后，在 Archive Compose 骨架注入本项目特色入口——我的页 `MySettingsScreen`（7.11u 骨架 4 分组无特色项）补视频/图片播放器/RSS 全局搜索/漫画/高亮/自动任务/**UrlRecord/统计 MetricGrid/AITool** 入口（对齐 design §1.8 特色清单；ProfileScreen3Level 删除后其 MetricGrid 统计卡需在本项目 buildSections 重建）；订阅/发现顶栏补全局搜索+分组（与 8.5/8.6 协同）；阅读页高亮入口补全（8.7）；确保特色功能不因壳替换丢失 — **2026-08-22 已完成大部分**：自动任务/AI设置/阅读记录（原先已有）+ **高亮/UrlRecord/RSS全局搜索 3 入口已注入 MyFragment.buildSections+handleRowClick**；**统计 MetricGrid 统计卡已重建**（MyFragment.loadMetrics 读 Room：flowShelfAll/allCount/rssSourceDao.size/readRecordDao.allTime → MySettingsScreen 顶部渲染）；**视频/图片/漫画入口已通过新建 `MyFeatureBooksActivity`（书架多媒体）承载**（ComponentActivity+LegadoTheme，flowShelfAll 按 isVideo/isImage 分组，点击按类型分派 VideoPlayerActivity/ReadMangaActivity/ReadBookActivity）、MyFragment 工具分组注入入口 + manifest 注册 + 编译门禁 compileAppDebugKotlin BUILD SUCCESSFUL（my_feature_* strings 已补 values+values-zh）；**阅读页高亮菜单入口已补**（ReadBookActivity 修复 menu_highlight_rule 断链——XML/string 已存在但 onCompatOptionsItemSelected 无分支，已加 case startActivity<HighlightRuleActivity> + import，compileAppDebugKotlin BUILD SUCCESSFUL；updateLog 已登记）
- [ ] 8.12 **接线点回归验证（2026-08-21 新增；作为 8.10 的防回归子项，避免重复执行）**：任务 7 A-E 实施后，Git diff + 真机核对所有特色接线点仍可达（订阅顶栏全局搜索、发现/订阅分组、我的页特色入口、视频/图片 type 分派、阅读高亮）；防 Archive 覆盖导致特色入口丢失

## 9. UI 标准建设（Phase 7，迁移全程实时沉淀）
- [ ] 9.1 建设 `docs/project-flow/ui-standards/`：组件目录（ui/widget/compose 全量清单 + **widget/components 本项目增强组件目录与用量规范**，承载 E4 特色弹框统一外观落点）
- [ ] 9.2 取色规范（ThemeUiPalette key 表 + R.color 兜底）
- [ ] 9.3 间距/圆角/字体规范（ComposeUiCorner + uiCornerScale + UiTypography）
- [ ] 9.4 页面骨架规范（AppManagementScaffold / AppSettingComponents / AppComposeDialogs 用法）
- [ ] 9.5 **弹框与壳层规范（2026-08-21 新增）**：ComposeDialogFragment / AppComposeDialogs / ComposeSettingFragment 用法 + `lib.dialogs`/`BaseDialogFragment` 淘汰边界，承接 E1 弹框 / E3 半迁移壳 / E4 特色统一外观
- [ ] 9.6 迁移登记表（每模块替换状态 + 特色接线点 + 组件使用记录 + §7.11 E 类实施进度）

## 10. 项目标识还原（Phase 8）
- [ ] 10.1 strings.xml 应用名改回本项目
- [ ] 10.2 启动图标 / logo 资源改回本项目
- [ ] 10.3 关于页仓库地址 / 开发者信息改回本项目（**依赖 7.11w 关于页回退 Archive AboutFragment 落地后再执行，避免被回退冲掉**）
- [ ] 10.4 清理 Archive 署名残留（**范围扩至本次搬入 UI 的 strings.xml / 布局 / 主题资源署名审计，非仅关于页**）

## 11. 验证与交付（Phase 9）
- [ ] 11.1 全量编译（测试包 `io.legado.miss.app.debug`）通过
- [ ] 11.2 按 `ai_tests` 八步流程全量端到端测试（`run_e2e.py --tc all`）（**以 §8 8.12 接线点回归为特色功能验收前置**）
- [ ] 11.3 覆盖安装回归（旧库→新库）+ 包体积对比报告
- [ ] 11.4 文档同步（docs/project-flow/ 各模块文档 + quick-reference + task-navigation + INDEX + 新增 E 类明细 archive-gap-*.md 与 §7.11/§8 联动内容）
- [ ] 11.5 updateLog 更新（面向用户语言，逐文件对照变更审计）
- [ ] 11.6 清理临时文件 / 调试日志（Grep 确认 0 残留）
- [ ] 11.7 用户最终验收（🛑 检查点 3）

---

## 决策项（检查点 1 已全部确认）

1. ✅ **Cronet 打包策略**：方案 1 `cronet-bundled:500.0.1`（用户已确认）— 已定
2. ✅ **主题 mode 默认值**：跟随 Archive 语义 "0"（用户已确认）— 已定
3. ✅ **Archive 重 AI 功能范围**：**完整搬入**（实体+DAO+业务+UI 入口全部搬入，不做裁剪；用户已确认，替代原"仅建表保编译"默认）— 已定
4. ✅ **EPub Core 新引擎**：**搬入 Archive 引擎**（用户已确认）— 已定
5. ✅ **迁移基座/独立项目**：以本项目为基座 + 独立项目实施（不向 Archive 提交合并申请）— 已确认
6. ✅ **迁移分支创建**：`migration-archive-ui` 从 master 干净点创建 — 已确认，待执行
7. ✅ **单元测试门禁（用户附加要求）**：每模块搬迁完成后对核心功能写单测并通过（`./gradlew test`）— 新增，已定
