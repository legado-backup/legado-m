# 设计文档 v3：视频嗅探架构级重构（SniffEngine 统一播放/下载 + 超越 M 浏览器 + 删除 WebView 债务）+ 订阅经典布局修复 + 线程数扩容

> 规格日期：2026-08-31 ｜ 状态：v3 架构级设计完成，待实施
> 证据基础：历史回归分析全文见 `docs/temp-analysis/video-sniff-regression-analysis-20260831.md`（git 溯源+spec 交叉印证）
> 安全声明：外部站点一律用"站点A/路径模式"表述，不引用真实域名与业务数据

---

## 零、现状能力全景（四轮反馈补强：先摸清现状再谈优化）

> 完整盘点三份报告（嗅探/播放/场景网络）见 docs/temp-analysis/video-{sniff,play}-capability-inventory.md 与 video-scenario-network-inventory.md（2026-08-31）。本节只列影响本设计的关键结论。

**现状架构速览**（文字箭头链）：
上滑切换 → VideoPlay.switchToArticle/switchToRoute（token 守卫）→ extractVideoUrlForEpisode 四层采集（快速路径直连后缀 → playerPageCache 5min → MacCMS player_aaaa 6s → DOM 复用 → WebView 抓包 R5 6s/1s，r5InProgress Deferred 去重）→ VideoPlay.startPlay 头组装（5 处重复，源配置+文章页 Referer）→ GSY setUp → Exo2MediaPlayer.prepareAsyncInternal → Exo 层 sniffVideoType（5s：HTML 预判→m3u8 短路 HEAD 预检 3s→Range 嗅探 8KB 三级内容证据 Probe 清单>17 项 Magic Number>Content-Type→URL 后缀仅兜底）→ buildFallbackTypes → applyMediaSourceByType → DataSource 五层组装（cacheDataSourceFactory→cronet/okhttpDataFactory→视频网络栈）→ 播放。

**影响本设计的关键现状结论**（13 条，每条标注处置 Phase）：

| # | 现状结论 | 处置 |
|---|---------|------|
| Z1 | 视频级预加载整体禁用态：triggerPreload 中 FirstFramePreloader/VideoPreloader 调用被注释（NPE 未修），videoPreloadCount 等配置项全部失效，"上滑秒开"实际靠 HTML 预热+LoadControl 激进缓冲 | Phase 3 重设计（AD-12） |
| Z2 | DataSource 头注入全局互覆盖：okhttp/cronetDataFactory 为 lazy 单例+setDefaultHeaders 替换式覆盖，预加载 createPreloadDataSource 也改同一工厂；SPLIT_TAG per-request 注入仅 OkHttp 分支，Cronet 无等价机制 | Phase 1 buildPlayHeaders 收口强化论据+Phase 3 HeaderResolver 根治 |
| Z3 | AES 密钥头注入双路径漂移：HlsKeyDataSourceFactory 只接旧入口 createMediaSource L258，主链路 applyMediaSourceByType L310 的 HLS Factory 未包装，加密流 key 防盗链主链路仅靠全局头兜底 | Phase 1 纳入（小改动高收益） |
| Z4 | SimpleCache 键不一致：预加载写原 URL 键、播放用重定向 finalUrl 键，预载数据可能永不命中 | Phase 3 键统一 |
| Z5 | isPreparing 重入保护（Exo2MediaPlayer L101）疑似死代码（无 CAS 读写），R5 双命中重复 acquire 防护可能被实例池架空 | Phase 1 确认恢复或删除 |
| Z6 | Cronet 与 DoH 无配置级结合：CronetEngine 仅 UseDnsHttpsSvcb+AsyncDNS，原生解析走系统 DNS；唯一结合点=错误回退链（CronetInterceptor L317-329 ERR_NAME_NOT_RESOLVED→清 DohDns 负缓存→OkHttp+DoH 接管），非用户可配置；不存在"Cronet 换 DoH"设置项 | §3.7/AD-11 已述，Phase 4 评估 customHost 注入 DoH 结果（可选项） |
| Z7 | cronet 用户开关（AppConfig.isCronet，PreferKey.cronet 默认 false，仅控制 OkHttp builder 是否装配 Cronet interceptor）与视频链路 CronetDataSource 装配是两条逻辑——cronetDataFactory 为无条件装配不受该开关控制（ExoPlayerHelper L1029） | Phase 3 梳理统一（先消解双"默认"表述，见 §3.7） |
| Z8 | addressCache hostMap 用户手配 IP 映射在 OkHttp 侧已失效（RetryableDns 未挂载），仅剩 Cronet customHost 消费 | 登记盲区，Phase 4 评估 |
| Z9 | 播放历史三缺陷：PlayHistory.rssSourceId 恒空串（复合主键同文章多线路互相覆盖）/记录的是嗅探后 URL（源侧 token 轮换永久失配）/WebView 降级期进度记忆读 GSY currentPosition 脱节 | Phase 2 顺带修进度脱节；Phase 3 记录原始 URL |
| Z10 | 书源章节视频空正文直接抛异常无降级，与订阅源路径不对称 | Phase 3 统一入口对称化 |
| Z11 | SSL 校验完全旁路（嗅探/播放链路信任所有证书），不可信源有中间人风险 | 登记安全风险（Out of Scope，独立 spec） |
| Z12 | HTTP/2 协议错误三层防御已有（videoStreamClient 强制 HTTP/1.1+Cronet HTTP/2 降级 1min+震荡 15min） | 保留现状 |
| Z13 | WebView 抓包实为 6 路 JS hook（fetch/XHR/media.src/createObjectURL/MIME/Performance API）+四路捕获（shouldInterceptRequest L360 8 后缀+video/tos+rtmp 排除 .ts / shouldOverrideUrlLoading L403 / onLoadResource L419 / ReadVideoUrlsRunnable 内部命中点 L490） | SniffEngine 资产复用清单 |
| Z14 | Range 嗅探重定向后头不重算：嗅探请求头在原始 URL 注入，3xx 跟随后沿用原 URL 头，重定向跨域时防盗链头（Referer/Cookie）失效→新域 403 被误判"HTTP 错误"走后缀兜底（HeaderResolver 收口播放头组装，未覆盖嗅探请求 videoStreamClient 的重定向语义） | Out of Scope 登记（Phase 4 评估重定向重算分支） |
| Z15 | buildFallbackTypes HTML 检测失真：Range 成功路径 Content-Type 证据仅映射 video/audio/m3u8/mpd，text/html→hintByCt=null→mimeType=null→isHtmlPage=false，UNKNOWN+HTML 直接空降级链多耗重试时间，与注释"HTML 直接跳过"不符 | Phase 4 与 F-12 一并修正（Content-Type text/html→mimeType 填充） |

**场景矩阵摘要**：订阅源文章视频/sortUrl 视频/书源正文视频/singleUrl 外部直链/本地文件/播放时缓存/下载后播放——各场景入口、嗅探路径与 headers 来源差异详见 video-scenario-network-inventory.md §1 矩阵表；SniffEngine 统一后所有场景收敛到 SniffRequest{intent} 单入口。

---

## 一、背景与演进（v1 → v2 → v3）

- **v1（初版，已废弃）**：R1 方案为"403 快速降级 WebView 播放页"。用户裁决否决——WebView 播放页是历史遗留产物将逐步废弃，把 403 主出口导向 WebView 与演进方向背道而驰。
- **v2（检查点1 修订版）**：方向改为"嗅探能力对标 M 浏览器"——嗅探上下文端到端流转（SniffCandidate）+ auth-retry-first 两大核心机制，P0 七项+P1 两项，目标直连播放成功率最大化。R2（订阅经典布局）/R3（线程数扩容）维持原方案。
- **v3（本次，架构级）**：用户二轮裁决升级为**架构级整体规划**，四个目标：① 嗅探引擎抽象统一播放/下载（消除两条链路分叉）；② 超越 M 浏览器（拦截面扩展+多候选评分）；③ 删除 WebView 播放器历史债务；④ 历史回归根因分析作为设计基础（三波衰退溯源）。v2 的 P0 成果全部保留，作为 v3 Phase 1 止血层；R2/R3 独立为 Phase 0 快修。

**v3 相对 v2 的核心变化**：v2 是"补点"——在既有播放链路上逐点修补；v3 是"收束"——承认播放/下载两条链路的头组装、清单解析、嗅探能力分叉本身就是历史教训的延续（三大排查结论 B），用 SniffEngine/HeaderResolver/M3u8Parser 三个共享抽象根治，并删除已判死刑的 WebView 播放器。

---

## 二、历史回归根因分析专章

### 2.1 巅峰形态（07-13~07-18）与四支柱

巅峰期自评"90%+ 非 DRM 场景可替代手填规则"，本质由四个支柱支撑：

1. **宽抓包窗口**：R5 WebView 抓包 timeout=15000ms/delay=3000ms（`git show 7e11d7399:VideoUrlExtractor.kt` 实证），慢站点/JS 动态加载站点有充分时间发出视频请求。
2. **直连兜底不轻易放弃**：正则兜底失败后回退"文章链接带头直连 ExoPlayer"（第 4 层），任何一层失败都不轻易放弃直连。
3. **OkHttp Cookie 闭环**：播放数据源走 OkHttp，WebView CookieManager 的会话 Cookie 经 CookieJar 可达播放请求。
4. **单层嗅探单 scope 池**：仅 R5 一层嗅探不互相截流；WebView 池单 scope，pauseTimers 无竞争。

