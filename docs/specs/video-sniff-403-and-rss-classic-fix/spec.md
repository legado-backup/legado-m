# Spec：视频嗅探统一引擎架构升级 v3（超越 M 浏览器）/ 订阅经典模式布局修复 / 更新缓存线程数上限提升

> 状态：spec v3 架构级版本（两轮用户反馈后全面重写，待评审 → plan → task）
> 日期：2026-08-31（v3）
> 证据来源：真机日志（技术结论已提取）+ 代码行号锚点（已逐条核实）+ 历史回归分析固化 `docs/temp-analysis/video-sniff-regression-analysis-20260831.md` + 下载链路分叉排查 + WebView 播放器依赖面排查
> 修订说明：
> - v1"403 快速降级 WebView"被用户一轮否决 → v2 改为 SniffCandidate 上下文回传 + auth-retry-first（对标 M 浏览器级）。
> - v2 被用户二轮否决其"点状修补"性质：要求架构级整体规划，禁止头疼医头脚疼医脚。五点具体要求：①深度排查历史变更（嗅探曾有巅峰期后衰退）②目标升级为超越 M 浏览器 ③嗅探能力抽象复用（播放与下载共享引擎）④评估删除 WebView 页面播放器（确认是摆设）⑤生产级、无死角、不引入新 bug。
> - v3 结论：逐点修补在三波历史衰退中已被证明失效，必须结构性收口为统一嗅探引擎，分阶段渐进实施，每阶段可独立验证与回滚。

---

## Intent

本任务为架构级升级 + 两个独立快修，目标从"对标 M 浏览器"升级为**"超越 M 浏览器"**：

1. **视频嗅探统一引擎架构升级**：历史排查实锤嗅探能力曾于 07-13~07-18 处于巅峰期（spec 自评"90%+ 非 DRM 场景可替代手填规则"），随后因三波变更衰退至今。根因是结构性缺陷（上下文断链、头组装分叉、解析能力重复建设）而非单点 bug——逐点修补已证明不可持续。v3 目标：
   - **统一嗅探引擎（SniffEngine）**：将播放、下载、预检三条调用链收敛到同一嗅探入口，输出带完整会话上下文的候选列表；
   - **超越 M 浏览器**：在恢复巅峰四支柱（宽窗口/直连优先/Cookie 闭环/单层不截流）基础上，扩展拦截面、多候选评分、playlist 感知；
   - **删除遗留债务**：移除实锤摆设的 WebView 页面播放器（模板 XHR setRequestHeader('Referer') 被 Chromium forbidden header 规范静默忽略，WebView 播放≈裸 HLS.js，无任何头优势）。
2. **订阅经典模式标签布局空白**：modern 模式向 recyclerView 写入的顶部 padding 切回经典模式时未重置（updateModernRssTopBarOverlay L509-528 写入无重置），需显式复位。
3. **更新和缓存线程数上限 64 → 256**：配套 WebView 池绝对钳制与平台线程池钳制，防 OOM。

2 与 3 与架构升级互相独立，作为 **Phase 0 独立快修先行交付**，共享同一 spec 管理。

> **现状能力全景盘点（四轮反馈补强）**：针对四轮用户反馈"对现状能力了解不全面"，已完成三份现状盘点报告（`docs/temp-analysis/video-sniff-capability-inventory.md` / `video-play-capability-inventory.md` / `video-scenario-network-inventory.md`），沉淀 13 条关键结论（Z1-Z13）并全部纳入设计（design.md「零章：现状能力全景」+ AD-12）。最重大发现：**视频级预加载整体禁用态（NPE 未修，Z1）**、**DataSource 头全局互覆盖（Z2）**、**AES key 双路径漂移（Z3）**——三者直接驱动本 spec 新增 R-P1-8/R-P1-9 与 R-P3-7/8/9。

---

## 三大排查结论（v3 的证据基础）

### A. 历史回归分析（固化于 `docs/temp-analysis/video-sniff-regression-analysis-20260831.md`）

- **巅峰期 07-13~07-18**：R5 抓包 15s 超时/3s 延迟 + 正则兜底失败回退文章链接直连（带头）+ OkHttp Cookie 闭环 + 单层嗅探单池。四支柱拆解即衰退史。
- **三波衰退**：
  - 07-26 `af3ba150c`：窗口 15s/3s→6s/1s + 删直连兜底 + 双层嗅探叠加；
  - 07-31 `d69e266fe`：Cronet 全局启用→播放 Cookie 断链 + M3u8PreCheck 引入（403 只补 UA、Fail 静默回退）；
  - 08-19 `bbc9d0a89`：WebView 池按 scope 误用进程级 pauseTimers 冻结嗅探 JS（08-30 已修）。
