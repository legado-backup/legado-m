# borrow-decisions.md — Legado 直系 fork 借鉴决策矩阵（三态）

> **三态定义**：
> - **Borrow**：推荐借鉴，收益明确、风险低、与本项目架构兼容
> - **Evaluate**：待评估，价值高但改动量大或产品方向需确认
> - **Not**：不建议借鉴（成本过高 / 与项目方向不符 / 收益低）
>
> **V2 修订（检查点2反馈后）**：
> 1. 逐条以本项目源码核验"现状"，**已覆盖项移出矩阵**（如 307/308、Bitmap 内存估算、WebDAV 进度、备份按需选择、视频预加载）
> 2. **AI 集成暂不接入**（用户明确指示），AI 相关全部移入 Not/暂缓，不进入 Borrow
> 3. 每条 Borrow 补充**落地路径**（改动点+参考 spec），确保可实施
>
> 决策依据：git clone 实测源码（AD-04）+ 本项目源码核验。收益/风险评分 1-5（5 最高）。优先级：P0 立即 / P1 近期 / P2 规划。

---

## 一、Borrow（推荐借鉴，均经本项目现状核验，无重复项）

| # | 功能项 | 来源 fork | 源码位置 | 收益 | 风险 | 优先级 | 落地路径（可实施） |
|---|--------|-----------|----------|------|------|--------|----------|
| B1 | **内置 CryptoJS**（无 jsLib 自动回退加密作用域，书源+订阅源+HttpTTS 通用） | legados | `model/SharedJsScope.kt:32-73` + `scripts/cryptojs.min.js` asset | 5 | 1 | P0 | ①新增 asset `app/src/main/assets/scripts/cryptojs.min.js`（MIT 许可）；②`SharedJsScope.kt` 增加 `CRYPTO_JS_ASSET` 常量与 `getCryptoScope()`；③**核心改动点在 `help/source/BaseSourceExtensions.kt:11-13` `getShareScope()`**：jsLib 为空时返回 `getCryptoScope()`。因 `getShareScope()` 是 `BaseSource` 接口扩展，而 `BookSource`/`RssSource`/`HttpTTS` 均实现 `BaseSource`（`RssSource.kt:128`），**一处改动同时覆盖书源、订阅源、HTTP TTS 三条 evalJS 链路**（`BaseSource.kt:336`/`AnalyzeUrl.kt:384`/`AnalyzeRule.kt:852` 均走 `source?.getShareScope()`），订阅源 ruleTitle/ruleDescription/ruleContent 等 JS 规则与书源规则同步获得 CryptoJS 能力；④JS 侧直接 `CryptoJS.MD5(...)`。纯增量无侵入 |
| B2 | **Brotli 解压（OkHttp 通道，书源+订阅源通用）** | legadoT | `help/http/DecompressInterceptor.kt`（`Accept-Encoding: gzip, deflate, br` + `BrotliInputStream`） | 4 | 1 | P0 | ①`gradle/libs.versions.toml` 加 `org.brotli:dec` 依赖；②`DecompressInterceptor.kt:21` 改 `Accept-Encoding: gzip, deflate, br`；③`when(encoding)` 增 `"br"` 分支用 `BrotliInputStream` 解压。**拦截器挂全局 `okHttpClient`（`HttpHelper.kt:188`）**，书源（AnalyzeUrl）与订阅源（`Rss.kt:54,104,160,306` 均走 AnalyzeUrl/SourceNetworkClient）请求同链路自动生效。注意 Cronet 通道已 enableBrotli，仅补 OkHttp 通道即可 |
| B3 | **旧书源 dnsIp/resolveIp 兼容（书源+订阅源通用）** | LegadoTeam | `model/analyzeRule/AnalyzeUrl.kt`（#573 `@SerializedName(value="dnsIp", alternate=["resolveIp"])`） | 4 | 1 | P0 | 本项目 `AnalyzeUrl.kt:858` 的 `dnsIp` 字段加 `@SerializedName(value="dnsIp", alternate=["resolveIp"])` 注解。**AnalyzeUrl 是书源与订阅源的共用请求器**（`Rss.kt:54,104,160,306` 均实例化 AnalyzeUrl 发请求），旧订阅源书写的 `resolveIp` 选项与旧书源同步兼容。纯兼容字段，Gson 自动反序列化，无逻辑改动 |
| B4 | **网络日志（敏感头脱敏，书源+订阅源通用）** | legado_NG | `help/http/NetworkLog.kt`（`sensitiveHeaderNames` L21 / `redactUrlForLog` L214）+ NetworkLogInterceptor.kt | 3 | 1 | P1 | ①移植 `NetworkLog.kt` + 拦截器（去 UI 依赖，只留记录核心）；②`AppConfig` 加 `recordHttpLog` 开关（默认关）；③接入 `LogUtils` 落盘（7 天清理已有机制）；④挂全局 `HttpHelper` 链（`HttpHelper.kt:188` 同 DecompressInterceptor 位置）。**书源+订阅源所有 HTTP 请求（列表/正文/搜索）自动记录**，与现有 AppLog TAG_HTTP 摘要互补 |
| B5 | **搜索结果存储字节上限** | Rimchars | `data/entities/SearchBookStoragePolicy.kt`（`MAX_STORED_ROW_BYTES=512KB` 各字段逐项上限） | 4 | 1 | P1 | ①移植 `SearchBookStoragePolicy` 工具类；②`SearchModel.kt:32-234` 保存/解析结果前对单条记录做字节校验，超限截断或跳过。防 CursorWindow 单行超限崩溃（本项目已出现过 SQLiteBlobTooBig，见 app-stability-round2 P1-1） |
| B6 | **书源 URL 变更迁移书架书籍** | Suml-1 | `data/dao/BookDao.kt:119` `update books set origin=:newUrl where origin=:oldUrl` + `BookSourceEditActivity.kt:655` | 4 | 2 | P1 | ①`BookDao` 加 `updateOrigin` SQL；②`BookSourceEditActivity` 保存书源时检测 URL 变更 + `hasBookByOrigin(oldUrl)` 有书则弹窗询问是否批量迁移；③与现有逐本 `migrateTo`（`Book.kt:400-420`）并存，迁移后提示重启刷新书架。防书籍变无源 |
| B7 | **规则回收站**（8 类规则 7 天保留） | youfengknight | `help/source/SourceRecycleBinHelp.kt` + `data/entities/SourceRecycleBin.kt` + `SourceRecycleBinDao` | 4 | 2 | P1 | ①新增 `sourceRecycleBin` 表（Room 迁移 +1 版本）；②`SourceRecycleBinHelp` 提供 recycle/restore/cleanupExpired；③删除书源/订阅源/替换规则等 8 类规则入口接入回收；④`AppConfig.sourceRecycleBinEnabled` 开关（默认关）。恢复可选覆盖/冲突检测 |
| B8 | **特殊内容保护** | legados | `help/book/SpecialContentProtector.kt`（41 行） | 4 | 1 | P1 | ①移植 41 行工具类；②净化/分段流程前对 `<usehtml>`/`<img>`/`[newpage]` 私有区占位符保护，流程后还原。防规则净化破坏格式块 |
| B9 | **书架显示阅读进度** | legados | `help/book/BookExtensions.kt:389` `readProgress()` + `AppConfig.showBookshelfReadProgress` | 3 | 2 | P2 | ①`BookExtensions` 加 `readProgress()`（基于 readRecord 百分比）；②书架 adapter 网格/列表加进度条（列表底部/网格封面叠加）；③`AppConfig` 开关默认关。低成本书架增强 |
| B11 | **缓存分项统计与删除** | refgd | `ui/book/cache/CacheManageViewModel.kt`（`loadStats` L148 / `buildStorageBreakdown` L677 / `deleteStorageDetail` L164） | 3 | 2 | P2 | ①缓存管理页按 书籍/音频/视频/主题 分类统计（遍历 `book_cache`/`exoplayer`/ACache 目录）；②支持分项查看+删除临时缓存。中等规模 UI+VM 改造 |
| B12 | **缓存并发率设置** | youfengknight | `AppConfig.cacheConcurrentRate` | 3 | 1 | P2 | `AppConfig` 加 `cacheConcurrentRate`，`CacheBookService.kt` 批量缓存时按比例限流（格式同书源 concurrentRate）。替代现有固定 `updateCacheThreadCount` 的补充维度 |
| B13 | **运行时内存压力监控** | legados | `help/MemoryPressure.kt`（90 行 `shouldTrimNow`/`throttleTrim` 1.5s 节流） | 3 | 2 | P2 | ①移植 90 行工具类；②Application `onTrimMemory` 低档位回调时 `shouldTrimNow` → 降 Glide 缓存 + 清 BitmapLruCache（`ImageProvider.kt:50`）。低内存设备防崩溃 |
| B14 | **WebDAV 备份删除/重命名** | Jingshiro | `help/AppWebDav.kt:126-170`（`getBackupFileList`/`deleteBackup`/`renameBackup`/`restoreWebDav`） | 3 | 1 | P2 | 本项目 `AppWebDav.kt:106-165` 已有列备份/上传/恢复，补 `deleteBackup`/`renameBackup` 两个 WebDAV 方法 + `BackupConfigFragment.kt` 长按菜单接线。低成本补缺 |
| B15 | **高亮规则捕获组样式（$N）解析** | Jingshiro | `help/book/ContentProcessor.kt:348-413` `applyHighlightRule` + `utils/CssStyleParser.kt` | 3 | 3 | P2 | 本项目已有 HighlightRuleMatcher（`HighlightRuleMatcher.kt:8-64`），仅借鉴**捕获组样式解析**：replacement 中 `$N` 周围样式标签按组套 HTML + 400 万字符 LRU 缓存。逐步移植，先支持 b/i/u/font/span |
| B16 | **想法批注分享/导出（Obsidian 双模式）** | Jingshiro | `ui/book/thought/ThoughtObsidianExporter.kt` + `ThoughtMarkdownGenerator.kt` + `ObsidianApi.kt` | 3 | 3 | P2 | 本项目已有 BookHighlight 划线/批注（`BookHighlight.kt`），仅补**导出链路**：Markdown 生成 + REST API/本地文件双模式导出 + 分享卡片。复用现有 BookHighlight 数据，不需新表 |