**巅峰 vs 现状关键维度对比**：

| 维度 | 巅峰期（07-13~07-18） | 现状（08-31） | 变化性质 |
|------|----------------------|---------------|---------|
| R5 抓包窗口 | 15000ms/3000ms | 6000ms/1000ms | 行为回归（第一波） |
| 直连兜底 | 第 4 层文章链接带头直连 | 已删除，改 WebView 提示事件 | 行为回归（第一波） |
| 嗅探层数 | 单层（R5） | 双层（R5 6s+Exo 层 5s）+m3u8 预检 3s | 结构复杂化 |
| 播放网络栈 | OkHttp（CookieJar 闭环） | Cronet（视频链路 cronetDataFactory 无条件装配，"默认启用"仅指该链路维度，见 §3.7），Cookie 断链 | 结构性回归（第二波） |
| m3u8 处理 | 统一路径直达播放 | 短路+HEAD 预检，403 仅补 UA，Fail 静默回退 | 预检截流（第二波） |
| WebView 池 | 单 scope 无竞争 | 3 scope，曾发生进程级误冻结（08-30 已修） | 已修复 |
| 命中回传 | URL-only（被兜底掩盖） | 同样 URL-only，掩盖层已全拆 | 缺陷暴露 |

### 2.2 三波衰退逐波机制分析

**第一波（07-26 `af3ba150c`）——预算压缩+兜底拆除**：R5 窗口 15s/3s→6s/1s（慢站点在 1s 内未发出视频请求即窗口关闭）；删除第 4 层直连兜底改 `VIDEO_FALLBACK_WEBVIEW` 提示（直连覆盖面收缩）；新增 Exo 层 sniffVideoType(5s) 与 R5(6s) 叠加为双层嗅探（超时预算叠加、链路复杂化）。动机是防非视频流 URL 进 ExoPlayer 报 3002，属 bug 修复引入的行为回归。

**第二波（07-31 `d69e266fe`+`578ae9705`）——Cookie 断链+预检截流**：Cronet 默认启用后 media3 播放数据源（CronetDataSource 路径）与 OkHttp CookieJar 体系脱节（注：回归报告称 `d69e266fe` 当日将 `AppConfig.isCronet` 置默认 true，属全局开关维度翻转——该开关仅控 OkHttp builder 的 Cronet interceptor 装配；而视频播放链路 cronetDataFactory 本就无条件装配 Cronet、不受该开关控制，本波衰退对播放链路的有效机制是"CronetDataSource 无 Cookie 注入"，非开关翻转本身，详见 §3.7 消解），嗅探拿到的会话 Cookie 无法传递给播放请求（支柱三断裂，结构性回归，影响面最大）；同日引入 M3u8PreCheckDataSource：.m3u8 短路+3s HEAD 预检，403 仅补 UA（M3u8PreCheckDataSource.kt L130-137，缺 Referer/Cookie），Fail 一律静默 "using original url"（ExoPlayerHelper.kt L377-406），预检把"最后补头机会"截流且无告警，负收益。

**第三波（08-19 `bbc9d0a89`）——基础设施误冻结**：WebView 池分 3 scope 后，pauseTimers/resumeTimers 为**进程级 API**却按单一 scope 的池空判断误判，发现/订阅页释放 WebView 时误冻结 GLOBAL 池中嗅探 WebView 的 JS，6s 窗口内 JS hook 全失效。08-30 已修复闭环（真机 3/3 PASS），但证明 WebView 基础设施改动对嗅探是高危区。

**回归点清单（逐条溯源，置信度依据回归分析报告）**：

| # | 提交 | 回归机制 | 置信度 |
|---|------|----------|--------|
| R1 | `bbc9d0a89`（08-19） | WebView 池 pauseTimers 进程级 API 按 scope 误判，误冻结嗅探 JS（08-30 已修复闭环） | 高（源码+spec 双证） |
| R2 | `d69e266fe`（07-31） | Cronet 默认启用未迁移 Cookie 上下文，播放会话与嗅探会话分裂 | 高（spec 明文） |
| R3 | `578ae9705`（07-31） | M3u8PreCheck 403 仅补 UA+Fail 静默回退，预检截流"最后补头机会" | 高（源码直证） |
| R4 | `af3ba150c`（07-26） | 窗口压缩 15s→6s+删直连兜底+双层嗅探叠加 | 高（diff 直证） |
| R5 | `7e11d7399`（07-13） | 四路命中点 URL-only 回传（shouldInterceptRequest/shouldOverrideUrlLoading/onLoadResource/ReadVideoUrlsRunnable，先天埋雷，后被放大） | 高（diff 直证） |
| R6 | `ac5a0a8aa`（07-28） | .html 后缀预判跳过 Range 嗅探，误杀 HTML 样式视频流 URL | 中 |
| R7 | `f17ce8a17`（07-12） | WebView 兜底引擎引入，降级链渐变为常态出口 | 中（方向性） |
| R8 | `4737db485`（07-10） | 头组装 5 处重复模式确立（债务而非回归） | 中 |
| R9 | 外部因素 | 站点风控增强放大一切断链缺陷 | 中 |

### 2.3 先天缺陷（巅峰期被掩盖）

- **命中点 URL-only 回传（07-13 即存在）**：四路命中点自诞生起即 `StrResponse(url!!, resUrl)` 丢弃命中现场上下文（BackstageWebView.kt L360 shouldInterceptRequest/L403 shouldOverrideUrlLoading/L419 onLoadResource/L490 ReadVideoUrlsRunnable 内部命中点），嗅探上下文（Cookie/Referer/UA）从未参与回传。
- **头组装 5 处分叉**：VideoPlay.kt 内部 5 个重复组装点（L466/515/540/646/1473），模式=源配置 headerMap+Referer=rssArticle.link，无 Cookie、无嗅探上下文。
- **巅峰期为何能用**：上述缺陷被四支柱掩盖——宽窗口保证嗅探本身命中、直连兜底保证"至少播出来"、Cookie 闭环保证会话可达。07-26/07-31 掩盖层逐项拆除后，断链缺陷全面暴露为 403/黑屏。

### 2.4 外部因素

站点风控增强（防盗链 403、一次性 token、UA/Cookie 校验更严）持续放大一切上下文断链缺陷，解释"同样的代码以前能播现在不能播"的部分现象。外部因素不可控，防御手段正是把嗅探上下文做成一等公民（AD-01）。

### 2.5 教训总结：为何逐点修补失效

三波衰退的共同模式：**每次修复都是针对单一症状的局部补丁，而系统性缺陷（上下文断链+头组装分叉）未根治，新补丁又引入新的截流点**（预检截流、双层嗅探叠加、进程级 API 误判）。v2 的 P0 逐点修补能止血，但不解决：① 播放/下载两链路分叉持续产生新的不一致；② WebView 播放器债务持续消耗维护面；③ 无"唯一收口点"则未来任何改动仍可能再次踩断嗅探路径。v3 的答案：抽象收口（AD-02/AD-06）+ 防衰退机制（第八章）。

---

## 三、Technical Approach

### 3.0 四层架构总览（自上而下箭头链）

调用方层：VideoPlay（PLAY 播放）/ VideoFragment+DownloadService（DOWNLOAD 下载）/ M3u8PreCheckDataSource+ExoPlayerHelper（PROBE 预检） → 意图请求 → SniffEngine（help/video/engine/ 新包）：SniffRequest{targetUrl, source, ruleData, intent} → 四层发现流水线（L1 静态解析 MacCMS/DOM → L2 WebView 抓包带上下文 → L3 直连探测 probe）→ List&lt;SniffCandidate&gt;{url, headers, mimeType, contentType, sourceMeta, timestamp} → 评分选优 → auth-retry（403 补头重试）→ 去重缓存 → 唯一候选 → HeaderResolver.buildHeaders(candidate, source, ruleData, targetUrl)（嗅探上下文优先+源配置兜底+CookieManager.getCookie(targetUrl) 兜底）→ 统一头（播放入 currentPlayHeaders；下载持久化 headersJson）→ 基础设施层：Exo2MediaPlayer/ExoPlayerHelper（播放）· ChunkDownloader/HlsDownloader（下载）· M3u8Parser（清单解析共享）。

### 3.1 SniffEngine（引擎门面）

- **输入模型 SniffRequest**：targetUrl（文章/页面链接）、source（书源/订阅源，RuleDataInterface 已抽象 resolveReferer 先例）、ruleData（页面上下文，用于 Referer 兜底与规则头）、intent（PLAY/DOWNLOAD/PROBE 三意图，决定评分权重与是否强制预检）。
- **四层发现流水线**（短路式，命中即收口）：
  - L1 静态解析：复用 VideoUrlExtractor 快速路径/MacCMS 正则与 VIDEO_SOURCE_REGEX（L98-160 可复用资产），无 WebView 开销，headers 留空 Map；
  - L2 WebView 抓包：BackstageWebView 四路命中点（L360/L403/L419/L490）回传 SniffCandidate（Phase 1 成果），携带命中现场 requestHeaders（仅 shouldInterceptRequest 路可获取 WebResourceRequest.requestHeaders，其余三路仅 URL 上下文）+CookieManager 动态 Cookie+WebView UA；
  - L3 直连探测（probe）：对候选 URL 发 HEAD/Range-1KB 小请求验活并采 Content-Type（Phase 4 深化）。
