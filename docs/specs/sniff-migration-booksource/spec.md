# Spec: 嗅探与滑动切换能力迁移至书源

## Intent

将 RSS 订阅源（RssSource）已有的三项成熟能力迁移至同类型书源（BookSource，bookSourceType 类型体系），补齐书源在图片/视频两类多媒体场景下的能力缺口：

1. **图片嗅探 → 图片书源（bookSourceType=2）**：ReadManga 静态解析返回 0 图时，接入 ImageSnifferWebView 嗅探兜底，解决 JS 渲染 / 防盗链站点正文无图可显示的问题。
2. **视频嗅探 → 视频书源（bookSourceType=4）**：VideoPlay 书源分支接入既有统一三层入口 `extractVideoUrlForEpisode`（MacCMS 播放页解析 → DOM 解析 → WebView 抓包），解决 `ruleContent` 返回播放页（HTML 而非视频直链）时 ExoPlayer 收到 HTML 报错的问题。
3. **上下滑动切换上/下集**：视频书源放开 `isUserInputEnabled` 支持集列表垂直滑动切换；图片书源支持按章节滚动加载（复用 RSS 图片源的 ImagePlay 加载模式）。

**核心原则**：纯行为扩展，不新增数据库字段、不做 schema 迁移，不改变 RSS 订阅源既有行为，复用已有嗅探基础设施（ImageUrlExtractor / VideoUrlExtractor / ImageSnifferWebView / BackstageWebView），遵循项目代码约束（object 单例、Coroutine 链式、`kotlin.runCatching`、AppLog 日志）。

## Scope

### In Scope（本次实现）

本次实现三项迁移，每项拆分为独立子项：

**1. 图片嗅探兜底 → 图片书源（bookSourceType=2）**

- **1.1** `ImageUrlExtractor` 新增 `sniffBookChapterImages(chapter, book, bookSource)` 薄封装：构造 `ImageSnifferWebView(chapter.url, headerMap, tag)` 复用 `sniffImageUrls()`（`IMAGE_SNIFF_JS` 5 路 hook + `IMAGE_SOURCE_REGEX` 拦截 + `sanitizeUrl`），不新增抽象容器、不触碰 RSS 链路
- **1.2** `ReadManga.getManageChapter`（L599-632）在 `BookHelp.flowImages` 静态解析结果为 0 图时，不再直接 `loadFail("正文没有图片")`，改为调用新重载触发嗅探兜底；嗅探结果仍为 0 时再进入原有失败路径
- **1.3** `ReadMangaActivity` 复用现有 `moveToNextChapter`/`moveToPrevChapter`（L274-321）导航框架，图片书源按章节滚动加载时逐章触发 `getManageChapter` 与嗅探

**2. 视频嗅探链 → 视频书源（bookSourceType=4）**

- **2.1** `VideoUrlExtractor.extractVideoUrlForEpisode`（L590-680，已有统一三层入口：MacCMS 播放页解析→DOM 解析→网络抓包，`isDirectVideoStreamUrl` 快速短路、5min 播放页缓存）第三参 `rssArticle: RssArticle?` 泛化为 `ruleData: RuleDataInterface?`，Referer 兜底取值适配书源（chapter.url/book.url）；RSS 调用点传参语义不变
- **2.2** `VideoPlay` 书源分支（L607-662）在 `WebBook.getContent` 返回正文后：`content` 以 `<` 开头维持现有 MPD 文本处理；否则将 URL 交给 `extractVideoUrlForEpisode(content, bookSource, chapter)`——直链由内部快路径直接返回，播放页经三层解析命中真实视频流，嗅探失败（返回 null）回退 URL 直连（现有 ExoPlayer 行为）
- **2.3** 嗅探链保留 R5_DELAY_TIME / R5_TIMEOUT（6s，`VideoUrlExtractor.kt:47-48`）超时控制与 Referer 注入（模拟 WebView 行为，解决 CDN 防盗链 404）

**3. 上下滑动切换上/下集**

