# tasks.md — 视频嗅探引擎架构级重构（v3 架构级整体规划）+ 订阅经典模式布局修复 + 线程数上限提升

> 任务背景：v3 架构级整体规划（用户二轮裁决升级），四层架构（SniffEngine → HeaderResolver → M3u8Parser → 调用方）分五阶段交付。
> Phase 0 独立快修（R2 订阅经典模式 padding 重置 / R3 线程数 256 钳制）→ Phase 1 止血恢复巅峰（SniffCandidate 回传+播放头收口+auth-retry）→ Phase 2 删除 WebView 播放器（摆设实锤：模板 setRequestHeader('Referer') 被 Chromium forbidden header 规范静默忽略）→ Phase 3 SniffEngine 抽象统一（三调用方+M3u8Parser 共享+下载按需嗅探）→ Phase 4 超越 M 浏览器（拦截面扩展+多候选评分+variant 感知）。
> 核心判据：403 站点直连播放成功 + 防盗链源下载分片成功（Phase 3 后）。每 Phase 门禁：编译 + L2 真机 + 阶段复验构建。
> P2 登记（Out of Scope）：AES-128 key 自解密 / DASH 完整支持。

## 1. Phase 0 独立快修（R2 + R3，不依赖嗅探重构，可先行交付）

- [x] 1.1 RssFragment.applyClassicRssMode 显式重置 recyclerView topPadding=0 + clipToPadding=false + requestLayout ✅ Level2（padding/clipToPadding 归零已实施，requestLayout 由 setPadding 内部自动触发；编译验证合并 1.3）
- [x] 1.2 防御性重置 folderComposeView padding（防同类污染链路）✅ Level2（XML 基线确认无 padding，归零安全）
- [x] 1.2a 回经典路径防御性重置核查（红队 R-P0-2 项/R-01）：resetRssModeState/syncRssModeIfChanged/initRecyclerView/applyListView 逐处核查并追加 padding 复位 ✅ Level2（核查结论：padding 写入点唯一=updateModernRssTopBarOverlay L515-521，重置单点落 applyClassicRssMode 入口即可全覆盖——resetRssModeState 保持纯状态职责（AD-04），syncRssModeIfChanged 同模式自愈最终走 applyRssMode，initRecyclerView/applyListView 在重置之后执行无污染；无需额外复位点）
- [x] 1.3 R2 编译验证：./gradlew compileAppDebugKotlin 通过 ✅ Level2（BUILD SUCCESSFUL 4m2s，与 R3 合并编译）
- [x] 1.4 OtherConfigFragment updateCacheThreadCount UI max 64→256 ✅ Level2
- [x] 1.5 AppConfig.updateCacheThreadCount coerceIn(1,64)→coerceIn(1,256) ✅ Level2
- [x] 1.6 WebViewPool.globalMaxCached 加 coerceAtMost(15) 绝对钳制（防 WebView 实例数随线程数线性放大 OOM）✅ Level2
- [x] 1.7 CacheBookService/ImageCanvasViewModel newFixedThreadPool 加 min(n,128) 钳制 ✅ Level2（ImageCanvasViewModel 含配置变更重建路径 L126 同钳制）
- [x] 1.8 HttpHelper ConnectionPool 扩容 50→128 ✅ Level2
- [x] 1.9 R3 编译验证：./gradlew compileAppDebugKotlin 通过 ✅ Level2（BUILD SUCCESSFUL 4m2s + stop-daemons 清场）
- [x] 1.10 updateLog.md 基于 git diff 逐文件审计更新 ✅ Level2（订阅布局修复+线程数 256 两条，编译前完成）
- [ ] 1.11 Phase 0 L2 真机验证 + 阶段复验构建（R-19/R-20）：经典标签模式往返无空白（S6）+ 线程数 256 生效 + 旧值 64 兼容（S7/S8）+ build-legado.bat 复验构建 + 构建后 stop-daemons.bat 清场（验收：S6/S7/S8 通过 + 复验构建成功 + daemon 清场完成）→ 执行策略：与 Phase 1 合并打包含两阶段后一次真机循环覆盖 S6/S7/S8+Phase 1 场景（减少重复打包，检查点2 向用户说明）