- **评分选优**：类型权重（m3u8 主清单>分片>直链视频）+分辨率提示（清单内 BANDWIDTH/RESOLUTION）+时序新近度（后命中优先于先命中，规避广告）；Phase 1 简化为"首命中+合法性校验"，Phase 4 完整评分器。
- **auth-retry**：对候选/预检 403 → HeaderResolver 补齐头（Referer+Cookie）重试一次 → 仍 403 → Rejected(statusCode) 语义（区别于瞬时 Fail）。
- **去重缓存**：playerPageCache+r5InProgress 并发去重模式泛化（VideoUrlExtractor L65-79 可复用资产），同页多调用方（播放+下载+预检）共享一次嗅探结果，intent 不同仅评分与预检策略不同。
- **对外接口（文字描述）**：`suspend fun execute(request: SniffRequest): SniffResult`（主入口，SniffResult 含候选列表/选中候选/Rejected 标记）；`fun play/download/probe(request): SniffResult`（三意图语义化封装，内部统一走 execute）；`fun invalidate(pageUrl)`（页面切换时清缓存）；auth-retry 与评分内聚在 execute 流水线内，调用方不感知重试细节。

### 3.2 HeaderResolver（统一头收口）

- `buildHeaders(candidate, source, ruleData, targetUrl): Map<String,String>`，merge 策略固定三层：嗅探上下文（命中现场头）优先 → 源配置 headerMap 兜底 → CookieManager.getCookie(targetUrl) 兜底 Cookie；Referer 兜底顺序：嗅探头 > 源配置 > ruleData 页面链接。
- **替代 5 处分叉**：播放链 VideoPlay 5 个重复点（L466/515/540/646/1473）+ VideoUrlExtractor headerMap（L302-312）+ ExoPlayerHelper.buildAntiLeechHeaders（L1077，BROWSER_UA+无 Cookie）；下载链 ChunkDownloader.resolveHeaders（L66-67，currentPlayHeaders ?: 仅 UA）+ DownloadService.parseHeaders（L597-607，恢复场景二次丢失）。
- **产出持久化 headersJson**：下载任务入库时序列化完整头，DownloadService 恢复/续传时 parseHeaders 直接还原（根治恢复场景二次丢失），旧任务无 headersJson 时降级现状 UA-only 行为。

### 3.3 M3u8Parser 共享模块（从 HlsDownloader 下沉）

- 抽取 `parsePlaylist / pickVariant / parseCrypto / resolveRelative` 四个纯函数到 help/video/engine/，HlsDownloader 现自研全套：清单 fetch（L218-228）、分片解析（L230-260）、AES key（L320-330，透传注释）、pickBestVariant（L341-371）、parseSegments（L379-402）、parseCrypto（L297-339）、resolve（L404-408）、时效签名缓解（L68-117）、remux（L427+）。
- 播放侧获得对应能力：M3u8PreCheckDataSource 预检从"无解析 HEAD"升级为"清单结构感知"（PROBE 意图调 parsePlaylist 验合法性）；Phase 4 播放侧 master playlist variant 感知（Exo 层用 pickVariant 选优清晰度）。
- 下沉原则：**等价迁移**——解析行为零变化，纯代码位置移动+可见性放开，下载侧回归风险最小化。

### 3.4 调用方接入

- **VideoPlay（PLAY）**：startPlay 改调 SniffEngine.play，消费候选+HeaderResolver 统一头落 currentPlayHeaders；switchToken 守卫、重嗅一次、onPlayerError 403 快速重试为 Phase 1 已就位能力。
- **Download/DownloadService（DOWNLOAD）**：VideoFragment 下载入口（L810-832 现状直接取 VideoPlay.videoUrl——播放嗅探的上下文对下载不可靠且耦合播放状态）改走引擎独立嗅探；headersJson 随任务持久化，下载器不再依赖"播放现场遗留头"。
- **M3u8PreCheck（PROBE）**：预检并入引擎 PROBE 意图，保留 .m3u8 短路定位，但 auth-retry+Rejected 语义替代"403 仅补 UA+Fail 静默回退"（重试复用共享 OkHttpClient——newBuilder 继承连接池/拦截器；首次预检 3s+补头重试独立 3s，外层总预算 6s）。

### 3.5 可复用资产清单（引擎不重复造轮子）

| 资产 | 位置 | 复用方式 |
|------|------|----------|
| playerPageCache+r5InProgress 并发去重 | VideoUrlExtractor L65-79 | 泛化为引擎去重缓存内核 |
| VIDEO_SNIFF_JS/VIDEO_SOURCE_REGEX | VideoUrlExtractor L98-160 | L1 静态解析与 L2 注入脚本原样复用 |
| videoStreamClient（强制 HTTP/1.1） | HttpHelper L246-250 | L3 直连探测与预检复用 |
| HttpCaptureHelper 抓包头重建 | HttpCaptureHelper L172-341 | HeaderResolver 头合并参考实现 |
| resolveReferer 已抽象 RuleDataInterface | RuleDataInterface L588-594 | SniffRequest.source 的来源抽象基础 |

### 3.6 分阶段实施（每阶段验证门禁+回滚锚点）