- **3.1** 视频书源：`VideoPlayerActivity` L432 的 `isUserInputEnabled = !isSinglePage` 放开对书源模式的限制——视频书源（book != null 且非 singleUrl）时基于集数（episodes/章节）创建多页 Fragment，垂直滑动切换上/下集
- **3.2** 图片书源：`ReadMangaActivity` 支持按章节滚动加载（滚动到章节末尾自动加载下一章图片，参照 RSS 图片源 ImagePlay 加载模式），单章内为图片列表

### Out of Scope（不在本次实现）

1. **不改 RSS 图片/视频源行为**：ImageUrlExtractor 现有 `(RssArticle, RssSource)` 重载、ImageCanvasViewModel L284 调用链、VideoPlay RSS 分支（L370-604）均保持不变，仅新增书源重载/分支
2. **不做数据库 schema 变更**：零 migration，bookSourceType 为已有字段（BookSource.kt:40-42），不新增任何配置字段；配置开关仅用运行时内存状态实现（见 R5）
3. **不迁移音频嗅探**：bookSourceType=1（音频）不在本次范围，音频书源保持现状（BookContent.kt:149 audio → putLyric 歌词分支）
4. **不迁移 ExoPlayer 层 mime 嗅探**：不改动 ExoPlayer 收到 HTML 时的底层探测/报错处理，仅在上游书源分支提前拦截解析
5. **不改入口分发**：入口分发仍走现有 `ContextExtensions.kt:66-81`、`FragmentExtensions.kt:94-109`、`BookInfoActivity.kt:1093-1117`（isVideo→VideoPlayerActivity、isImage→ReadMangaActivity），不做入口重构
6. **不实现图片书源的跨卷/跨集滑动手势切换**：图片书源仅按章节滚动加载，不做 RSS 图片源那样的上下滑动跨文章切换（书源无文章概念，章节导航已有 moveToNextChapter/moveToPrevChapter）
7. **不新增 UI 设置项（本次仅运行时行为）**：详见 R5 权衡说明

## Approach

### Selected Approach（推荐方案）

**1. 图片嗅探：复用 `ImageSnifferWebView`，`ImageUrlExtractor` 加书源薄封装**

复用 `ImageSnifferWebView`（`url/headerMap/tag` 构造 + `sniffImageUrls()`，`IMAGE_SNIFF_JS` 5 路 hook、`IMAGE_SOURCE_REGEX`、WebView 池与并发守卫），`ImageUrlExtractor` 在静态 `flowImages` 解析 0 图时以 `chapter.url` + 书源 `headerMap` 触发嗅探兜底。`ReadManga.getManageChapter` 在 `imageCount == 0 && !chapter.isVolume` 时插入嗅探兜底路径，而非直接失败。

**理由**：嗅探基础设施（ImageSnifferWebView 池、JS hook、超时与并发守卫）已成熟且经历过 RSS 图片源实战验证；`ImageSnifferWebView` 构造函数本就不依赖 Rss 类型，书源侧几乎零适配，侵入面最小。

**2. 视频嗅探：直接复用 `extractVideoUrlForEpisode` 既有统一三层入口**

`VideoUrlExtractor.extractVideoUrlForEpisode(url, source: BaseSource?, ruleData)`（L590-680，multiline-on-demand-extraction 已实现）已是统一三层入口：`isDirectVideoStreamUrl` 快路径短路直链 → MacCMS 播放页解析（6s+5min 缓存）→ DOM 解析 → `extractWithWebView` 网络抓包（`R5_DELAY_TIME=1000ms`/`R5_TIMEOUT=6000ms`），失败返回 null、CancellationException 传播。书源分支直接把 `WebBook.getContent` 返回的 URL 交给它（`source=bookSource`、`ruleData=chapter`），命中即用嗅探结果播放，null 则维持原直连回退。

**理由**：不复制第二套嗅探链，RSS 与书源共用同一统一入口，行为一致、维护成本最低。RSS 分支调用点现传 `rssArticle`，泛化 `ruleData` 后**零行为变化**。

**3. 滑动切换：书源放开 `isUserInputEnabled` + `episodes` 驱动多页；图片书源三章连读已满足滚动**