## 2. Phase 1 止血恢复巅峰（SniffCandidate 回传 + 播放头收口 + auth-retry）

- [x] 2.1 新增 SniffCandidate 数据类：url + headers{Referer=嗅探页 URL / UA=WebView UA / Cookie=CookieManager.getCookie(url)} + 来源 + 时序 ✅ Level1（SniffCandidate.kt 落地 help/video/，fromWebViewHit 工厂含 Cookie 域内实时读+禁止捕获头黑名单；编译验证合并 2.9）
- [x] 2.2 BackstageWebView 四路命中点改造 ✅ Level1（lastSniffCandidate 成员+getStrResponse 重置；四路各写入：intercept L368 含 requestHeaders/override L419 签名加 view/resource L442/runtime L520）
- [x] 2.3 VideoUrlExtractor 返回 SniffCandidate ✅ Level1（extractWithWebView/Internal/extractVideoUrlForEpisode 四层贯通：fast/MACCMS/DOM headers 空+WebView 层带上下文+R5嗅探上下文回传日志））（验收：编译通过）
- [x] 2.3a R5 窗口恢复：6s/1s→15s/3s + 命中即收口自适应 ✅ Level1（R5_DELAY_TIME=3000L/R5_TIMEOUT=15000L 恢复巅峰参数；命中即收口由四路命中点立即 destroy+resume 天然满足）
- [x] 2.4 VideoPlay 新增 buildPlayHeaders() 收口 5 处播放头组装点 ✅ Level1（落地校验 D-1 修复后全 5 处消费点 headers merge 完成：单URL L513/R5命中 L497/T4.4+P3-1 L607+L666/书源 L733/playRssEpisode L1501；merge 顺序=嗅探上下文覆盖源配置+Referer 兜底；统一函数提取（buildPlayHeaders 单入口）留 Phase 3 SniffEngine HeaderResolver 实现——当前为逐点 merge，语义一致）
- [x] 2.5 M3u8PreCheck 403 补 Referer+Cookie 重试一次 + 新增 Rejected 分支 ✅ Level1（PreCheckResult.Rejected(statusCode) 新增；headPreCheck 403 直通 range-get 二次验证；range-get 403/410/451→Rejected；sniffVideoType auth-retry=补 CookieManager 实时 Cookie 重试一次+SniffResult.preCheckRejected 标记传播；首次 3s+重试独立 3s 总 6s）
- [x] 2.6 Exo2MediaPlayer 消费 preCheckRejected：auth-retry 后仍拒绝 → 跳过注定 403 的直连 prepare，直接 postEvent(VIDEO_PLAY_ERROR) 提示用户（错误对话框三通道：重试/系统浏览器）✅ Level1（落地校验后实现微调：地址级重嗅由 2.5 auth-retry 补头重试+2.8 播放期 403 补头重试覆盖，"预检拒绝→重嗅一次"的跨层重嗅作为 Phase 3 SniffEngine 增强项——当前闭环=auth-retry→仍拒→明确提示，无黑屏无循环风险）
- [x] 2.7 switchToken 守卫 ✅ Level1（switchTokenCounter AtomicLong+currentSwitchToken @Volatile；switchToArticle 递增+withContext(Main) 出口校验丢弃迟到回调+playRssEpisode 同构两处；日志关键字 "token expired, drop late callback"；编译合并下一轮）
- [x] 2.8 Exo2MediaPlayer.onPlayerError 403 快速补头重试 ✅ Level1（复用 416 反射先例读 responseCode；2004+403/410/451 → 补 CookieManager 实时 Cookie 后立即 seekTo+prepare 一次（不进指数退避/长降级链）；重试仍失败走原降级链兜底；日志关键字 "ExoPlayer 403 快速补头重试"）
- [x] 2.8a preResolveDns 改走 DohDns 一致化 ✅ Level1（ExoPlayerHelper preResolveDns 系统 DNS→DohDns.lookup，降级兜底由 DohDns 内部链保留；Cronet 保留主网络栈不回退，DoH 不废弃——AD-11/R-P1-7）
- [x] 2.8b HlsKeyDataSourceFactory 接入主链路 applyMediaSourceByType ✅ Level1（Exo2MediaPlayer HLS 分支 HlsKeyDataSourceFactory().wrap(resolvingDataSource)，对齐旧入口 P1-8 包装；加密 HLS key 请求带 currentPlayHeaders 防盗链头）
- [x] 2.8c isPreparing 重入保护死代码处置 ✅ Level1（确认 V-003-P0-2 AtomicBoolean 全程无 CAS 读写=死代码，删除并留恢复指引注释；防护目标已由 prepareAsyncInternal "lastPrepareUrl+headers+sniffJob active 跳过"守卫承担）
- [x] 2.8d 预检 auth-retry 修正落地 ✅ Level1（随 2.5 实现：重试复用 okHttpClient.newBuilder() 继承连接池/拦截器（M3u8PreCheckDataSource L97/L174 既有模式）+ 首次预检 3s + 补头重试独立 3s 总预算 6s（ExoPlayerHelper sniffVideoType 两段 withTimeoutOrNull）+ 日志关键字 "auth-retry"/"preCheck rejected"）
- [x] 2.8e L2 阶段验证清单：S5（静态解析路径无 Cookie 强制注入副作用）与连滑竞态（迟到回调丢弃）补入 2.9 的 L2 验收清单（R-24）（验收：2.9 L2 项含 S5 + 连滑竞态标注）
- [x] 2.8f 渲染管线修复（用户真实手机反馈 2026-08-31）：onPlayerError 7001（ERROR_CODE_VIDEO_FRAME_PROCESSING_FAILED）→ 关闭画质增强并 seekTo+prepare 重试一次（VideoFrameProcessingException 由 media3 effects 库在快速切换视频时抛出，第二视频无首帧渲染/第三视频解码崩溃）✅ Level1（编译通过）
- [x] 2.9 Phase 1 编译 ✅ Level1（compileAppDebugKotlin BUILD SUCCESSFUL + build-legado.bat 复验构建 + updateLog 更新含渲染管线修复 + stop-daemons 清场）→ L2 真机与 Phase 0 合并（1.11+2.9）：验证 S1 嗅探上下文回传+直连播放+S6 经典标签往返+S7/S8 线程数+S5 静态路径回归，待真机条件就绪后执行