- **Phase 0 独立快修**（R2+R3，7 文件）：R2 订阅经典布局 padding 重置（RssFragment.applyClassicRssMode 显式恢复 clipToPadding=false+top padding 归零+folderComposeView 防御归零）；R3 线程数 256+三处钳制（OtherConfigFragment numberAction max 256、AppConfig coerceIn(1,256)、WebViewPool coerceAtMost(15)、CacheBookService+ImageCanvasViewModel min(n,128)、HttpHelper ConnectionPool(128)）。门禁：classic 首屏 L2 用例+线程 256 配置压测；回滚锚点：单 commit revert。
- **Phase 1 止血恢复巅峰**（v2 P0 全量+巅峰参数，7 文件）：SniffCandidate 四路命中点回传（shouldInterceptRequest L360/shouldOverrideUrlLoading L403/onLoadResource L419/ReadVideoUrlsRunnable 内部命中点 L490，仅拦截路有 requestHeaders）、buildPlayHeaders 收口（时序约束：setDefaultHeaders 全局覆盖仅在 setUp 时序点调用；预加载/并发场景必须独立 DataSource factory 实例，防全局头互相污染）、预检 auth-retry+Rejected（重试复用共享 OkHttpClient：newBuilder 继承连接池/拦截器；超时预算为首次预检 3s+补头重试独立 3s，外层总预算 6s）、重嗅一次、switchToken、onPlayerError 403 快速重试；另恢复 R5 窗口 6s/1s→15s/3s 并加"命中即收口"自适应（检测到视频请求提前收口，快站点不多等）+Z3 AES key Factory 接入主链路+Z5 isPreparing 死代码确认处置。门禁：真机直连成功率对比基线（恢复前 vs 恢复后，防盗链源样本≥5）；回滚锚点：参数常量+代码单 commit。
- **Phase 2 删 WebView 播放器**（10 文件）：删除 WebViewVideoPlayer 及全部引用面；失败路径三通道保留——tryNextFallback 降级链+BUFFERING 超时自愈（独立于 WebView）、retryExoPlayback 重试按钮复用、错误对话框"重试/系统浏览器"通道；存量 playerType=2 持久化迁移：首次启动读旧值 2→写回 1（一次性迁移，现 coerceIn(0,2)→(0,1) 仅 UI coerce 不改存储值，存储残留 2 需一次性写回归位）。门禁：全类型源播放回归（m3u8/mp4/ts/mpd）+存量配置覆盖安装验证；回滚锚点：整阶段单 commit revert。
- **Phase 3 SniffEngine 抽象统一**（新引擎 4 文件+改造 7 文件）：引擎接口+三调用方接入+M3u8Parser 下沉共享+下载按需嗅探+headersJson 持久化协议+AD-12 预加载重设计+Z4 SimpleCache 键统一+Z9 播放历史原始 URL+Z10 书源对称化+Z7 cronet 开关统一。门禁：播放/下载双链路端到端用例+下载续传恢复用例；回滚锚点：调用方逐个接入，任一调用方异常可单独回退到 Phase 1 直连路径（引擎为纯新增包）。
- **Phase 4 超越 M 浏览器**（2-3 文件）：拦截面扩展（响应 Content-Type 白名单 video/*、application/vnd.apple.mpegurl、application/dash+xml、audio/*、video/mp2t+URL 模式 .flv/.ts/.mpd）+修正 L1 排除规则与 Content-Type 判定顺序（现 BackstageWebView L344 contains('.html') 在正则与 Content-Type 之前执行，误杀 HTML 壳内直链视频的源，即回归点 R6；与 Z15 buildFallbackTypes HTML 检测失真一并修正，否则拦截面扩展对 R6 场景无效）+多候选完整评分器+播放侧 master playlist variant 感知（M3u8Parser.pickVariant 进播放链）。P2 登记（后续版本）：播放侧 AES key 下载侧透传对齐（主链路接入已由 Phase 1 Z3 完成，HlsKeyDataSourceFactory 剩余下载侧透传对齐）、DASH 多周期支持。门禁：候选评分 AppLog 观测+独立回退验证；回滚锚点：Phase 4 独立 commit，不触 Phase 0-3。

---

### 3.7 网络栈定位：Cronet 与 DoH（用户三轮追问澄清，防实施走样）

**Cronet 定位：保留且为主网络栈，绝不回退 OkHttp。**

- **为什么默认启用**：Cronet 默认启用是**用户决策的爬取能力优化**——两个"默认"的准确指代（消解双"默认"矛盾）：`AppConfig.isCronet`（PreferKey.cronet 默认 false）仅控制 OkHttp builder 是否装配 Cronet interceptor；视频播放链路 cronetDataFactory 为无条件装配不受该开关控制（ExoPlayerHelper L1029）——"默认启用"仅指视频链路（07-31 `d69e266fe` "perf: 全链路优化嗅探稳定性与网络健康度"提交涉及全局开关维度，回归报告称当日置默认 true；无论该开关历史值如何翻转，视频链路本就无条件走 Cronet，实施者不得误以为改 isCronet 能控制播放链路）。Cronet 相比 OkHttp 对爬取场景的核心优势：QUIC/h3 传输（0-RTT 恢复、队头阻塞消除，日志实证源站接口 h3 协商成功）、连接复用与连接迁移、TLS 栈指纹更接近真实浏览器（降低被风控拦截概率）。lib/cronet 基础自 fork 初始 commit 即集成，默认启用是其角色升级而非引入失误。
- **历史回归的正确解读**：第二波衰退中"Cronet 默认启用 → Cookie 断链"的本质**不是 Cronet 的缺陷**，而是网络栈迁移时 Cookie 注入机制未跟上——OkHttp 侧有 NetworkInterceptor 的 `cookieJarHeader` 条件注入兜底，而 media3 `CronetDataSource` 直连 CronetEngine 无对应机制，且 CronetInterceptor 的注入条件（cookieJarHeader）视频播放路径不满足。**v3 的处置是在 Cronet 链路补齐注入**（HeaderResolver 统一组装 → `cronetDataFactory.setDefaultRequestProperties` + CronetInterceptor 条件复核），不是退回 OkHttp。
- **DoH 定位：保留并一致化，不废弃。**

**DoH（DohDns）现状盘点**：

| 组件 | 现状 | DNS 来源 |
|------|------|---------|
| DohDns（help/http/DohDns.kt） | 双国内 DoH 服务器（阿里 dns-query + 腾讯 doh.pub，bootstrap IP 直连）+负缓存+并行探测+冷启动降级+连续失败禁用回退 | 仅挂 OkHttp 栈（HttpHelper L177-179 `builder.dns(DohDns)`），绕过本地 DNS 污染/SNI 阻断 |
| 播放预解析 preResolveDns（ExoPlayerHelper L305-317） | 播放前对视频 host 预热解析（纯 JVM 缓存预热，异常静默） | **java.net.InetAddress 系统 DNS，未走 DohDns**（不一致点） |
| Cronet 内置 resolver | CronetEngine 自带 DNS（平台限制：Engine builder 不支持自定义 Dns 接口） | 系统 DNS（DoH 无法覆盖，预解析预热缓解） |

**v3 集成动作**：
1. Phase 1 补小项：`preResolveDns` 改走 DohDns（一致化：预解析也享受 DoH 反污染与缓存，降级链已有系统 DNS 兜底）；
2. Phase 1 已含：HeaderResolver 头注入覆盖 CronetDataSource 路径（Cookie 断链修复的主战场就在 Cronet 链路）；
3. DoH 收益范围声明：OkHttp 栈请求（嗅探预检、下载分片 videoStreamClient、源站接口回退路径）继续全覆盖；Cronet 栈因平台限制保持内置 resolver，靠 preResolveDns 一致化预热弥补首连延迟。

## 四、Architecture Decisions

> 格式：Y-Statement 完整六要素（Context / Concern / Decision / Goal / Tradeoff / Status）

### AD-01 嗅探上下文端到端回传（先天缺陷根治）

- **Context**：四路命中点（shouldInterceptRequest L360/shouldOverrideUrlLoading L403/onLoadResource L419/ReadVideoUrlsRunnable 内部命中点 L490）自 07-13 起即 StrResponse(url, resUrl) 只回传 URL，命中时刻 requestHeaders、CookieManager 动态 Cookie、WebView UA 全部丢弃；巅峰期被四支柱掩盖，07-26/07-31 掩盖层拆除后全面暴露为 403。
- **Concern**：嗅探结果离开其真实可访问环境后，播放/下载端只能用源配置头+固定 UA 重新猜测访问环境，头猜错即被源站拒绝；这是历史回归链条的第一根因（先天缺陷），逐点修补无法根治。
- **Decision**：SniffCandidate 数据类承载 {url, headers, mimeType, contentType, sourceMeta, timestamp}；四路命中点均构造 headers（可获取的上下文差异：仅 shouldInterceptRequest L360 拦截点有 WebResourceRequest.requestHeaders——读之并合并 CookieManager.getCookie(url)+settings.userAgentString；其余三路——shouldOverrideUrlLoading L403/onLoadResource L419/ReadVideoUrlsRunnable L490——只有 URL 上下文，用 CookieManager+settings+view.url 构造。平台约束：requestHeaders 不含网络栈注入的 Cookie，导航请求 Referer 也不保证在列，Cookie 一律以 CookieManager.getCookie(url) 为准）；getStrResponse 采用扩展式改造（原 body 用法不变，新增 headers 字段）。
- **Goal**：嗅探结果从"裸 URL"升级为"资源+实际可访问环境"，作为 v3 引擎的核心模型端到端流转，根治先天缺陷。
- **Tradeoff**：返回类型 String→对象需同步全部调用方（均在修改清单内）；headers 默认空 Map 静态路径零破坏；比 v2 多携带 mimeType/contentType/sourceMeta 三个字段（为 Phase 4 评分预留），序列化开销可忽略。
- **Status**：Accepted（2026-08-31，v3 继承 v2 P0-1 并扩展字段）

### AD-02 HeaderResolver 统一收口（5 处分叉是结构性根源）

- **Context**：头组装在播放链 3 处（VideoPlay 内部 5 个重复点 L466/515/540/646/1473、VideoUrlExtractor L302-312、ExoPlayerHelper.buildAntiLeechHeaders L1077）与下载链 2 处（ChunkDownloader.resolveHeaders L66-67=currentPlayHeaders ?: 仅 UA、DownloadService.parseHeaders L597-607=恢复场景二次丢失）分叉，语义同一实现各异。
- **Concern**：同一"为资源构造访问头"语义 5 处独立演化，任何一处补 Cookie/补 Referer 都无法覆盖其余四处；播放/下载行为不一致正是用户"能播不能下"的直接结构性根源，逐点修补在历史上已被证明失效（2.5 节）。
- **Decision**：新增 HeaderResolver.buildHeaders(candidate, source, ruleData, targetUrl) 唯一收口点，merge 策略"嗅探上下文优先→源配置兜底→CookieManager.getCookie(targetUrl) 兜底"；5 处分叉全部改为调用；下载链产出持久化 headersJson。
- **Goal**：访问头构造唯一出口、可单测；播放与下载永远获得一致的头策略。
- **Tradeoff**：机械触碰 5 处既有路径（语义等价替换，Phase 3 执行）；头冲突时嗅探值优先——依据是嗅探上下文是资源实际可访问时刻的实测有效环境，源配置只是声明式猜测；旧下载任务 headersJson 缺失需降级路径（第七章）。
- **Status**：Accepted（2026-08-31，v3 新增，替代 v2 AD-02 的 buildPlayHeaders 局部收口）

### AD-03 auth-retry-first + Rejected 语义分支

- **Context**：M3u8PreCheckDataSource.headPreCheck 403 仅补 UA（L130-137），verifyExtM3UHeader 同样；预检结果仅 Success/Fail 两态，Fail 被 ExoPlayerHelper 静默 "using original url"（L377-406）。
- **Concern**：403 最常见原因是头不全（缺 Referer/Cookie），只补 UA 必然再失败；"确定性拒绝"与"瞬时失败"共用 Fail 语义，下游无法区分"该补头重试"与"该放弃"，预检形同虚设还叠加 3s 延迟。
- **Decision**：预检 403 → HeaderResolver 合并完整头 auth-retry 一次（重试请求复用共享 OkHttpClient——newBuilder 继承连接池/拦截器，禁止 new 新实例重付 DNS+TCP+TLS 全握手）→ 仍 403 返回 PreCheckResult.Rejected(statusCode)，与 Fail（5xx/超时/IO 瞬时）语义分离；Rejected 驱动上游重嗅一次，仍 Rejected 给确定性提示；Fail 回退 original url 行为保留但记 AppLog。
- **Goal**：对齐成熟嗅探器 auth-retry-first 机制，拒绝语义显式化，预检从负收益转为有效截流层。
- **Tradeoff**：403 场景多一次头部小请求（HEAD/Range-1KB）——超时预算为首次预检 3s+补头重试独立 3s（外层总预算 6s），避免单请求 read 超时=整个窗口导致 auth-retry 被外层超时截杀（弱网 RTT 300-500ms 下重试若 new 新实例重付全握手必逼近或超过 3s，形同虚设）；重试复用共享 OkHttpClient 使第二次请求仅付 RTT；枚举扩展需同步嗅探协程分支。
- **Status**：Accepted（2026-08-31，继承 v2 AD-03）

### AD-04 switchToken 竞态守卫（最小侵入递增序号）

- **Context**：VideoPlay.loadScope（L290）SupervisorJob 并列树，switchToArticle 的 cancel（L1283）覆盖不到 startPlay 内层异步回调；switchToRoute 已有 token 守卫先例（L1238-1247）。
- **Concern**：快速上滑切换时旧文章解析回调晚于新文章 setUp 到达，旧 URL/头覆盖播放器，产生错序播放与黑屏。
- **Decision**：VideoPlay 新增 AtomicLong switchToken 递增序号，switchToArticle/playRssEpisode 入口递增；startPlay 全部异步回调在 player.setUp 前校验 token，不一致丢弃并记 AppLog。不重构协程树。
- **Goal**：不动既有协程结构前提下消除过期回调覆盖，与 switchToRouteToken 模式一致。
- **Tradeoff**：过期协程仍跑完网络请求（浪费少量流量但不触 UI/播放器状态）；AtomicLong 免溢出讨论。
- **Status**：Accepted（2026-08-31，继承 v2 AD-04）

### AD-05 删除 WebView 播放器（摆设实锤+失败路径三通道）

- **Context**：WebViewVideoPlayer.kt（269 行）及其引用面共 10 文件；摆设实锤——模板 setRequestHeader('Referer') 被 Chromium forbidden header 规范静默忽略，WebView 播放器连防盗链核心头都设不上；用户两轮裁决（v1 否决降级出口、v3 明确删除债务）；画质增强仅 ExoPlayer 引擎生效、WebView 引擎规避，直连失败时用户在增强档位体验割裂。
- **Concern**：保留 WebView 播放器=维持 10 文件引用面+双引擎维护负担+与演进方向冲突；但直接删除需确认失败路径不劣化——现状 SSL 握手失败场景（Exo2MediaPlayer L834-844 走 WebView 承接）删除后需要有承接出口。
- **Decision**：Phase 2 整体删除 10 文件引用面；失败路径三通道承接——① tryNextFallback 降级链+BUFFERING 超时自愈（独立于 WebView 的既有能力）；② retryExoPlayback 重试按钮复用；③ 错误对话框"重试/系统浏览器"通道（系统浏览器天然具备完整 Cookie/JS 环境，能力等价覆盖 WebView 播放页且无维护成本）；存量 playerType=2 经 coerceIn 自动落 1。
- **Goal**：消除双引擎维护负担与体验割裂，失败路径确定性优于"黑盒 WebView"。
- **Tradeoff**：SSL 握手失败等少数场景从"WebView 自动承接"退化为"提示重试/系统浏览器"（占比低，列入监控）；删除面 10 文件需一次性完整提交防半删状态。
- **Status**：Accepted（2026-08-31，v3 新增）

### AD-06 SniffEngine 抽象统一播放/下载（分叉正是历史教训）

- **Context**：播放与下载两条链路在嗅探能力、头组装、清单解析三方面全面分叉：播放侧有 M3u8PreCheck 预检（无解析）+ExoPlayer 内置清单处理；下载侧 HlsDownloader 自研全套解析（L218-408）；嗅探能力仅播放链具备，下载直接取播放现场的 VideoPlay.videoUrl+currentPlayHeaders（VideoFragment L810-832）。
- **Concern**：下载复用播放现场意味着：播放嗅探失败则下载必然失败、播放与下载意图的评分标准不同（下载要全量分片、播放要主清单）却共用一个 URL、播放状态切换可能污染下载输入；历史教训表明分叉链路的修补成本随分叉点数量超线性增长。
- **Decision**：新增 SniffEngine（help/video/engine/）统一接收 SniffRequest{targetUrl, source, ruleData, intent}，三意图 PLAY/DOWNLOAD/PROBE 共享四层发现流水线与去重缓存，仅评分与预检策略按意图差异化；三调用方（VideoPlay/Download+DownloadService/M3u8PreCheck）逐个接入。
- **Goal**：嗅探能力播放/下载/预检一处建设三处受益；未来任何嗅探增强（如 Phase 4 拦截面）自动覆盖全链路。
- **Tradeoff**：下载按需嗅探引入独立抓包开销（DOWNLOAD 首次点击多一次 L2 流水线，去重缓存使同页播放已嗅探过的场景零额外开销）；引擎抽象有一次性学习/迁移成本（Phase 3 承担）。
- **Status**：Accepted（2026-08-31，v3 新增）

### AD-07 M3u8Parser 下沉共享而非播放侧自研流水线

- **Context**：HlsDownloader 自研全套 HLS 解析（清单 fetch/分片/AES key/pickBestVariant/parseSegments/parseCrypto/resolve/时效签名缓解/remux，L68-427+）；播放侧预检无解析能力，Phase 4 需要 variant 感知。
- **Concern**：若播放侧另起炉灶自研清单解析，将复制下载/播放第二处分叉（重蹈 5 头组装分叉覆辙）；若强行让播放侧复用 HlsDownloader 整体，则拖入 remux/文件写入等下载专属职责。
- **Decision**：从 HlsDownloader 抽取 4 个纯函数（parsePlaylist/pickVariant/parseCrypto/resolveRelative）下沉到 help/video/engine/M3u8Parser，下载侧改调用共享模块，播放侧 PROBE/variant 感知直接消费；remux/文件 IO 留在 HlsDownloader。
- **Goal**：清单解析一处实现双链路共享，解析规则 bug 修复自动同步两侧。
- **Tradeoff**：等价迁移需回归下载全量用例（清单/加密/多码率三类样本）；纯函数化要求去除对下载器状态的隐式依赖（迁移工作量可控）。
- **Status**：Accepted（2026-08-31，v3 新增）

### AD-08 多候选评分选优与拦截面扩展（超越 M 浏览器）

- **Context**：shouldInterceptRequest 仅靠 URL 特征模式命中，裸路径无后缀的 CDN 清单/分片漏拦；window.__videoUrls__ 单列表首命中即用，多候选场景（广告分片/多清晰度）首命中可能是广告或低清。
- **Concern**：拦截面不足与首命中即用两个限制使直连能力止步于 M 浏览器之下；但盲目扩拦截面会引入误报与评分抖动。
- **Decision**：Phase 4 拦截面扩展采用响应 Content-Type 白名单（video/*、HLS/DASH 清单类型、audio/*、mp2t）+URL 模式扩展（.flv/.ts/.mpd）；多候选评分器（类型权重+清单分辨率提示+时序新近度）代替首命中，广告分片靠"时序+类型"双重降权；评分结果 AppLog 观测调参。
- **Goal**：拦截面与选优能力对齐并超越 M 浏览器（借助源配置与 ruleData 上下文，M 浏览器不具备）。
- **Tradeoff**：评分是启发式存在选优波动（独立交付可回退）；Content-Type 读取需消费 shouldInterceptRequest 的 webResourceResponse（仅对白名单类型生效，开销可控）。
- **Status**：Accepted（2026-08-31，继承 v2 AD-06 并入 Phase 4）

### AD-09 分阶段渐进实施（每阶段独立验证回滚，反对一次性重构）

- **Context**：v3 全量范围含参数恢复、上下文回传、10 文件删除、引擎抽象、拦截面扩展五个层次；历史教训（08-19 一次基础设施改动即引发系统性嗅探失能）表明大爆炸式合入的回归定位成本极高。
- **Concern**：一次性重构若中途失败，既无法验证单项收益，也无法归因回归；而"只规划不分解"会重演逐点修补失效模式。
- **Decision**：五阶段流水线 Phase 0→4，依赖关系：Phase 0 独立（可先行交付）；Phase 1 止血（最高优先级，独立产生直连成功率收益）；Phase 2 删除债务（依赖 Phase 1 失败路径三通道就位）；Phase 3 抽象统一（以 Phase 1 成果为引擎内核）；Phase 4 增强（依赖引擎就位）。每阶段带验证门禁（L2 固化用例+真机验证）与独立回滚锚点（单 commit）。
- **Goal**：每个阶段独立可验证、可回滚、可交付，止血收益（Phase 1）不因后续阶段风险被阻塞。
- **Tradeoff**：分阶段总周期长于一次性实施；中间态存在"已删 WebView 但引擎未就位"的过渡形态（Phase 1 直连能力已恢复，WebView 在 Phase 2 仅剩极少数失败场景兜底，可接受）。
- **Status**：Accepted（2026-08-31，v3 新增）

### AD-10 线程数 256 上限+三处独立钳制

- **Context**：updateCacheThreadCount 上限 64（UI max+coerceIn，默认 16），派生 WebViewPool.globalMaxCached=max(n/10,5)、CacheBookService/ImageCanvasViewModel 线程池 newFixedThreadPool(n)、HttpHelper ConnectionPool(50,5,MINUTES)。
- **Concern**：直接放开 256 无防护将产生 25 个缓存 WebView（每实例 20~50MB）、256 线程栈、50 连接池排队瓶颈三重风险。
- **Decision**：UI max 与 coerceIn 同步放宽 64→256（默认 16 不变）；三处独立钳制：WebViewPool 追加 coerceAtMost(15)（绝对钳制）、两处线程池 min(n,128)（软钳制，覆盖初始创建与变更重建两条路径）、ConnectionPool 扩至 (128,5,MINUTES)。
- **Goal**：吞吐上限 4 倍提升同时三处资源上限确定，任一配置值不 OOM。
- **Tradeoff**：256 配置下实际执行线程钳到 128（超出排队）；WebView 池 15 个对超高并发复用率略降；存量 ≤64 配置零影响。
- **Status**：Accepted（2026-08-31，继承 v2 AD-08）

### AD-11 Cronet 保留为主网络栈 + DoH 一致化（不回退、不废弃）

- **Context**：用户三轮追问澄清两点——①Cronet 默认启用是用户决策的爬取优化（QUIC/h3/连接复用/TLS 指纹接近浏览器），历史回归中的"Cronet Cookie 断链"是注入机制未跟上而非 Cronet 缺陷，须在文档明确防止实施时误回退 OkHttp；②DohDns（双国内 DoH 服务器，OkHttp 栈防 DNS 污染）自嗅探优化引入，v3 初稿通篇未提，疑似废弃；另发现 preResolveDns（播放预解析）用系统 DNS 与 DohDns 不一致。
- **Concern**：架构文档缺网络栈定位会导致实施走样（误回退 Cronet/误删 DoH）；DNS 策略不一致使播放预解析绕过了 DoH 反污染能力。
- **Decision**：Cronet 保留为主网络栈，Cookie/头注入在 Cronet 链路补齐（HeaderResolver → cronetDataFactory + CronetInterceptor 条件复核）；DoH 保留并一致化——preResolveDns 改走 DohDns；Cronet 内置 resolver 因平台限制（Engine builder 不支持自定义 Dns）保持现状，靠预解析预热弥补。
- **Goal**：网络栈定位文档化防走样；DNS 策略一致化消除反污染盲区；爬取优势（QUIC/h3）与防污染能力（DoH）同时保全。
- **Tradeoff**：preResolveDns 走 DoH 首解析略增延迟（降级链已有系统 DNS 兜底）；Cronet 栈无法直接享受 DoH（平台限制，预热缓解）。
- **Status**：Accepted（2026-08-31，v3 三轮追问新增）

### AD-12 预加载体系重设计（基于 SniffEngine 预采集，Phase 3）

- **Context**：Z1——视频级预加载（FirstFramePreloader/VideoPreloader）因 NPE bug 被注释禁用，预加载配置项（videoPreloadCount/BytesMB/TriggerProgress、playerPrecacheRange）全部失效；Z4——SimpleCache 预载键（原 URL）与播放键（重定向 finalUrl）不一致即使启用也可能永不命中；上滑秒开当前仅靠 HTML 预热+LoadControl。
- **Concern**：预加载是"超越 M 浏览器"上滑体验的核心（M 浏览器依赖浏览器自身缓存）；带病复活旧预加载会复现 NPE 且键不一致浪费带宽。
- **Decision**：Phase 3 在 SniffEngine 就位后重设计预加载：预加载语义改为"预嗅探下一集（SniffEngine DOWNLOAD 前置采集候选+HeaderResolver 头快照）+SimpleCache 以 finalUrl 键预填首分片"；禁用的旧预加载代码与失效配置项在 Phase 3 一并清理或按新语义重写。预填头污染防线：预填首分片必须使用独立 DataSource 工厂实例或 per-request 头注入（禁止复用全局 lazy 单例工厂的 setDefaultRequestProperties，否则下一集头快照会污染当前播放中视频的分片请求）。
- **Goal**：上滑下一集命中预采集即近零等待；配置项与实际行为一致。
- **Tradeoff**：预嗅探消耗额外 WebView/网络资源（复用 r5InProgress 去重+仅在 WiFi/前台时触发缓解）；Phase 3 之前预加载维持禁用（现状不劣化）。
- **Status**：Accepted（2026-08-31，v3 四轮现状盘点新增）

---

## 五、Data Flow

### 5.1 播放主数据流（含 auth-retry 分支）

上滑切换 → switchToArticle → switchToken++ → startPlay → SniffEngine.play(SniffRequest{文章链接, source, ruleData, PLAY}) → L1 静态解析命中（headers 空 Map）或 L2 抓包命中（headers=命中现场头+动态 Cookie）→ 评分选优出唯一候选 → HeaderResolver.buildHeaders（嗅探头优先+源配置兜底+CookieManager.getCookie(videoUrl) 兜底）→ mergedHeaders 落 currentPlayHeaders → token 校验 → player.setUp(url, mergedHeaders) → PROBE 预检（.m3u8 时引擎内触发）→ 分支A 预检 200 → applyMediaSourceByType → 直连播放；分支B 预检 403 → HeaderResolver 补齐 Referer+Cookie auth-retry 一次（重试复用共享 OkHttpClient，独立 3s 重试预算、外层总预算 6s） → 成功转入分支A → 仍 403 → Rejected(statusCode) → VideoPlay 消费 → 新 Cookie 重嗅一次（单周期限一次）→ 命中且 token 一致 → 转 setUp 链 → 仍 Rejected → 提示"视频地址被源站拒绝，请稍后重试"（不经 WebView）。

播放期兜底流：播放中 onPlayerError(errorCode=2004, 反射 responseCode∈{403,410,451}) → 防重入检查 → HeaderResolver 重取 Cookie 补头快速重试一次 → 成功续播 → 失败 → 触发重嗅一次 → 仍失败 → tryNextFallback 降级链+BUFFERING 超时自愈 → 错误对话框"重试/系统浏览器"。

静态解析零嗅探头退化路径：L1 静态解析命中且无 WebView 上下文 → SniffCandidate.headers 为空 Map → HeaderResolver 退化为"源配置 headerMap+Referer"现状骨架 → CookieManager 兜底仅该域确有 Cookie 时追加 → 输出头与现状一致（或仅多域内 Cookie），直连行为不劣化。

过期回调丢弃守卫流：旧文章解析回调（慢）晚于新文章 setUp（快）到达 → 回调捕获 switchToken ≠ 当前 switchToken → 丢弃+AppLog → 播放器保持新文章状态，不产生错序覆盖。

### 5.2 下载主数据流（含 headersJson 续传）

下载入口（VideoFragment L810-832 改造点）→ SniffEngine.download(SniffRequest{页面链接, source, ruleData, DOWNLOAD}) → 独立嗅探（去重缓存命中播放现场结果则零开销）→ 评分（DOWNLOAD 权重：完整清单/全量分片优先）→ HeaderResolver.buildHeaders → 候选 URL+headersJson 序列化持久化入任务表 → DownloadService 启动 → parseHeaders(headersJson) 还原完整头（根治恢复场景二次丢失）→ ChunkDownloader（普通分片）或 HlsDownloader（HLS，解析改调 M3u8Parser）用统一头下载 → 续传/暂停恢复/重试均读同一 headersJson（不再依赖播放现场遗留头）。旧任务无 headersJson → 降级 resolveHeaders 现状行为（currentPlayHeaders ?: 仅 UA）。

### 5.3 预检数据流（PROBE 意图）

嗅探候选为 .m3u8 → 引擎 PROBE 意图触发 M3u8Parser.parsePlaylist 清单结构校验（新增能力，原预检无解析）→ HEAD/Range-1KB 预检（合并头，首次预算 3s）→ 200 → Content-Type+清单结构判定返回类型结论；403 → auth-retry 补头一次（重试复用共享 OkHttpClient：newBuilder 继承连接池/拦截器，不重付 DNS+TCP+TLS 握手；独立 3s 重试预算，外层总预算 6s——原"3s 窗口内可控"语义修正为独立重试预算，避免单请求 read 超时=整个窗口）→ 成功转正常 → 仍 403 → Rejected(statusCode) 上抛驱动重嗅；5xx/超时/IO → Fail（瞬时语义）→ 回退 original url（保留）+AppLog 告警（新增，消除静默）。

### 5.4 订阅模式切换 padding 生命周期（R2）

初始进入：fragment_rss.xml 初始态 recycler_view padding=0、clipToPadding=false → classic→modern：applyModernRssMode → 顶栏回调 → updateModernRssTopBarOverlay → clipToPadding=true + setPadding(left, topBar.height, right, bottom) → modern 内高度变化：重写 padding（top 取新高度，余透传）→ modern→classic（修复点）：resetRssModeState（纯状态清理不变）→ applyClassicRssMode 开头显式恢复 clipToPadding=false + setPadding(当前left, 0, 当前right, 当前bottom) + folderComposeView padding 防御归零。修复后不变式：classic 模式 padding 恒为 (XML值, 0, XML值, XML值) 且 clipToPadding=false，与是否经历过 modern 无关；modern 行为完全不变。

---

## 六、File Changes

### Phase 0（7 文件）

| # | 文件 | 修改点 | 变更类型 | 风险 |
|---|------|--------|----------|------|
| 1 | ui/main/rss/RssFragment.kt | applyClassicRssMode（L383-419）padding/clipToPadding 恢复+folderComposeView 防御归零 | Modify | 低 |
| 2 | ui/config/OtherConfigFragment.kt | numberAction max 64→256（L452-463） | Modify | 低 |
| 3 | help/config/AppConfig.kt | updateCacheThreadCount coerceIn(1,64)→(1,256) | Modify | 低 |
| 4 | help/webView/WebViewPool.kt | globalMaxCached 追加 coerceAtMost(15) | Modify | 低 |
| 5 | service/CacheBookService.kt | 线程池 min(n,128)（含重建路径） | Modify | 低 |
| 6 | ui/image/ImageCanvasViewModel.kt | 线程池 min(n,128)（含重建路径） | Modify | 低 |
| 7 | help/http/HttpHelper.kt | ConnectionPool(50,5,MINUTES)→(128,5,MINUTES) | Modify | 低 |

### Phase 1（7 文件，含唯一新增 SniffCandidate）

| # | 文件 | 修改点 | 变更类型 | 风险 |
|---|------|--------|----------|------|
| 1 | help/video/SniffCandidate.kt | 新增数据类（url/headers/mimeType/contentType/sourceMeta/timestamp） | 新增 | 低 |
| 2 | help/http/BackstageWebView.kt | 四路命中点（L360 shouldInterceptRequest/L403 shouldOverrideUrlLoading/L419 onLoadResource/L490 ReadVideoUrlsRunnable）上下文回传+getStrResponse 扩展 | Modify | 中 |
| 3 | help/video/VideoUrlExtractor.kt | 三层返回 SniffCandidate；R5 窗口 6s/1s→15s/3s+命中即收口 | Modify | 中 |
| 4 | model/VideoPlay.kt | buildPlayHeaders 收口 5 处+switchToken+Rejected 重嗅入口 | Modify | 中 |
| 5 | help/exoplayer/M3u8PreCheckDataSource.kt | 403 合并头 auth-retry→Rejected(statusCode) 枚举分支 | Modify | 中 |
| 6 | help/exoplayer/ExoPlayerHelper.kt | sniffVideoType（L377-406）Rejected 分支+预检入参合并头 | Modify | 中 |
| 7 | help/gsyVideo/Exo2MediaPlayer.kt | onPlayerError（L736）2004+403 复用反射先例（L758-777 模式）补头快速重试+防重入 | Modify | 中 |
| 8 | help/exoplayer/ExoPlayerHelper.kt | HlsKeyDataSourceFactory 接入主链路 applyMediaSourceByType（Z3：加密流 key 防盗链头主链路生效，替代 P2 登记） | Modify | 低 |
| 9 | help/gsyVideo/Exo2MediaPlayer.kt | isPreparing 重入保护（L101）死代码确认处置：恢复 CAS 读写或删除（Z5） | Modify | 低 |

### Phase 2（10 文件）

| # | 文件 | 修改点 | 变更类型 | 风险 |
|---|------|--------|----------|------|
| 1 | ui/video/WebViewVideoPlayer.kt | 整文件删除（269 行） | Delete | 中 |
| 2 | res/layout/fragment_video.xml | 删 WebView 容器（L30-38）+btn_switch_back（L41-55） | Modify | 低 |
| 3 | ui/video/VideoFragment.kt | 删 btnSwitchBack/WebView 引擎引用与切换逻辑（L73/L190-215/L248/L337/L362-426） | Modify | 中 |
| 4 | ui/video/VideoPlayerActivity.kt | 删 WebView observe（L1563+）/切换对话框（L1586-1635）/switchCurrentToWebView（L1673-1676） | Modify | 中 |
| 5 | help/gsyVideo/Exo2MediaPlayer.kt | 删 5 处 post WebView 事件点（L403/L646/L844/L912/L939） | Modify | 中 |
| 6 | constant/EventBus.kt | 删 WebView 切换事件常量（L63 及相邻事件项） | Modify | 低 |
| 7 | assets/hls.min.js + assets/hls_video_player_template.html | 删除（WebView 播放器专用资产 2 文件） | Delete | 低 |
| 8 | res/values/strings.xml | 删 player_type_webview（L2032）等 3+1 条 | Modify | 低 |
| 9 | res/drawable/ic_swap_horiz.xml | 删除切换按钮图标 | Delete | 低 |
| 10 | ui/video/VideoSettingsPanelContent.kt | 播放器类型选项删 WebView 项（L488-500/L652-656），coerceIn(0,2)→(0,1)；存量 playerType=2 持久化迁移：首次启动读旧值 2→写回 1（一次性迁移，仅 UI coerce 不改存储值） | Modify | 低 |

### Phase 3（新引擎 4 文件+改造 7 文件）

| # | 文件 | 修改点 | 变更类型 | 风险 |
|---|------|--------|----------|------|
| 1 | help/video/engine/SniffEngine.kt | 引擎门面：SniffRequest/四层流水线/评分/auth-retry/去重缓存 | 新增 | 中 |
| 2 | help/video/engine/SniffModels.kt | SniffRequest/SniffCandidate 扩展/SniffResult/SniffIntent | 新增 | 低 |
| 3 | help/video/engine/HeaderResolver.kt | 统一头收口+headersJson 序列化协议 | 新增 | 低 |
| 4 | help/video/engine/M3u8Parser.kt | 从 HlsDownloader 下沉：parsePlaylist/pickVariant/parseCrypto/resolveRelative | 新增 | 中 |
| 5 | model/VideoPlay.kt | PLAY 接入引擎；播放头组装改调 HeaderResolver | Modify | 中 |
| 6 | ui/video/VideoFragment.kt | 下载入口（L810-832）改走引擎 DOWNLOAD 按需嗅探 | Modify | 中 |
| 7 | service/DownloadService.kt | parseHeaders（L596-607）改按 headersJson 协议恢复 | Modify | 低 |
| 8 | help/download/ChunkDownloader.kt | resolveHeaders（L66-67）改调 HeaderResolver | Modify | 低 |
| 9 | help/download/HlsDownloader.kt | 解析逻辑改调 M3u8Parser；头来源改 HeaderResolver | Modify | 中 |
| 10 | help/exoplayer/ExoPlayerHelper.kt | PROBE 并入引擎（与 M3u8PreCheck 协同） | Modify | 中 |
| 11 | model/VideoPlay.kt | triggerPreload 预加载重写（AD-12：预嗅探下一集+SimpleCache finalUrl 键预填首分片——预填必须独立 DataSource 工厂实例或 per-request 头注入，禁止复用全局单例工厂 setDefaultRequestProperties；清理禁用旧代码与失效配置） | Modify | 中 |
| 12 | data/entities/PlayHistory.kt | 播放历史记录嗅探前原始 URL（修复源侧 token 轮换失配）+修复 rssSourceId 恒空与复合主键多线路覆盖（Z9） | Modify | 低 |

### Phase 4（2-3 文件）

| # | 文件 | 修改点 | 变更类型 | 风险 |
|---|------|--------|----------|------|
| 1 | help/http/BackstageWebView.kt | 拦截面扩展（Content-Type 白名单+URL 模式 .flv/.ts/.mpd）+修正 L1 排除规则与 Content-Type 判定顺序（现 L344 contains('.html') 前置于正则与 Content-Type 执行，误杀 HTML 壳内直链视频的源，R6；含 Z15 buildFallbackTypes HTML 检测失真修正） | Modify | 中 |
| 2 | help/video/engine/SniffEngine.kt | 多候选完整评分器（类型权重+分辨率提示+时序新近度） | Modify | 中 |
| 3 | help/video/engine/M3u8Parser.kt | 播放侧 master playlist variant 感知（可选，与 #2 配套） | Modify | 低 |

P2 登记项（后续版本，不在本规格实施范围）：播放侧 AES key 下载侧透传对齐（主链路接入已由 Phase 1 Z3 完成，ExoPlayerHelper L254-276 剩余下载侧透传对齐）、DASH 多周期支持。

---

## 七、兼容性与回归风险

### Phase 0

- 存量配置 ≤64 零影响：coerceIn(1,256) 区间扩大无钳制动作；WebViewPool n≤150 区间 max(n/10,5).coerceAtMost(15) 与原值一致（n=64 时 6<15）；min(64,128)=64 不变；ConnectionPool 扩容仅提升复用。新配置 65~256 三处钳制独立生效，资源上限确定。
- RssFragment 为 classic 进入侧幂等自愈，不触碰 modern 写入逻辑；resetRssModeState 纯状态职责不变，既有调用方零影响。

### Phase 1

- 静态解析路径零回归：headers 为空 Map 时收口函数退化为"源配置 headerMap+Referer"现状骨架；CookieManager 兜底仅该域确有 Cookie 时追加，无 Cookie 输出与现状一致。
- 头冲突嗅探值优先的依据：嗅探上下文是资源实际可访问时刻的实测有效环境（真实 Cookie/Referer/UA 刚在页面侧访问成功），源配置只是声明式猜测。
- Cookie 域安全性：CookieManager.getCookie(url) 按域过滤，不跨域泄露；嗅探头同样来自同域命中现场。分片走独立 CDN 域名时 getCookie 为空属预期降级（回退源配置头，不比现状差）。
- 窗口恢复 15s/3s 对快站点最多多等数秒，"命中即收口"自适应消除该代价；token 守卫为一次 Long 比较，正常顺序播放恒等零影响。
- getStrResponse 扩展式改造对既有消费方透明（原 body 用法不变）；VideoUrlExtractor 返回类型变更的全部调用方（VideoPlay/Exo2MediaPlayer）均在修改清单内。

### Phase 2

- 存量 playerType=2 自动迁移：coerceIn(0,2)→(0,1) 使旧值 2 落 1（内置播放器）+首次启动一次性持久化迁移（读旧值 2→写回 1）——仅 UI coerce 不改存储值会留下已废弃值 2 的存储残留，未来任何新增 playerType 消费点都会踩到，迁移消除该隐患；覆盖安装验证门禁覆盖该路径。
- SSL 握手失败场景（Exo2MediaPlayer L834-844 原走 WebView 承接）：删除后由"提示重试/系统浏览器"承接，占比低，列入监控；若真机数据显示占比显著，P2 评估"系统浏览器一键携带 URL"增强。
- 失败路径三通道独立于 WebView 已在 Phase 1 就位（tryNextFallback+BUFFERING 超时/retryExoPlayback/错误对话框双通道），删除不产生失败承接真空。
- 画质增强割裂面消除：WebView 引擎规避增强的问题随删除消失，所有用户恒在 ExoPlayer 引擎，增强档位体验一致。
- 删除面 10 文件一次性单 commit 提交，禁止半删状态（编译期引用检查兜底）。

### Phase 3

- 下载续传兼容：旧任务 headersJson 缺失 → parseHeaders 降级现状行为（UA-only 或播放现场遗留头），零破坏迁移；新任务起写 headersJson。
- M3u8Parser 下沉为等价迁移：解析行为零变化，下载侧回归以清单/加密/多码率三类样本用例门禁。
- 引擎接入逐调用方切换：任一调用方异常可单独回退到 Phase 1 直连路径（引擎为纯新增包，旧路径保留一个阶段后清理）。
- 播放/下载双链路 Phase 1 成果（上下文回传/auth-retry/守卫）经 HeaderResolver/引擎继承，不重复实现。

### Phase 4

- 拦截面扩大误报三重过滤：Content-Type 白名单（非模糊匹配）+既有 window.__videoUrls__ 去重+下游合法性校验（扩展名/时长黑名单）。
- 评分波动可独立回退：Phase 4 独立 commit，回退不触 Phase 0-3；AppLog 记录候选来源与评分结果供调参。

---

## 八、阻塞点排查结论

**结论：无阻塞点，可分阶段实施。** 论证：

- **兼容性**：SniffCandidate/SniffModels/HeaderResolver/M3u8Parser 为纯新增；getStrResponse 扩展式改造对既有消费方透明；VideoUrlExtractor/ExoPlayerHelper/Exo2MediaPlayer 返回与行为变更的全部调用方均在修改清单内，不存在清单外隐式依赖；headersJson 为可选字段带默认降级。
- **性能预算**：auth-retry 为头部小请求，超时预算为首次预检 3s+补头重试独立 3s（外层总预算 6s），重试复用共享 OkHttpClient（newBuilder 继承连接池/拦截器）不重付全握手；下载按需嗅探被去重缓存摊薄（同页共享）；15s 窗口配"命中即收口"不增加快站点等待。
- **删除可行性**：WebView 播放器 10 文件引用面已全量盘点（第六章 Phase 2 表），摆设实锤（forbidden header 规范静默忽略 Referer 注入）确认其存在价值低于维护成本；失败三通道独立就位后无承接真空。
- **资产复用已核实**：playerPageCache+r5InProgress（VideoUrlExtractor L65-79）、VIDEO_SNIFF_JS/VIDEO_SOURCE_REGEX（L98-160）、videoStreamClient（HttpHelper L246-250）、HttpCaptureHelper 抓包头重建（L172-341）、resolveReferer 已抽象 RuleDataInterface（L588-594）——引擎无需从零造轮子。

**残留风险（3 项，接受并监控）**：

1. 极端反爬源（JS 挑战/强风控）Phase 2 后无 WebView 自动承接，由"重试/系统浏览器"提示通道承接，直连成功率短期存在下限；缓解=Phase 4 拦截面与评分持续提升命中率，真机数据驱动。
2. 多候选评分启发式波动：广告分片与主片区分依赖类型+时序双信号，极端源可能选优抖动；缓解=Phase 4 独立交付+AppLog 观测调参+可独立回退。
3. M3u8Parser 等价迁移工作量不确定：HlsDownloader 纯函数化若遇隐式状态依赖，迁移范围可能扩大；缓解=Phase 3 门禁三类样本用例，迁移不改变解析行为为硬性验收标准。

**防再次衰退机制（v3 制度化保障）**：

1. **每阶段 L2 固化用例**进 `ai_tests/scripts/`：Phase 0 classic 首屏+线程钳制、Phase 1 直连成功率基线（防盗链源样本≥5，Play/Rejected 双路径）、Phase 2 全类型源播放回归+存量配置迁移、Phase 3 下载续传恢复+双链路端到端；后续任何改动跑用例即回归。
2. **架构守则回灌子规范**：① 共享基础设施（WebView 池等）进程级 API 必须全局引用计数/互斥（08-19 事故教训）；② 新功能合入前必须验证不改变嗅探路径三要素——网络栈、Cookie、头上下文（Cronet 断链教训）；③ 访问头构造唯一出口 HeaderResolver，禁止新增组装点（5 处分叉教训）。三条写入项目子规范并在 code review 门禁执行。
3. **单一收口的可测性**：SniffEngine/HeaderResolver 就位后，未来嗅探相关改动收敛到唯一变更点，回归面从"全链路"缩小为"引擎单模块"，从结构上消除"逐点修补失效"的重演条件。

---

## 九、红队审查与修订记录

- **2026-08-31 红队穿透审查**（报告：`docs/temp-analysis/video-design-redteam-20260831.md`）：结论"有条件可实施"——BLOCKER 0 / MAJOR 8 / MINOR+WARN 17；28 锚点抽查 23 PASS。审查方法：设计一致性 vs 真实代码逐行抽查 vs 三份现状盘点报告交叉比对。
- **本轮修订（同日，v3.1）**：
  - **F-01**：RssFragment 路径修正 `ui/rss/article/` → `ui/main/rss/`（Phase 0 表 #1，行号 L383 本身正确）；
  - **F-02**：AD-01/零章 Z13/回归点 R5/§2.3/§3.1/§3.6 Phase 1/File Changes Phase 1 "三路命中点"全部修正为"四路命中点"——L360 shouldInterceptRequest/L403 shouldOverrideUrlLoading/L419 onLoadResource/L490 ReadVideoUrlsRunnable 内部命中点，消除名称-行号错位，补齐 JS hook 兜底路径（ReadVideoUrlsRunnable）的命中上下文回传，并明示各路上下文差异（仅拦截路有 WebResourceRequest.requestHeaders）；
  - **F-04**：AD-12 追加预填头污染防线（预填首分片必须独立 DataSource 工厂实例或 per-request 头注入，禁止复用全局 lazy 单例工厂 setDefaultRequestProperties）+Phase 1 buildPlayHeaders 时序约束（setDefaultHeaders 全局覆盖仅 setUp 时序点，预加载/并发场景独立 factory 实例）+Phase 3 File Changes #11 同步；
  - **F-05**：AD-03/§3.4/§5.1/§5.3/§8 auth-retry 机制修正——重试复用共享 OkHttpClient（newBuilder 继承连接池/拦截器，禁止 new 新实例重付全握手）；超时预算改为首次预检 3s+补头重试独立 3s（外层总预算 6s），spec 语义由"3s 窗口内可控"修正为"独立重试预算"；
  - **F-06**：Phase 2/§7/File Changes Phase 2 #10 追加存量 playerType=2 持久化迁移（首次启动读旧值 2→写回 1，一次性迁移；原 coerceIn 仅 UI coerce 不改存储值）；
  - **F-07**：§3.7/Z7/§2.1/§2.2 双"Cronet 默认"消解——`AppConfig.isCronet`（PreferKey.cronet 默认 false）仅控 OkHttp builder 装配；视频链路 cronetDataFactory 无条件装配不受开关控制（ExoPlayerHelper L1029），"默认启用"仅指视频链路；§2.2 第二波"开关翻转"表述标注为全局开关维度；
  - **F-12**：Phase 4 描述与 File Changes Phase 4 #1 纳入 L1 排除规则与 Content-Type 判定顺序修正（BackstageWebView L344 contains('.html') 前置于正则与 Content-Type，误杀 HTML 壳内直链视频源，回归点 R6）；
  - **F-13 → Z14**：Range 嗅探重定向后头不重算（3xx 跟随后沿用原 URL 头，跨域防盗链头失效）——显式 Out of Scope 登记，Phase 4 评估重定向重算分支；
  - **F-14 → Z15**：buildFallbackTypes HTML 检测失真（UNKNOWN+HTML 直接空降级链）——Phase 4 与 F-12 一并修正。
  - 未在本轮处理的 MINOR/WARN 项（F-03 buildAntiLeechHeaders 锚点偏移至 L1095、F-08~F-11 处置 owner 悬空、W-01~W-05 表述类）留待实施阶段随对应 Phase 一并落实，其中 F-03 实施 AD-02 时按 L1095 执行。