- 视频书源：`VideoPlayerActivity` L424/L432 的 `isSinglePage` 判定改为「`singleUrl` 或（书源且 `episodes` 空/单集）」；多集书源 `VideoPagerAdapter.getItemCount` 以 `episodes.size` 建页，`onPageSelected` 书源分支 `chapterInVolumeIndex = position` 后 `startPlay`，垂直滑动切换上/下集。
- 图片书源：`ReadManga.buildMangaContent`（L242-268）本就三章连读滚动，本次仅插入嗅探兜底，不动滑动/分页结构。

**理由**：视频书源复用成熟 ViewPager2 多页机制，改动极小；图片书源滚动已存在，嗅探是唯一新增点。

### Alternatives Considered

| # | 迁移项 | 替代方案 | 描述 | 否决理由 |
|---|--------|---------|------|---------|
| 1 | 图片嗅探 | 方案A1: 在 ReadManga 内部新写一套嗅探 | ReadManga 直接持有 WebView 嗅探逻辑，不复用 ImageUrlExtractor | 与 RSS 图片源逻辑重复，两套嗅探维护成本翻倍；WebView 池/JS hook/并发守卫均需重写；违反 lazy principle 与 DRY |
| 1 | 图片嗅探 | 方案A2: 统一数据源层（WebBook 层自动嗅探） | 在 WebBook.getContent 或 BookContent 层对 image 类型 book 自动附加嗅探结果 | WebBook 是通用网络层，耦合嗅探会污染音频/文本/视频书源；嗅探是阅读体验层行为，应放在 ReadManga 消费侧；改动面大、回归风险高 |
| 1 | 图片嗅探 | 方案A3（选定）: ImageUrlExtractor 薄封装复用 ImageSnifferWebView | ReadManga 0 图时构造 WebView 嗅探 | 复用最大、侵入最小，嗅探器实现与 RSS 完全一致（见 Selected Approach） |
| 2 | 视频嗅探 | 方案B1: 不动 VideoUrlExtractor，书源分支内嵌正则解析 | 在 VideoPlay 书源分支直接写正则提取视频 URL | 正则只覆盖单一场景，无 extractPrecise 的标签/Meta/JSON/JS 变量能力，无 WebView 抓包兜底；与 R5 链路行为不一致，解不到的网络场景多 |
| 2 | 视频嗅探 | 方案B2: 让书源 ruleContent 直接返回 m3u8（改规则约定） | 要求用户书源规则返回视频直链而非播放页 | 治标不治本，无法处理 JS 渲染/防盗链播放页；与 RSS 视频源"播放页→嗅探"的约定不一致；需改书源规范且不可控 |
| 2 | 视频嗅探 | 方案B3（选定）: 复用 `extractVideoUrlForEpisode` 统一入口，泛化 ruleData | 书源分支直接调用既有三层入口，R3 处 RSS 调用零行为变化 | 复用度最高、零重复实现、书源/RSS 同源同链路（见 Selected Approach） |
| 3 | 滑动切换 | 方案C1: 视频书源保持禁用滑动，用集数选择器 | 维持 isUserInputEnabled=false，用户点击左下角集数选择器切换 | 与 RSS 视频源体验割裂；集数多时选择器交互效率低；本次需求明确要求滑动切换 |
| 3 | 滑动切换 | 方案C2: 单独实现视频书源的切换 UI/Adapter | 为书源模式新建一套分页 adapter 与手势 | 与 VideoPagerAdapter 现有集数模式重复；维护两套分页逻辑；侵入大 |
| 3 | 滑动切换 | 方案C3（选定）: 书源多集时以 `episodes` 驱动 ViewPager2 多页并放开 isUserInputEnabled | 复用集数模式建页 | 改动小、滑动体验与 RSS 视频一致（见 Selected Approach） |

### Drawbacks（选定方案的已知缺点）

