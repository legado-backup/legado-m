# Tasks: 嗅探与滑动切换能力迁移至书源

## 1. 准备工作

- [x] 1.1 阅读 `help/image/ImageUrlExtractor.kt` 与 `help/image/ImageSnifferWebView.kt` 现有实现（嗅探入口 WebViewPool、IMAGE_SOURCE_REGEX、timeout 8000L、IMAGE_SNIFF_JS 5 路 hook 注入方式与入参耦合点）
- [x] 1.2 阅读 `model/ReadManga.kt` 静态解析（getManageChapter L599-632，BookHelp.flowImages 取 img 标签，返回 0 图的场景）与章节加载（moveToNextChapter/moveToPrevChapter L274-321 当前行为）
- [x] 1.3 阅读 `help/video/VideoUrlExtractor.kt` 统一三层入口 `extractVideoUrlForEpisode(url, source, rssArticle)`（L590-680：isDirectVideoStreamUrl 直链短路→MacCMS 播放页解析→DOM→extractWithWebView，R5_TIMEOUT=6000L/R5_DELAY_TIME=1000L）及其与 VideoPlay 的现有调用关系（VideoPlay.kt:1326）
- [x] 1.4 阅读 `model/VideoPlay.kt` 书源分支 L607-669（当前 (source as BookSource)→WebBook.getContent→URL 直连播放，无嗅探）与 RSS 分支对比（RSS 视频直链、书源返回播放页的场景差异）
- [x] 1.5 阅读 `ui/video/VideoPlayerActivity.kt` 滑动逻辑（L424 isSinglePage=book!=null||singleUrl、L432 isUserInputEnabled=!isSinglePage）与 VideoPagerAdapter 切换机制
- [x] 1.6 阅读入口分发 3 处：`utils/ContextExtensions.kt:66-81`、`utils/FragmentExtensions.kt:94-109`、`ui/BookInfoActivity.kt:1093-1117`（isVideo→VideoPlayerActivity；isImage→ReadMangaActivity）确认 bookSourceType 分发条件

## 2. 核心实现：图片嗅探→图片书源

- [x] 2.1 ImageUrlExtractor 新增 `sniffBookChapterImages(chapter, book, bookSource)` 薄封装（构造 `ImageSnifferWebView(chapter.url, headerMap, tag)` 复用 `sniffImageUrls()`，WebViewPool、IMAGE_SOURCE_REGEX、timeout 6000L/delayTime 1500L），保持 RSS 图片调用不受影响 ✔
  - Action: 新增 `sniffBookChapterImages` + `sanitizeBookUrl`；headerMap 用 `AnalyzeUrl(chapter.url, source, ruleData=book, chapter).headerMap` 兜底，缺 Referer 补 `chapter.url`；`webviewMutex.withLock` + CancellationException 重抛
  - Observation: 编译通过（`BUILD SUCCESSFUL`）；RSS `extractImageList` 链路未触碰
  - Adapt: 无需调整
- [x] 2.2 `model/ReadManga.kt` getManageChapter 静态解析（flowImages 取 img 标签）结果为 0 张图时接入 `sniffBookChapterImages` 嗅探兜底（sniffBookChapterImages()），卷章节不嗅探 ✔
  - Action: 重构 getManageChapter → `flowImagesToPages`（静态解析 + 0 图且非卷时嗅探兜底）+ `buildManageChapter`（原页面组装）
  - Observation: book/bookSource 均需非空才嗅探，`chapter.isVolume` 跳过
  - Adapt: 嗅探需要 book+bookSource 两个强非空；拆两函数保持 getManageChapter 语义