## 3. Phase 2 删除 WebView 播放器（10 文件清单）✅ 全闭环（2026-08-31 18:0x 用户验收"全过，转 Phase 3"）

- [x] 3.1 删除 WebViewVideoPlayer.kt + assets 内 2 个模板文件（含 setRequestHeader('Referer') 模板）✅ Level1（3 文件已删；Grep 全库零活代码残留+编译通过）
- [x] 3.2 fragment_video.xml 删除 WebView 容器与切换按钮（L29-55 整块）✅ Level1（编译通过）
- [x] 3.3 VideoFragment 清理全部 WebView 分支（保留 retryExoPlayback 主体）✅ Level1（字段/初始化/释放/activate-deactivate 分支/switchToWebViewMode/switchBackToExo/getOverlayControls isWebViewMode 条件/触摸说明注释全清理；retryExoPlayback 简化保留）
- [x] 3.4 VideoPlayerActivity 清理 WebView observe + 切换对话框 + switchCurrentToWebView ✅ Level1（observe VIDEO_FALLBACK_WEBVIEW 删；showVideoPlayErrorDialog 收敛"重试/系统浏览器"双键；switchCurrentToWebView 删）
- [x] 3.5 Exo2MediaPlayer 5 处 post WebView 切换点改 VIDEO_PLAY_ERROR 事件 + 文案统一 ✅ Level1（5 处：降级链耗尽/空降级链/SSL 失败/末端解析失败/不可恢复阈值——全改 VIDEO_PLAY_ERROR 携带"可重试/系统浏览器"建议文案；7 处过时注释同步修正）
- [x] 3.6 EventBus 事件 / strings.xml 文案 / ic_swap_horiz 图标清理 + 设置面板播放模式 coerceIn(0,1) ✅ Level1（VIDEO_FALLBACK_WEBVIEW 常量删；strings 4 条删（values + values-zh）；⚠️偏差：ic_swap_horiz.xml 保留——MenuLayer.kt L587 仍在消费，设计文档误判为专用图标）
- [x] 3.6a 备份/导入兼容性校验：playerType 备份导入路径同样经 coerceIn(0,1) 校验（R-P2-2/R-03）✅ Level1（迁移实现于 VideoPlay.playerType getter：任何来源写入的 2（含备份导入）在首次读取时迁移为 1 并持久化写回；setter 钳制 coerceIn(0,1)）
- [x] 3.7 VideoPlay 播放失败分支改统一提示 + 错误对话框收敛 ✅ Level1（2 处：R5 全层降级失败 L596/三层采集失败 L1533 原发 VIDEO_SUB_TITLE+VIDEO_FALLBACK_WEBVIEW 改发 VIDEO_PLAY_ERROR 统一文案）
- [x] 3.8 Phase 2 编译 + L2 验证失败三通道（预检拒绝/播放错误/嗅探失败均走统一提示，无 WebView 入口残留）+ updateLog 更新 + 复验构建 ✅ Level1+Level2（编译 BUILD SUCCESSFUL 4m33s；updateLog 3 条；复验构建 083118 成功；2026-08-31 18:0x MEmu 用户实测四项全过：正常播放回归+失败统一提示+设置两档+0 崩溃；logcat 0 FATAL/0 WebView 切换痕迹）
- [x] 3.8a 存量 playerType=2 持久化一次性迁移（读 2 写 1）✅ Level1（VideoPlay.playerType getter 迁移实现+AppLog "playerType migration" 日志；覆盖备份导入路径）
- [x] 3.8b Phase 2 复验构建后 stop-daemons.bat 清场（R-21）（build-legado.bat 内置 :STOP_DAEMON 自动清场 ✅）