| 缺点 | 接受理由 |
|------|---------|
| 图片嗅探有最长约 12s 的总超时（L1 500ms + L2 6s + 缓冲），嗅探失败的书源章节会经历延迟才进入 loadFail | 嗅探是兜底路径，仅静态解析 0 图时触发；有 L2_WEBVIEW_TIMEOUT_MS 硬超时与 webviewMutex 并发守卫；RSS 图片源同款延迟已被用户接受 |
| 视频书源接入嗅探增加解析耗时（extractWithWebView 最坏 6s），播放页场景下用户等待变长 | 播放页场景原本就会播放失败（ExoPlayer 收到 HTML），嗅探是"从失败变成功"；成功路径为 isDirectVideoStreamUrl 直链快路径（零延迟）或 MacCMS/DOM 静态解析（毫秒级），仅 WebView 抓包兜底层才慢 |
| `VideoUrlExtractor` `ruleData` 参数泛化会改动既有方法签名，有回归风险 | RSS 分支行为保持不变的回归约束（同输入同输出）；`RssArticle` 实现 `RuleDataInterface`，类型宽化后 RSS 调用点零改动；配合真机回归验证 |
| 视频书源放开滑动后，单集书源（episodes 为 null）仍单页无滑动，行为随集数动态变化 | 与集数数量严格对应，符合用户预期（有集才需要滑）；singleUrl 保持禁用滑动不受影响 |
| 图片书源嗅探是逐章触发，多章连读时可能多次触发 WebView 嗅探 | 仅 0 图章节触发；`extractVideoUrlForEpisode` 已有 5min 播放页缓存（视频侧）；图片侧因书源章节数量有限、且嗅探结果不落库，暂不加章节缓存（如后续真机发现重复嗅探明显再评估） |

### Prior Art（类似工作参考）

- **RSS 嗅探架构**：`help/image/ImageUrlExtractor.kt`（三层降级：L1 静态解析 → L2 ImageSnifferWebView 嗅探 → L3 合并去重，IMAGE_SNIFF_JS 5 路 hook，webviewMutex 并发守卫，TOTAL_TIMEOUT_MS=12s）与 `help/video/VideoUrlExtractor.kt`（extractPrecise / extractWithWebView / extractByRegex / resolvePlayerPageUrl，R5_DELAY_TIME=1000L / R5_TIMEOUT=6000L）——本次迁移的嗅探能力均来自这两处，书源侧直接复用
- **multiline-on-demand-extraction spec**：`docs/specs/multiline-on-demand-extraction/spec.md`——多线路多集按需采集架构，VideoPlay.startPlay 中 `hasNewRoutesMode`（ruleRoutes/ruleEpisodes 非空）分支与 playRssEpisode 统一采集入口，本次视频书源分支接入 R5 链与其协同（书源无 ruleRoutes/ruleEpisodes，仍走单层 WebBook.getContent + 嗅探兜底）
- **video-article-swipe-switch spec**：`docs/specs/video-article-swipe-switch/spec.md`——VideoPagerAdapter 多模式策略（书源单页/单URL单页/rssArticles 多页/rssEpisodes 多页），VideoPlayerActivity `isUserInputEnabled` 控制；本次视频书源滑动切换在其集数模式基础上放开
- **image-sniffer-optimization spec**：`docs/specs/image-sniffer-optimization/spec.md`——图片嗅探优化规范（P0 三层降级验收、shouldInterceptRequest 拦截、JS hook 注入），本次图片书源兜底直接复用其成果

## Requirements

### R1：图片书源嗅探兜底（bookSourceType=2）

