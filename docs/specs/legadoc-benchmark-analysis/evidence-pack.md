# 证据包 — legadoC（阅读C）vs 本项目（8 轮分析汇总）

> 用途：迁移设计起草的统一事实源（独立于 NG 任务）。
> legadoC 根：`F:\myself\github\WeAgentChat\temp\legadoC_src\legadoC-own`（own 分支，v3.26.082723c，2026-08-27；71 stars；包名 io.legado.app.c；targetSdk 36；DB v112）
> 血统：阅读R ← Rimchars/legado（Archive）← lyc——与本项目（Sigma 系）**不同源**；纯 View 体系 0 Compose（README 明确不吸收 Compose 重构）
> 本项目根：f:\myself\github\WeAgentChat\temp\legado（DB v108）

## A. 朗读架构原语化重构（legadoC 最大差异化，与 NG 多角色正交可叠加）

核心思想：引擎只发布"读到哪里"（generation 单调防乱序事件流），显示跟随/翻页/高亮全部 UI 侧纯函数现算派生，引擎与显示零直写。

| 模块 | 实现 | 关键位置（LC/=legadoC） |
|------|------|------|
| 位置货币 | ReadAloudPosition（章节绝对字符位）+ ReadAloudPositionUpdate + generation 单调 + isCurrentPosition 消费端丢弃过期 | LC/model/ReadAloud.kt:40-125 |
| 发布点契约 | 引擎私有光标仅自读写，对外仅 publishAloudPosition/publishParagraphProgress 两发布点（注释明文） | LC/service/BaseReadAloudService.kt:166-174/:130/:1102-1148/:1157/:1275-1284/:1301-1357/:1864-1906 |
| 纯函数跟随 | shouldFollowAloudAdvance（prev!=null&&同章&&前进&&显示页==出发页）——无任何存储跟随状态；isViewBehindAloud 派生脱节；ReaderPanelMode 纯派生 | LC/ui/book/read/ReadBookActivity.kt:2083-2095/:2101-2110、model/ReadAloudUiState.kt:53-61 |
| 原语 A/B | setAloudStart（只写朗读起点，:2231-2280）/backToAloudProgress（唯一允许直写显示，:2112-2135/:2137）；强制追页=翻页翻译成 restartFromPage（:2289-2301） | 同上 |
| 绘制期投影 | TextLine.isReadAloud 为 get() 现算（非存储字段），绘制时直接消费；AloudSpan 存储态已彻底删除 | LC/ui/book/read/page/entities/TextLine.kt:74-82、ReadView.kt:1075 |
| 预测换页 | 系统 TTS：measuredCharRate EMA（rate=rate*0.7+sample*0.3，>500ms 采样）+ schedulePageBreakPrediction（breakOffset/rate）+ speakGeneration 防乱序；HTTP 引擎：ExoPlayer duration/字符数 真实步长，流式无时长退化 lastCharDurationMs（初值 100ms）；预测只影响发布时机不影响翻页 | LC/service/TTSReadAloudService.kt:67-75/:180-206/:996-1047、HttpReadAloudService.kt:775-815（:792/:108）、BaseReadAloudService.kt:289-292 契约 |

本项目反差：BaseReadAloudService.kt:375/:401/:783/:790 直调 ReadBook.moveTo*；HttpReadAloudService.kt:562 播放过界直翻页、:548 duration<=0 直接 return（无流式兜底）；TTS_PROGRESS 事件有发布无观察者（BaseReadAloudService.kt:357 postEvent）；高亮为页级存储态 removePageAloudSpan（ReadBook.kt:554）；readAloudByPage 单键未拆。
**双向断裂（V1 回灌，"死事件"表述升级）**：本项目事件链为双向断裂——①TTS_PROGRESS 有发布无观察者（BaseReadAloudService.kt:357 postEvent，全库零 observeEvent 订阅）；②READ_ALOUD_PROGRESS 有观察者无发布者（ReadBookActivity.kt:5135-5156 孤儿观察者，内含 :5145 ReadBook.durChapterPos 直写 + :5148 upPageAloudSpan 页级高亮直写）——发布侧/观察侧各断一头，与 legadoC "引擎只发布、UI 纯派生"契约形成正交反差。
迁移面（三步，合计 3.5-4.5 天）：①发布层新建 ~250 行（0.5d）②引擎侧去直写（1.5-2d）③UI 跟随+绘制投影（1.5-2d+真机回归，风险集中绘制路径）。

## B. 多媒体插入体系（本项目完全空白）