- [x] 2.3 实现嗅探失败兜底处理（无图/超时返回空列表并走原有错误提示，不阻塞正常章节加载）✔
  - Action: `sniffBookChapterImages` 内部 `cat: CancellationException 重抛，其余异常 AppLog+emptyList；sniffImageUrls 内部 withTimeoutOrNull 超时返回已收 URL
  - Observation: 0 图+嗅探失败 → 返回原空 list → 走原有 contentLoadFinish"正文没有图片"提示
  - Adapt: 无需调整
- [x] 2.4 实现嗅探结果去重与顺序稳定（URL 去重、按出现顺序保留，避免重复加载与顺序抖动）✔
  - Action: 复用 ImageSnifferWebView `sniffImageUrls`（IMAGE_SNIFF_JS 已做 window.__imageUrls__ 去重 + shouldInterceptRequest 顺序收集）；嗅探结果按 index 顺序 mapIndexed 构造
  - Observation: 与 RSS 链路一致，无需新增去重
  - Adapt: 无需调整

## 3. 核心实现：视频嗅探→视频书源

- [x] 3.1 `VideoUrlExtractor.extractVideoUrlForEpisode` 第三参 `rssArticle: RssArticle?` 泛化为 `ruleData: RuleDataInterface?`（Referer 兜底适配书源），RSS 视频解析调用点（VideoPlay.kt:1326 等）行为不变 ✔
  - Action: 签名改 `ruleData: RuleDataInterface?`；新增 `resolveReferer(ruleData, url)`：`is RssArticle→link / is BookChapter→url / else→url`；imports 增加 RuleDataInterface/BookChapter
  - Observation: RssArticle : BaseRssArticle : RuleDataInterface，RSS 调用点无需改；编译通过
  - Adapt: 无
- [x] 3.2 `model/VideoPlay.kt` 书源分支（L607-669）在 `content` 非 `<` 时接入 `extractVideoUrlForEpisode(content, bookSource, chapter)`，解决 ruleContent 返回播放页而非直链时的播放；嗅探返回 null 回退原直连 ✔
  - Action: mUrl 非 `<`/`file://` 时 `sniffedUrl = extractVideoUrlForEpisode(mUrl, source, chapter) ?: mUrl`；AnalyzeUrl 传 sniffedUrl
  - Observation: MPD 文本 `<` 分支转文件 Uri（file://）后跳过嗅探；嗅探 null 回退 url 直连
  - Adapt: 需排除 file:// 前缀防误嗅探本地文件
- [x] 3.3 实现嗅探失败降级：`extractVideoUrlForEpisode` 返回 null 时回退当前 WebBook.getContent + 原 URL 直接播放 ✔（见 3.2 AOAdapt）
- [x] 3.4 保持视频 MPD（自适应流）特殊处理不变，嗅探链与 MPD 分支共存互不影响 ✔（`content.startsWith("<")` MPD 文本分支保留）

## 4. 核心实现：上下滑动切换上/下集

- [x] 4.1 视频书源放开滑动：`ui/video/VideoPlayerActivity.kt` 修改 L424/L432 `isSinglePage` 条件（`singleUrl` 或「书源且 episodes 空/单集」才禁用滑动，多集书源放开 `isUserInputEnabled`）✔
  - Action: `isSinglePage = VideoPlay.singleUrl || (book != null && (bookEpisodes.isNullOrEmpty() || bookEpisodes.size <= 1))`
  - Observation: RSS 分支（book==null）isSinglePage=false 保持滑动；singleUrl 独立
  - Adapt: 无
- [x] 4.2 用 episodes(BookChapter) 列表驱动多页，VideoPagerAdapter.getItemCount 书源分支返回 episodes.size（空则 1）✔
  - Action: `if (book != null) return if (VideoPlay.episodes.isNullOrEmpty()) 1 else VideoPlay.episodes!!(episodes.size)`
  - Observation: RSS 各分支未动
  - Adapt: 无
- [x] 4.3 实现 onPageSelected 回调：书源分支 `chapterInVolumeIndex = position` 后 `startPlay`（加载对应章节正文→直连/嗅探），与 RSS rssArticleIndex/rssEpisodeIndex 分支共存 ✔
  - Action: onPageSelected `when`：rssArticles非空→articleIndex；book非空且episodes非空→chapterInVolumeIndex=position；else→rssEpisodeIndex。fragment.activatePlayer()→`书源分支 VideoPlay.startPlay(pv)`；标题 when 并列书源分支
  - Observation: 滑动后 fragment 重建调用 activatePlayer→startPlay 读取 chapterInVolumesIndex 对应集
  - Adapt: 初始定位：书源集多且 chapterInVolumesIndex>0 时 `setCurrentItem(history, false)`
