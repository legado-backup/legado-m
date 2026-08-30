# sniff-stability-enhance-20260731（嗅探稳定性增强）

## 1. Intent（意图说明）

### 1.1 背景

用户于 2026-07-31 19:41 对 `sniff-result-pipeline-fix` 正式包（legado_miss_app_3.26.073118.apk）进行真机测试后反馈："整体效果比之前好多了，但是我期望更好"。

针对该反馈，对最新会话日志（logs(8).zip，含 39 个 appLog 文件 + logcat.txt，覆盖 2026-07-31 07:22 ~ 19:22）进行深度分析，形成《真机测试日志深度分析报告》。报告确认前一阶段 5 个 FR 修复整体生效，但识别出 9 个仍需优化的问题，涉及嗅探重复执行、DoH 不稳定、HTTP/2 协议错误、favicon 请求 spam、StreamReset 重试失效、日志噪声、证书错误重复降级、首帧延迟方差大、JS 变量解析容错缺失等方面。

### 1.2 意图

本功能旨在在不破坏已交付正式包基础的前提下，通过增量优化进一步降低嗅探重复率、提升 DNS 解析稳定性、消除视频流协议错误、减少无效网络请求与日志噪声，从而将"整体效果比之前好多了"提升至"用户期望更好"的水平。

### 1.3 价值

- **性能价值**：减少 41% 嗅探重复开销、137 次/会话 favicon 网络请求、152 次/会话日志噪声
- **稳定性价值**：消除 HTTP/2 协议错误降级、避免 Activity 切换导致的重试失效、降低首帧延迟方差
- **体验价值**：缩小首帧渲染延迟差距（当前 701~5309ms，差距 7.5 倍），提升特定源嗅探成功率

---

## 2. Scope（范围）

### 2.1 做什么（In Scope）

| 编号 | 优化项 | 涉及模块 |
|------|--------|----------|
| FR-1 | R5 嗅探去重锁 | VideoUrlExtractor / R5 嗅探器 |
| FR-2 | DoH 负缓存时长优化 + 启动健康检查 | DohDns |
| FR-3 | 视频流强制 HTTP/1.1 | Cronet / HttpHelper / ExoPlayerHelper |
| FR-4 | favicon.ico 缓存 | HttpHelper / 缓存层 |
| FR-5 | StreamReset 重用 NonCancellable | StreamReset 重试逻辑 |
| FR-6 | Cronet 探测跳过日志采样 | Cronet 探测日志 |
| FR-7 | 证书错误记忆缓存 | Cronet 降级逻辑 |
| FR-8 | play.php 类 URL 预解析 | 视频流预解析层 |
| FR-9 | window.__videoUrls__ 解析容错 | R5 嗅探 JS 解析 |

### 2.2 不做什么（Out of Scope）

- **不重构网络层架构**：已交付正式包基础不能动，仅在现有 Cronet/OkHttp 双引擎架构上做增量优化
- **不升级 Cronet 版本**：Cronet 150 SIGABRT 原生崩溃问题（56 次）属于独立 P0 问题，由专项任务处理，不在本功能范围内
- **不新增 DoH 服务器**：FR-5 已证明国外服务器不可达，增加数量无效，本功能仅优化现有 2 个国内服务器的使用策略
- **不修改 ExoPlayer 复用机制**：PlayerPool 已存在，复用率验证不在本功能范围
- **不调整 R5 超时时间**：当前 timeout=6000ms 保持不变，动态超时调整属于后续优化

---

## 3. Approach（技术方案）

### 3.1 Selected Approach（选定方案）

**增量优化现有嗅探与网络管线**：在 `sniff-result-pipeline-fix` 已交付的基础上，针对日志识别的 9 个具体问题点实施精准修复，不触碰整体架构。

**选定理由**：

1. **风险可控**：已交付正式包（legado_miss_app_3.26.073118.apk）已通过用户验证"整体效果比之前好多了"，架构基础稳固，增量优化不会引入回归风险
2. **收益明确**：每个 FR 都有日志量化证据支撑（如 41% 重复率、137 次 favicon 请求、152 次日志噪声），收益可度量
3. **实施成本合理**：9 个 FR 中 6 个为低难度、3 个为中难度，可在单次迭代内完成
4. **符合用户期望**：用户明确表示"期望更好"，全面覆盖 P0~P3 优先级问题，而非只做一半