- **先天缺陷**：BackstageWebView.shouldInterceptRequest 自 07-13 `7e11d7399` 诞生即只回传 URL、丢弃 headers，巅峰期被直连兜底 + OkHttp Cookie 掩盖，兜底拆除后全面暴露。
- **排除项**：下载/画质增强非衰退诱因（时间线不吻合）。

### B. 下载链路分叉排查

- **下载无独立嗅探**：VideoFragment L810-832 直接取 VideoPlay.videoUrl + ChunkDownloader.resolveHeaders()（`currentPlayHeaders ?: 仅 UA`）——同样头缺失，且恢复场景二次丢失（headersJson 空→仅剩 UA，防盗链源必 403）。
- **解析能力重复建设**：下载侧 HlsDownloader 自研全套 m3u8 解析（master/variant pickBestVariant/AES-128 parseCrypto/相对拼接/DISCONTINUITY/时效签名缓解/ts-mp4 remux），播放侧靠 ExoPlayer 内置 + M3u8PreCheck 预检——同一能力两套实现。
- **头组装分叉 5 处**（播放 3 + 下载 2 同构逻辑），是头丢失的结构性根源。

### C. WebView 页面播放器删除可行性排查

- **实锤摆设根因**：模板 XHR `setRequestHeader('Referer')` 被 Chromium forbidden header 规范静默忽略，WebView 播放≈裸 HLS.js，无法携带防盗链头，降级价值为假。
- **依赖面收敛**：消费点唯一（VideoPlayerActivity L1563）、Fragment 引用仅 VideoFragment、assets 仅 hls_video_player_template.html + hls.min.js，共 **10 文件删除清单**（plan 阶段精确化）。
- **设置迁移**：playerType 2（WebView）→ `coerceIn(0, 1)` 自动落 1（内置）。
- **须保留的独立机制**：tryNextFallback 降级链（HLS→DASH→Progressive）与 BUFFERING 超时自愈，与被删 WebView 分支解耦；失败路径已有"提示+重试+系统浏览器"三通道基础。

---

## Scope

### In Scope

**Phase 0：独立快修（与架构无依赖，先行交付）**
- R2 订阅经典模式 padding 重置（applyClassicRssMode 入口重置 + 防御性复位覆盖 + folderComposeView）。
- R3 线程数 64→256（UI max + AppConfig coerceIn）+ 三处钳制（WebViewPool `coerceAtMost(15)`、CacheBookService/ImageCanvasViewModel `min(n,128)`、HttpHelper ConnectionPool 128）。

**Phase 1：止血恢复巅峰（v2 P0 全量，可独立交付）**
- SniffCandidate 上下文回传（BackstageWebView 三路命中点读 `request.requestHeaders` + CookieManager + settings.userAgentString）。
- buildPlayHeaders 收口（VideoPlay 5 处同构点全部改走单点，merge 策略=嗅探上下文优先+源配置兜底+Cookie 兜底）。
- M3u8PreCheck 403 补 Referer+Cookie 重试 + PreCheckRejected 分支（重嗅 1 次→仍失败→用户提示，禁止静默 using original url）。
- switchToken 守卫（迟到回调丢弃，对齐 switchToRoute L1238-1247 模式）。
- onPlayerError 403 快速补头重试（2004 → 补齐头重试 1 次 → 失败触发重嗅）。

**Phase 2：删除 WebView 播放器债务**
- 10 文件清单删除（模板/JS 资产、WebView 播放分支、消费点、设置读取处；plan 出精确清单）+ 设置迁移 playerType 2→coerceIn(0,1)。
- 失败路径统一为"提示+重试+系统浏览器"三通道；保留 tryNextFallback 降级链与 BUFFERING 自愈。

**Phase 3：SniffEngine 抽象统一**
- 引擎接口落地（help/video/）+ 三调用方接入（播放 VideoPlay / 下载 Download/DownloadService / 预检 M3u8PreCheck 并入引擎 probe 阶段）。
- HeaderResolver 统一头组装收口（播放/下载/预加载/预检统一调用，结果持久化到下载任务 headersJson 支持续传）。
- M3u8Parser 共享解析模块（下沉 HlsDownloader 自研能力，播放侧预检/预加载共用）。
- 下载按需嗅探（播放地址未就绪时按调用方意图触发引擎嗅探）。

