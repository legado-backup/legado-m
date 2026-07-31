# V2 渗透式深度审查报告（2026-07-31 15:55）

> openspec-document-auditor 子代理渗透式审查：完整读取 13 个文件（4 设计文档 + 9 源码）
> 对照源码逐行验证，补充第一轮审计（audit-report-v2.md）的纰漏

---

## 新发现 ERROR（14 个，之前审计未发现）

### NEW-ERROR-1: design.md §3.1 伪代码变量顺序与实际源码冲突
- **问题**：design.md §3.1 伪代码顺序为"降级检查 → `val original = chain.request()` → originalUrl → 302 缓存检查"。但实际源码 CronetInterceptor.kt L82 中 `original` 在降级检查之前赋值，降级检查内部 L102 `original.url.host` 已使用 `original`。伪代码顺序会导致 `original` 未定义就被使用。
- **源码证据**：CronetInterceptor.kt L82 `val original: Request = chain.request()` 在降级检查之前；L102 `original.url.host` 在降级检查内部使用
- **影响**：实施者按伪代码顺序编写会编译错误或逻辑错误
- **修订建议**：design.md §3.1 伪代码修正为：`isCanceled 检查 → original = chain.request() → 降级检查 → 302 缓存检查 → engine 获取`

### NEW-ERROR-2: FR-1 缓存命中分支跳过 Keep-Alive/Accept-Encoding 头清理，触发 400 BadRequest
- **问题**：design.md §3.1 缓存命中分支 `return chain.proceed(redirectedRequest)` 跳过 CronetInterceptor.kt L130-L131 的 `removeHeader("Keep-Alive")` 和 `removeHeader("Accept-Encoding")`。原始请求带着 `Keep-Alive: 300` 头（HttpHelper.kt L118），CronetInterceptor L129 注释明确警告"手动设置会导致400 BadRequest"。
- **源码证据**：CronetInterceptor.kt L129-L131 注释"移除Keep-Alive,手动设置会导致400 BadRequest"
- **影响**：FR-1 缓存命中后 OkHttp 收到带 Keep-Alive 头的请求，可能触发 400 BadRequest，缓存命中反而失败
- **修订建议**：缓存命中分支在构造 redirectedRequest 前执行 `removeHeader("Keep-Alive")` 和 `removeHeader("Accept-Encoding")`，或复用 L128-143 的 builder 逻辑

### NEW-ERROR-3: FR-2 未处理 degradedForSession=true 时证书错误刷新降级计时
- **问题**：design.md §3.2 仅说"不累计 protocolErrorCount"，但未处理 `degradedForSession=true` 时证书错误落入 CronetInterceptor.kt L271-L278 的 `else if (degradedForSession)` 分支，会刷新 `degradedTimeMs` 延迟恢复探测。证书错误是目标站点问题，不应延迟 Cronet 恢复。
- **源码证据**：CronetInterceptor.kt L271-L278 `else if (degradedForSession) { degradedTimeMs = System.currentTimeMillis(); recoverySuccessCount = 0 }`
- **影响**：恢复探测期间证书错误会刷新降级计时，Cronet 恢复被无限延迟，与 FR-6"让 Cronet 尽快恢复"目标矛盾
- **修订建议**：FR-2 的 isCertificateError 分支必须在 L271 之前插入并 `return`，避免落入降级计时刷新分支

### NEW-ERROR-4: FR-3 清理负缓存在 DoH 熔断期间无效
- **问题**：design.md §3.3 说"清理 DoH 负缓存（强制下次重新尝试 DoH）"，但 DohDns.kt L189 的熔断逻辑 `if (now < dohDisabledUntil) return Dns.SYSTEM.lookup(hostname)` 优先于负缓存检查（L179）。DoH 熔断期间（冷启动 30s 或常规 5min）即使清理负缓存，OkHttp 降级路径仍走系统 DNS，不会重试 DoH。
- **源码证据**：DohDns.kt L189 熔断检查优先于 L179 负缓存检查
- **影响**：FR-3 的"强制下次重新尝试 DoH"在 DoH 熔断期间无效，设计意图落空
- **修订建议**：FR-3 同时清理 `dohDisabledUntil`（置 0），或明确说明仅清理负缓存的局限性