**核心技术决策**：

| 决策点 | 选择 | 理由 |
|--------|------|------|
| R5 去重实现 | ConcurrentHashMap<path, Deferred> 内存锁 | 协程友好，重复请求复用 Deferred 结果，无需阻塞 |
| DoH 负缓存时长 | 30s → 10s | 临时失败不应长时间缓存，10s 平衡误判与污染 |
| 视频流协议 | 禁用 h2，强制 h1.1 | 服务端 HTTP/2 实现问题无法客户端修复，h1.1 兼容性更好 |
| favicon 缓存 | 内存 Bitmap + 磁盘按域名 24h | 双层缓存兼顾命中率和内存占用 |
| StreamReset 重试 | 移除cancel()+连接池evictAll清理 | chain.call().cancel()会取消整个Call导致重试必然失败，改用连接池清理 |
| 证书错误记忆 | 内存缓存 5 分钟 | 证书状态短时间内不会变化，避免无效降级尝试 |

### 3.2 Alternatives Considered（否决的替代方案）

| 方案 | 核心思路 | 否决理由 |
|------|----------|----------|
| 方案 A：全面重构网络层架构 | 推翻现有 Cronet/OkHttp 双引擎，统一为单一网络抽象层，从架构层面解决所有问题 | 风险过高：已交付正式包基础不能动；重构涉及 50+ 文件，回归测试成本巨大；用户已认可当前架构"比之前好多了"，推翻重做不符合增量演进原则 |
| 方案 B：仅优化 P0+P1，跳过 P2/P3 | 只实施 FR-1~FR-4（P0+P1），跳过 FR-5~FR-9（P2+P3）以快速交付 | 用户明确期望"更好"，不能只做一半；P2 的日志噪声（152 次/会话）和证书错误重复降级（~10 次）对体验有可感知影响；P3 的首帧延迟方差（7.5 倍）和 JS 解析容错影响特定源可用性 |
| 方案 C：增加更多 DoH 服务器 | 在 FR-5 移除国外服务器后，新增更多国内 DoH 服务器以提升可用性 | FR-5 已证明国外服务器不可达，增加数量无法解决根本问题；当前 2 个国内服务器失败根因是负缓存过长和缺少健康检查（FR-2），而非服务器数量不足；增加服务器会增大配置维护成本 |

### 3.3 Drawbacks（已知缺点）

| 缺点 | 影响 | 接受理由 |
|------|------|----------|
| R5 去重锁引入额外内存占用 | ConcurrentHashMap<path, Deferred> 常驻内存，每条记录约 200 字节 | 嗅探场景并发量有限（单次会话 < 50 次），内存开销可忽略；Entry 在 Deferred 完成后及时移除 |
| 视频流强制 h1.1 失去 HTTP/2 多路复用优势 | 同域名多分片请求无法复用连接，可能轻微增加连接建立开销 | 视频流场景连接复用率本就不高（分片按需加载）；消除 ERR_HTTP2_PROTOCOL_ERROR 降级的收益远大于多路复用损失 |
| favicon 磁盘缓存可能存储过期图标 | 24h 过期内站点更换 favicon 不会立即反映 | favicon 变更极低频，24h 过期可接受；用户可手动清缓存刷新 |
| 证书错误记忆 5 分钟可能导致证书修复后未及时生效 | 站点更新证书后，5 分钟内仍走 OkHttp 降级 | 5 分钟窗口短，且 OkHttp 降级功能正常，仅损失 Cronet 性能优势；过期后自动重试 Cronet |
| StreamReset 用 NonCancellable 可能导致 Activity 销毁后仍在重试 | 图片加载在 Activity 销毁后继续重试，浪费少量资源 | 图片请求由图片库管理生命周期，NonCancellable 仅保护重试动作本身；重试失败或完成后正常释放 |

### 3.4 Prior Art（参考的成熟方案）

