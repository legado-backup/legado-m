# Specs 索引（docs/specs/）

> 功能设计文档索引。活跃 spec 按 OpenSpec 工作流管理（README/spec/design/tasks 四文档）；历史 spec 已于 2026-08-30 文档规整时归档至 [archive/](./archive/)。最后更新：2026-08-30。

## 一、活跃 Spec（61 个）

状态说明：✅ 已完成/已实施/设计完成，🔄 设计中/开发中/实施中，— README 未标注状态。

| Spec | 状态 | 一句话说明 |
|------|------|------------|
| [bookshelf-refresh-and-title-font](./bookshelf-refresh-and-title-font/README.md) | ✅ | 书架下拉刷新转圈不消失+顶栏标题字号不统一修复 |
| [bugfix-20260822](./bugfix-20260822/README.md) | 🔄 | 20260822 真机反馈 6 类问题+12 处 FATAL 崩溃+运行时异常专项修复 |
| [bugfix-ui-20260824](./bugfix-ui-20260824/README.md) | 🔄 | 20260824 用户反馈 11 项 UI/功能修复（图片圆角/搜索框/顶栏/分组/入口/文案等） |
| [cache-entry-relocate](./cache-entry-relocate/README.md) | 🔄 | 「我的」页功能归堆重构（内容与规则/外观/同步/工具/精准管理/关于 6 组框架） |
| [cache-toggle-rename-rss-all-label](./cache-toggle-rename-rss-all-label/README.md) | ✅ | 文案调整：视频缓存开关改名「播放时缓存」+订阅「全部」分组标签缩短 |
| [config-needs-restart-fix](./config-needs-restart-fix/README.md) | ✅ | 配置修改需重启生效统一修复（订阅顶栏残留+书架布局不生效）+视效对齐 archive |
| [cookie-management-fix](./cookie-management-fix/README.md) | ✅ | Cookie 管理链路修复（WebView/CookieStore/OkHttp 同步断裂 6 问题） |
| [cronet-global-enable-20260731](./cronet-global-enable-20260731/README.md) | 🔄 | Cronet 默认自动启用与扩展使用方案（P0 全局启用已落地） |
| [dialog-leftovers-compose](./dialog-leftovers-compose/README.md) | ✅ | 弹框遗留项 Compose 化（autoTask 两弹框+urlrecord 详情/过滤弹框迁移） |
| [douyin-style-video-player](./douyin-style-video-player/README.md) | ✅ | 抖音风格沉浸式竖屏视频播放器重设计（垂直滑动+悬浮控件+三态切换） |
| [download-hls-complete-fix](./download-hls-complete-fix/README.md) | 🔄 | 下载 HLS 完成链路修复（m3u8 下载成功但产物异常三连问题） |
| [download-manager-maturity](./download-manager-maturity/README.md) | 🔄 | 下载器成熟化改造（Room 持久化+断点续传+暂停恢复+并发上限+重试） |
| [download-manager-optimize](./download-manager-optimize/README.md) | ✅ | 下载管理深度优化（P1 正确性+引擎健壮性+IDM 动态分段引擎） |
| [exoplayer-resilience](./exoplayer-resilience/README.md) | ✅ | ExoPlayer 韧性优化（MimeSniffer 识别链+WebView 降级两层防护） |
| [fix-highlight-rule-toggle-refresh](./fix-highlight-rule-toggle-refresh/README.md) | ✅ | 高亮规则管理页复选框切换不即时刷新修复（Compose 跳过引用比较） |
| [fix-rss-search-scope](./fix-rss-search-scope/README.md) | 🔄 | 订阅搜索范围上下文修复（分组/标签/类型内搜索按上下文收窄） |
| [folder-cover-ratio-archive-align](./folder-cover-ratio-archive-align/README.md) | 🔄 | 文件夹封面比例对齐 Archive（0.7→0.75 消除拉长失真） |
| [folder-cover-replace-bugfix](./folder-cover-replace-bugfix/README.md) | ✅ | 书架/订阅文件夹自定义封面替换失效回归修复 |
| [folder-view-welcome-refactor](./folder-view-welcome-refactor/README.md) | ✅ | 书源/订阅源文件夹视图重构+欢迎页增强+前端样式审计 |
| [forks-ecosystem-analysis](./forks-ecosystem-analysis/README.md) | 🔄 | 阅读 M 功能借鉴与整体实施（17 fork 生态分析完成+分阶段借鉴落地） |
| [global-spec-restructure](./global-spec-restructure/README.md) | 🔄 | 全局规范重组（AGENTS.md 跨项目通用内容迁移至全局规范） |
| [header-search-unify](./header-search-unify/README.md) | ✅ | 主 Tab 头部搜索入口统一（以订阅页为标准，书架/我的对齐） |
| [highlight-dialog-compose](./highlight-dialog-compose/README.md) | ✅ | 高亮三弹框 Compose 化迁移（编辑/分组管理/预设规则） |
| [image-canvas-3fix-20260728](./image-canvas-3fix-20260728/README.md) | — | 图片画布模块 3 问题根因修复（基于日志包证据链） |
| [image-player-vertical-canvas-optimization](./image-player-vertical-canvas-optimization/README.md) | 🔄 | 内置图片播放器垂直画布优化（垂直长画布+点击查看大图） |
| [image-thread-coordination-fix-20260731](./image-thread-coordination-fix-20260731/README.md) | 🔄 | 图片加载与视频切换线程协调修复（正式包反馈两类问题） |
| [legados-forks-comparison](./legados-forks-comparison/README.md) | ✅ | legados Fork 对比与集成方案（逐文件源码对比识别可集成特性） |
| [legado-skill-v2-rebuild](./legado-skill-v2-rebuild/README.md) | 🔄 | Legado Skill V2 重建方案（基于第十轮深度审计的统一重建） |
| [list-residue-compose](./list-residue-compose/README.md) | ✅ | 遗留列表 Compose 化收尾（CacheActivity 缓存列表+Explore 瀑布列表） |
| [memory-mechanism-redesign](./memory-mechanism-redesign/README.md) | ✅ | 项目记忆机制改造（项目记忆独立至 .trae/memory+废弃 conv_id） |
| [multiline-on-demand-extraction](./multiline-on-demand-extraction/README.md) | 🔄 | 多线路多集按需采集架构优化（ruleContent 返回播放页 URL+按需采集 m3u8） |
| [my-topbar-unify](./my-topbar-unify/README.md) | 🔄 | 「我的」页头部迁移 MainTopBarView（与书架/订阅/发现观感统一） |
| [network-perf-stability](./network-perf-stability/README.md) | 🔄 | 网络性能与稳定性深度优化（OkHttp/Cronet/协程/缓存/图片解密） |
| [p0-bugfix-round1](./p0-bugfix-round1/README.md) | ✅ | P0 核心 Bug 修复第一轮（2026-07-08 改动发现的 4 项） |
| [player-mature-solutions-alignment](./player-mature-solutions-alignment/README.md) | 🔄 | 播放器成熟方案对齐（可观测性+视频/图片核心能力+网络韧性，5 Phase） |
| [player-review-and-optimization](./player-review-and-optimization/README.md) | ✅ | 视频/图片播放器审查与优化整合（8 份审查报告 108 项+12 个 ADR） |
| [reader-overlay-compose](./reader-overlay-compose/README.md) | 🔄 | 阅读器浮层 Compose 化（S5 骨架：菜单层+浮层壳核分离，正文零改动） |
| [rss-classic-layout-align](./rss-classic-layout-align/README.md) | ✅ | 经典订阅布局管理与书架对齐修复（margin/排序/书名/弹框等 7 项实锤） |
| [rss-folder-cover-dialog-align](./rss-folder-cover-dialog-align/README.md) | ✅ | 订阅文件夹封面弹框对齐书架（标准弹框+预览+恢复默认） |
| [rss-folder-subtag-fix](./rss-folder-subtag-fix/README.md) | 🔄 | 订阅文件夹样式点进文件夹头部误显标签/箭头修复 |
| [rss-image-load-optimization](./rss-image-load-optimization/README.md) | 🔄 | 图片订阅源加载优化（参考书源：URL 缓存+采样解码+并发预下载） |
| [rss-video-player-enhancement](./rss-video-player-enhancement/README.md) | 🔄 | 订阅源视频播放器增强（多集选择/调试日志/自动抓取 R1-R5） |
| [sniff-migration-booksource](./sniff-migration-booksource/README.md) | ✅ | 嗅探与滑动切换能力迁移至书源（图片/视频嗅探+上下滑动切换） |
| [sniff-regression-rss-image-crash](./sniff-regression-rss-image-crash/README.md) | ✅ | 嗅探回归与图片订阅源崩溃取证修复（WebView 池全局互斥+崩溃回灌） |
| [source-arch-mutual-borrow](./source-arch-mutual-borrow/README.md) | 🔄 | 书源/订阅源架构差异分析与机制层互补优化（6 个共享机制组件，V2） |
| [source-layout-redesign](./source-layout-redesign/README.md) | ✅ | 书源/订阅源布局设置重做（视图模式/排序/类型筛选/统一配置对话框） |
| [subpage-topbar-unify](./subpage-topbar-unify/README.md) | 🔄 | 子页面头部统一（全 App TitleBar 子页批量迁移 MainTopBarView） |
| [tag-mode-unify](./tag-mode-unify/README.md) | 🔄 | 书架订阅标签样式统一（对齐 Archive MainTopBarView 顶栏标签体系） |
| [theme-rss-header-layout-sync](./theme-rss-header-layout-sync/README.md) | ✅ | 主题设置与订阅/发现页头部布局联动修复（即时刷新+废弃 key 清理） |
| [thread-pool-audit](./thread-pool-audit/README.md) | 🔄 | 线程池配置全面审查（13 项配置点静态审查） |
| [topbar-icon-semantics-fix](./topbar-icon-semantics-fix/README.md) | 🔄 | 顶栏图标语义与功能修复（Archive 迁移三级丢失链全量普查） |
| [topbar-search-entry-align](./topbar-search-entry-align/README.md) | ✅ | 主 Tab 头部搜索入口形态统一与主题取色对齐（消费主题槽位） |
| [ui-redesign-m3](./ui-redesign-m3/README.md) | 🔄 | UI 重构设计（对标 M3 设计语言，全量页面 Compose 化，ADR 01-22） |
| [ui-style-unify-deep-fix](./ui-style-unify-deep-fix/README.md) | 🔄 | UI 风格统一深度修复（头部 5 类+弹框 4 套体系双基线收敛） |
| [ui-theme-gap-audit](./ui-theme-gap-audit/README.md) | 🔄 | UI 主题管理缺口审计与全量样式测试（F/L/P 三维清单+测试用例集+修复轮） |
| [video-back-fullscreen-fix](./video-back-fullscreen-fix/README.md) | 🔄 | 视频播放器返回按钮修复+全屏按钮迁移+真全屏优化 |
| [video-download-manager](./video-download-manager/README.md) | ✅ | 视频下载与下载管理整合（自研 IDM 式分片引擎+m3u8 重封装） |
| [video-extractor-enhancement](./video-extractor-enhancement/README.md) | 🔄 | 内置视频抓取能力增强（自动抓取视频链接补齐规则短板） |
| [video-player-image-enhance](./video-player-image-enhance/README.md) | ✅ | 视频播放器画质增强三级档位（色彩参数/CAS 锐化降噪/Anime4K 超分） |
| [video-player-theme-unify](./video-player-theme-unify/README.md) | ✅ | 视频播放器主题统一（控制条/弹框动态设色+硬编码色清理） |
| [video-player-ux-fixes](./video-player-ux-fixes/README.md) | ✅ | 视频播放器体验五项修复（下载按钮/快进灵敏度/弹框透明/标题/图标） |