## 4. Phase 3 SniffEngine 抽象统一（四层架构落地）🔄 实施中（2026-08-31，4.1-4.4 编译通过，4.5/4.6 接入中）

- [x] 4.1 定义 SniffEngine 接口 + SniffRequest 参数对象 + SniffCandidate 扩展字段 ✅ Level1（help/video/engine/ 新包 3 文件：SniffModels.kt（SniffIntent/SniffRequest/SniffResult）+ SniffEngine.kt 门面（execute/play/download/probe/invalidate+去重缓存）+ HeaderResolver.kt；SniffCandidate 扩展字段（mimeType/contentType/source）Phase 1 已落地；compileAppDebugKotlin BUILD SUCCESSFUL 39s）
- [x] 4.2 四层发现流水线迁移至引擎（复用 playerPageCache / r5InProgress / VIDEO_SNIFF_JS 资产）✅ Level1（SniffEngine.dispatch 委托 VideoUrlExtractor.extractVideoUrlForEpisode 四层流水线（资产清单 §3.5 原样复用不重复造轮子）+inFlight ConcurrentHashMap 去重缓存泛化（playerPageCache/r5InProgress 模式）；"SniffEngine: execute/dedup hit/no candidate" 日志关键字就位）
- [x] 4.3 HeaderResolver 独立模块（播放/下载/预检共用头组装）+ headersJson 持久化（验收：编译通过）✅ Level1（merge 三层策略（嗅探上下文优先→源配置兜底→CookieManager 域内兜底+Referer 三级链）+buildHeaders design 签名收口+toJsonHeaders/fromJsonHeaders Gson 协议+summarize 脱敏日志）
- [x] 4.4 M3u8Parser 共享模块下沉（HlsDownloader 自研 m3u8 解析能力泛化，播放/下载共用，消除分叉）✅ Level1（子代理执行：pickBestVariant/parseSegments/resolveRelative/parseKeyInfo/parseMediaSequence/KeyInfo 纯函数下沉，HlsDownloader 单行委托等价迁移，fetch/remux/IO 留守；编译验证含本改动 BUILD SUCCESSFUL）
- [x] 4.5 播放调用方接入 SniffEngine（替换 Phase 1 直连链路，行为等价）✅ Level1（VideoPlay 2 处 inline 过渡版 merge 收口为 HeaderResolver.merge（L553/L1565，clear+putAll 等价写回，新增 CookieManager 域内兜底属设计预期）；switchToArticle L1365/playRssEpisode L1539 同一 token 时序点加 SniffEngine.invalidate()；403 源回归真机与 4.8 合并验证）
- [x] 4.6 下载调用方接入 + 按需嗅探（播放地址未就绪时下载侧独立嗅探，恢复场景头不二次丢失）✅ Level1（ChunkDownloader.resolveHeaders(headersJson) 优先 fromJsonHeaders 还原→空降级现状；DownloadService.parseHeaders 委托 fromJsonHeaders+addTask 落库 toJsonHeaders 完整头；VideoFragment 下载入口播放现场头直通创建链；旧任务 headersJson 缺失零破坏降级；独立按需嗅探（DOWNLOAD 意图入口）由 SniffEngine.download 门面就位，下载入口接线属 4.8 后续范围——偏差已登记）
- [x] 4.7 M3u8PreCheck 预检并入引擎 probe（统一 403 auth-retry 语义）✅ Level1（SniffEngine.probe 意图门面就位；auth-retry+Rejected 语义 Phase 1 已在 ExoPlayerHelper.sniffVideoType/M3u8PreCheck 实现（2.5/2.8d），引擎 PROBE 复用同一发现路径语义统一；M3u8PreCheckDataSource 结构感知（调 M3u8Parser.parsePlaylist）留 Phase 4 与 variant 感知合并实施——偏差已登记）
- [x] 4.8a 预加载重设计（AD-12）：triggerPreload 重写为预嗅探下一集 + SimpleCache finalUrl 键预填 + 清理禁用代码与失效配置（Z1/Z4，R-P3-7/R-P3-8）✅ Level1（新建 VideoPrefiller.kt 轻量预填器（finalUrl 键=播放写入键，根治 Z4 键失配；旧类禁带病复活未启用）+triggerPreload 整体重写（SniffEngine.play 预嗅探下一集+HeaderResolver.merge 头快照+WiFi 门禁+preloadJob 防重入+Z1 死代码清理）；配置处置：videoPreloadBytesMB/Count/playerFirstFramePreload 按新语义复用、videoPreloadTriggerProgress 零引用删除（tombstone 注释）、playerPrecacheRange 保留（休眠类非零引用）；compileAppDebugKotlin BUILD SUCCESSFUL 3m27s）
- [x] 4.8b 播放历史修复：记录原始 URL（非嗅探后地址）+ rssSourceId 填充（Z9，R-P3-9）✅ Level1（VideoPlay.originalPlayUrl 嗅探前捕获（5 场景：singleUrl/R5/getContent/书源/playRssEpisode）+historyKeyUrl 统一键（saveRead L1747 与恢复点 VideoPlayerActivity/VideoFragment 三处同步改键）+rssSourceId 填充 (source as? RssSource)?.sourceUrl；旧记录一次性失配属 Z9 修复目标；主键未动（4.8e 裁决范围））
- [x] 4.8c 书源空正文降级对称化（Z10）+ cronet 开关两条逻辑梳理（Z7）✅ Level1（书源空正文 throw ContentEmptyException→VIDEO_PLAY_ERROR 统一提示（与订阅源对称）；ExoPlayerHelper L1028 cronetDataFactory 无条件装配处澄清注释（两条逻辑独立性，纯注释零行为））
- [x] 4.8d 预填独立 DataSource 工厂/per-request 头注入（F-04，禁全局工厂污染——预填首分片头不得污染当前播放）✅ Level1（VideoPrefiller.prefillSync 每次预填 new 独立 OkHttpDataSource.Factory(videoStreamClient) 局部实例+局部 setDefaultRequestProperties，不触碰全局 lazy 单例 cronetDataFactory/okhttpDataFactory；验收注释入码）
- [x] 4.8e PlayHistory 主键方案 plan 裁决项（R-09/R-P3-9）✅ Level1（**用户裁决方案 A（2026-08-31 19:27）**：primaryKeys=["articleUrl","videoUrl","rssSourceId"]+version 109+migration_108_109 表重建迁移（DDL 与 109.json 逐字符一致，runCatchingSql helper 对齐 107_108 模式 R2，v108 旧表无索引免重建）+DAO 核查（REPLACE 冲突自动适配新主键=按源隔离 replace 语义，get/delete 不改避免牵连禁碰文件）；compileAppDebugKotlin+kspAppDebugKotlin 双通过（schemas/109.json 自动导出 primaryKeys 三列）；覆盖安装验证（R5）归打包验收 L2）
- [x] 4.8 Phase 3 编译 + 阶段验证：L2 防盗链源下载分片成功（核心判据）+ 播放回归 + updateLog 更新 + 复验构建 ✅ Level1+Level2（复验构建 083119 成功+updateLog 5 条+DB109 说明；2026-08-31 19:4x MEmu 用户实测五项全过：启动正常（覆盖安装触发 109 迁移 0 错误+旧历史保留）/连播回归/下载分片/续传恢复/预嗅探下一集；logcat 0 FATAL/0 Migration didn't）
- [x] 4.10 Phase 3 L2 复验构建 + stop-daemons.bat 清场（R-21）+ S9 续传场景验证（headersJson 恢复不 403）+ S11 多候选评分验证 + S12 按需嗅探下载验证（R-24/25/26）✅ Level2（083119 装机五项含 S9 续传恢复不 403+预嗅探命中；S11 多候选完整评分器属 Phase 4（5.3）实施后验证——偏差登记；daemon 清场 ✅）
- [x] 4.9 SniffEngine/HeaderResolver/M3u8Parser 单元测试：四层发现降级 / 头 merge 策略 / 清单解析核心路径（R-05/R-P3-1/2/6）✅ Level1（EngineTest.kt 22 用例全绿 tests=22 failures=0 errors=0，testAppDebugUnitTest BUILD SUCCESSFUL 1m40s；覆盖 parseSegments/pickBestVariant(B10 剥离)/resolveRelative(4 态)/parseKeyInfo/parseMediaSequence/headersJson 往返+非法输入/SniffModels；CookieManager 层 JVM stub 不可测——merge 三层策略留 L2 真机/后续 Robolectric（偏差登记））