- **R1.1** `ImageUrlExtractor` 新增 `suspend fun sniffBookChapterImages(chapter: BookChapter, book: Book, bookSource: BookSource): List<String>`：构造 `ImageSnifferWebView(chapter.url, headerMap, tag)` 复用 `sniffImageUrls()`，书源 `headerMap` 经 `AnalyzeUrl`/`BookSource` 头部注入；原 RSS 链路 `extractImageList` 保持不变
- **R1.2** `ReadManga.getManageChapter`（L599-632）：`BookHelp.flowImages` 结果为 0 且 `!chapter.isVolume` 时，触发新重载嗅探兜底；嗅探结果非空则用嗅探结果构建 MangaPage 列表，仍为空才维持原 `loadFail("正文没有图片")` 路径
- **R1.3** 嗅探结果必须去重（distinctUntilChanged，与现有 L599-601 行为一致），每张图片构建 MangaPage（chapterIndex/chapterSize/mImageUrl/index/mChapterName），并正确设置 imageCount
- **R1.4** 卷章节（chapter.isVolume）不触发嗅探，维持现有 `ReaderLoading` 逻辑
- **R1.5** 嗅探遵循协程取消语义：CancellationException 必须重新抛出，不记录为失败；嗅探超时由 L2_WEBVIEW_TIMEOUT_MS（6s）与 TOTAL_TIMEOUT_MS（12s）控制
- **R1.6** 图片书源正文获取沿用 `WebBook.getContent`（L363-377）链路（downloadNetworkContent），嗅探仅在消费侧（ReadManga）触发，不改网络层

### R2：视频书源嗅探链（bookSourceType=4）

- **R2.1** `VideoUrlExtractor.extractVideoUrlForEpisode`（L590-680）第三参 `rssArticle: RssArticle?` → `ruleData: RuleDataInterface?`，Referer 兜底：Rss 取 `link`、书源取 `chapter.url`、否则 `url`；RSS 调用点（VideoPlay.kt:1326 等）行为不变
- **R2.2** `VideoPlay` 书源分支（L607-662）在 `content.trim()` 非空且非 `<` 开头时，先 `extractVideoUrlForEpisode(content, source: BookSource, chapter)`：命中视频流则用其交给 player；返回 null（含内部分层全部失败/超时）则维持原 URL 直连（`AnalyzeUrl → resolvePlayerPageUrl → player.setUp`）
- **R2.3** `<` 开头的正文维持现有 MPD 文本处理（MD5 md5Encode + `.mpd` 临时文件 + Uri.fromFile），不进入嗅探链
- **R2.4** 嗅探链必须保留 Referer 注入（`Referer` = 章节/书籍 URL，模拟 WebView 行为解决 CDN 防盗链 404）与 R5_DELAY_TIME / R5_TIMEOUT（6s）超时控制
- **R2.5** 嗅探失败（全层未命中）时回退到原 URL 直连行为，不抛异常、不阻塞播放流程；`ContentEmptyException("正文为空")` 仅在 content 为空时抛出（维持现状）
- **R2.6** 弹幕/副文逻辑不变：书源视频书仍按 `BookContent.kt:148-159` 走 `putDanmaku`；audio 视频正文不被 HTML 化的约定（保持 URL 字符串）不变

### R3：滑动切换上/下集

- **R3.1** 视频书源：`VideoPlayerActivity` L424/L432 的 `isSinglePage` 判定改为「`singleUrl` 或（`book != null` 且 `episodes` 为空/仅 1 集）」；多集时 `isUserInputEnabled = true`，`VideoPagerAdapter.getItemCount` 书源分支以 `episodes.size` 建页，垂直滑动切换上/下集
- **R3.2** 单集视频书源（episodes 为 null 或仅 1 集）与 singleUrl 模式保持 `isUserInputEnabled = false` 单页，不出现无意义的空白滑动
- **R3.3** 滑动切换集数时 `onPageSelected(pos)` 书源分支设置 `chapterInVolumeIndex = pos` 并触发 `startPlay`（复用既有索引管理加载对应章节正文 → 直连/嗅探）；标题/进度与 `saveRead` 正确同步
- **R3.4** 图片书源：`buildMangaContent` 三章连读结构不变，章节边界由既有 `moveToNextChapter`/`moveToPrevChapter`（L274-321）与滚动位置管理；本次仅新增各章静态 0 图时的嗅探兜底（R1.2）
- **R3.5** 切换章节时显示加载状态（ReaderLoading/mCallback），嗅探等待期间不阻塞滚动操作；嗅探失败章节保持原有 `loadFail` 提示

### R4：兼容性