### NEW-ERROR-5: FR-6 修改 RECOVERY_PROBE_INTERVAL_MS 影响 4 处降级时长，非仅恢复探测频率
- **问题**：design.md §3.5 仅说"恢复探测频率从 5 分钟缩短为 3 分钟"，但 CronetInterceptor.kt L40 的 `RECOVERY_PROBE_INTERVAL_MS` 被多处使用：L96（正常降级间隔）、L239（恢复探测失败后降级时长，非 HTTP/2）、L261（达阈值降级时长，非震荡非 HTTP/2）、L277（非协议错误降级时长日志）。修改会影响所有这些场景。
- **源码证据**：CronetInterceptor.kt L96/L239/L261/L277
- **影响**：缩短 RECOVERY_PROBE_INTERVAL_MS 会缩短所有非 HTTP/2、非震荡的降级时长，弱网下 Cronet 频繁探测，加剧乒乓
- **修订建议**：FR-6 应新增独立常量 `RECOVERY_PROBE_CHECK_INTERVAL_MS`（仅用于 L88 恢复探测触发检查），不修改 `RECOVERY_PROBE_INTERVAL_MS`

### NEW-ERROR-6: ERR_SSL_PROTOCOL_ERROR 同时匹配 isCertificateError 和 isHttp2ProtocolError，分支顺序敏感
- **问题**：`ERR_SSL_PROTOCOL_ERROR` 含 `ERR_SSL_`（匹配 FR-2 isCertificateError）和 `PROTOCOL_ERROR`（匹配 CronetInterceptor.kt L206 isHttp2ProtocolError）。如果 FR-2 的 isCertificateError 分支插入在 isProtocolError/isHttp2ProtocolError 判定之后，`ERR_SSL_PROTOCOL_ERROR` 会被误判为 HTTP/2 协议错误，累计降级 + 1 分钟降级，与 FR-2"证书错误不累计降级"设计意图矛盾。
- **源码证据**：CronetInterceptor.kt L205-L206 `isHttp2ProtocolError = ... || errMsg.contains("PROTOCOL_ERROR", true)`
- **影响**：分支顺序错误导致 SSL 协议错误被误降级，FR-2 失效
- **修订建议**：design.md 必须明确 isCertificateError 分支在 isProtocolError/isHttp2ProtocolError 判定之前插入，且 isCertificateError 判定后立即 `return`

### NEW-ERROR-7: design.md §3.1 使用 maskUrl 函数但未定义
- **问题**：design.md §3.1 缓存命中日志 `AppLog.putDebug("Cronet 302 cache hit: ${maskUrl(originalUrl)} → ${maskUrl(cachedRedirect)}")` 使用 `maskUrl` 函数，但现有代码无此函数（DohDns.kt L377 只有 `maskHost`，CronetInterceptor.kt 无任何 mask 函数）。
- **源码证据**：DohDns.kt L377-L379 `maskHost` 函数；CronetInterceptor.kt 全文无 maskUrl
- **影响**：实施时编译错误，或实施者自行实现 maskUrl 但脱敏策略不一致
- **修订建议**：design.md §3.1 提供 maskUrl 实现（参考 DohDns.maskHost 模式）

### NEW-ERROR-8: FR-1 缓存命中检查与降级检查的顺序两难未解决
- **问题**：FR-1 缓存命中检查与降级检查的顺序存在两难：
  - 缓存命中在降级检查之前（WARN-7 建议）→ 降级期间缓存命中走 OkHttp，跳过 L86-L111 恢复探测，Cronet 永远不恢复
  - 缓存命中在降级检查之后（design.md 顺序）→ 降级期间不查缓存（WARN-7），每次请求走 OkHttp 全链路延迟
- **源码证据**：CronetInterceptor.kt L86-L111 恢复探测逻辑在降级检查内部
- **影响**：无论哪种顺序都有缺陷，FR-1 与降级机制存在交互冲突
- **修订建议**：design.md 应说明：降级期间缓存命中仍走 OkHttp（接受不恢复探测的折中），或缓存命中后检查 degradedForSession，若降级则放弃缓存走 Cronet 恢复探测