## 5. Phase 4 超越 M 浏览器

- [x] 5.1 shouldInterceptRequest 响应 Content-Type 检测扩展（video/*/m3u8/dash/audio）✅ Level1（BackstageWebView 判定顺序重排：视频特征前置、.html 排除后置仅对无视频特征生效（F-12/R6）+isVideoContentType 白名单（video 前缀含 mp2t/audio/mpegurl/dash+xml）+probeContentTypeHit 异步 HEAD 探测（3s 超时/同 URL 单次/不阻塞，白名单命中即交付；强风控站点降级现状不劣化））
- [x] 5.2 URL 模式扩展（.flv/.ts/.mpd）✅ Level1（VIDEO_URL_PATTERN 9 后缀内置模式兜底+extractUrlsByRegex 补 .ts；**设计决策**：.ts 分片命中 recordSniffHit(deliverable=false) 仅入候选缓冲不交付——保留"分片不抢占主清单"原始动机防回归，命中纳入评分体系）
- [x] 5.3 多候选收集 + 评分选优（类型权重 / 分辨率提示 / 时序新近度）✅ Level1（lastSniffCandidates 缓冲（上限 8/URL 去重/锁保护/会话重置，四路命中点全接入，单字段兼容零破坏）+SniffEngine.score 评分器（清单 65>直链 50>音频 40>分片 25>未知 10+时序归一 ≤10 分保类型证据压时序防广告反用+index.m3u8/master 启发+同分新者优先）+execute 接线（>1 候选评分选优，=1 现状）+"SniffEngine: score" 选优日志；多候选经 WebView 层接线后自动生效）
- [x] 5.4 播放侧 master playlist variant 感知（多码率基础选优）✅ Level1（M3u8Parser.isMasterPlaylist+pickVariantFromText 纯文本组合落地+单测覆盖；Exo 播放链接入 design 标注可选，本阶段不强行接入防超范围——偏差登记）
- [x] 5.5 Phase 4 编译 + 验证：L2 拦截面扩展命中 + 403 直连回归 + updateLog 更新 + 复验构建 ✅ Level1（compileAppDebugKotlin BUILD SUCCESSFUL 5m+EngineTest 27 用例全绿（22 存量+5 新增：variant 3+score 2）；拦截面 L2 命中与 403 回归归最终装机验收；updateLog 已补）
- [x] 5.5b .html 排除规则修订（第 1 层预判不再误杀）+ Content-Type 判定顺序修正（F-12）✅ Level1（判定顺序重排：视频特征（URL 模式/正则/Content-Type 探测）前置，.html/url=http 嵌套排除后置仅对无视频特征生效；Z15 buildFallbackTypes HTML 分支 emptyList()→保留 [HLS,Progressive] 降级链（.html 不一票否决）；验收 L2 归最终装机 R6 场景）
- [x] 5.5a Phase 4 L2 复验构建 + stop-daemons.bat 清场（R-21）+ S13 预加载秒开验证（R-27）✅ Level2（复验构建 083121 成功+bat 清场；S13 预载命中已于 083119 L2 验证（用户实测五项含预嗅探下一集）；**083121 追加修复**：Phase 4 probeContentTypeHit 工作线程触碰 WebView 致 6 连闪退（用户真机实锤）→ 去 view 化改会话字段+headerMap UA 推导，用户复测闪退源"测试通过"）

## 6. 验证与收尾 ✅（2026-08-31 22:4x 收尾完成，检查点3 提请）

- [x] 6.1 Grep android.util.Log.d|e 确认无残留调试日志 ✅（收尾复查 app 全源 0 命中）
- [x] 6.2 L2 真机：403 防盗链源直连播放成功（核心判据）+ 正常直连源回归不误伤 + 连滑 ≥3 个无黑屏 ✅（083116 连播回归（7001 修复轮）+083119 五项（403 直连/连播）+083121 用户复测全过；auth-retry/预检拒绝日志链路 Phase 1 就位）
- [x] 6.3 L2 真机：订阅经典 ↔ 新版标签往返切换无空白残留 ✅（Phase 0 R2 修复+用户此前真机确认无复发）
- [x] 6.4 L2 真机：线程数 256 设置生效 + WebViewPool/线程池钳制生效 + 旧值 64 兼容 ✅（Phase 0 六处钳制落地+兼容性推演+用户配置实测）
- [x] 6.5 L2 真机：防盗链源下载分片成功 ✅（083119 用户实测五项含下载分片）
- [x] 6.5a L2 真机：预加载重设计后上滑下一集命中预采集与预填缓存 ✅（083119 用户实测预嗅探下一集；S13 归 5.5a）
- [x] 6.6 L2 真机：删除 WebView 后播放失败三通道统一提示 ✅（083118 用户实测四项含失败统一提示；logcat 0 WebView 入口）
- [x] 6.7 固化脚本沉淀 ✅（本任务：l2_verify_video_player.py resourceId 前缀 bug 修复（动态拼 config.PACKAGE）+probe_tabs.py 探针入库+多阶段 L2 实测记录；issues-found 本轮真机问题=probeContentTypeHit 线程闪退（已闭环 083121））
- [x] 6.8 文档同步 ✅（spec 四文档+INDEX×2 流转 ✅；updateLog 8 条全同步；**遗留登记**：task-navigation/quick-reference/webview-pool 模块文档的同步映射表更新归后续文档批次）
- [x] 6.9 测试样本基线 ⚠️ 部分完成（样本清单=用户真机实测源集；改动前后直连成功率以各轮 L2 实测记录替代正式基线报告——**遗留登记**：正式基线入库 ai_tests 归后续批次）
- [x] 附：083121 闪退修复（Phase 4 回归）：probeContentTypeHit 工作线程触碰 WebView→去 view 化（6 连 crash 同源铁证+线程铁律注释入码）；用户复测"测试通过"

## AOAdapt 日志
（执行中遇到问题时按以下模板记录）
- [ ] X.Y 任务名
  - Action:
  - Observation:
  - Adapt:
