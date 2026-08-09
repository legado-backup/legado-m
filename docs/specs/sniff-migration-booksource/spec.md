# Spec: 嗅探与滑动切换能力迁移至书源

## Intent

将 RSS 订阅源（RssSource）已有的三项成熟能力迁移至同类型书源（BookSource，bookSourceType 类型体系），补齐书源在图片/视频两类多媒体场景下的能力缺口：

1. **图片嗅探 → 图片书源（bookSourceType=2）**：ReadManga 静态解析返回 0 图时，接入 ImageSnifferWebView 嗅探兜底，解决 JS 渲染 / 防盗链站点正文无图可显示的问题。
2. **视频嗅探 → 视频书源（bookSourceType=4）**：VideoPlay 书源分支接入 R5 嗅探链（extractPrecise → extractWithWebView → extractByRegex），解决 `ruleContent` 返回播放页（HTML 而非视频直链）时 ExoPlayer 收到 HTML 报错的问题。
3. **上下滑动切换上/下集**：视频书源放开 `isUserInputEnabled` 支持集列表垂直滑动切换；图片书源支持按章节滚动加载（复用 RSS 图片源的 ImagePlay 加载模式）。

**核心原则**：纯行为扩展，不新增数据库字段、不做 schema 迁移，不改变 RSS 订阅源既有行为，复用已有嗅探基础设施（ImageUrlExtractor / VideoUrlExtractor / ImageSnifferWebView / BackstageWebView），遵循项目代码约束（object 单例、Coroutine 链式、`kotlin.runCatching`、AppLog 日志）。

## Scope

### In Scope（本次实现）

本次实现三项迁移，每项拆分为独立子项：

**1. 图片嗅探兜底 → 图片书源（bookSourceType=2）**

- **1.1** `ImageUrlExtractor.extractImageList` 新增 `BookChapter` 重载：接收 `(chapter, book, bookSource, ruleContent, ruleImage)` 参数组，复用既有三层降级链路（L1 静态解析 → L2 WebView 嗅探 → L3 合并去重）
- **1.2** `ReadManga.getManageChapter`（L599-632）在 `BookHelp.flowImages` 静态解析结果为 0 图时，不再直接 `loadFail("正文没有图片")`，改为调用新重载触发嗅探兜底；嗅探结果仍为 0 时再进入原有失败路径
- **1.3** `ReadMangaActivity` 复用现有 `moveToNextChapter`/`moveToPrevChapter`（L274-321）导航框架，图片书源按章节滚动加载时逐章触发 `getManageChapter` 与嗅探

**2. 视频嗅探链 → 视频书源（bookSourceType=4）**

- **2.1** `VideoUrlExtractor` 解耦 `RssArticle` 入参：将 RSS 分支使用的 extractPrecise / extractWithWebView / extractByRegex / resolvePlayerPageUrl 抽象为不依赖 RssArticle 的内部能力（入参改为 URL + Header 上下文），RSS 分支行为保持不变
- **2.2** `VideoPlay` 书源分支（L607-669）在 `WebBook.getContent` 返回正文后，先判断内容是否为播放页而非视频直链：`content` 以 `<` 开头维持现有 MPD 文本处理；否则当普通 URL 交给 player 前，先执行 R5 嗅探链（extractPrecise → extractWithWebView → extractByRegex）尝试解析出真实视频流 URL
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

**1. 图片嗅探：`extractImageList` 新增 `BookChapter` 重载，接入既有三层降级**

复用 ImageUrlExtractor 的三层降级架构（L1 静态解析 `L1_STATIC_TIMEOUT_MS=500ms` → L2 WebView 嗅探 `L2_WEBVIEW_TIMEOUT_MS=6s`、`IMAGE_SNIFF_JS` 5 路 hook、`IMAGE_SOURCE_REGEX`、`webviewMutex` 并发守卫 → L3 合并去重），新增 BookChapter 重载把书源上下文（book/bookSource/chapter）适配为嗅探所需的 URL 与规则参数。`ReadManga.getManageChapter` 在 `imageCount == 0 && !chapter.isVolume` 时插入嗅探兜底，而非直接失败。

**理由**：嗅探基础设施（ImageSnifferWebView 池、JS hook、超时与并发守卫）已成熟且经历过 RSS 图片源实战验证；新增重载是侵入面最小、复用度最高的方式，避免为书源另起一套嗅探实现。

**2. 视频嗅探：VideoUrlExtractor 解耦 RssArticle 入参 + VideoPlay 书源分支接入 R5 嗅探链**

将 RSS 分支已验证的 R5 嗅探链（extractPrecise 精确解析 → extractWithWebView 网络抓包 → extractByRegex 正则兜底）抽成不依赖 RssArticle 的内部方法，在 `VideoPlay` 书源分支拿到 `WebBook.getContent` 返回的正文后：`<` 开头走 MPD 文本文件（现有逻辑）；否则先按播放页尝试 R5 嗅探链，命中则用嗅探到的视频流 URL 交给 player，未命中则回退为 URL 直连（现有行为）。

**理由**：解决了"ruleContent 返回播放页 → ExoPlayer 收到 HTML"这一书源视频源的核心痛点；RSS 分支已验证 R5 链的可靠性，书源直接复用可保持两条链路行为一致、维护成本低。

**3. 滑动切换：视频书源放开 isUserInputEnabled + 图片书源按章节滚动加载**

- 视频书源：`VideoPlayerActivity` L424 的 `isSinglePage` 判定仅保留 `singleUrl` 真值，当 `book != null` 且存在多个集数（episodes/卷章节）时按集数建页，`isUserInputEnabled = true`，垂直滑动切换上/下集（复用 VideoPagerAdapter 集数列表模式，L22-41）。
- 图片书源：ReadManga 已有按章节滚动加载的骨架（loadContent → getManageChapter → moveToNextChapter），本次仅在其加载结果中加入嗅探兜底，滚动行为本身复用现有框架。

**理由**：视频书源与 RSS 视频源共用 VideoPlayerActivity/ViewPager2，放开开关即可获得成熟滑动切换体验，改动极小；图片书源复用现有章节导航，无需引入新的交互架构。

### Alternatives Considered

| # | 迁移项 | 替代方案 | 描述 | 否决理由 |
|---|--------|---------|------|---------|
| 1 | 图片嗅探 | 方案A1: 在 ReadManga 内部新写一套嗅探 | ReadManga 直接持有 WebView 嗅探逻辑，不复用 ImageUrlExtractor | 与 RSS 图片源逻辑重复，两套嗅探维护成本翻倍；WebView 池/JS hook/并发守卫均需重写；违反 lazy principle 与 DRY |
| 1 | 图片嗅探 | 方案A2: 统一数据源层（WebBook 层自动嗅探） | 在 WebBook.getContent 或 BookContent 层对 image 类型 book 自动附加嗅探结果 | WebBook 是通用网络层，耦合嗅探会污染音频/文本/视频书源；嗅探是阅读体验层行为，应放在 ReadManga 消费侧；改动面大、回归风险高 |
| 1 | 图片嗅探 | 方案A3（选定）: extractImageList 新增 BookChapter 重载 | 复用三层降级，ReadManga 0 图时触发 | 复用最大、侵入最小，嗅探行为与 RSS 图片源完全一致（见 Selected Approach） |
| 2 | 视频嗅探 | 方案B1: 不动 VideoUrlExtractor，书源分支内嵌正则解析 | 在 VideoPlay 书源分支直接写正则提取视频 URL | 正则只覆盖单一场景，无 extractPrecise 的标签/Meta/JSON/JS 变量能力，无 WebView 抓包兜底；与 R5 链路行为不一致，解不到的网络场景多 |
| 2 | 视频嗅探 | 方案B2: 让书源 ruleContent 直接返回 m3u8（改规则约定） | 要求用户书源规则返回视频直链而非播放页 | 治标不治本，无法处理 JS 渲染/防盗链播放页；与 RSS 视频源"播放页→嗅探"的约定不一致；需改书源规范且不可控 |
| 2 | 视频嗅探 | 方案B3（选定）: VideoUrlExtractor 解耦 + 书源分支接入 R5 链 | 复用 RSS 已验证的 R5 嗅探链 | 两条链路行为一致，RSS 侧零改动，书源侧获得全部降级能力（见 Selected Approach） |
| 3 | 滑动切换 | 方案C1: 视频书源保持禁用滑动，用集数选择器 | 维持 isUserInputEnabled=false，用户点击左下角集数选择器切换 | 与 RSS 视频源体验割裂；集数多时选择器交互效率低；本次需求明确要求滑动切换 |
| 3 | 滑动切换 | 方案C2: 单独实现视频书源的切换 UI/Adapter | 为书源模式新建一套分页 adapter 与手势 | 与 VideoPagerAdapter 现有集数模式重复；维护两套分页逻辑；侵入大 |
| 3 | 滑动切换 | 方案C3（选定）: 放开 isUserInputEnabled + 复用集数模式 | 书源多集时按 episodes 建页垂直滑动 | 改动一行条件 + 复用现有 ViewPager2 集数模式，体验与 RSS 视频源一致（见 Selected Approach） |