## 二、Evaluate（待评估，改动大或方向需确认）

| # | 功能项 | 来源 fork | 源码位置 | 收益 | 风险 | 优先级 | 评估要点 |
|---|--------|-----------|----------|------|------|--------|----------|
| E1 | **视频无缝过渡队列**（refgd 的 preloadNextEpisode/appendNext 无黑屏衔接） | refgd | `model/VideoPlay.kt:352` + `ExoVideoManager.kt:80` | 4 | 3 | P2 | 本项目已实现自动连播+下一集/文章预加载（`VideoPlay.kt:1263-1290` + `VideoPreloader`），但切换是整集切换；refgd 的播放队列无缝过渡（ExoPlayer ConcatenatingMediaSource2 提前排队）可评估是否值得消除切集黑屏。需先做切集体验基准 |
| E2 | **纯 JS 单文件书源引擎** | legados | `model/jsSource/`（JsSourceEngine/JsSourceConfig/JsSourceBook/JsSourceMarshaller） | 5 | 3 | P2 | 架构级扩展（突破声明式）。涉及 `BookSource` 加 mainJs 列（Room 迁移）+ `WebBook.kt` 8 处分派 + JS 源编辑器。与既有 5 模式规则引擎并存。价值最高但需专项任务 |
| E3 | **智能分组（在读/未读/已读）** | HapeLee | `data/AppDatabase.kt:284-313` + `BookGroup.kt:40-42` | 4 | 3 | P2 | 自动插入分组涉及 DB 虚拟分组改造 + 书架联查（在读/已读判定需 readRecord join）。需评估与现有静态分组（IdRoot/IdAll/IdAudio/IdVideo）的融合 |
| E4 | **详细阅读记录（会话级+Web 可视化）** | Jingshiro | `data/entities/DetailedReadRecord.kt` + `help/readrecord/DetailedReadRecordHelper.kt:14-177` + `ReadRecordWebActivity.kt` | 4 | 3 | P2 | 新表（startTime-endTime 会话）+ LifecycleObserver 采集器 + 2 分钟合并窗口 + 2565 行前端 assets。本项目现有 readRecordDetail 按日聚合，升级到会话级是中等规模。评估是否值得（对阅读习惯分析价值高） |
| E5 | **TTS 路由器体系** | legado_NG | `help/tts/ReadAloudTtsRouter.kt`（route L36 / globalScriptNarratorEngine L238） | 4 | 3 | P2 | 引擎注册/流式/变速强，需与现有 `model/ReadAloud.kt:29-41` 简单引擎选择重构集成。评估收益：多引擎路由对朗读扩展有价值 |
| E6 | **云 TTS Provider**（7 家） | HapeLee | `help/tts/` provider 目录 | 3 | 3 | P2 | 依赖各云厂商 API Key + 计费，产品形态需确认；且当前系统 TTS + HTTP TTS 已覆盖基本需求。低优先级 |
| E7 | **章节翻译（分块缓存+重试）** | HapeLee | `domain/usecase/TranslateChapterUseCase.kt` | 4 | 3 | P2 | 依赖翻译 API Key；产品形态（谁付费/哪些书源）需确认。技术实现（分块+缓存+重试）本身可复用 |
| E8 | **RSS 书籍化阅读** | huajideshutiao | `ui/book/rss/`（ReadRssActivity/ReadRssViewModel/RssJsExtensions） | 3 | 3 | P2 | 把 RSS 文章转成书本阅读（目录/进度/书架），是独立使用模式，与本项目现有"网页/图片/视频"三态分发（`ReadRss.kt`）如何共存需产品确认 |
| E9 | **朗读会话+TTS 队列窗口** | Rimchars | `service/BaseReadAloudService.kt:200` + `TtsQueueWindow.kt` | 3 | 3 | P2 | 队列窗口（TtsQueueToken/Reservation）可独立拆出；角色缓存预热依赖 AI 体系（暂缓）。仅队列窗口可单测移植 |
| E10 | **阅读书票（完读藏书票）** | Jingshiro | `ui/book/read/page/provider/BookplateDrawer.kt:36-531` + `TextPageFactory.kt` | 3 | 3 | P2 | 尾页完读自动弹（评分+时长+笔记+评价），产品化评估；与阅读统计联动需新增 finishTime 标记 |
| E11 | **阅读轮次标签（读完/N 刷）** | Jingshiro | `help/book/ReadIterationHelper.kt` + `Book.kt` readIteration | 3 | 3 | P2 | 书架圆角标签"读完/N 刷"，新增字段 + 完读判定 + 6 处 adapter 改造。价值中等 |
| E12 | **主题导出（FullTheme JSON+资源 zip）** | Jingshiro | `help/config/ThemeExportHelper.kt:31-321` | 3 | 2 | P2 | 全量主题打包（背景/封面/底部图标/阅读设置）导入导出。本项目已有主题机制，补导出 zip 即可 |
| E13 | **阅读成就（21 档称号）** | legados | `ui/book/readRecord/ReadAchievementActivity.kt` | 2 | 2 | P2 | 游戏化元素，与 E4 详细记录联动才有意义。低优先级 |

