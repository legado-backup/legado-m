# 证据包 — legado_NG vs 本项目（8 轮子代理分析汇总）

> 用途：迁移设计起草的统一事实源。所有结论均有 NG/本项目源码路径证据。
> NG 根：`F:\myself\github\WeAgentChat\temp\legado_NG_src\legado_NG-main`（快照 3.26.082815）
> 本项目根：`f:\myself\github\WeAgentChat\temp\legado`（DB v108）

## A. 网络层（结论：本项目超集，仅 2 项可借）

本项目领先（NG 无增量，无需动）：HttpHelper 拦截器布线（FaviconCache/RedirectCache/DoH/StreamResetRetry/UrlRecord）、DecompressInterceptor(Brotli+回退)、OkHttpUtils 307/308、SSLHelper TLS、OkHttpExceptionInterceptor(CancellationException 守卫+host 定位)、NetworkLog 持久化(logs/ 7 天)、CookieStore(P18/P6/P9+LRU tracking 淘汰)、CookieManager(issue7+runBlocking(IO))、Coroutine.kt 取消守卫、WebViewPool(多 Scope GLOBAL/DISCOVERY/RSS+resettingPool+destroyOnMainThread+trimMemory+pauseTimers 互斥，回池清理为 NG 超集)、CronetInterceptor 熔断降级、CronetHelper ANR 修复、cronet-bundled=500.0.1 锁定路线、BackstageWebView(嗅探注入/60s 超时/存活守卫)。

NG 可借鉴（2 项）：
1. 按源 Cookie 命名空间：`help/http/BookSourceCookieStore.kt:25-175`（`book_source_cookie_{ns}:` 前缀+persistent/session 双轨+forSource() 工厂+clear(sourceUrl)）——只借概念，须落在本项目 CookieStore 修复基线上（NG 自身有随机淘汰/null 覆盖缺陷）
2. JSBridge 结果按源缓存：`help/webView/WebJsExtensions.kt` 的 `bookSourceCacheStoreOrNull`（本项目全局 CacheManager 多源互覆）——前置依赖 StorageScope

清理项：本项目死文件 `lib/cronet/CronetInterceptor.kt.bak`。
风险：NG cronet 128 动态下载（CronetLoader.kt 400 行+cronet.json 四 ABI MD5）为单点故障，本项目锁定路线更稳。

## B. 规则引擎/书源执行链（结论：API 无缺口，NG 强在沙箱，本项目强在工程性）

文件清单：analyzeRule/webBook 清单一致（AnalyzeUrl 差 204 行/AnalyzeRule 差 140 行）。help/source/ NG 独有 5 文件：SourceInteractionPolicy/BookSourceFileAccessPolicy/BookSourceStorageScope/BookSourceCacheStore/ExploreKindBehavior；本项目独有 8 文件（SourceNetworkClient/SourceContentFilter/SourceLastHostHelper/SourcePreconnectHelper/SourceRecycleBinHelp/SourceWebViewController/SourceCacheManager/SourceExt）。

JsExtensions：主文件 102 函数签名逐一比对完全一致；任务清单所列 reLoginView/refreshBookToc/refreshExplore/refreshContent/@webjs:/StrResponse.callTime/skipRateLimit 本项目**均已具备**；本项目独有 refreshParagraph/clearTtsCache/ParagraphRuleJsExtensions 全族/showBrowser 增强。NG 无本项目缺失 JS API。

NG 三层安全开关（全部嵌求值入口）：
1. 类导入白名单：`modules/rhino/.../RhinoClassShutter.withBookSourceClassPolicy(enabled=source is BookSource)`（NG BaseSourceExtensions.kt:25-32；ThreadLocal 深度计数可重入；书源模式 io.legado.app.* 白名单仅 {StrResponse}，RhinoClassShutter.kt:56-58；封 android.webkit.CookieManager；RhinoClassShutter.kt:50-55 注释"新增白名单条目需现有书源证据+回归测试"）。接入点 2 处：AnalyzeUrl.kt:375 / AnalyzeRule.kt:831
2. 弹窗拦截：`help/source/SourceInteractionPolicy.kt`（28 行）挂协程上下文（SearchModel.kt:46/BookInfoViewModel.kt:321/ChangeBookSourceViewModel.kt:102），requireSourceDialogAllowed 抛 SourceInteractionBlockedException，防批量流程中书源滥弹验证码
3. 文件沙箱：`BookSourceFileAccessPolicy`（canonical+requireStrictChild）+`BookSourceStorageScope.namespace`=SHA-256("book\0"+sourceUrl)（BookSourceStorageScope.kt:9-13）；NG JsExtensions getFile/readTxtFile/deleteFile/unzipFile 经 resolveBookSourceFile 限 `cache/bookSourceCache/{ns}/`