### Drawbacks（选定方案的已知缺点）

| 缺点 | 接受理由 |
|------|---------|
| 图片嗅探有最长约 12s 的总超时（L1 500ms + L2 6s + 缓冲），嗅探失败的书源章节会经历延迟才进入 loadFail | 嗅探是兜底路径，仅静态解析 0 图时触发；有 L2_WEBVIEW_TIMEOUT_MS 硬超时与 webviewMutex 并发守卫；RSS 图片源同款延迟已被用户接受 |
| 视频书源接入 R5 嗅探链增加解析耗时（extractWithWebView 最坏 6s），播放页场景下用户等待变长 | 播放页场景原本就会播放失败（ExoPlayer 收到 HTML），嗅探是"从失败变成功"；成功路径为 extractPrecise 静态解析（毫秒级），仅兜底层才慢 |
| VideoUrlExtractor 解耦 RssArticle 会改动现有方法签名/内部结构，有回归风险 | RSS 分支行为保持不变的回归约束（保持同一链路同输入同输出），改动仅限参数抽象，配合真机回归验证；RSS 分支代码路径不变 |
| 视频书源放开滑动后，单集书源（episodes 为 null）仍单页无滑动，行为随集数动态变化 | 与集数数量严格对应，符合用户预期（有集才需要滑）；singleUrl 保持禁用滑动不受影响 |
| 图片书源嗅探是逐章触发，多章连读时可能多次触发 WebView 嗅探 | 仅 0 图章节触发；嗅探成功的结果按章节缓存于内存（运行时状态，不落库），重复阅读同一章不重复嗅探 |

### Prior Art（类似工作参考）

- **RSS 嗅探架构**：`help/image/ImageUrlExtractor.kt`（三层降级：L1 静态解析 → L2 ImageSnifferWebView 嗅探 → L3 合并去重，IMAGE_SNIFF_JS 5 路 hook，webviewMutex 并发守卫，TOTAL_TIMEOUT_MS=12s）与 `help/video/VideoUrlExtractor.kt`（extractPrecise / extractWithWebView / extractByRegex / resolvePlayerPageUrl，R5_DELAY_TIME=1000L / R5_TIMEOUT=6000L）——本次迁移的嗅探能力均来自这两处，书源侧直接复用
- **multiline-on-demand-extraction spec**：`docs/specs/multiline-on-demand-extraction/spec.md`——多线路多集按需采集架构，VideoPlay.startPlay 中 `hasNewRoutesMode`（ruleRoutes/ruleEpisodes 非空）分支与 playRssEpisode 统一采集入口，本次视频书源分支接入 R5 链与其协同（书源无 ruleRoutes/ruleEpisodes，仍走单层 WebBook.getContent + 嗅探兜底）
- **video-article-swipe-switch spec**：`docs/specs/video-article-swipe-switch/spec.md`——VideoPagerAdapter 多模式策略（书源单页/单URL单页/rssArticles 多页/rssEpisodes 多页），VideoPlayerActivity `isUserInputEnabled` 控制；本次视频书源滑动切换在其集数模式基础上放开
- **image-sniffer-optimization spec**：`docs/specs/image-sniffer-optimization/spec.md`——图片嗅探优化规范（P0 三层降级验收、shouldInterceptRequest 拦截、JS hook 注入），本次图片书源兜底直接复用其成果

## Requirements

### R1：图片书源嗅探兜底（bookSourceType=2）