- **OkHttp 的 CacheControl**：参考其双层缓存（内存 + 磁盘）设计 favicon 缓存策略
- **Glide 的 ActiveResource + LRUCache**：参考其内存缓存管理思路处理 favicon Bitmap
- **Kotlin Coroutines NonCancellable**：官方推荐用于"必须在当前协程上下文中完成"的关键操作
- **Chromium 的 CronetUrlRequest**：参考其对协议错误的降级处理逻辑

---

## 4. Requirements（功能需求）

### FR-1（P0）: R5 嗅探去重锁

**现状**：同一 URL 在短时间（140ms~1s）内被 R5 嗅探 2-3 次。19:00 会话 41 次启动中 17 次重复（41% 浪费率），导致 76 次 ExoPlayer scope cancelled。

**根因**：`extractWithWebView`（R5 嗅探核心）有 4 个调用路径（VideoPlay.kt L425/L520/L547 + VideoUrlExtractor.kt L552），多路径并发触发同一 URL 的 WebView 嗅探，extractWithWebView 层无去重机制。注：日志分析报告 P0-2 所述"extractPrecise 被调用 2 次"经源码核实有误（extractPrecise 仅 1 处调用 VideoPlay.kt L380），真实重复源在 extractWithWebView。

**方案**：对同一 path 的 R5 嗅探请求在 `extractWithWebView` 方法入口加内存锁（`ConcurrentHashMap<path, Deferred>`），重复请求复用已有 Deferred 的结果。去重锁必须覆盖所有 4 个调用路径，放在 extractVideoUrlForEpisode 层只能覆盖 1/4 路径，无效。

**验收标准**：

- [ ] 同一 path 在 1s 内的多次 R5 嗅探请求只执行 1 次 WebView 创建
- [ ] 重复请求复用 Deferred 结果，回调只触发 1 次
- [ ] 41 次启动场景下，重复启动次数从 17 次降至 0 次
- [ ] ExoPlayer scope cancelled 次数从 76 次显著下降（目标 < 10 次）
- [ ] Deferred 完成后 Entry 及时从 Map 移除，无内存泄漏
- [ ] 异常情况下（嗅探失败）锁正确释放，不阻塞后续请求

---

### FR-2（P1）: DoH 负缓存时长优化 + 启动健康检查

**现状**：FR-5 移除国外服务器后，剩余 2 个国内 DoH 服务器仍频繁失败。19:00 会话 21 条 DoH 失败日志，1 次 DoH 被禁用 5 分钟。

**根因**：负缓存 30s 过长（DoH 临时失败后 30s 内不重试），无启动健康检查机制。

**方案**：

1. 负缓存时长从 30s 调整为 10s
2. 启动时探测 2 个 DoH 服务器的延迟和成功率，选择更优的为主服务器（探测域名改为国内域名如 www.baidu.com，不用 cloudflare-dns.com 国外域名，避免国内不可达导致探测结果不准）
3. 检测到 loopback/reserved 地址返回时立即标记该服务器不健康
4. E7 整改：修复已有 `asyncPreheatDoh()` 方法（L262）的探测域名从 `cloudflare-dns.com` 改为 `www.baidu.com`，与 preheatDohServers 统一探测域名（避免国外域名不可达导致误判 DoH 不可用）；明确 preheatDohServers（App 启动预热）与 asyncPreheatDoh（冷启动失败后 30s 异步恢复）职责分工，两者不冲突

**验收标准**：

- [ ] DoH 负缓存时长配置为 10s（可配置常量）
- [ ] 应用启动时对 2 个 DoH 服务器执行健康探测（延迟 + 成功率）
- [ ] 自动选择探测结果更优的服务器作为主服务器
- [ ] 检测到 loopback/reserved 地址返回时立即标记不健康并切换
- [ ] DoH 被禁用 5 分钟的情况不再出现（或出现频率显著下降）
- [ ] 健康探测有超时保护（单服务器探测超时 < 3s），不阻塞启动

---

### FR-3（P1）: 视频流强制 HTTP/1.1

**现状**：视频流请求出现 `ERR_HTTP2_PROTOCOL_ERROR`（InternalErrorCode=-337），3 次协议错误触发 Cronet 降级 OkHttp。