### NEW-ERROR-9: FR-1 缓存命中走 OkHttp 在 FR-5 不实施时反而导致请求失败
- **问题**：FR-1 缓存命中走 `chain.proceed(redirectedRequest)` 进入 OkHttp TLS 栈（Conscrypt），丢失 Cronet BoringSSL TLS 指纹优势。如果 FR-5 评估决定不实施，CDN 基于 TLS 指纹拒绝 OkHttp 请求，FR-1 缓存命中反而导致请求失败。
- **源码证据**：HttpHelper.kt L147 `addInterceptor`（application interceptor），`chain.proceed()` 进入 OkHttp core
- **影响**：FR-1 与 FR-5 存在依赖关系，FR-5 不实施时 FR-1 可能降低成功率
- **修订建议**：design.md 明确 FR-1 依赖 FR-5（或 FR-1 缓存命中后通过 `proceedWithCronet` 走 Cronet）

### NEW-ERROR-10: FR-5 方案B"仅降级时切换到 CronetTransport"技术不可行
- **问题**：design.md §3.4 方案B "保留 CronetInterceptor，仅降级时切换到 CronetTransport"。但 OkHttp 的 `Call.Factory` 是客户端级别配置（`OkHttpClient.Builder.callFactory`），在客户端构建时固定，不能按请求切换。
- **影响**：FR-5 方案B 无法实施，误导评估
- **修订建议**：design.md 删除方案B，或改为"方案B：自定义 Call.Factory 根据降级状态选择（复杂度高，不推荐）"

### NEW-ERROR-11: FR-1 putRedirectCache "超限全清"策略过于粗暴，缓存命中率突降
- **问题**：design.md §3.1 `putRedirectCache` 的"超限全清"策略会清空所有缓存映射，导致缓存命中率突降。现有 RedirectCacheInterceptor.kt L35 用 `LruCache` 实现平滑淘汰。
- **源码证据**：RedirectCacheInterceptor.kt L35 `LruCache<String, RedirectEntry>(MAX_CACHE_SIZE)` 平滑淘汰
- **影响**：FR-1 全清策略下，缓存满 200 条后一次全清，命中率呈锯齿状
- **修订建议**：FR-1 改用 `LruCache`（与现有 RedirectCacheInterceptor 一致）

### NEW-ERROR-12: FR-1 缓存命中分支跳过 Referer 处理，CDN 防盗链可能拒绝
- **问题**：FR-1 缓存命中分支 `chain.proceed(redirectedRequest)` 跳过 CronetInterceptor.kt L133-L141 的 Referer 处理（HTTP + Mozilla UA + https Referer → http Referer）。
- **源码证据**：CronetInterceptor.kt L133-L141 Referer 协议降级处理
- **影响**：缓存命中后 Referer 不降级，CDN 防盗链场景请求失败
- **修订建议**：缓存命中分支复用 L128-143 的 builder 逻辑（含 Referer 处理）

### NEW-ERROR-13: FR-1 缓存命中分支跳过 CookieManager.loadRequest，Cookie 不重新加载
- **问题**：FR-1 缓存命中分支跳过 CronetInterceptor.kt L145-L147 的 `CookieManager.loadRequest(newReq)`。缓存命中后 redirectedRequest 保留 original 的 Cookie（针对原 URL），但新 URL 可能需要不同 Cookie。
- **源码证据**：CronetInterceptor.kt L145-L147 `if (newReq.header(cookieJarHeader) != null) { newReq = CookieManager.loadRequest(newReq) }`
- **影响**：缓存命中后 Cookie 加载逻辑与正常路径不一致，可能导致 Cookie 失效
- **修订建议**：缓存命中分支在构造 redirectedRequest 后执行 CookieManager.loadRequest

### NEW-ERROR-14: FR-2 logCertError 复用 lastLoggedError 与协议错误共享去重状态
- **问题**：design.md §3.2 `logCertError` 复用现有 CronetInterceptor.kt L63-L65 的 `lastLoggedError`/`lastLoggedErrorTime`，与协议错误日志去重（L230-234）共享状态。证书错误和协议错误交替发生时，去重窗口失效。
- **源码证据**：CronetInterceptor.kt L230-L234 协议错误日志去重用 `lastLoggedError = errMsg`
- **影响**：证书错误和协议错误交替发生时日志刷屏，去重失效
- **修订建议**：FR-2 为证书错误单独维护 `lastCertError`/`lastCertErrorTime`