- **R1.1** `ImageUrlExtractor` 新增 `suspend fun extractImageList(chapter: BookChapter, book: Book, bookSource: BookSource, ruleContent: String?, ruleImage: String?): List<String>` 重载，内部适配书源上下文后复用既有三层降级链路；原 `(RssArticle, RssSource)` 重载保持不变
- **R1.2** `ReadManga.getManageChapter`（L599-632）：`BookHelp.flowImages` 结果为 0 且 `!chapter.isVolume` 时，触发新重载嗅探兜底；嗅探结果非空则用嗅探结果构建 MangaPage 列表，仍为空才维持原 `loadFail("正文没有图片")` 路径
- **R1.3** 嗅探结果必须去重（distinctUntilChanged，与现有 L599-601 行为一致），每张图片构建 MangaPage（chapterIndex/chapterSize/mImageUrl/index/mChapterName），并正确设置 imageCount
- **R1.4** 卷章节（chapter.isVolume）不触发嗅探，维持现有 `ReaderLoading` 逻辑
- **R1.5** 嗅探遵循协程取消语义：CancellationException 必须重新抛出，不记录为失败；嗅探超时由 L2_WEBVIEW_TIMEOUT_MS（6s）与 TOTAL_TIMEOUT_MS（12s）控制
- **R1.6** 图片书源正文获取沿用 `WebBook.getContent`（L363-377）链路（downloadNetworkContent），嗅探仅在消费侧（ReadManga）触发，不改网络层

### R2：视频书源嗅探链（bookSourceType=4）

- **R2.1** `VideoUrlExtractor` 解耦 `RssArticle`：extractPrecise / extractWithWebView / extractByRegex / resolvePlayerPageUrl 改为接收 URL + Header 上下文（不再依赖 RssArticle 对象），RSS 分支调用点同步适配但行为保持不变
- **R2.2** `VideoPlay` 书源分支（L607-669）在 `content.trim()` 非空且非 `<` 开头时，先经 R5 嗅探链解析：命中视频流 URL 则用其结果交给 player；未命中则维持原 URL 直连（AnalyzeUrl → resolvePlayerPageUrl → player.setUp）
- **R2.3** `<` 开头的正文维持现有 MPD 文本处理（MD5 md5Encode + `.mpd` 临时文件 + Uri.fromFile），不进入嗅探链
- **R2.4** 嗅探链必须保留 Referer 注入（`Referer` = 章节/书籍 URL，模拟 WebView 行为解决 CDN 防盗链 404）与 R5_DELAY_TIME / R5_TIMEOUT（6s）超时控制
- **R2.5** 嗅探失败（全层未命中）时回退到原 URL 直连行为，不抛异常、不阻塞播放流程；`ContentEmptyException("正文为空")` 仅在 content 为空时抛出（维持现状）
- **R2.6** 弹幕/副文逻辑不变：书源视频书仍按 `BookContent.kt:148-159` 走 `putDanmaku`；audio 视频正文不被 HTML 化的约定（保持 URL 字符串）不变

### R3：滑动切换上/下集

- **R3.1** 视频书源：`VideoPlayerActivity` L424 `isSinglePage = book != null || singleUrl` 改为仅 `singleUrl` 时 true；当 `book != null` 且集数（episodes/卷章节）多于 1 个时，`isUserInputEnabled = true`，VideoPagerAdapter 按集数建页垂直滑动切换上/下集
- **R3.2** 单集视频书源（episodes 为 null 或仅 1 集）与 singleUrl 模式保持 `isUserInputEnabled = false` 单页，不出现无意义的空白滑动
- **R3.3** 滑动切换集数后必须正确恢复 `chapterInVolumeIndex` 并触发对应章节的 `WebBook.getContent` → 嗅探/直连加载（复用 VideoPlay 现有章节索引管理）
- **R3.4** 图片书源：支持按章节滚动加载，滚动到当前章节末尾自动触发 `moveToNextChapter`，逐章经 `getManageChapter`（含 R1 嗅探兜底）加载；`moveToNextChapter`/`moveToPrevChapter`（L274-321）框架不变
- **R3.5** 切换章节时显示加载状态（ReaderLoading），嗅探等待期间不阻塞滚动操作

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
- **R5.4** 嗅探成功的结果按章节缓存于内存（图片：chapter → 图片列表；视频：URL → 嗅探结果），重复访问同章节/同 URL 不重复嗅探；退出阅读/播放后清理

### R6：性能与失败处理