- **R4.1** 文本书源（bookSourceType=0）、音频书源（1）、文件书源（3）零改动，不受本次迁移影响
- **R4.2** RSS 图片源（ImageUrlExtractor 原重载、ImageCanvasViewModel:284）与 RSS 视频源（VideoPlay L370-604）行为完全不变，逐项真机回归
- **R4.3** 数据库零迁移：无 schema 变更、无新字段，覆盖安装兼容；R5 配置开关为运行时内存状态，不持久化
- **R4.4** 入口分发不变：`ContextExtensions.kt:66-81`、`FragmentExtensions.kt:94-109`、`BookInfoActivity.kt:1093-1117`、`BookExtensions.kt:45-48`（isVideo/isImage）维持原逻辑
- **R4.5** 图书列表模板源（含 image/video 类型的书籍列表）不受影响，嗅探仅在进入阅读/播放后触发
- **R4.6** 保持项目代码约束：object 单例、`Coroutine.async{}...onError{}.onSuccess{}` 链式、`kotlin.runCatching`、`isNullOrBlank()`、AppLog.put 日志（禁 Timber / 禁 android.util.Log.e 残留）

### R5：配置开关

- **R5.1** 视频书源嗅探链以运行时内存开关控制（默认开启，本次无 UI 设置项），开关关闭时书源分支完全维持现有"URL 直连"行为
- **R5.2** 图片书源嗅探兜底同样受运行时开关控制（默认开启），关闭时维持"0 图即 loadFail"现状
- **R5.3** 开关为内存状态，App 重启后重置为默认开启；不落库、不改编辑页 UI（避免 schema 变更与 UI 改造成本，本次范围外）
- **R5.4** 视频侧复用 `extractVideoUrlForEpisode` 已有的 5min 播放页缓存（URL → 嗅探结果），重复播放同一集不重复嗅探；图片侧不引入章节内存缓存（见 Drawbacks 权衡），退出阅读后释放 WebView 池引用

### R6：性能与失败处理

- **R6.1** 图片嗅探总耗时受 TOTAL_TIMEOUT_MS（12s）约束，L2 使用 WebViewPool 且受 webviewMutex 并发守卫，同一时间仅 1 个 WebView 嗅探实例（避免池耗尽）
- **R6.2** 视频嗅探受 R5_DELAY_TIME / R5_TIMEOUT（6s）约束，成功路径为 isDirectVideoStreamUrl 直链短路（零延迟）、MacCMS/DOM 静态解析（毫秒级），extractWithWebView 仅在前者未命中时触发
- **R6.3** 嗅探全失败降级路径必须可用：图片书源 → loadFail（用户可重试/退出）；视频书源 → URL 直连（保留现有 ExoPlayer 报错/WebView 降级链路）
- **R6.4** 嗅探期间用户退出/切换章节必须及时取消：协程取消异常（CancellationException）重新抛出，不记录为失败、不误报 AppLog
- **R6.5** 日志使用 AppLog.put / AppLog.putDebugWithTag（TAG_IMAGE_SNIFF），URL 路径模式化（sanitizeUrl），不输出真实域名/token（遵守 output-safety 规范）
- **R6.6** 嗅探网络请求复用现有 AnalyzeUrl 与防盗链头注入机制（显式 header，不与全局态耦合），保证 CDN 防盗链站点可正常加载

## Scenarios

### Scenario 1: 图片书源 0 图嗅探成功（主流程）

1. 用户打开一本图片书源（bookSourceType=2）的漫画，进入 ReadMangaActivity
2. ReadManga 调用 `WebBook.getContent` 获取章节正文，`BookHelp.flowImages` 静态解析返回 0 张图
3. `getManageChapter` 检测 `imageCount == 0 && !chapter.isVolume`，触发 `ImageUrlExtractor.sniffBookChapterImages(chapter, book, bookSource)`
4. 该薄封装构造 `ImageSnifferWebView(chapter.url, headerMap, tag)`，加载章节页面
5. IMAGE_SNIFF_JS 5 路 hook + shouldInterceptRequest 捕获 20 张图片 URL
6. 结果 distinct + sanitize 后返回，构建 MangaPage 列表并设置 imageCount=20
7. 用户正常滚动阅读漫画
8. `buildMangaContent` 预加载 prev/cur/next 三章，滚动到边界由既有移动机制切换，遇 0 图章节重复嗅探兜底