## 三、Not（不建议借鉴）

| # | 功能项 | 来源 fork | 原因 |
|---|--------|-----------|------|
| N1 | **S3 云存储** | Rimchars | 引入 AWS SDK 大依赖，本项目已有 WebDAV 备份体系，收益/成本不匹配 |
| N2 | **Relay 隧道服务**（公开 Web 中继） | Rimchars | 安全模型复杂（公开中继+息屏保活），非本项目目标场景 |
| N3 | **纯 JS 书源编辑器内核** | legados | 与 E2 引擎绑定，需编辑器+语法高亮全链路，依赖太重 |
| N4 | **Max 口令分享** | legados | 依赖其上传服务生态，本项目无对应服务端 |
| N5 | **epubcore 原生引擎重写** | Rimchars | 30 文件全新解析引擎，本项目 epub 解析已稳定，重构风险高收益低 |
| N6 | **domain 层 Clean Architecture 重构** | Suml-1 | 架构级重构，涉及全量数据流改造，本项目当前架构无需引入 |
| N7 | **鸿蒙 ArkTS 移植** | mgz0227 | 完全不同的平台工程，且原仓库已声明不再开源 |
| N8 | **MD3 Compose 迁移** | HapeLee/325506 | 纯 UI 重构（已排除领域），且与 Material3 强绑定 |
| N9 | **307/308 重定向跟随** | Max 系 | **本项目已实现**（`OkHttpUtils.kt:42-57` + followRedirects + RedirectCacheInterceptor），无需引入 |
| N10 | **Bitmap 内存估算（estimatedMemorySize）** | Rimchars | **本项目已覆盖**（`ImageProvider.kt:50-60` BitmapLruCache byteCount 估算+动态 resize） |
| N11 | **WebDAV 阅读进度同步** | 325506 | **本项目已实现**（`AppWebDav.kt:244-338` uploadBookProgress/downloadAllBookProgress 批量合并） |
| N12 | **备份按需选项目（shouldBackupTarget）** | refgd | **本项目已超集**（`BackupSelectorConfig.kt` 30 个 BackupItem 勾选 + BookCacheSelectorConfig 按书勾选） |
| N13 | **视频预加载/无缝切换体系** | refgd | **本项目已领先**（R5 嗅探+VideoPreloader+FirstFramePreloader+80% 文章预缓冲+实例池，见 analysis-report 领域 6）；仅无缝过渡队列列入 E1 评估 |
| N14 | **AI 助手/Agent/MCP/翻译（全套）** | Rimchars/Jingshiro/NG/HapeLee | **用户明确暂不接入 AI 集成**；能力已在 analysis-report 领域 4 存档，未来启动时再评估 |
| N15 | **订阅内容搜索（Rimchars RssSearchActivity）** | Rimchars | **本项目已有 `rss-unified-search`**（跨源并发搜索 `RssSearchModel` + `ui/rss/search/RssSearchActivity`，按 searchUrl 远程检索，详见 `docs/specs/archive/rss-unified-search/`）；Rimchars 的 `ui/rss/article/RssSearchActivity.kt` 同样是 searchUrl 远程搜索（非本地全文），且仅单源，功能为本项目子集，无需引入 |