- **R6.1** 图片嗅探总耗时受 TOTAL_TIMEOUT_MS（12s）约束，L2 使用 WebViewPool 且受 webviewMutex 并发守卫，同一时间仅 1 个 WebView 嗅探实例（避免池耗尽）
- **R6.2** 视频嗅探受 R5_DELAY_TIME / R5_TIMEOUT（6s）约束，优先走 extractPrecise 静态解析（毫秒级），extractWithWebView 仅在前者未命中时触发
- **R6.3** 嗅探全失败降级路径必须可用：图片书源 → loadFail（用户可重试/退出）；视频书源 → URL 直连（保留现有 ExoPlayer 报错/WebView 降级链路）
- **R6.4** 嗅探期间用户退出/切换章节必须及时取消：协程取消异常（CancellationException）重新抛出，不记录为失败、不误报 AppLog
- **R6.5** 日志使用 AppLog.put / AppLog.putDebugWithTag（TAG_IMAGE_SNIFF），URL 路径模式化（sanitizeUrl），不输出真实域名/token（遵守 output-safety 规范）
- **R6.6** 嗅探网络请求复用现有 AnalyzeUrl 与防盗链头注入机制（显式 header，不与全局态耦合），保证 CDN 防盗链站点可正常加载

## Scenarios

### Scenario 1: 图片书源 0 图嗅探成功（主流程）

1. 用户打开一本图片书源（bookSourceType=2）的漫画，进入 ReadMangaActivity
2. ReadManga 调用 `WebBook.getContent` 获取章节正文，`BookHelp.flowImages` 静态解析返回 0 张图
3. `getManageChapter` 检测 `imageCount == 0 && !chapter.isVolume`，触发 `ImageUrlExtractor.extractImageList(BookChapter 重载)`
4. L1 静态解析（ruleContent/ruleImage 或 body@html 兜底）返回 0 张，触发 L2 WebView 嗅探
5. ImageSnifferWebView 加载章节页面，IMAGE_SNIFF_JS 5 路 hook + shouldInterceptRequest 捕获 20 张图片 URL
6. L3 合并去重，返回 20 张图片，构建 MangaPage 列表并设置 imageCount=20
7. 用户正常滚动阅读漫画
8. 滚动到章节末尾，`moveToNextChapter` 自动加载下一章，重复上述流程

### Scenario 2: 视频书源返回播放页，R5 嗅探命中（主流程）

1. 用户打开一本视频书源（bookSourceType=4）的剧集，进入 VideoPlayerActivity
2. VideoPlay 书源分支调用 `WebBook.getContent` 获取章节正文
3. 正文非空且非 `<` 开头，判定为播放页而非视频直链，进入 R5 嗅探链
4. extractPrecise（标签/Meta/JSON/JS 变量）命中真实 m3u8 地址（毫秒级）
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
4. 第 2 章静态解析 0 图，触发嗅探兜底（L2 WebView），成功返回 8 张图
5. 第 2 章图片加载完成，用户继续滚动
6. 到达最后一章末尾，`moveToNextChapter` 返回 false（无下一章），阅读结束，进度正确保存

### Scenario 5: 嗅探全失败降级

1. 图片书源场景：某章节静态解析 0 图，L2 WebView 嗅探 6s 超时且未捕获图片，L3 合并结果仍为空
2. 保持 `imageCount == 0` 分支，进入 `loadFail("正文没有图片")`，用户看到失败提示可重试/退出
3. 视频书源场景：`ruleContent` 返回播放页，extractPrecise / extractWithWebView（6s 超时）/ extractByRegex 全部未命中
4. 回退为 URL 直连：`AnalyzeUrl` → `resolvePlayerPageUrl` → `player.setUp`，保留现有 ExoPlayer 收到 HTML 的报错/降级链路
5. AppLog 记录完整降级链路（L1/L2/L3 或 嗅探链各层命中/失败），不误报协程取消为失败

### Scenario 6: 回归验证（RSS 与既有书源不受影响）

1. RSS 图片源：打开订阅源图片文章，ImageCanvasViewModel L284 调用原 `(RssArticle, RssSource)` 重载，三层降级行为与迁移前一致
2. RSS 视频源：打开订阅源视频文章，VideoPlay RSS 分支（L370-604，含 hasNewRoutesMode 多线路多集、ruleContent 空 → extractPrecise、VIDEO_FALLBACK_WEBVIEW）行为与迁移前一致
3. 文本书源：普通小说书源正常阅读，正文 HTML 化逻辑不受影响
4. 音频书源：歌词获取（putLyric）不受影响，`<` 开头 MPD 视频文本处理（R2.3）行为不变
5. 视频书源单集/singleUrl 模式：`isUserInputEnabled = false` 单页，无空白滑动
6. 覆盖安装升级：数据库无迁移、无新字段，升级后既有书源与设置全部保留