**根因**：服务端 HTTP/2 实现问题，视频流分片加载（206 Partial Content）时触发协议错误。**E6 整改根因补充**：视频流播放主路径走 ExoPlayer DataSource（cacheDataSourceFactory → cronetDataFactory/okhttpDataFactory），其中 okhttpDataFactory 已配置 HTTP/1.1（ExoPlayerHelper.kt:1013，P2-C 修复已存在）；但 ExoPlayerHelper L417/L740 的 m3u8 预检查等请求走 okHttpClient + CronetInterceptor（默认协商 HTTP/2），日志中 ERR_HTTP2_PROTOCOL_ERROR（"回退到 OkHttp"来自 CronetInterceptor L324 isProtocolError 分支）来自后者，非播放主路径。

**方案**（E6 整改：三重覆盖 + 诊断先行）：

1. 保留原方案：HttpHelper 新增 `videoStreamClient`（继承 okHttpClient 配置 + protocols=listOf(Protocol.HTTP_1_1)）
2. 保留原方案：CronetInterceptor.intercept 入口检测视频流特征（m3u8/mp4/ts 分片）跳过 Cronet
3. 新增：ExoPlayerHelper L417/L740 的 `okHttpClient.newCall` 请求（m3u8 预检查等）改用 `videoStreamClient`，强制 HTTP/1.1
4. 实施前先加诊断日志确认 ERR_HTTP2_PROTOCOL_ERROR 真实来源（在 CronetInterceptor.isProtocolError 分支 L324 增加日志输出请求 path + 调用栈）

**验收标准**：

- [ ] 识别视频流请求（URL 含 m3u8/mp4/ts 分片特征或 206 Partial Content 响应）
- [ ] 视频流请求强制使用 HTTP/1.1 协议
- [ ] 视频流场景下不再出现 ERR_HTTP2_PROTOCOL_ERROR
- [ ] 非视频流请求不受影响，仍可使用 HTTP/2
- [ ] Cronet 降级 OkHttp 的次数从 3 次降至 0 次（视频流场景）
- [ ] ExoPlayerHelper 的 m3u8 预检查请求（L417/L740）使用 HTTP/1.1（videoStreamClient）

---

### FR-4（P1）: favicon.ico 缓存

**现状**：每次加载 RSS 源/页面都请求 favicon.ico，19:00 会话 137 次请求，每次耗时 400-600ms。

**根因**：无 favicon.ico 缓存机制，每次都走网络。

**方案**：

1. 内存缓存 Bitmap，后续请求直接命中内存
2. 磁盘缓存按域名存储，24 小时过期
3. 同域名并行请求合并为一个（去重）

**验收标准**：

- [ ] 首次请求 favicon.ico 后缓存 Bitmap 到内存
- [ ] 后续同域名请求直接命中内存缓存，不走网络
- [ ] 磁盘缓存按域名存储，24 小时后自动过期
- [ ] 应用重启后磁盘缓存仍有效（24h 内）
- [ ] 同域名并行请求合并为 1 次网络请求
- [ ] 137 次/会话的网络请求降至 < 5 次（仅首次加载各域名）
- [ ] 缓存失败时不影响功能正常使用（降级走网络）

---

### FR-5（P2）: StreamReset 重用 NonCancellable

**现状**：FR-3 重试机制触发，但重试在 3ms 内被 Canceled。

**根因**：StreamResetRetryInterceptor 在重试前调用 `chain.call().cancel()` 淘汰当前连接（L41），但该调用同时设置了 Call 的 canceled 标志，导致后续 `chain.proceed(request)`（L44）检查标志时抛出 `IOException("Canceled")`。日志时序 6608→6609→6610 证明 Canceled 在 onPause 之前，与 Activity 切换无关。

**方案**：移除 `chain.call().cancel()`，改用 `okHttpClient.connectionPool().evictAll()` 清理连接（StreamResetRetryInterceptor 是 object 单例，直接引用同模块 HttpHelper 全局 okHttpClient，避免 `chain.call().client()` API 不可行问题），避免取消整个 Call。重试时 Call 状态保持可用，chain.proceed(request) 可正常执行。

**验收标准**：

- [ ] 移除 chain.call().cancel()，改用 okHttpClient.connectionPool().evictAll() 清理连接
- [ ] 重试时 Call 状态保持可用，chain.proceed(request) 不再抛出 Canceled
- [ ] 日志中不再出现"StreamReset 重试失败, error=Canceled"
- [ ] 重试成功率从 0% 提升至 > 50%