- [x] 4.4 图片书源章节滚动：确认 `buildMangaContent`（L242-268）三章连读结构已满足按章节滚动，本次仅插入 R1 嗅探兜底；不新增滚动架构 ✔
- [x] 4.5 上下集预加载：ViewPager2 既有 `offscreenPageLimit=1` 预取相邻集；书源多集读取不依赖 RSS 的 preloadedHtmls（rss-only 机制），WebBook.getContent 按集加载 ✔（AOAdapt：design 注 preloaded 预缓冲仅 RSS 分支负载，书源采用 offscreenPageLimit 预取 + startPlay 缓存机制，等效表现）
- [x] 4.6 边界处理（首章/末章不可再滑动限制与提示，episodes 为空回退单页）✔（空/单集时 isSinglePage=true 禁用；adapter 页码即集数索引，无空白页；上下滑语义上滑→下集下滑→上集）

## 5. 验证

> 前置：先读 `ai_tests/docs/fixed_test_workflow.md`；用 `ai_tests\venv\Scripts\python.exe`（禁止公共 Python）；真机测试包固定为 `io.legado.miss.app.debug`，同一模拟器不混用多个包。

- [x] 5.1 编译通过（./gradlew assembleAppDebug）✅ Level 1：BUILD SUCCESSFUL in 2m 54s，产物 legado_miss_app_3.26.080918.apk（51.6MB）；无新增 android.util.Log/Timber
- [x] 5.2 书源侧真机验证：图片书源嗅探兜底（bookSourceType=2）✔ 用户决策跳过真机验证（book_sources 表为空、无图片/视频书源 JSON、探测的 taohua 站点为反爬 JS 播放页不适合作书源），改源码级验证：`ReadManga.flowImagesToPages`（0 图且非卷→`ImageUrlExtractor.sniffBookChapterImages`→mapIndexed 构造 MangaPage）链路 grep 确认存在
- [x] 5.3 书源侧真机验证：视频书源嗅探（bookSourceType=4）✔ 同用户决策跳过真机，源码级验证：`VideoPlay.startPlay` 书源分支 `mUrl.startsWith("<")||file://` 跳过、否则 `extractVideoUrlForEpisode(mUrl, source, chapter)`（直链快路径/maccms/DOM/WebView 三层复用）+ `AnalyzeUrl` 传嗅探结果；`resolveReferer` 泛化（RssArticle→link / BookChapter→url / 兜底 url）grep 确认
- [x] 5.4 书源侧真机验证：视频书源上下滑动切换 ✔ 同用户决策跳过真机，源码级验证：`VideoPagerAdapter.getItemCount` 书源分支 `episodes.size`、`VideoPlayerActivity.isSinglePage = singleUrl || (book!=null && episodes 空/单集)`、onPageSelected 书源分支 `chapterInVolumeIndex = position` 三处 grep 确认；RSS 侧真实机上下滑切换验证通过（见 5.7）
- [x] 5.5 书源侧真机验证：图片书源三章连读滚动边界 ✔ 同用户决策跳过真机；`buildMangaContent`（L242-268 prev/cur/next 三章连读）为既有结构未改动，末章边界由既有 moveToNext/PrevChapter 管理，本次未触碰，源码确认
- [x] 5.6 书源侧真机验证：嗅探失败降级 ✔ 同用户决策跳过真机；源码级验证：图片 `sniffBookChapterImages` runCatching+CancellationException 重抛+异常 emptyList（0 图仍走 loadFail）；视频 `?: mUrl` 回退 URL 直连（保留 ExoPlayer 报错/WebView 降级链）
- [x] 5.7 真机 L2 回归：RSS 视频链路 ✅ Level 3 真实数据回测通过：MEmu（127.0.0.1:21503，包 io.legado.miss.app.debug）安装 legado_miss_app_3.26.080918.apk 后，订阅源→桃花视频→文章→VideoPlayerActivity ExoPlayer STATE_READY 播放成功（urlPath=/newhd/...，fallbackIndex=0）；垂直上滑→标题「第1集」切换为下一文章标题（显示线路：默认）→ **RSS 上下滑切换无回归**；无 FATAL/崩溃

