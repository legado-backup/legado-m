# Archive 前端 UI 迁移整合 — 任务清单（tasks.md）

> 修订 v2（2026-08-19）：基于最新 tag `archive-v3-3.26.08172114` 深度分析（rev2 五份报告）与用户调整意见重写。
> 状态标记：`- [ ]` 待办 / `- [x]` 完成（⚠️ 代码完成 / ✅ 功能验证）。编译门禁 = `./gradlew assembleAppDebug`（测试包 `io.legado.miss.app.debug`）。

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
- [ ] 1.3 修改 `gradle.properties`：`CronetVersion=500.0.1`、`CronetMainVersion` 同步
- [ ] 1.4 删除 `app/cronetlib/` 本地 6 jar 与 `fileTree` 依赖，改 `cronet-bundled:500.0.1` Maven 构件
- [ ] 1.5 适配 `app/build.gradle`（media3-datasource-cronet 排除项按新构件调整）
- [ ] 1.6 更新 `app/cronet-proguard-rules.pro`（keep 规则适配 500.0.1）
- [ ] 1.7 验证 `CronetHelper.kt`/`CronetInterceptor.kt`/`DohDns.kt` 对 500.0.1 API 兼容（编译 + 真机网络/嗅探）
- [ ] 1.8 编译 `assembleAppDebug` + 对比 APK 体积（验证减包效果）
- [ ] 1.9 真机验证 Cronet 网络请求与视频播放/嗅探能力不退化

## 2. 地基补齐（Phase 0，编译硬约束先行）
- [ ] 2.1 `gradle/libs.versions.toml` 新增 4 个 Compose 生态依赖：miuix 0.8.8 / reorderable 3.1.0 / LazyColumnScrollbar 2.2.0 / liquidglass 1.0.3
- [ ] 2.2 composeBom 对齐 ARCHIVE 版本（2025.10.00，评估与现有代码兼容性）
- [ ] 2.3 复制 `utils/SearchBookMergeUtils.kt`（从 ARCHIVE，ExploreShow 结果合并去重）
- [ ] 2.4 复制 `ui/video/VideoBookPreloader.kt`（从 ARCHIVE，SearchViewModel 依赖）
- [ ] 2.5 `help/webView/WebViewPool.kt` 补 `Scope` 枚举（GLOBAL/DISCOVERY/RSS）
- [ ] 2.6 `model/webBook/WebBook.kt` `exploreBook/exploreBookAwait` 补 `webViewPoolScope`/`shouldBreak` 参数
- [ ] 2.7 编译门禁 `assembleAppDebug` 通过

## 3. 后端支撑搬入（Phase 1）
- [ ] 3.1 `model/ReadBook.kt` 补 10 个新方法（reloadCurrentContent / invalidateParagraphRuleLayout / refreshCurrentParagraphRuleResult / invalidateEpubResource / markRecentRead / markReadAloudUserNavigation / stopReadAloudForBookSwitch / clearLastBookProgress / relayoutCurrentContent / upToc 同步）与 5 方法加参（moveToNextPage/moveToPrevPage/skipToPage/setPageIndex/saveRead/contentLoadFinish）
- [ ] 3.2 `data/dao/BookDao.kt` 补 `flowShelf*`/`BookShelfDisplay`/`BookShelfIdentity`/`getDisplayInfosByUrls` 系列（书架/订阅/发现列表数据源）
- [ ] 3.3 搬入 `help/AppCloudStorage.kt` + `lib/cloud/`（云存储抽象，被 ReadBookViewModel 等 20 文件引用）
- [ ] 3.4 搬入 EPub Core 引擎 `model/localBook/epubcore/`（16 文件）+ `EpubBox/EpubLayoutEngine` 系列（**用户已确认搬入**，随 Archive 阅读页 UI 完整接入）
- [ ] 3.5 搬入 `model/MediaTocRefresh.kt`、`ParagraphBubbleRenderer.kt`
- [ ] 3.6 搬入 `help/config/` 新类（AppearanceKitManager/TopBarConfig/MainBottomNavConfig/NavigationBarIconConfig 等，随 UI 引用）
- [ ] 3.7 搬入 **AI 全量业务后端** `help/ai/*`（AI 助手 / AI 记忆 / AI Agent / AI 绘图 / 角色 / 朗读 BGM / 段落规则，**用户已确认完整搬入，不做裁剪**）
- [ ] 3.8 编译门禁 `assembleAppDebug` 通过
- [ ] 3.9 单元测试门禁：`ReadBook` 新方法 / `WebBook.exploreBook` 新参数 / `BookDao.flowShelf*`（Room in-memory）单测通过