---

## 新发现 WARN（25 个，之前审计未发现）

### NEW-WARN-1: 重定向超过 20 次的边界未处理
- AbsCallBack.kt L93-L97 `MAX_FOLLOW_COUNT=20`，超过则 `request.cancel()` + `onError(IOException("Too many redirect"))`。errMsg 不匹配任何判定，落入降级计时刷新分支。

### NEW-WARN-2: proceedWithCronet 返回 null 时 NPE 边界未处理
- CronetInterceptor.kt L155 `!!` 在 proceedWithCronet 返回 null 时抛 NPE，NPE message 是 null，不匹配任何判定。

### NEW-WARN-3: FR-6 cronetEngineHealthy 与现有 engine==null 检查功能重叠
- 现有 L116-L125 已处理"引擎不可用"场景。即使修复死锁，cronetEngineHealthy 仍冗余。建议移除（ERROR-1 方案C）。

### NEW-WARN-4: design.md 异常处理分支插入顺序不明确
- isCertificateError/isNameNotResolvedError 与 isConnectionRefused/isProtocolError 的相对顺序不明确，可能导致误判。

### NEW-WARN-5: FR-2 证书错误码列表遗漏 20+ 个
- Chromium 实际有 20+ 个证书错误。应直接复用 L208-209 前缀匹配 `ERR_CERT_` + `ERR_SSL_`。

### NEW-WARN-6: FR-3 未验证 CronetException.asIOException() 转换后 message 是否保留错误码
- asIOException() 转换后 IOException 的 message 是否保留 `ERR_NAME_NOT_RESOLVED` 未验证。需真机日志验证。

### NEW-WARN-7: CronetInterceptor 已含 9+ 个降级机制，design.md 应提供完整 intercept() 代码
- 伪代码无法表达分支交互。建议 design.md 提供修改后的完整 intercept() 方法代码。

### NEW-WARN-8: FR-1 未说明是否移除现有 RedirectCacheInterceptor（死代码但仍注册）
- HttpHelper.kt L109 仍注册 RedirectCacheInterceptor（死代码）。两套缓存并存增加开销。

### NEW-WARN-9: RedirectCacheEntry data class 可能被 R8 混淆字段名
- proguard-rules.pro 需添加 keep 规则。

### NEW-WARN-10: README 根因表 R2/R6 与 FR 的映射关系不清晰
- R2（Cronet 频繁降级）同时对应 FR-5 和 FR-6，R6（TLS 指纹）也对应 FR-5。多对一关系不清晰。

### NEW-WARN-11: FR-1 缓存容量 200 条比现有 500 条小，降低命中率
- spec.md L27 "缓存容量：200 条"，现有 RedirectCacheInterceptor.kt L103 `MAX_CACHE_SIZE = 500`。

### NEW-WARN-12: FR-1 TTL 5 分钟比现有 10 分钟短，增加 302 往返
- spec.md L28 "TTL：5 分钟"，现有 RedirectCacheInterceptor.kt L104 `CACHE_TTL_MS = 10 * 60 * 1000L`。

### NEW-WARN-13: tasks.md 7.2 未明确多层重定向缓存测试
- 未明确多层 vs 单层、A→C 映射验证方法。

### NEW-WARN-14: FR-1 过期清理只在查询/写入触发，无后台清理
- 低频访问场景过期条目占用内存。

### NEW-WARN-15: tasks.md 阶段七缺少多层重定向/FR-5 实施/回归/性能测试
- 测试覆盖不足，回归风险高。

### NEW-WARN-16: tasks.md 无回归测试，FR-1/2/3/6 可能影响现有降级机制
- 现有 9+ 个降级机制可能被破坏。需新增回归测试任务。