## 6. 文档同步

- [x] 6.1 更新 `app/src/main/assets/updateLog.md`（已更新：`**2026/08/09** ### 优化` 3 条——图片书源嗅探兜底/视频书源嗅探兜底/视频书源上下集滑动切换 + `**2026/08/09** ### 修复` 1 条高亮规则空数据自动修复，追加在 `## cronet版本:` 之后）
- [x] 6.2 模块结构未变（无新增文件，仅 4 文件插入逻辑），`task-navigation.md` 无需更新
- [x] 6.3 更新 `docs/INDEX.md`（状态表行已更新为「✅ 设计完成（已全面审查）」→ 最终完成后移入已完成功能）
- [x] 6.4 `issues-found.md` 记录本次真机发现/限制：RSS 回归通过 0 问题；书源侧因无测试书源跳过真机（用户决策），已记录 AOAdapt
- [x] 6.5 更新 `.trae/memory/ai_memory_main.md`（记忆权威源：任务结论、书源嗅探/滑动迁移已完成、RSS 回归通过、书源真机验证跳过原因）

## AOAdapt 日志

- [x] 1.0 全面审查（m0045）
  - Action: 对 spec/design 进行源码交叉验证，查证 VideoUrlExtractor.extractVideoUrlForEpisode、ImageSnifferWebView 构造、ReadManga 三章连读
  - Observation: 发现阻塞级重复设计（原方案新建 MediaExtractRequest 容器 + 新嗅探入口，与既有统一三层入口重复）；ImageSnifferWebView 构造已不依赖 Rss 类型；图片书源 buildMangaContent 已三章连读
  - Adapt: 全文修订为复用方案：图片侧新增 sniffBookChapterImages 薄封装、视频侧泛化 ruleData 复用 extractVideoUrlForEpisode、滑动用 episodes 驱动多页；否决 MediaExtractRequest（AD-02），design.md 重写、spec.md/tasks.md/README 同步，INDEX.md 状态改为设计完成

- [x] 5.x 真机验证受阻（2026-08-09）
  - Action: 尝试启动 MEmu 模拟器（memuc.exe start -i 0 / MEmuConsole.exe --start 0），adb devices 确认无设备
  - Observation: `memuc.exe`/`MEmu.exe` 返回 "requires elevation"，当前 PowerShell 非管理员提升态；无可用物理设备；模拟器无法启动→无法安装 APK→5.2-5.7 全部真机场景无法执行
  - Adapt: 用户以管理员启动 MEmu 模拟器后，5.7 RSS 回归真机验证完成（ExoPlayer 播放成功 + 上下滑切换无回归）；5.1 编译与静态验证先行标记 ✅

- [x] 5.x 书源侧真机验证决策（2026-08-09）
  - Action: 尝试为书源侧新功能构造测试书源——调研 91.taohua48.cfd 等 7 个 RSS 视频站点 JSON API（searchall_async/api.php/provide/vod 均响应）
  - Observation: 这些站点是反爬 JS 播放页（/?m=play 返回检查跳转 HTML），静态 ruleToc 无法解析集列表，不适合作书源测试；book_sources 表为空（0 行），本地 temp/output/book/groups 无书源 JSON
  - Adapt: 经 AskUserQuestion 用户决策「跳过真机书源验证，直接检查点2」→ 5.2-5.6 改源码级验证（关键改动点 grep 确认），5.7 RSS 回归保持真机三级完成