## 二、根目录散件与模板

| 文件 | 说明 |
|------|------|
| [TEMPLATE.md](./TEMPLATE.md) | OpenSpec 功能设计文档模板（新 spec 目录四文档以此生成） |
| [tvbox-review-checkpoint1.md](./tvbox-review-checkpoint1.md) | TVBox 方案审查记录（检查点 1） |
| [tvbox-review-four-angles.md](./tvbox-review-four-angles.md) | TVBox 方案审查记录（四角度） |

## 三、归档区（docs/specs/archive/）

> 历史 spec 已归档（2026-08-30 文档规整），共 100 个 spec 目录+2 个散件分析文档。其中 42 个为**停滞设计归档待定**（README 顶部有标注，可随时恢复）；其余为已完成或已有明确结论的 spec。目录名即归档前路径，完整内容见 `archive/<spec名>/`。

### 已完成归档（58 个）

`ai-tests-deep-audit` `android-ui-optimization` `app-stability-round2` `bugfix-20260730-batch1` `builtin-themes` `context-compression-feedback-preservation` `cronet-proguard-fix-20260731` `cronet-so-download-fix-20260731` `dependency-upgrade-optimization` `docs-consolidation` `e2e-ui-executor-hardening` `harden-blank-highlight-rules-20260808` `highlight-rule-fix-20260727` `image-canvas-thread-fix-20260728` `image-gallery-activity` `image-sniffer-optimization` `jvm-extract-refactor` `legado-core-optimization` `legado-skill-unified-redesign` `logging-audit-and-enhancement` `pageindex-local-experience-engine` `player-comprehensive-audit-20260729` `precise-manage` `python-client-optimization` `rhino-engine-upgrade` `rss-cache-first` `rss-concurrency-and-checksource-optimization` `rss-image-decrypt-optimization` `rss-parse-optimization` `rss-unified-search` `sigma-sync-202607` `simulation-fidelity-95` `skill-architecture-optimization` `skill-deep-optimization-v2` `skill-html-fetch-enhancement` `skill-improvement` `skill-trio-optimization` `sniff-result-pipeline-fix-20260731` `sniff-stability-fix-20260731` `source-layout-bookshelf-style` `source-layout-detail-refinement` `spec-system-optimization` `ssl-handshake-investigation` `sub-agent-budget-optimization` `test-infra-upgrade` `theme-architecture-v2` `thread-pool-split-config` `tvbox-source-converter` `video-article-swipe-switch` `video-control-visibility-enhancement` `video-gesture-overhaul` `video-m3u8-cache` `video-mute-highspeed` `video-playback-failure-fix-20260726` `video-playback-issues-round1` `video-search-sniff-fix-20260727` `video-ui-dedup-layout-adjust` `yesterday-changes-deep-audit`