NG cookie/cache 绑定：bindings["cookie"]=BookSourceCookieStore.forSource（12+ 调用点：BackstageWebView/BottomWebViewDialog/VideoPlayerActivity/WebViewActivity/BookInfoActivity/WebViewLoginFragment 等）；bindings["cache"]=source.scriptCacheObject()→BookSourceCacheStore（~172 行，注册表+删源清理）。NG 存在 CS 覆盖 H 优先级问题，本项目 P5 修复（setCookie 仅补缺失 key）领先。
SharedJsScope：NG 增 scopeNamespace 隔离——**不建议迁**（切断跨源共享 jsLib 生态）。
本项目领先：全局编译/正则 LruCache（script 32/regex 64）、getElements 容错、customIp LruCache(100)、网络自动重试、SourceNetworkClient 收敛 loginCheck 样板、RSS 并行解析（Semaphore 限流）、RSS 搜索（RssSearchModel 319 行）、sortUrl JS 防死锁（30s future）。
NG ExploreKindBehavior.kt：发现页 8 种 renderRole 归一——仅设计参考。

## C. 数据层（结论：基线已分叉，迁移须重写版本链）

NG v114：entities 42 文件/dao 27；本项目 v108：entities 69/dao 44（本项目广度大）。**两侧 v108 已分叉**（本项目独有 35 张表：ai_agent_sessions/jobs/traces、ai_memory_*+fts、read_aloud_bgm_*、paragraph_rules、cover_gallery_*、download_tasks、source_recycle_bin、playHistories 等；NG v108 独有 13 张 AI/角色表）。**不能复用 NG migration_108_109..113_114，必须以本项目 108.json 为起点重写版本链**。

NG 新增 13 实体：AiChatConversation/AiChatMessageNode(消息树分支+selectIndex)/AiSkill(scope AGENT+builtIn)/AgentMemory(3 组索引)/AgentToolExecutionIntent(contentHash+argumentsHash 防重放)/AgentToolResultArtifact/AgentToolReceiptAcknowledgement(复合 PK 消费关系)/BookCharacterProfile(workKey=normalize(书名)\n作者，抗 bookUrl 变化)/BookCharacter(workKey 维度)/BookTtsCastRole/BookCharacterTtsBinding(复合 PK 5 类绑定)/BookTtsCastRoleContribution(可重建缓存)/TtsVoiceEntity/TtsEngineRuntimeEntity。新增 DAO 6 个。

v108→v114 演进：v109 ignored 列/v110 6 列/v111 contributions 表/v112 binding 2 列/**v113 DROP httpTTS（破坏性）**/v114 bookmarks+5 列(高亮方案冲突：本项目用独立 highlights 表)。

**同名不同构冲突**：本项目 BookCharacter（bookUrl 维度，speechRouteJson/roleLevel/skills）vs NG（workKey 维度+FK CASCADE）——引入前必须合并/改名。search_keywords 结构冲突（本项目 (word,type) 复合主键保留）。httpTTS 本项目有扩展在用，**不照搬 NG v113 DROP**。

NG 数据层亮点：全列显式 @ColumnInfo(defaultValue)（增量迁移免回填）、JSON-in-TEXT+三哈希幂等、语义/缓存/消费三层分离、workKey 归一化域键。

## D. UI/服务全景（结论：NG=AI+TTS+设计系统纵深；本项目=广度+视频多媒体）

NG 新增 5 Activity：ReadAloudPlayerActivity（全屏播放+9 动效渲染器）/BookCharacterActivity/BookCharacterTtsActivity/BookStoryboardActivity/AiChatActivity（本项目已有 ui/main/ai/AiChatActivity，平移非缺失）+1 Service：McpService（dataSync 前台）。
NG 独有 ui 子包：**ui/design**（design/theme 6 文件+design/components/compose 35 组件+view 10 组件）。
本项目独有 ui 子包 9 个：adapter/autoTask/debug/download/highlight/image/theme/urlrecord/welcome。
反向核对（本项目独有，NG 无）：视频增强套件（NG help/exoplayer 仅 1 文件 vs 本项目 11 文件；ui/video 14 vs 4；无 PiP）、订阅现代模式（modern-rss 嵌入式）、自动任务（0 命中）、中继隧道、调试工具、外观套件、图片画廊。高亮：NG 仅有 ReadHighlightRule 数据类弱等价（无管理 UI/无 matcher 引擎族 9 文件）。
NG 模块边界模式：「能力引擎进 help/<域>，UI 薄壳进 ui/<域>，跨端协议进 web/<域>」，包名即模块。
Web 前端几乎同源（78 vs 80 文件，仅本项目多 backupRouter+BackupManager.vue）。