- 锚点：IllustrationAnchor（between_paragraphs/chapter_end，anchorPos=段落字符偏移+前后段文本指纹校验，help/illustration/IllustrationAnchor.kt:10-15）
- 存储：BookIllustration 实体（books CASCADE，含 pdfPage/pdfRect）+ illustration://UUID.ext URI + externalFiles/illustrations/{bookFolder}/；随书导出/导入（EPUB sidecar legado_illustrations.json，IllustrationHelp.kt:43-103）
- 排版：TextChapterLayout 生成 ImageColumn（图片/视频/音频三媒体，音频独立块；宫格/独占一页，ImageColumn.kt:22-33/:216-238）
- 播放：音频内嵌 AudioBlockPlayer（ExoPlayer 全局单例+翻页续播+进度绘制+触摸 seek，ContentTextView.kt:1229-1241 点击分发）；视频/图片弹 PhotoDialog（ViewPager+逐项 ExoPlayer，PhotoDialog.kt:44-196）
- 目录页 IllustrationFragment/Adapter；编辑入口 IllustrationEditDialog（:31-43）
- 量级：~15 类，2-3 周（Room 迁移+排版引擎改造）

## C. AI 体系（与本项目同源 ui/main/ai 包，legadoC 分层更细）

- **AI 章节净化**（核心差异化）：AI 不改写正文，生成替换净化规则沉淀进替换体系——RULE_GROUP="AI净化"（AiChapterPurifyService.kt:25），三类 typo/noise/ad（Config.kt:25），scope=[书名,源URL]+scopeContent=true+字面去重（:363-388）；幂等=缓存原文 SHA-256 指纹+AiChapterPurifyRecord 表（:65-98）；链路=ReadBookActivity.startAiChapterPurify:3059→Service→ContentProcessor 预处理:105-113→Helper.generateRules:108（分块+Semaphore 1-8+重试 0-10）→AiChatService.generateStructuredText（temperature=0）→parseAndValidate:309→入库→upReplaceRules 热刷新；markChapterEdited 用户编辑即永不重跑（:287-321）。量级 3-5 天（本项目已有同协议 AiChatService，缺 generateStructuredText+规则沉淀）。
- **AI 创作工作台（生图）**：AiCreationDialog（TabLayout+创作卡片 creationCardDao，ReadBookActivity.kt:1339/1393）→AiCreationHelper.generatePrompt（聊天模型润色）→ImageTaskHolder（并发 3，失败转串行，429 实证）→OpenAI images 风格 POST+b64_json/url 双协议+模板渲染 {{model}}/{{prompt}}/{{n}}+变量（ImageHelper.kt:316-384）→filesDir/creation_results→MediaStore 相册→浮动状态球；独立 AiCreationProviderConfig 9 字段+内置 4 家+testConnection 真实出图；生视频=半成品仅 testConnection（CogVideoX/Wan 轮询）。量级 1-2 周（只迁图片链）。
- **生图执行层超集（V1 回灌）**：本项目已有完整生图执行层——AiImageService 四协议 generateByOpenAi:86/generateByImagesApi:98/generateByResponses:144/generateByJs:221（help/ai/AiImageService.kt）+b64/url 归一（:355 base64 补 data:image 前缀、:381 b64_json/base64/b64 三键提取）+32MB 防线（MAX_IMAGE_BYTES=32*1024*1024 :30，:438/:457 消费；另有响应上限 48MB :31）；AiImageProviderConfig 17 字段（ui/main/ai/AiConfigModels.kt:173-190）+AiGeneratedImage 22 字段实体（data/entities/AiGeneratedImage.kt:19-42，含书/章节/角色溯源+favorite+groupId）+图库管理。**legadoC 仅贡献编排层**（三级降级批量/浮动状态球），执行层零迁移成本。
- **听书 AI**：AiStoryboardConfig（分镜模型配置 :18）+AiMultiVoiceDialog（多音色）+BookRole 角色卡——与 NG 分镜方向类似但更浅。
- **供应商分层**：聊天 AiProviderConfig 5 字段+独立 AiModelConfig（providerId+modelId 按场景引用）+生图/视频独立 ProviderConfig 9 字段+技能包（AiSkillConfig content+sourceUrl）+MCP Client+ServerConfig；OpenAI 兼容+SSE+tools+SSE_IDLE 看门狗（AiChatService.kt:827/:1270-1272）。
- **澄清（V1 回灌）**：本项目 SourceContentFilter（help/source/SourceContentFilter.kt:22 object）是**统一 WebView 资源 URL 过滤**（filterUrl:30 黑名单优先 startsWith/regex→拦截、黑名单空时白名单命中→放行），**非正文净化**——与 AI 章节净化（替换规则沉淀）零交集，勿在迁移评估中混淆两者职责。