---

## 四、决策汇总统计

| 决策 | 数量 | 占比 |
|------|------|------|
| Borrow | 15 | 36% |
| Evaluate | 13 | 31% |
| Not | 15 | 36% |
| 合计 | 43 | 100% |

**实施要求**（Borrow 15 项统一）：
1. **每功能点含日志埋点**：统一 `AppLog.putDebugWithTag`（`constant/AppLog.kt:123`）+ 新 TAG 常量，release 正式包 ERROR/WARN/INFO 仍进 logcat，供真机 `adb logcat -s <TAG>:I` 采集；TAG 清单与埋点位置见 design.md「日志埋点总纲」
2. **正式包真机验证**：全部实施完成后打包正式包（`build-legado.bat release`，`io.legado.miss.app.release`），用户真机测试回传 logcat，AI 执行日志分析子任务逐项核验（见 tasks.md 阶段 6）

**优先落地路线**（P0 三连 + P1 双项，均网络层/规则引擎低风险纯增量）：
1. **B1 CryptoJS** → **B2 Brotli（OkHttp 通道）** → **B3 resolveIp 兼容** → **B4 网络日志** → **B5 搜索存储上限**：前四项可合并为一次"网络层+规则引擎优化"任务（参考 `forks-reference.md` 方法论），B5 属稳定性可同批或独立
2. **P1 数据安全增强**（B6 书源 URL 迁移 / B7 规则回收站）可合并为一次"数据安全"任务
3. **P2 低风险小件**（B8 特殊内容保护 / B14 WebDAV 删除重命名 / B12 缓存并发率）可随相关模块顺手落地

## 五、与既有 spec 的关系

- **forks-archive-comparison**（Archive 7 维度）：本矩阵 B5/B7/E10 与其 Archive 结论同源，本次以新快照（1505c1d5）复核一致
- **legados-forks-comparison**（辞晨 10 项集成设计）：B1/B2/B8/E2 与其集成方案一致，可作为实施参考文档
- **本项目既有 spec 关联**：B5 关联 `app-stability-round2`（P1-1 SQLiteBlobTooBig）；视频能力领先结论关联 `rss-video-player-enhancement`/`exoplayer-resilience`/`sniff-result-pipeline-fix-20260731`/`douyin-style-video-player`/`video-article-swipe-switch`/`image-sniffer-optimization`/`image-player-vertical-canvas-optimization` 等已沉淀 spec
- 后续任何功能借鉴任务，从本矩阵取对应条目 → 跳转 analysis-report.md 对应领域章节获取源码引用 → 按 forks_comparison_methodology.md 执行对比