---

### FR-6（P2）: Cronet 探测跳过日志采样

**现状**：09:12 会话"Cronet 探测跳过非失败 host"日志刷屏 152 次。

**根因**：每次请求都判断 host 是否匹配 hintHost 并输出日志。

**方案**：

1. putDebug 已是 DEBUG 级别（release 包 logcat 不输出），重点改为采样输出减少 recordLog=true 时的文件日志量
2. 每 10 次跳过只输出 1 次汇总日志

**验收标准**：

- [ ] "Cronet 探测跳过非失败 host"日志保持 DEBUG 级别（putDebug 已是 DEBUG）
- [ ] Release 包 logcat 不输出该日志（putDebug 已满足）
- [ ] Debug 包下每 10 次跳过只输出 1 次汇总日志（含累计次数）
- [ ] 152 次/会话的日志噪声降至 < 20 次
- [ ] 不影响"探测命中失败 host"的正常日志输出

---

### FR-7（P2）: 证书错误记忆缓存

**现状**：多个站点证书不受信任，~10 次 `ERR_CERT_AUTHORITY_INVALID`，每次都尝试 Cronet 再降级 OkHttp。

**根因**：无证书错误记忆，每次请求都走 Cronet 失败再降级 OkHttp。

**方案**：对同一 host 的证书错误做内存缓存（5 分钟），避免每次都尝试 Cronet 再降级。

**验收标准**：

- [ ] 对同一 host 的证书错误缓存 5 分钟
- [ ] 缓存有效期内同 host 请求直接走 OkHttp 降级，不尝试 Cronet
- [ ] 缓存过期后自动重试 Cronet（检测证书是否已修复）
- [ ] 不累计降级计数的现有逻辑保持不变
- [ ] 证书错误降级次数从 ~10 次显著下降（目标 < 2 次/会话）
- [ ] 缓存有容量上限（避免无限增长），采用 LRU 淘汰

---

### FR-8（P3）: play.php 类 URL 预解析

**现状**：首帧渲染延迟 701~5309ms，差距 7.5 倍。慢的案例都是 /play.php 重定向播放器。

**根因**：play.php 类 URL 需要重定向 + 解析 + 再请求，累计延迟。

**方案**：对已知需重定向的播放器 URL 做预解析 + 缓存。

**验收标准**：

- [ ] 识别需重定向的播放器 URL 特征（如 /play.php 模式）
- [ ] 在列表页或播放器初始化前触发预解析
- [ ] 预解析结果缓存，播放器初始化时直接复用
- [ ] play.php 类 URL 的首帧延迟从 2718~5309ms 降至 < 2000ms
- [ ] 预解析失败时不阻塞正常播放流程（降级走原流程）
- [ ] 缓存有合理过期时间（避免播放地址失效）

---

### FR-9（P3）: window.__videoUrls__ 解析容错

**现状**：1 次 R5 嗅探失败"解析 window.__videoUrls__ 失败"，特定源的 JS 变量格式问题。

**根因**：BackstageWebView.kt L475 用 `GSON.fromJsonArray<String>(result).getOrNull()` 解析 window.__videoUrls__，GSON 解析失败时无容错处理。

**方案**：GSON 解析失败时尝试正则提取 URL（覆盖 m3u8/mp4/mkv/flv/mp3/m4a/aac/mpd 格式）。

**验收标准**：

- [ ] `GSON.fromJsonArray` 失败时不直接抛出异常，进入容错分支
- [ ] 容错分支使用正则表达式提取 URL
- [ ] 正则提取支持常见视频流格式（m3u8/mp4/mkv/flv/mp3/m4a/aac/mpd 等）
- [ ] 特定源的 JS 变量格式问题可正确解析
- [ ] R5 嗅探成功率从 ~90% 提升至 > 95%
- [ ] 容错失败时仍正常返回失败结果，不崩溃

---

## 5. Scenarios（场景）

### 5.1 场景一：用户连续点击多个视频源（R5 去重）

**前置条件**：用户在 RSS 源列表页浏览

**流程**：