### NEW-WARN-17: design.md §5.3 性能测试项在 tasks.md 无对应任务
- 性能验收标准（spec.md L204 "302 缓存查询延迟 ≤ 1ms"）无法验证。

### NEW-WARN-18: FR-1 缓存命中跳过 engine 获取，持久化缓存场景会导致 cronetEngine 不初始化
- 当前无影响（内存级缓存），未来持久化缓存场景有问题。

### NEW-WARN-19: FR-6 markCronetEngineHealthy 调用位置不明确
- design.md §3.5 只定义方法，未说明在 intercept() 哪个位置调用。

### NEW-WARN-20: tasks.md 6.3 "验证降级阈值动态调整"描述不准确
- FR-6 实际是"降级计数豁免清单扩展"，无动态阈值。

### NEW-WARN-21: spec.md NFR-3 "不影响现有 Cronet 降级机制"与 FR-6 修改 RECOVERY_PROBE_INTERVAL_MS 矛盾
- FR-6 修改现有常量影响 4 处降级时长。

### NEW-WARN-22: design.md §7.1 "不修改核心逻辑"表述不准确
- FR-6 修改 RECOVERY_PROBE_INTERVAL_MS（现有常量），FR-2/3 在 isProtocolError 之前插入分支。

### NEW-WARN-23: design.md §3.4 FR-5 评估未说明 Cronet 包装类的存在
- HttpHelper.kt L144-L153 通过 `Cronet.loader?.install()` 和 `Cronet.interceptor` 访问 Cronet（io.legado.app.help.http.Cronet 包装类）。

### NEW-WARN-24: tasks.md 5.1 WebSearch 查询依赖可能返回过时信息
- 建议用 Maven Central API 查询最新版本，或直接在 build.gradle 中尝试引入依赖编译验证。

### NEW-WARN-25: FR-1 缓存命中分支跳过 CronetInterceptor L133-141 Referer 处理
- 与 NEW-ERROR-12 相关，HTTP + Mozilla UA + https Referer 场景 Referer 不降级。

---

## 遗漏的根因（3 个）

### MISS-1: 图片加载下降根因分析严重不足
- **根因**：V2 文档主要聚焦视频嗅探和 TLS 指纹，但图片加载通过 Glide + okHttpClientManga 间接接入 Cronet（HttpHelper.kt L169-L187）。图片加载下降的可能根因包括：
  1. Glide 磁盘缓存策略（与 OkHttp 50MB 缓存冲突）
  2. Glide 连接池（不复用 OkHttp 50 连接池）
  3. Glide 生命周期管理（Activity 销毁后回调泄漏）
  4. ReadManga.rateLimiter（HttpHelper.kt L181 限制图片加载速率）
  5. ProgressResponseBody 开销（HttpHelper.kt L176 包装增加开销）
  6. 图片 URL 302 重定向未缓存（FR-1 应解决）
  7. 图片 CDN TLS 指纹（FR-5 应解决）
- **影响**：V2 方案可能无法解决图片加载问题
- **是否需要新增 FR**：是，需要新增 FR-7"图片加载根因分析与优化"

### MISS-2: 遗漏内存压力/GC/线程池/Cookie/UA 等根因
- 内存压力导致 GC 频繁 / OkHttp dispatcher 线程池饱和 / Cookie 失效 / UA 被封
- **是否需要新增 FR**：是，需要新增 FR-8"真机日志深度分析"

### MISS-3: FR-1 缓存命中走 OkHttp 与 FR-5 的依赖关系未分析
- FR-1 与 FR-5 存在隐式依赖，FR-5 不实施时 FR-1 可能降低成功率
- **是否需要新增 FR**：否，需在 design.md 明确依赖关系

---

## 之前审计修正（2 个）

### CORRECT-1: WARN-10 FR-3 注释表述需修正方向
- **之前说的**：Cronet 默认用系统 DNS（非 DohDns）
- **实际应该是**：Cronet 有自己的 AsyncDNS（CronetHelper.kt L185 `options.put("AsyncDNS", ...)`），不经过 DohDns。但 OkHttp 降级路径用 DohDns。注释应改为"Cronet AsyncDNS 解析失败，清理 DohDns 负缓存以便 OkHttp 降级路径通过 DoH 重试"