## D. 文音融合（AudioTextFusion 全家桶，legadoC 独有）

AudioTextFusion.kt:44（681 行）：文本书+有声书按章节/卷配对（pairChapters:295/volumeCompatible:369）→正文段落 overlay JSON 写入音频书 lyric 字段（OverlayInsertion:70/fuseOverlayDetailed:416/applyOverlay:460）实现"听书带字"；SourceAudioResolver:12 解析音频源 media 地址+AudioTextMapping 时间轴；SourceAudioReadAloudService（365 行）书源音频朗读服务；融合数据存 chapters.variable 键 audioTextFusion 不冲原始 lyric（:46-47），reconcile 事务可回滚。与本项目 AudioPlay/AudioPlayService 体系并存冲突，需产品决策。

## E. 前端 UI（纯 View，番茄化）

- 番茄化：悬浮玻璃胶囊底栏（24dp 圆角+solid/glass/frosted 三态+可切 floating/sidebar+独立悬浮搜索球，activity_main.xml:35-104）；书架 style1/style2 双样式+长按多选拖拽；阅读菜单沉浸式+局部模糊只模糊自身+200ms 淡入淡出（ReadMenu.kt:71-90/:458-528 menuBlurGeneration 代数防乱序）；弹窗统一底部操作区。
- 合集书架：book_collections+book_collection_items（双 CASCADE）+book_collection_children（自关联树）+book_shortcuts（books CASCADE+collections SET_NULL 双外键）；虚拟 Book 模式（BookType.notShelf 位+body.copy 注入不落库，BookShortcutHelp.kt:18-160）；马赛克拼图封面（2x2 空位 INVISIBLE，BookCollectionCover:21-28）；递归 CTE 树查询+应用层环检测（BookCollectionDao:149-289）。
- 合集并存裁决（V1 回灌）：本项目 BookType.notShelf 位**已存在**（constant/BookType.kt:54=0b100_0000_0000，注释"1024 未正式加入书架的临时阅读书籍"；BookDao 实测 11 处引用：9 处 `WHERE (type & notShelf)=0` 过滤 :75-:185 + :192 isNotShelf 投影 + :422 delete）——legadoC 虚拟 Book 模式的位基础设施本项目同款，非纯外借概念；C3 裁决：**BookGroup 与合集并存**（不替换现有分组体系），matchesGroup 虚拟组映射衔接。
- 发现页 RowUi 规则驱动渲染：ExploreKind（url/text/button/toggle/select）→DiscoverTagItem.toDiscoverRowUi（ExploreFragment.kt:1010-1024）→RowUiDialog→RowUiForm.render（FlexboxLayout 五控件 :55-66）→onValueChanged/onAction 回填重载；登录 UI 同链（loginUi JSON+`<js>` 动态，SourceLoginDialog.kt:141-155/:248-249）。本项目 RowUi 实体与 legadoC **主构造 7 字段逐字段一致**（name/type/action/chars/default/viewName/style；差异在类体成员：legadoC 多 isChoice:31/isAction:34/modernBackgroundRes:37 计算属性+applyModernStyle:44，见 legadoC data/entities/rule/RowUi.kt）；ExploreFragment **非无接线**，实有≈500 行散装 Flexbox 等价实现（renderDiscoverDialog{Kinds:2225/Url:2255/Button:2305/Toggle:2324/Select:2376/TextInput:2422} 6 函数，散装区间 ExploreFragment.kt:2225-2651 含 create/bind/eval 辅助）——C3 定位=**"收敛替换"非"从零接线"**。
- 设计系统：lib/theme/UiCorner.kt 三表面组 SurfaceGroup{UI,READING,DIALOG}+groupColor 唯一分派（:15-19/:118-127）+四轨透明度链（uiLayoutSurfaceAlpha→floatingGroupAlpha→{bookshelfCoverAlpha 独立轨/readingGroupAlpha=菜单α×全局α}，:69-103）+dialogBlurRadius 10-34dp；surface/SurfaceStyle.kt 可调表面唯一视觉描述 data class+SurfaceStyles 工厂；view/ 9 组件族；ReaderSheetStyle Palette 8 色明暗混色。
- 朗读面板动画纪律：动画入口收束主线程（view.post/buildMainHandler）+代数防乱序（menuBlurGeneration）+animator 单持有。
- 桌面小组件×2：ReadGoalWidget/ReadRankWidget（legadoC 独有）。