## E. AI 体系（详见第一轮报告，关键事实）

供应商抽象：AiProvider 接口→3 协议实现（OpenAiCompatible/GoogleAi/Claude）；AiProviderSetting 24 字段超参数化（gson alternate 短 key）；AiDefaultProviders 12 家预设；AiManager 单例路由；AiModelRegistry 能力富化。关键文件：help/ai/AiManager.kt、AiChatClient.kt（压缩调度）、AiChatContextManager.kt（~750 行压缩核心：六桶 token 估算+实测校准+PRE_TURN/MANUAL+兜底裁剪）、AiSkillPackageRegistry（assets/skills/ 不可变快照：内容哈希/64 文件/256KB 上限）、assets/ai/context_compaction.md。
MCP：service/McpService.kt（前台服务+网络变化重绑）→web/mcp/McpHttpServer(NanoHTTPD)→McpServer.serve()（1600+ 行，POST /、/mcp，JSON-RPC 批量；initialize/tools/resources/prompts 全套）；BookshelfMcpTools/SettingsMcpTools/AgentMemoryMcpTools 复用 api controller；限幅常量严格。内部通道 McpInternalToolCatalog（6 模块 50+ 工具，writeCapability 标记+确认）。开关=DEBUG 或设置项。本项目已有反向物：help/ai/AiMcpClient.kt（MCP 客户端）。

## F. 听书体系（关键事实）

服务层：BaseReadAloudService+TTSReadAloudService（系统 TTS 单音色）+HttpReadAloudService（~1700 行多角色核心）+AudioPlayService。引擎：help/tts/ 20 类（TtsEngineStore/TtsEngineSetting/SCRIPT 类型/TtsScriptEngineClient/TtsWebSocketEngineClient/TtsStreamingAudio/TtsSpeedPolicy/ReadAloudCacheManager——缓存名 MD5 含 scenarioMode+voiceId+styleId）。
路由：ReadAloudTtsRouter.route() 五级 character→castRole→dialogue_male/female→dialogue 默认→narrator→引擎默认；speakerId+别名双路匹配；场景覆盖仅 AUTO 绑定生效；AppConfig.readAloudMultiRole 开关，仅 SCRIPT 引擎。
AI：AiTtsStoryboardHelper ~2800 行（分镜生成/缓存/复评）+BookTtsCastingCoordinator（confidence≥0.7，scene_voice≥0.85）+技能包 tts_storyboard v4（分层装配 base-routing 恒载）+tts_casting。
播放：NextChapterPlaybackPlan 跨章无缝；Compose 播放器 23 文件+6 动效双实现。UI 位置差异：NG=全屏 Activity；本项目=面板/悬浮窗体系（ReadAloudPlayerPanel/ReadAloudSystemFloatingWindow）。

## G. 视觉体系（关键事实）

ui/design：NgAppTheme/NgThemeResolver/NgColorSystem/NgColorMath/NgThemeSnapshot/NgThemeSceneHostView；35 Compose 组件+10 View 组件；ng_bg_*.xml 53 个。
液态玻璃：改造 Kyant0/AndroidLiquidGlass（Apache 2.0）；NgLiquidGlassBackdrop（GraphicsLayer.record+ColorMatrix 降饱和+RenderEffect blur API31+AGSL RuntimeShader 折射 API33+七通道色散）；View 侧 NgViewLiquidGlassRenderer（RenderNode+OnPreDrawListener+containsDescendant 防递归）；padding=blur-折射高度防视觉残留。
切换：NgVisualSystemStore（TRANSPARENT_GLASS/LIQUID_GLASS，SP key ngVisualSystem.v1 与主题 key 分离）；NgVisualSurface 单一调度点+NgMaterialRole 9+ 语义角色→NgLiquidGlassDefaults.spec(role)；降级链 API<31/E-Ink/无 backdrop→透明玻璃回退。
主题 Resolver：旧四色→materialkolor HCT 8 scheme→M3 ColorScheme+NgThemeSnapshot 不可变快照；"只读旧状态、不读写偏好"。
Compose 度：545 文件中 156 含 @Composable（29%）；核心配置/管理/弹框链路 70-80% 已迁。

## H. 工程安全/CI（关键事实）

8 项沙箱修补机制详见 B/C 节；有回归测试守护（RhinoBookSourceClassPolicyTest/NativeBookTest）。18PlusList.txt（base64 主域 HashSet，SourceHelp.list18Plus）。CI：release.yml（版本 3.%y.%m%d%H sed 注入+secrets 重建 key.jks+自动发版）/test.yml（concurrency+矩阵）/cronet.yml（每周一自动 PR）/web.yml。versionCode=10000+gitCommits；包名 io.legado.app.ng。