### CORRECT-2: INFO-6 "不修改核心逻辑"需升级为 ERROR
- **之前说的**：表述问题
- **实际应该是**：FR-6 修改 RECOVERY_PROBE_INTERVAL_MS（现有常量）直接影响核心降级逻辑（L96/L239/L261/L277），应升级为 ERROR（见 NEW-ERROR-5）

---

## 总体评估

### 纰漏数量
- 新发现 ERROR：14 个
- 新发现 WARN：25 个
- 遗漏根因：3 个
- 之前审计修正：2 个
- **总计：44 个纰漏**（含第一轮 6 ERROR + 17 WARN = 23 个，两轮合计 67 个）

### 方案可行性：低
- FR-1 存在 5 个 ERROR（缓存命中跳过头清理/Referer/Cookie/与降级检查两难/与 FR-5 依赖/全清策略），实施后可能降低成功率
- FR-2 存在 3 个 ERROR（未处理降级计时刷新/错误码列表不全/分支顺序敏感），实施后可能误降级
- FR-3 存在 1 个 ERROR（DoH 熔断期间无效），实施后设计意图落空
- FR-5 存在 2 个 ERROR（方案B 不可行/与 FR-1 依赖），评估结论可能失真
- FR-6 存在 2 个 ERROR（RECOVERY_PROBE_INTERVAL_MS 影响范围/cronetEngineHealthy 死锁），实施后可能加剧乒乓

### 实施风险：高
- CronetInterceptor.kt 已含 9+ 个降级机制，FR-1/2/3/6 新增 14 个 ERROR 风险点，分支交互复杂
- 图片加载下降根因未分析（MISS-1），V2 方案可能无法解决用户反馈
- FR-1 缓存命中走 OkHttp 与 FR-5 不实施时反而降低成功率（NEW-ERROR-9）

### 推荐 V3 重构方向

1. **FR-1 重构**：
   - 缓存命中分支复用 L128-143 的 builder 逻辑（含 Keep-Alive/Accept-Encoding/Referer/Cookie 处理）
   - 改用 LruCache 平滑淘汰（替代全清策略）
   - 缓存键加 Referer 维度（防盗链感知）
   - 明确缓存命中与降级检查的顺序（建议：降级检查之前查缓存，缓存命中仍触发恢复探测）
   - 说明与 FR-5 的依赖关系（FR-5 不实施时缓存命中走 Cronet 而非 OkHttp）
   - 提供 maskUrl 函数实现

2. **FR-2 重构**：
   - isCertificateError 改前缀匹配 `ERR_CERT_` + `ERR_SSL_`（复用 L208-209）
   - 分支在 isProtocolError/isHttp2ProtocolError 之前插入并 return（避免 ERR_SSL_PROTOCOL_ERROR 误判）
   - 处理 degradedForSession=true 时的降级计时刷新（证书错误不刷新）
   - 为证书错误单独维护去重状态

3. **FR-3 重构**：
   - 改为 host 级精准清理 `clearNegativeCache(hostname)`
   - 同时清理 dohDisabledUntil（或说明仅清理负缓存的局限性）
   - 注释改为"Cronet AsyncDNS 失败，清理 DohDns 负缓存以便 OkHttp 降级路径通过 DoH 重试"

4. **FR-5 删除方案B**：仅保留方案A（完全替换），明确 OkHttp core 失效的影响清单

5. **FR-6 重构**：
   - 移除 cronetEngineHealthy（依赖现有 engine==null 检查）
   - 新增独立常量 RECOVERY_PROBE_CHECK_INTERVAL_MS（仅用于恢复探测触发检查），不修改 RECOVERY_PROBE_INTERVAL_MS
   - 重命名为"降级计数豁免清单扩展"

6. **新增 FR-7**：图片加载根因分析（Glide 配置/rateLimiter/ProgressResponseBody/真机日志）

7. **tasks.md 补充**：阶段 1.1 加 RedirectCacheInterceptor.kt + Cronet 包装类；阶段七加多层重定向测试/回归测试/性能测试/单元测试

8. **design.md 提供完整 intercept() 代码**（而非伪代码），覆盖所有分支交互