### 停滞设计归档待定（42 个，README 顶部有标注，可随时恢复）

`ai-llm-testing` `apk-release-publish-20260729` `apk-size-optimization` `archive-ui-migration-202608` `book-source-edit-anr-fix-20260731` `build-workflow-optimization` `e2e-automated-testing` `forks-archive-borrow-implementation` `forks-archive-comparison` `git-multi-remote-isolation` `global-issue-fix-and-spec-sedimentation` `global-spec-optimization` `gsy-fullscreen-button-removal` `highlight-rule-restore-default-20260729` `jvm-webview-and-test-fix` `legado-client-enhancement` `legado-skill-optimization` `legado-skill-optimization-v2` `legado-skill-v3-rebuild` `legado-skill-v4-rebuild` `real-device-test-plan` `realdevice-test-fix-003-20260727` `realdevice-test-fix-004-20260727` `realdevice-test-fix-20260727` `repo-cleanup` `rss-age-verify-autobypass` `rss-batch-optimize-v2` `rss-v5_7-deep-fix` `skill-core-capability-rebuild` `skill-optimization` `skill-usability-optimization` `sniff-stability-enhance-20260731` `source-convert-20260730` `source-folder-cover` `source-repair-loop-optimization` `sync-upstream-optimizations-20260816` `tech-doc-audit-and-fix` `tvbox-optimization` `v3.26.0717-bug-fix-batch` `video-buffer-speed-optimization` `video-player-m3u8-fix` `video-prebuffer-enhancement`

### 散件分析文档（2 个）

`player-deep-analysis-20260726.md` `player-deep-analysis-20260726-v2.md`