## 4. 主题系统整合（Phase 2）
- [ ] 4.1 升级 `help/config/ThemeConfig.kt` 为 32 字段（含 AtomicTextFileStore 原子写 + configSnapshot 缓存 + 背景图安全校验 + 字体-表面撞色守卫）
- [ ] 4.2 新增 `constant/PreferKey.kt` ~50 个主题 key（日夜双键）
- [ ] 4.3 搬入 `lib/theme/ThemeRuntimeKeys.kt` + 执行一次性夜间迁移 `migrateLegacyNightValues`（App.attachBaseContext 钩子）
- [ ] 4.4 搬入 `lib/theme` 六件套：ThemeUiPalette / UiCorner / ComposeUiCorner / UiTypography / LegadoComposeTheme / TopBarSearchStyle
- [ ] 4.5 搬入 `ui/widget/compose/ComposeThemeImageLayer.kt`、`AppUiTokens.kt`
- [ ] 4.6 搬入 `help/config/ThemePackageManager.kt`、`AppearanceKitManager.kt`（主题包/外观套件子系统）
- [ ] 4.7 统一 `themeMode` 默认值语义：**跟随 Archive（"0"跟随系统，用户已确认）**
- [ ] 4.8 搬入 `ui/config/ThemeManageActivity.kt`、`AppearanceKitActivity.kt`、`ui/config/compose/ComposeSettingFragment.kt`、`lib/prefs/fragment/ComposePreferenceScreen.kt`
- [ ] 4.9 保留 OURS `ThemeSync`/`LegadoTheme` 驱动存量页面，验证两套 Compose 主题共存
- [ ] 4.10 编译门禁 `assembleAppDebug` 通过
- [ ] 4.11 主题切换/日夜间/背景图真机验证

## 5. 数据库实体合并（Phase 3）
- [ ] 5.1 盘点 Archive 25 独有实体 + 14 DAO 清单（参照 rev2-sa2 报告）
- [ ] 5.2 搬入 Archive 25 实体 + DAO 到 `data/entities` / `data/dao`（含 2 个 FTS4 实体）
- [ ] 5.3 保留 OURS 9 特色实体（BookHighlight/CoverGallery*/PlayHistory/ReadRecordDetail/SourceRecycleBin/UrlRecord/AutoTaskRule/SourceGroupCover）
- [ ] 5.4 `AppDatabase.kt` bump v104 → v108，按 5 批迁移：v105（阅读增强 6 表）/ v106（AI 绘图+角色+摘要 5 表）/ v107（AI 朗读语音 7 表 + HttpTTS +3 列）/ v108（AI Agent+记忆 5 表 + 2 FTS4）
- [ ] 5.5 FTS4 虚拟表手动 `CREATE VIRTUAL TABLE` + 回填（不可用普通 Room 迁移）
- [ ] 5.6 生成新 schema 快照到 `app/schemas/`
- [ ] 5.7 覆盖安装回归：旧库（v104 含特色数据）→ 新库（v108）不崩溃、数据保留（真机）
- [ ] 5.8 编译门禁 `assembleAppDebug` 通过

## 6. UI 基建搬入（Phase 4）
- [ ] 6.1 搬入 `ui/widget/compose/*` 全量组件库（AppManagementScaffold/ComposeDialogFragment/AppComposeDialogs/AppSettingComponents/ComposeFastScroller/LegadoComposeTheme/ComposeViewOwners/BookCoverImage/SearchBookListItem/LegadoMiuixComponents 等 21 文件）
- [ ] 6.2 核对 R.color 兜底色资源（background_card/background_menu/bg_divider_line 等）是否存在，缺失补齐
- [ ] 6.3 编译门禁 `assembleAppDebug` 通过