**Phase 4：超越 M 浏览器（增强）**
- 拦截面扩展（响应 Content-Type：video/*/m3u8/dash/audio + URL 模式 .flv/.ts/.mpd）。
- 多候选评分选优（媒体类型/分辨率提示/命中时序/命中层级加权，代替首个命中即用）。
- 播放侧 master playlist variant 感知（借助共享 M3u8Parser，不改 ExoPlayer 内部选流）。

### Out of Scope

- **播放流水线自研替换 ExoPlayer**：ExoPlayer HLS 引擎成熟，只共享"解析与头"，不自研播放数据流水线。
- **DASH 完整支持 / 播放侧 AES-128 key 解密增强**：P2 登记为后续 spec（AES 已有 HlsKeyDataSourceFactory 基础）。
- **下载侧自研嗅探重复建设**：统一后不需要——下载只调用 SniffEngine + HeaderResolver，禁止再造一套。
- **跨书源章节嗅探泛化**：暂缓，本期聚焦订阅源视频（type=4 书源已接入的三层入口保持兼容）。
- **不换网络栈/播放内核**：media3 + Cronet 体系保持；不做线程池架构重构；不做 CDN 防盗链签名逆向对抗（403 处置 = 补上下文头 + 重嗅）。
- **SSL 校验旁路治理**（现状盘点发现）：属安全治理范畴，独立安全 spec 承接，不混入本架构 spec。
- **"Cronet 换 DoH"用户配置项**（现状盘点 Z6 补强新增）：现状无此设置，不做；AD-11 保持 Cronet + DoH 在错误回退链中隐式协作，customHost 注入评估登记 Phase 4。

### 分阶段实施与阶段门禁（风险递进）

| Phase | 风险 | 交付物 | 门禁 |
|-------|------|--------|------|
| 0 | 低（UI/配置钳制） | 快修 2 组 | 编译 + L2 真机 |
| 1 | 中（播放链行为变更） | 止血 6 条 | 编译 + L2 真机 + S1-S5 复测 |
| 2 | 中（删除代码） | 债务清理 | 编译 + 全仓无残留引用 + 三通道验证 |
| 3 | 高（抽象重构） | 引擎统一 | 编译 + L2 + S1-S5 回归复测（语义等价）+ 下载场景 |
| 4 | 中（拦截面扩大） | 增强能力 | 编译 + L2 + 误报回归 |

每阶段完成门禁：编译通过 + L2 真机验证 + 阶段复验构建（并发文件修改规范）；任一阶段失败可独立回滚，不影响已交付阶段。

---

## Approach

### Selected Approach

**统一嗅探引擎四层架构 + 分阶段渐进实施**，理由：

1. **历史证明"逐点修补"失效**：三波衰退中每次局部修复（压窗口/加预检/删兜底）都引入新回归，根源是缺陷分布在不同调用链的结构性重复中，必须结构性收口。
2. **四层架构**：
   - **SniffEngine 统一嗅探引擎**（新抽象，help/video/）：输入 = 目标 url + 源上下文（BaseSource + RuleDataInterface）+ 调用方意图；输出 = `List<SniffCandidate>{url, headers(嗅探会话真实头), mimeType, contentType, sourceMeta(命中层级 MacCMS/DOM/WebView/直连), 时序}`；内部四层发现（静态解析/DOM/WebView 抓包带上下文回传/直连探测）+ auth-retry（403 补头重试）+ 多候选评分选优 + 去重缓存（复用 playerPageCache/r5InProgress 资产）。
   - **HeaderResolver 统一头组装**：buildPlayHeaders 收口为唯一入口，merge = 嗅探上下文优先 + 源配置兜底 + `CookieManager.getCookie(videoUrl)` 兜底；播放/下载/预加载/预检统一调用，结果持久化到下载任务 headersJson 支持续传。
   - **M3u8Parser 共享解析模块**：下沉 HlsDownloader 自研能力（variant 选择/AES-128 key/相对拼接/清单解析）为共享模块，播放侧预检/预加载与下载侧共用；播放侧播放仍走 ExoPlayer 内置 HLS 引擎，不自研播放流水线。
   - **调用方适配**：播放（VideoPlay）/下载（Download/DownloadService，支持"播放地址未就绪时按需嗅探"）/预检（M3u8PreCheck 并入引擎 probe 阶段）。
3. **分阶段让每阶段可独立验证回滚**：Phase 0/1 先交付用户可感知修复（快修+止血），Phase 2 清债，Phase 3 架构收口，Phase 4 增强——风险递进、验证递进。
4. **删除 WebView 播放器而非保留兜底**：forbidden header 规范使其失去头优势，删除消除维护面与"假兜底"误导。

### Alternatives Considered

| 方案 | 否决理由 |
|------|---------|
| a) **v1 快速降级 WebView 播放** | **用户裁决否决**：排查实锤 WebView 播放是摆设（Chromium 禁改 Referer，≈裸 HLS.js）；快速降级不解决上下文丢失根因，且与目标相悖 |
| b) **v2 点状修复不做架构** | **用户二轮裁决否决**：头疼医头脚疼医脚不可持续；三波衰退证明局部修复互相打架，必须架构级收口 |
| c) **全面自研播放流水线替换 ExoPlayer** | 否决：工作量巨大；ExoPlayer HLS 成熟稳定；只需共享解析与头（M3u8Parser + HeaderResolver）即可获得同等收益 |
| d) **下载侧独立建嗅探** | 否决：下载/播放分叉正是历史教训（5 处头组装分叉 + 解析重复建设）；统一引擎后下载按需调用即可 |
| e) **一次性全量重构不分阶段** | 否决：回归风险不可控；历史证明嗅探链路对基础设施改动高度敏感（08-19 误冻结事故），分阶段+阶段门禁是唯一可控路径 |
| f) **恢复巅峰期直连兜底作为长期方案** | 否决：兜底只是掩盖上下文断链缺陷（07-26 删兜底后缺陷全面暴露即为证），且体验差；SniffCandidate 上下文回传才是根治 |
| g) 仅在播放器侧无脑重试 N 次 | 否决：403 是确定性拒绝，头不变重试结果相同；必须先补上下文再重试（auth-retry-first） |
| h) 线程数上限提到 512+ | 否决：连接池/文件句柄收益递减，256 已覆盖高端机需求；512 下钳制压力大于收益 |

### Drawbacks

- **架构层抽象增加代码层次**：SniffEngine/HeaderResolver/M3u8Parser 三层新抽象。缓解：接口最小化（引擎仅一个入口方法族）+ 调用方仅 3 个（播放/下载/预检）。
- **分阶段周期拉长**：全程 5 阶段。缓解：Phase 0/1 先交付用户可感知修复，后续阶段独立排期不阻塞前者。
- **WebView 删除后 SSL 失败场景无替代**：证书异常站点此前可进 WebView 播放页。占比低可接受，走"提示+重试+系统浏览器"三通道。
- **多候选评分可能选非最优**：评分权重无法覆盖全部站点特征。缓解：权重可调 + 单资源页面行为不变 + 日志记录选中理由便于迭代。
- **引擎抽象期新旧路径短暂双轨**（Phase 3）：三调用方逐个接入期间两套代码并存。缓解：Phase 1 已收口头组装，双轨面收窄到"发现逻辑"且以阶段门禁语义等价验证。

### Prior Art

- **巅峰期 `7e11d7399` 设计**：15s 抓包窗口 + 直连兜底哲学，Phase 1 恢复其行为语义，Phase 3 收口其结构。
- **猫抓（cat-catch）/ M3U8D 等成熟嗅探器**：上下文端到端流转 + auth-retry-first + 四层发现 + 多候选评分，v3 四层架构逐项对标。
- **switchToRoute token 守卫**（VideoPlay.kt L1238-1247）：`++token` 序号丢弃迟到回调，真机已验证，R-P1-5 直接复用。
- **HlsDownloader 自研解析资产**：pickBestVariant/parseCrypto/相对拼接全套 m3u8 解析已在下载侧稳定运行，M3u8Parser 共享模块直接下沉复用。
- **sniff-migration-booksource AD-06 RuleDataInterface 抽象先例**：书源 type=4 接入统一三层入口时验证过"调用方意图 + 数据接口抽象"模式，SniffEngine 输入设计沿用。

---

## 阻塞点与风险排查结论

历史三波衰退启示：**嗅探链路对"基础设施/网络栈/兜底逻辑"改动高度敏感**，每阶段门禁（编译+L2+复验构建）为强制防线；新功能合入前必须验证不改变嗅探路径的网络栈、Cookie 与头上下文。

| # | 阻塞点/风险 | 排查结论 | 处置 |
|---|------------|---------|------|
| 1 | **Cookie 断链**（CronetDataSource 无 CookieJar；BackstageWebView.setCookie 在 onPageFinished 才存 CookieStore，命中常早于它） | **已解**：`CookieManager.getInstance().getCookie(videoUrl)` 实时读取，全局同步不依赖时序 | Phase 1 |
| 2 | **头组装分叉 5 处**（播放 3 + 下载 2） | **一次解决**：Phase 1 收口 buildPlayHeaders，Phase 3 升级为 HeaderResolver 全调用方统一 | Phase 1→3 |
| 3 | **预检超时窗**（3s） | **不变**：auth-retry 在既有窗口内完成，重嗅走独立机制 | Phase 1 |
| 4 | **UA 不一致**（WebView UA vs 播放固定 BROWSER_UA） | **已识别**：SniffCandidate 携带 WebView 真实 UA，merge 下嗅探 UA 优先 | Phase 1 |
| 5 | **头替换式覆盖**（okhttpDataFactory setDefaultHeaders 替换式；CronetInterceptor 条件注入不满足视频播放） | **已识别**：统一经 currentPlayHeaders 下发，CronetInterceptor 注入逻辑 plan 阶段复核 | Phase 1 |
| 6 | **下载恢复场景二次丢失**（headersJson 空→仅 UA 必 403） | **根治**：HeaderResolver 结果持久化到 headersJson，恢复时头完整 | Phase 3 |
| 7 | **WebView 池等共享基础设施为高危区**（08-19 进程级误冻结事故） | **已修但须固防**：进程级 API 全局互斥已纳入固化用例；Phase 2 删除 WebView 播放分支时须确认不触碰 WebViewPool 嗅探路径 | 全阶段 |
| 8 | **新风险：嗅探页头污染**（嗅探页头带给不需要的站点） | Cookie 域校验（仅注入 videoUrl 同域）+ merge 源配置兜底 | 设计内置 |
| 9 | **新风险：引擎双轨期回归** | 语义等价验证：Phase 3 接入后 S1-S5 全量复测须与 Phase 1 行为一致 | Phase 3 门禁 |
| 10 | **新风险：拦截面扩大误报** | 多候选评分 + 既有去重 + 单资源行为不变门禁 | Phase 4 |
| 11 | **WebView 删除后 SSL 失败无替代** | 占比低，失败路径三通道（提示+重试+系统浏览器）承接 | Phase 2 |

---

## Requirements

### R-P0：独立快修（先行，2 组）

**组 1：订阅经典模式 padding 重置**
- **R-P0-1** `applyClassicRssMode`（L383-419）显式重置 `recyclerView` topPadding=0 + clipToPadding 复位 + requestLayout()。可验证：modern→classic 后 topPadding == 0，无空白。
- **R-P0-2** 防御性重置覆盖 `resetRssModeState`/`initRecyclerView`/`applyListView` 三处回经典路径 + `folderComposeView` 同类复位；modern 自身 overlay 写入（L509-528）保持原样。可验证：任一路径进入经典模式无空白；标签↔文件夹往返无残留；modern 行为与改动前一致；杀进程重进不回归。

**组 2：线程数上限 64→256 + 钳制**
- **R-P0-3** UI `max = 256`（OtherConfigFragment L460）+ AppConfig `coerceIn(1, 256)`（L2876）。可验证：可选 1-256；写 300 落盘 256。
- **R-P0-4** WebViewPool `globalMaxCached` 加 `coerceAtMost(15)` 绝对钳制。可验证：线程数 256 时 == 15。
- **R-P0-5** `CacheBookService`/`ImageCanvasViewModel` newFixedThreadPool 加 `min(n, 128)` 钳制。可验证：256 时实际线程数 == 128。
- **R-P0-6** HttpHelper ConnectionPool 50→128（消费点审计配套，真机验证并发 socket 占用；不实施则 plan/task 记录决策）。可验证：批量缓存无 OOM；旧值（≤64）与备份导入行为兼容。

### R-P1：止血恢复巅峰（10 条）

- **R-P1-1** `SniffCandidate` 数据类 + BackstageWebView 四路命中点统一上下文回传（对齐 design 红队 F-02 四路捕获清点）：`shouldInterceptRequest`（L358-366）读 `request.requestHeaders`；`shouldOverrideUrlLoading`（L403）；`onLoadResource`（L415-427）与 `ReadVideoUrlsRunnable`（L464-498）用 CookieManager + settings.userAgentString + 当前页 URL 组装。可验证：四路命中均产生带 headers 候选，AppLog 可区分命中路径。
- **R-P1-2** `buildPlayHeaders()` 收口：VideoPlay 5 处同构点（L464-478/L503-528/L539-552/L640-659/L1477-1479，同构 L406-423）全部改走单点；merge = 嗅探上下文优先 + 源配置兜底 + `CookieManager.getCookie(videoUrl)` 兜底（不依赖源 cookieJar 开关，WebView 值优先）；结果写入 currentPlayHeaders 全局权威源。可验证：403 站点播放请求头含嗅探页 Referer + 非空 Cookie（日志仅记字段名与长度）。
- **R-P1-3** M3u8PreCheck auth-retry + 确定性拒绝分支：403 → 补 Referer+Cookie 重试 1 次（首次预检 3s + 补头重试独立 3s，总预算 6s；重试复用共享 OkHttpClient，newBuilder 继承连接池——design 红队 F-05 修订）；仍 403 → PreCheckRejected → 触发重嗅 → 仍失败 → 用户提示；**禁止静默 "using original url"**；超时/IOException 不消耗重试。可验证：403 站点日志出现"预检 403→补头重试→成功/仍拒→重嗅"完整序列。
- **R-P1-4** 重嗅一次机制：预检拒绝与播放 403 共用统一重嗅入口（复用 R5 机制，新 cookie 可能刷新一次性 token）；同一播放会话重嗅至多 1 次，防循环。可验证：重嗅后新候选头为新 cookie 会话；无重嗅风暴。
- **R-P1-5** switchToken 守卫：startPlay/switchArticle 迟到回调按 token/episodeIndex 校验丢弃。可验证：快速连滑 N 次仅最后结果生效，无旧集数覆盖。
- **R-P1-6** onPlayerError 403 快速补头重试：errorCode 2004 → 用补齐后的头重试 1 次 → 失败触发 R-P1-4 重嗅。可验证：403 场景从 error 到恢复显著短于改动前，无"全链 403 黑屏"。
- **R-P1-7** 网络栈定位与 DoH 一致化（用户三轮追问新增）：Cronet 保留为主网络栈不回退 OkHttp（Cookie 断链修复=Cronet 链路补注入）；DohDns 保留不废弃；`preResolveDns`（ExoPlayerHelper L305-317）改走 DohDns（现状系统 DNS 不一致）。可验证：播放预解析日志出现 DohDns 命中序列；Cronet 播放请求头含嗅探上下文（头字段名+值长度落日志，值不落）。
- **R-P1-8** AES 密钥头注入主链路接入（现状盘点 Z3 补强新增）：HlsKeyDataSourceFactory（现仅接旧入口 createMediaSource L258）包装主链路 applyMediaSourceByType L310 的 HLS Factory，使加密 HLS 源的 key 请求同样走统一头组装。可验证：加密 HLS 源播放日志出现 key 请求带嗅探上下文头（字段名+值长度落日志，值不落）。
- **R-P1-9** isPreparing 重入保护死代码处置（现状盘点 Z5 补强新增）：确认恢复 CAS 防护或删除（现状 L101 声明无读写，属死代码）。可验证：R5 双命中场景无重复 acquire 日志。
- **R-P1-10** R5 窗口恢复 + 命中即收口自适应（design §3.6 Phase 1 已列，红队 R-07 修订补录）：R5 窗口 6s/1s→15s/3s + 命中即收口（检测到视频请求提前收口，快站点不多等）。可验证：慢源嗅探成功率对比基线提升；快站点无额外等待日志。

### R-P2：删除 WebView 播放器债务（4 条）

- **R-P2-1** 按 10 文件清单删除（模板 html + hls.min.js 资产、WebView 播放引擎类、VideoFragment 分支引用、VideoPlayerActivity L1563 消费点、playerType 相关读取与 UI；plan 出精确清单）。可验证：删除后编译通过，全仓搜索无 WebView 播放分支残留引用。
- **R-P2-2** 设置迁移：playerType 值 2 → `coerceIn(0, 1)` 自动落 1（内置），备份导入同校验。可验证：旧用户升级后自动为内置播放且无崩溃，设置项不再出现 WebView 选项。
- **R-P2-3** 失败路径三通道：直连与重嗅全部失败 → "错误提示 + 手动重试 + 系统浏览器打开"，不静默黑屏。可验证：人为构造全部失败场景，三通道均可达。
- **R-P2-4** 保留独立自愈机制：tryNextFallback 降级链（HLS→DASH→Progressive）与 BUFFERING 超时自愈不动，确认与被删 WebView 分支解耦。可验证：降级链各档位触发路径回归通过。

### R-P3：SniffEngine 抽象统一（9 条）

- **R-P3-1** SniffEngine 接口落地（help/video/）：输入（目标 url + BaseSource + RuleDataInterface + 调用方意图）；输出 `List<SniffCandidate>{url, headers, mimeType, contentType, sourceMeta(命中层级 MacCMS/DOM/WebView/直连), 时序}`；内部四层发现（静态解析/DOM/WebView 抓包/直连探测）+ auth-retry + 去重缓存（复用 playerPageCache/r5InProgress）。可验证：编译 + L2 真机（四层发现命中日志）+ 引擎单测覆盖四层发现路径与输出结构（tasks 4.9）。
- **R-P3-2** HeaderResolver 统一头组装：buildPlayHeaders 升级为 HeaderResolver，播放/下载/预加载/预检统一调用；结果持久化到下载任务 headersJson。可验证：编译 + L2 真机（三调用方同输入头组装结果一致，日志核对；下载任务恢复后 headersJson 非空且完整）+ 头 merge 策略单测（tasks 4.9）。
- **R-P3-3** 播放调用方接入：VideoPlay 改调引擎（行为与 Phase 1 语义等价），M3u8PreCheck 并入引擎 probe 阶段。可验证：S1-S5 全量复测通过。
- **R-P3-4** 下载调用方接入：VideoFragment L810-832 与 ChunkDownloader.resolveHeaders 改走 HeaderResolver，消除 `currentPlayHeaders ?: 仅 UA` 分叉。可验证：下载防盗链源分片成功（S9）。
- **R-P3-5** 下载按需嗅探：播放地址未就绪时下载任务可触发引擎按需嗅探（调用方意图 = download，不影响播放会话缓存）。可验证：冷启动直接下载场景嗅探→下载链路通。
- **R-P3-6** M3u8Parser 共享解析模块：下沉 HlsDownloader 能力（master/variant pickBestVariant/AES-128 parseCrypto/相对拼接/DISCONTINUITY/时效签名缓解/ts-mp4 remux 边界），播放侧预检/预加载与下载侧共用；播放流水线仍走 ExoPlayer 内置 HLS。可验证：编译 + L2 真机（下载侧既有场景回归不破坏）+ 清单解析核心路径单测（tasks 4.9）。
- **R-P3-7** 预加载重设计（AD-12，现状盘点 Z1/Z4 补强新增）：triggerPreload 重写为"预嗅探下一集 + SimpleCache finalUrl 键预填"；清理整体禁用的旧预加载代码（NPE 未修）与失效配置项。可验证：上滑下一集命中预采集近零等待；配置项行为一致。
- **R-P3-8** SimpleCache 缓存键统一 finalUrl（现状盘点 Z4 补强新增，现状原始 URL 与嗅探后地址混用）。可验证：预载缓存命中日志。
- **R-P3-9** 播放历史修复（现状盘点 Z9 补强新增）：记录原始 URL（非嗅探后 finalUrl）+ rssSourceId 填充；主键修复（若裁决改主键）涉及 Room schema v108→v109 迁移，必须遵守 `database-migration-safety` 规范；方案 A（改主键+迁移）与方案 B（查询层去重不改 schema）留 plan 裁决（红队 R-09 修订补录）。可验证：历史记录字段完整。

### R-P4：超越 M 浏览器增强（3 条）

- **R-P4-1** 拦截面扩展：响应 Content-Type 检测（video/*、application/vnd.apple.mpegurl、application/dash+xml、audio/*）+ URL 模式（.flv/.ts/.mpd 等）。可验证：仅靠 Content-Type/URL 特征可识别的资源（无典型 .m3u8 后缀）嗅探命中。
- **R-P4-2** 多候选评分选优：按媒体类型/分辨率提示/命中时序/命中层级加权，代替首个命中即用；保留既有去重。可验证：多资源页面选中最高分候选，日志记录候选数与选中理由；单资源页面行为不变。
- **R-P4-3** 播放侧 master playlist variant 感知：借助共享 M3u8Parser 解析主列表识别最佳 variant，供评分与预检参考（不改 ExoPlayer 内部选流）。可验证：多码率站点评分命中正片 variant。
- P2 登记后续（Out of Scope）：播放侧 AES-128 key 解密增强（HlsKeyDataSourceFactory 已有基础）、DASH 完整支持。

---

## Scenarios

### S1：403 防盗链站点补头后直连成功（Phase 1 核心，验收核心判据）

- **Given** 某订阅源视频启用 Referer/Cookie 防盗链，WebView 嗅探可捕获地址但直接播放 403。
- **When** 播放该视频（含上滑切换）。
- **Then** 候选携带完整上下文 → buildPlayHeaders 补齐 → 预检 403 时 auth-retry 成功 → **ExoPlayer 直连播放成功**；仅 auth-retry 与重嗅均失败才走失败路径三通道。AppLog 记录补头重试与命中路径序列（头值不落日志）。

### S2：正常直连站点零回归（Phase 1 回归保护）

- **Given** 视频接口可直连（预检成功或预检超时但 ExoPlayer 可播）。
- **When** 连续上滑切换多个视频。
- **Then** 预检成功走 finalUrl、超时走 original url，行为与改动前一致；无多余重试/重嗅、无延迟感知。

### S3：预检 auth-retry（Phase 1 预检窗口）

- **Given** 站点对裸 UA 请求返回 403，补 Referer+Cookie 后可访问。
- **When** m3u8 预检首次 403。
- **Then** 补头重试 1 次后通过（首次预检 3s + 补头重试独立 3s，总预算 6s，重试复用共享 OkHttpClient 连接池），播放继续；仍 403 则重嗅 1 次；再失败才提示。超时/IOException 不消耗重试次数。

### S4：快速连滑迟到回调丢弃（Phase 1 竞态）

- **Given** 上滑嗅探协程执行中（耗时 >2s 的站点）。
- **When** 嗅探返回前再次上滑切换集数。
- **Then** 旧回调 token 校验失败被丢弃；新嗅探正常接管，无画面被旧集数覆盖。

### S5：静态解析路径零影响（Phase 1/3 门禁，L2 验证 tasks 2.8e）

- **Given** 源走静态解析路径（直接接口返回视频地址，不经 WebView 嗅探，无 SniffCandidate）。
- **When** 正常播放与上滑切换。
- **Then** 头组装仅走源配置兜底分支（与改动前一致），无嗅探上下文注入、无 Cookie 强制注入副作用。

### S6：经典 ↔ 新版模式往返无空白（Phase 0 组 1）

- **Given** 订阅页经典模式 + 标签展示。
- **When** 切到新版模式（recyclerView 被写入 topPadding）再切回经典。
- **Then** topPadding == 0、clipToPadding 复位、无空白；与杀进程重进结果一致；文件夹模式往返亦无残留。

### S7：线程数 256 + 资源钳制（Phase 0 组 2）

- **Given** 用户将更新和缓存线程数调至 256。
- **When** 触发批量缓存更新并观察 WebView 缓存池与平台线程池。
- **Then** globalMaxCached == 15（非 25）；两处线程池 == 128（非 256）；进程无 OOM，任务正常完成。

### S8：线程数旧值与备份兼容（Phase 0 组 2）

- **Given** 旧备份含 32；另一备份含非法值 999。
- **When** 恢复备份并进入设置页。
- **Then** 32 原样生效；999 被 coerceIn(1,256) 校验为 256 落盘；UI 与实际值一致。

### S9：下载防盗链源分片成功（Phase 3 核心判据，续传子场景验证 tasks 4.10）

- **Given** 同一防盗链订阅源视频，播放已直连成功（S1 通过）。
- **When** 对该视频发起下载（含中途取消后恢复续传）。
- **Then** ChunkDownloader 经 HeaderResolver 取到与播放一致的完整头，分片下载成功；恢复场景 headersJson 完整非空，续传不 403。

### S10：删除 WebView 后失败路径三通道（Phase 2）

- **Given** WebView 播放器已删除，某视频直连与重嗅均失败（如证书异常站点）。
- **When** 播放失败。
- **Then** 用户看到明确错误提示，可选择"重试"（重新走引擎链路）或"系统浏览器打开"；无静默黑屏；tryNextFallback 降级链与 BUFFERING 自愈仍独立生效。

### S11：多候选评分选优（Phase 4，L2 验证 tasks 4.10）

- **Given** 页面嗅探捕获多个候选（广告切片低分 + 正片高分）。
- **When** 嗅探完成。
- **Then** 按媒体类型/分辨率提示/命中时序/命中层级评分选中正片候选播放；日志记录候选数与选中理由；候选去重无重复播放。

### S12：播放地址未就绪时下载按需嗅探（Phase 3，L2 验证 tasks 4.10）

- **Given** 用户未进过播放页（无 playerPageCache），直接对订阅源视频发起下载。
- **When** 下载任务启动。
- **Then** 以 download 意图触发 SniffEngine 按需嗅探，取得候选与头后进入分片下载，结果不污染播放会话缓存。

### S13：预加载重设计后上滑秒开（Phase 3，AD-12）

- **Given** 预加载重设计落地（预嗅探下一集 + SimpleCache finalUrl 键预填，整体禁用的旧预加载代码已清理）。
- **When** 正在播放当前集，上滑切换下一集。
- **Then** 下一集命中预采集候选与预填缓存，近零等待起播；SimpleCache 以 finalUrl 命中预载分片（命中日志可查）；预加载相关配置项开关行为与改动前语义一致。

---

## 验收门禁

1. 全部 R 项可验证断言通过（真机验证用测试包 `io.legado.miss.app.debug`）。
2. **核心判据 = S1（403 站点补头后直连播放成功）+ S9（下载防盗链源分片成功）**，两判据均通过才算架构目标达成。
3. 阶段门禁：每 Phase 完成 = 编译通过 + L2 真机验证 + 阶段复验构建（并发文件修改规范）；Phase 1 接入前 S1-S5 必测，Phase 3 语义等价以 S1-S5 全量复测为门禁。
4. S6/S7/S8 为 Phase 0 门禁必测；S10/S11/S12 按所属阶段必测。
5. 日志安全：Cookie/token 等头值不落日志，仅记录字段名与值长度；全部新日志走 `AppLog.put`。
6. 改动遵循 AGENTS.md 代码约束（Coroutine.async 链式封装、runCatching 带 `kotlin.` 前缀、NoStackTraceException、禁止 Timber）。
7. updateLog 按 version-delivery-sync 规范逐阶段更新；每阶段结束后按并发规范做 git diff 校验与文档同步。