1. 用户点击源 A 的视频项，进入播放器
2. 列表页触发 `extractPrecise` 解析视频 URL（R5 嗅探启动）
3. 播放器初始化再次触发 `extractPrecise`（同 path）
4. FR-1 去重锁命中，复用第 2 步的 Deferred 结果
5. R5 嗅探只执行 1 次，回调只触发 1 次
6. ExoPlayer 正常加载视频流，无 scope cancelled

**预期结果**：嗅探开销减半，播放器加载流畅，无重复回调导致的 ExoPlayer 取消。

### 5.2 场景二：DoH 服务器临时故障（DoH 健康检查）

**前置条件**：应用启动，主 DoH 服务器临时不可达

**流程**：

1. 应用启动触发 DoH 健康探测
2. 主服务器探测超时（> 3s），备用服务器探测成功（延迟 200ms）
3. 自动选择备用服务器为主
4. 用户请求视频流，DoH 解析成功
5. 主服务器恢复后，负缓存 10s 后自动重试

**预期结果**：DoH 故障不影响用户正常浏览，无 5 分钟禁用情况。

### 5.3 场景三：视频流分片加载（HTTP/1.1 强制）

**前置条件**：用户播放 m3u8 视频流

**流程**：

1. 播放器请求 m3u8 索引文件
2. FR-3 识别视频流特征，强制 HTTP/1.1
3. 后续 ts 分片请求均使用 HTTP/1.1
4. 分片加载正常，无 ERR_HTTP2_PROTOCOL_ERROR
5. 无 Cronet 降级 OkHttp 触发

**预期结果**：视频流加载稳定，无协议错误中断。

### 5.4 场景四：RSS 源列表加载（favicon 缓存）

**前置条件**：用户进入 RSS 源列表页，含 20 个源

**流程**：

1. 列表页加载 20 个源的 favicon
2. 首次加载 20 个域名，各发起 1 次网络请求
3. FR-4 缓存 Bitmap 到内存 + 磁盘
4. 用户下滑刷新，20 个 favicon 全部命中内存缓存
5. 应用重启后，24h 内命中磁盘缓存

**预期结果**：首次加载后无网络请求，刷新流畅。

### 5.5 场景五：StreamReset 重试连接池清理

**前置条件**：用户在播放页浏览，图片加载触发 StreamReset 重试

**流程**：

1. 图片请求触发 ERR_HTTP2_PROTOCOL_ERROR
2. StreamReset 启动重试
3. FR-5 移除 chain.call().cancel()，改用 connectionPool.evictAll() 清理故障连接
4. 重试时 Call 状态保持可用，chain.proceed(request) 正常执行
5. 重试成功，图片正常显示

**预期结果**：重试不再因 Call.cancel() 失败，重试成功率从 0% 提升至 >50%。

### 5.6 场景六：证书不受信任站点（证书错误记忆）

**前置条件**：用户访问证书不受信任的站点

**流程**：

1. 首次请求触发 ERR_CERT_AUTHORITY_INVALID
2. Cronet 降级 OkHttp（信任所有证书）
3. FR-7 缓存该 host 的证书错误（5 分钟）
4. 后续 5 分钟内同 host 请求直接走 OkHttp
5. 5 分钟后自动重试 Cronet（检测证书是否修复）

**预期结果**：避免重复尝试 Cronet 再降级，减少无效请求。

### 5.7 场景七：play.php 重定向播放（URL 预解析）

**前置条件**：用户点击 /play.php 类播放链接

**流程**：

1. 列表页识别 /play.php 特征，触发预解析
2. 预解析完成重定向 + 解析，缓存最终视频流 URL
3. 用户进入播放器，直接复用缓存的 URL
4. ExoPlayer 加载视频流，首帧渲染

**预期结果**：首帧延迟从 2718~5309ms 降至 < 2000ms，接近直链场景。

### 5.8 场景八：JS 变量格式异常（解析容错）

**前置条件**：用户访问特定源，JS 变量格式异常

**流程**：

1. R5 嗅探抓取到 `window.__videoUrls__` 内容
2. `JSON.parse` 失败（格式异常）
3. FR-9 进入容错分支，正则提取 URL
4. 正则成功提取视频流 URL
5. 嗅探成功，返回结果

**预期结果**：特定源嗅探成功率提升，不再因 JSON 解析失败而中断。