### Scenario 2: 视频书源返回播放页，统一入口嗅探命中（主流程）

1. 用户打开一本视频书源（bookSourceType=4）的剧集，进入 VideoPlayerActivity
2. VideoPlay 书源分支调用 `WebBook.getContent` 获取章节正文
3. 正文非空且非 `<` 开头，判定为播放页而非视频直链，进入 R5 嗅探链
4. `extractVideoUrlForEpisode`（统一三层入口：isDirectVideoStreamUrl 直链短路 → MacCMS 播放页解析 → DOM/WebView 抓包）命中真实 m3u8 地址
5. 注入 Referer 头（章节 URL），`resolvePlayerPageUrl` 解析后 `player.setUp` 开始播放
6. 用户在播放器中垂直滑动切换上/下集，切换后再次走 getContent → 嗅探链

### Scenario 3: 视频书源多集垂直滑动切换

1. 用户打开一本含 30 集的视频书源
2. `isSinglePage = singleUrl`（false），`book != null` 且 episodes 共 30 个，`isUserInputEnabled = true`
3. ViewPager2 按 30 集创建多页 Fragment
4. 用户在播放器中向上滑动 → 切换到下一集，向下滑动 → 切换到上一集
5. 每次切换更新 `chapterInVolumeIndex`，加载对应章节视频并播放
6. 用户选择"第 5 集"→ 滑动到第 6 集，标题与集数状态正确同步

### Scenario 4: 图片书源按章节滚动加载

1. 用户打开一本 50 章漫画书源（bookSourceType=2）
2. 第 1 章静态解析出 12 张图，直接展示
3. 用户滚动到第 1 章末尾，触发 `moveToNextChapter`，显示 ReaderLoading
4. 第 2 章静态解析 0 图，触发 `sniffBookChapterImages` 嗅探兜底，成功返回 8 张图
5. 第 2 章图片加载完成，用户继续滚动
6. 到达最后一章末尾，`moveToNextChapter` 返回 false（无下一章），阅读结束，进度正确保存

### Scenario 5: 嗅探全失败降级

1. 图片书源场景：某章节静态解析 0 图，`sniffBookChapterImages` 嗅探 6s 超时且未捕获图片，返回空列表
2. 保持 `imageCount == 0` 分支，进入 `loadFail("正文没有图片")`，用户看到失败提示可重试/退出
3. 视频书源场景：`ruleContent` 返回播放页，`extractVideoUrlForEpisode` 全部分层（MacCMS/DOM/WebView 抓包 6s 超时）未命中
4. 回退为 URL 直连：`AnalyzeUrl` → `resolvePlayerPageUrl` → `player.setUp`，保留现有 ExoPlayer 收到 HTML 的报错/降级链路
5. AppLog 记录完整降级链路（L1/L2/L3 或 嗅探链各层命中/失败），不误报协程取消为失败

### Scenario 6: 回归验证（RSS 与既有书源不受影响）

1. RSS 图片源：打开订阅源图片文章，ImageCanvasViewModel L284 调用原 `(RssArticle, RssSource)` 重载，三层降级行为与迁移前一致
2. RSS 视频源：打开订阅源视频文章，VideoPlay RSS 分支（L370-604，含 hasNewRoutesMode 多线路多集、ruleContent 空 → extractPrecise、VIDEO_FALLBACK_WEBVIEW）行为与迁移前一致，`extractVideoUrlForEpisode` 参数泛化后调用点行为不变
3. 文本书源：普通小说书源正常阅读，正文 HTML 化逻辑不受影响
4. 音频书源：歌词获取（putLyric）不受影响，`<` 开头 MPD 视频文本处理（R2.3）行为不变
5. 视频书源单集/singleUrl 模式：`isUserInputEnabled = false` 单页，无空白滑动
6. 覆盖安装升级：数据库无迁移、无新字段，升级后既有书源与设置全部保留