## F. 用户日志勾选体系（legadoC 独有）

LogModule.kt:14-24 十模块枚举（GENERAL 兜底常显+9 可勾选）+classify() 单点按调用方类名自动归属（:68-154，pinnedByClassPrefix 钉定表防嵌套双归属）+AppLog 100 条内存环+filesDir/app.log Base64 持久化重启恢复（AppLog.kt:146-177）+logsForView 按勾选过滤；"记录调试日志开关已删"（调试日志始终记录，putDebug :135-144）。对比本项目 AppLog=AI 采集向（26 TAG 常量 adb logcat -s 过滤），互补。

## G. 工程治理

- AGENTS.md 319 行宪法式：工作模式五级分层（纯编码默认禁编译测试/真机绝对禁令）；构建纪律 >30s 必须后台+30s 轮询+退出码/产物校验；交付产物 aapt dump badging+apksigner verify 退出码门禁；版本基线单点滚动。
- 双仓防泄露：.githooks/pre-push 禁直推 own+commit-msg 中文校验；publish-oss-source.ps1=git filter-repo 剥离 6 条专有路径+全历史零命中校验+双仓双历史。
- CI：❗workflows 已于 2026-08-22 全部移除（AGENTS.md:309"不得重新引入"），纯本地构建链 gradlew :app:assembleAppC -Pabi=arm64-v8a -PVERSION_CODE + 签名参数化零密钥入库；冷编译 3m41s 实测。
- DB：v112（migration 10-43+90-112，AutoMigration 止 89→90）；schemas 缺 97/106/111（其债务）；106→107 book_shortcuts 五步重建范式（_new→拷→DROP→RENAME→索引，DatabaseMigrations.kt:182-211）。
- 安全：无 NG 式沙箱；仅 RhinoWrapFactory.register(BookSource, NativeBaseSource.factory) 属性隐藏+BookScriptObject 隐藏 setUseReplaceRule（App.kt:237-248）——只防篡改源状态，不防文件/网络滥用。

## H. 网络层（结论：本项目超集）

legadoC 14 个 http 文件本项目全有；本项目独有 8 个（DoH 448 行/HttpCaptureHelper 403/NetworkLog 343/StreamResetRetry/RedirectCache/UrlRecord/FaviconCache/NetworkLogInterceptor，+2641 行）。legadoC 保留原版缺陷（CookieStore 空值覆盖+随机淘汰；Coroutine.kt 无 CancellationException 守卫——全层唯一 legadoC 落后点，反向确认本项目修复正确）；cronet 128 动态下载（CronetLoader 383 行）+lazy 引擎（主线程触发链 ANR 隐患）；WebView 单池 GLOBAL+discard() 销毁式（Archive 系 closed/isActiveWebView 范式在 legadoC **不存在**）。**唯一可借：WebViewHtmlStore.kt:15-49（49 行，HTML 落盘 filesDir/webview_html/ UUID+白名单校验，解决大 HTML 走 Bundle 触发 Binder 1MB 限制；集成于 BottomWebViewDialog.kt:148-149/:206/:595-601/:884-885 onSaveInstanceState 只传引用）**。

## I. 规则引擎（含本项目 1 个高风险 bug）

- **【本项目高风险 bug】AnalyzeRule 缓存污染**：本项目 makeUpRule（AnalyzeRule.kt:722）原地修改 rule（rule=infoVal.toString()），而 F-P1-C4 已把 stringRuleCache 改 LruCache(64)——缓存命中二次使用时规则残留上次拼接结果。legadoC 引入不可变 ResolvedSourceRule（AnalyzeRule.kt:800 返回 rule/replaceRegex/replacement/paramSize 快照，makeUpRule 不再原地改）正是解法。
  - 污染向量三分（V1 回灌）：**V1**=getStringList 的 LinkedTreeMap 分支（AnalyzeRule.kt:234-236）与 getString 同型分支（:327-329，赋值行 :329）`result[ruleList.first().rule]` 直取**不调 makeUpRule**——绕过拼接路径直读 .rule；**V2**=replaceRegex/replacement/replaceFirst 赋值无清零（:769-780，本次规则无 ## 后缀时三成员残留上次拼接值）；**V3**=递归 getString 重入半更新（:766 `rule = infoVal.toString()` 原地改，重入时 putRule 已写入的半更新态对外可见）。三类向量与 LruCache 命中叠加即触发错规则。