## 7. 核心页面逐模块替换（Phase 5）
- [ ] 7.1 管理页先行：书源管理 / 订阅源管理 / 配置页 / 主题管理替换为 Archive 版
- [ ] 7.2 主界面替换：MainActivity（可配置底部导航）/ 书架（style1/2 + compose）/ 发现（含现代发现套件）/ 我的 / 订阅 / 阅读记录
- [ ] 7.3 书源相关：书源列表 / 编辑 / 调试 / 分组替换
- [ ] 7.4 搜索相关：搜索页 / 结果页（SearchResultScreen）/ 搜索范围替换
- [ ] 7.5 详情/目录：BookInfoComposeActivity / TocComposeScreen 替换
- [ ] 7.6 阅读页：BaseReadBookActivity / ReadBookActivity 按 Archive 版替换（含 **EPub Core 引擎接入，用户已确认搬入**）
- [ ] 7.7 其余页面：缓存 / 下载 / 备份 / 我的信息等按模块替换
- [ ] 7.8 AI UI 页面完整搬入（**用户已确认**）：`ui/book/character/*`、AiChatActivity、朗读 BGM/段落规则管理页等，与 `help/ai/*` 业务打通
- [ ] 7.9 每模块编译门禁 + 冒烟验证（✅ 逐模块标记）
- [ ] 7.10 清理本项目废弃 XML 资源与废弃自研 Compose 壳层（被 Archive 版替代的）

## 8. 特色功能整合（Phase 6，P0/P1/P2 分级）
- [ ] 8.1 **P0 视频播放器**：保留 `ui/video/*`（11 文件）+ `model/VideoPlay` 增强版 + `help/video` + `help/exoplayer` 增强层；`model/VideoPlay` 合并 ARCHIVE `chapterLinkCache` 预加载优化；接入 Archive 组件库统一外观
- [ ] 8.2 P0 视频滑动切换链路真机验证（上下滑动切换下一内容 + 自动加载下一页 + WebView 降级触摸拦截）
- [ ] 8.3 P0 前置嗅探链路真机验证（JS 覆写 fetch/XHR + WebView 拦截 + MIME 嗅探 + M3U8/HLS 加固）
- [ ] 8.4 **P0 图片播放器**：保留 `ui/image/*`（12 文件）+ `help/image`，接入新 UI 入口（ReadRss type=1 分派保留）
- [ ] 8.5 **P0 RSS 订阅源全局搜索**：保留 `ui/rss/search/*`（8 文件）+ `model/rss/RssSearchModel`；订阅 tab 搜索栏=全局搜索入口（ARCHIVE 单源搜索保留）
- [ ] 8.6 **P1 分组编辑**：发现页/订阅 tab 重新注入分组入口 + `GroupTabRow` + `SourceGroupCover` + 批量分组；订阅源管理页补分组管理入口（复用 ARCHIVE 通用分组组件）
- [ ] 8.7 **P1 高亮体系**：保留 `help/Highlight*`（8 文件）+ `ui/highlight/*` + `BookHighlight` 实体 + ReadBook/备份接线
- [ ] 8.8 **P2 漫画**：复用 ARCHIVE `ui/book/manga/` + 回填 OURS Webtoon/ScrollTimer/Gesture/嗅探兜底增量
- [ ] 8.9 **P2 规则订阅/分组封面**：RuleSub 直接用 ARCHIVE 版；`SourceFolderAdapter` 分组封面适配主题
- [ ] 8.10 特色功能全量真机端到端验证（L1/L2）

## 9. UI 标准建设（Phase 7，迁移全程实时沉淀）
- [ ] 9.1 建设 `docs/project-flow/ui-standards/`：组件目录（ui/widget/compose 全量清单）
- [ ] 9.2 取色规范（ThemeUiPalette key 表 + R.color 兜底）
- [ ] 9.3 间距/圆角/字体规范（ComposeUiCorner + uiCornerScale + UiTypography）
- [ ] 9.4 页面骨架规范（AppManagementScaffold / AppSettingComponents / AppComposeDialogs 用法）
- [ ] 9.5 迁移登记表（每模块替换状态 + 特色接线点 + 组件使用记录）

## 10. 项目标识还原（Phase 8）
- [ ] 10.1 strings.xml 应用名改回本项目
- [ ] 10.2 启动图标 / logo 资源改回本项目
- [ ] 10.3 关于页仓库地址 / 开发者信息改回本项目
- [ ] 10.4 清理 Archive 署名残留

## 11. 验证与交付（Phase 9）
- [ ] 11.1 全量编译（测试包 `io.legado.miss.app.debug`）通过
- [ ] 11.2 按 `ai_tests` 八步流程全量端到端测试（`run_e2e.py --tc all`）
- [ ] 11.3 覆盖安装回归（旧库→新库）+ 包体积对比报告
- [ ] 11.4 文档同步（docs/project-flow/ 各模块文档 + quick-reference + task-navigation + INDEX）
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