- 章节列表并发去重：legadoC WebBook.kt chapterListJobs: ConcurrentHashMap<String,Deferred>+ChapterListResult(book.copy())+applyChapterListBookState（19 字段回填）防重复拉目录（A=575L vs 本项目 397L）。
- BookScriptObject（help/rhino/BookScriptObject.kt:10-25，39 行）：隐藏 setUseReplaceRule，Book::class 注册 factory（App.kt:245）——补 Rhino 防篡改缺口（本项目 JS 可改替换规则开关）。
- exploreKinds 缓存键：legadoC 多因素 MD5（variable/type/order/hostIndex/host/jsLib/lastUpdateTime）+isValidExploreKindsRule() 校验防坏规则入缓存（BookSourceExtensions.kt）；本项目旧 key=MD5(url+exploreUrl) 无校验。
- 浏览器钩子 3 API：onBrowserOpenRequested:322/onBrowserAwaitRequested:327/getAppVariant:1177（legadoC 独有，评论快照 fallbackBrowserHtml/fallbackReviewResourceBook 配套）。
- 本项目独有保留：SourceNetworkClient 封装/sortUrlJsExecutor 线程修复/RSS 搜索/网络重试/Cookie 合并 P5/LruCache 全局缓存/RssArticle idx_origin_sort 索引/SourceHelp 进程内缓存。

## J. 数据层（legadoC v112；两侧分叉）

legadoC 独有实体 13：BookCollection/BookCollectionItem（双 CASCADE）/BookCollectionChild（自关联树）/BookShortcut（双外键 CASCADE+SET_NULL）/BookIllustration/AiChapterPurifyRecord（(bookUrl,chapterIndex) 主键+SHA-256 指纹）/CreationCard/CreationResult/BookRole（workKey 正式角色卡）/BookTtsCastRole（identityState stable/pending/guest 状态机）/BookTtsVoiceBinding（(workKey,targetType,targetId)+engineId v112 加列）/TtsEngineRuntimeEntity/TtsVoiceEntity。独有 DAO 9（BookCollectionDao 含递归 CTE+环检测+事务 move；BookRoleDao 一管三表）。同名差异：Book 多 mediaType Int+索引降级 (name,author,mediaType)+ReadConfig.aiChapterPurifyEnabled/sourceAudio*+@Ignore shortcutId；Bookmark 多 style 位掩码/styleColors/isPageBookmark；BookSource/RssSource 本项目多 lastHost 等。演进链 105→112 每版见 DatabaseMigrations.kt:39-236。亮点：虚拟 Book（BookType.notShelf 位+FK 占位）、fusion overlay 存 variable、workKey 稳定键。警示：版本号不可照抄（两侧 v108 不同 schema）；FK 表变更走 _new 五步范式；mediaType 引入需降级唯一索引；Bookmark style 一步建终态。

## K. UI 全景

Activity：legadoC 62 vs 本项目 110。legadoC 独有：BookCollectionActivity（藏书阁马赛克）/BookTocLoadingActivity/TtsEngineManageActivity/AiCreation 三对话框/IllustrationFragment/IllustrationEditDialog/2 桌面小组件。本项目独有：外观套件 6/容器管理 4/AI 套件 6/角色分段规则 7/调试 7/管理 3/订阅搜索 3/其他 8 + Service 独有 6（AutoTask/Relay/WebDavTask/CheckRssSource/AiTaskKeepAlive/AudioPlayService）。反向核对 8 项 7 独有（modern-rss 两侧共有）。朗读 UI：legadoC=对话框内嵌形态（悬浮窗仅开关）；本项目=三形态体系（系统悬浮窗/应用胶囊/播放面板）。设计系统：legadoC lib/theme 21 文件（UiCorner+SurfaceStyle+9 组件族）vs 本项目 22 文件（View 族 1:1 同构+ui/theme Compose 补充层+App* 组件族 60+）。Web 前端：+686 行全为本项目 BackupManager 新增。

## L. 工程与安全

CI 双方均无（legadoC 已删除 workflows 且禁止恢复；本地链+签名参数化+产物 aapt/apksigner 验证纪律）；本项目 bat 编排+ai_tests。targetSdk 双 36（legadoC minSdk 21 vs 本项目 23）。安全：legadoC 仅属性隐藏级，无沙箱——NG 安全体系仍是唯一对标源。日誌：legadoC 用户勾选向 vs 本项目 AI 采集向，互补可叠加。
