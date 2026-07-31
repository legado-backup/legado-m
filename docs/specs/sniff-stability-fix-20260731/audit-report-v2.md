# V2 设计文档审计报告（2026-07-31 15:45）

> 双子代理并行审核：README+spec 审计 + design+tasks 审计
> 对照源码：CronetInterceptor.kt / SSLHelper.kt / DohDns.kt / HttpHelper.kt / RedirectCacheInterceptor.kt / AbsCallBack.kt
> 网上方案：cronet-okhttp 官方库（Google，2026-02-24 发布）/ SSL 信任所有证书标准方案 / OkHttp 302 缓存机制

---

## ERROR（必须修订，否则方案不可行）

### ERROR-1: FR-6 cronetEngineHealthy 标志位存在鸡生蛋逻辑死锁
- **问题**：design.md §3.5 将 `cronetEngineHealthy` 初始值设为 `false`，`intercept()` 开头检查 `if (!cronetEngineHealthy) return chain.proceed(...)` 直接走 OkHttp；而 `markCronetEngineHealthy()` 仅在 Cronet 请求成功后调用。当标志位为 false 时永远不尝试 Cronet → 永远不会成功 → 标志位永远为 false → Cronet 被永久禁用。
- **影响**：启用 FR-6 后 Cronet 完全失效，视频嗅探能力不升反降，与目标相悖。
- **修订建议**：方案A——初始值改为 `true`，仅在 `cronetEngine` lazy 初始化异常或 `CronetLoader.install()` 失败时置 `false`；方案B——在 `engine = cronetEngine` 获取成功后立即调用 `markCronetEngineHealthy()`（而非首次请求成功后）；方案C——移除该标志位，现有 `if (engine == null) return chain.proceed(original)` 已覆盖"引擎不可用"场景，标志位冗余。

### ERROR-2: FR-2 isCertificateError 仅匹配 4 个固定错误串，遗漏其他 ERR_CERT_* 错误
- **问题**：design.md §2.2 的 `isCertificateError()` 仅匹配 `ERR_CERT_AUTHORITY_INVALID`/`ERR_SSL_PROTOCOL_ERROR`/`ERR_SSL_DECRYPT_ERROR`/`ERR_SSL_VERSION_OR_CIPHER_MISMATCH` 四种。但 Chromium 证书错误还有 `ERR_CERT_COMMON_NAME_INVALID`/`ERR_CERT_DATE_INVALID`/`ERR_CERT_SYMANTEC_LEGACY`/`ERR_CERT_KNOWN_INTERCEPTION_BLOCKED` 等。现有 CronetInterceptor.kt L208 用前缀匹配 `ERR_CERT_`+`ERR_SSL_`（更宽泛）。
- **影响**：未被匹配的证书错误会落入现有 `isProtocolError` 分支（L196-201 不含 cert，但会落入 L271 `else if (degradedForSession)` 刷新降级计时），与 FR-2"证书错误不累计降级"的设计意图矛盾，可能触发误降级。
- **修订建议**：改用前缀匹配 `errMsg.contains("ERR_CERT_", true) || errMsg.contains("ERR_SSL_", true)`，与现有 L208 逻辑一致；或显式列出全部证书错误码并说明为何排除其他。

### ERROR-3: FR-5 design.md 使用 `CronetTransport.newFactory(cronetEngine)` API，与 cronet-okhttp 官方实际 API 不符
- **问题**：design.md §3.4 方案A 注释代码为 `.callFactory(CronetTransport.newFactory(cronetEngine))`。但 cronet-okhttp 官方库（`com.google.net.cronet:cronet-okhttp`）的 Call.Factory 集成方式为 `CronetCallFactory.newBuilder(engine).build()`，Interceptor 方式为 `CronetInterceptor.newBuilder(engine).build()`。`CronetTransport` 是更早期/非官方命名，当前版本可能不存在。
- **影响**：FR-5 评估阶段会因 API 不存在而直接失败，评估结论失真。
- **修订建议**：核实 cronet-okhttp 最新版 API（0.1.1+，2026-02-24 发布），将 design.md 中 API 更正为 `CronetCallFactory.newBuilder(engine).build()`；同时说明 Interceptor 方式与现有项目 `CronetInterceptor`（基于 `cronetEngine.newUrlRequestBuilder` 原生 API）的命名冲突（同名不同实现）。

### ERROR-4: FR-5 核心逻辑矛盾
- **问题**：R2 说"Cronet 频繁降级 OkHttp"，降级原因是 Cronet 协议错误（QUIC/HTTP2/connection refused，见 CronetInterceptor.kt L196-201）。FR-5 说"让 OkHttp 降级时也用 Cronet BoringSSL"——但降级正是因为 Cronet 协议层故障，用 cronet-okhttp 桥接层同样会遇到相同协议错误。
- **影响**：FR-5 可能无法解决核心问题。cronet-okhttp 仅在"Cronet 引擎可用但 OkHttp TLS 指纹被拒绝"场景有效，但实际降级场景是 Cronet 自身协议错误。
- **修订建议**：明确 FR-5 适用场景边界，或直接放弃 FR-5，聚焦 FR-6（减少误降级，让 Cronet 尽量保持启用）。

### ERROR-5: FR-5 会导致 OkHttp 拦截器链全部失效
- **问题**：HttpHelper.kt L107-154 注册了 6+ 个拦截器（OkHttpExceptionInterceptor、RedirectCacheInterceptor、UA拦截器、Cookie网络拦截器、DecompressInterceptor、CronetInterceptor）。cronet-okhttp 作为 Call.Factory 会绕过 OkHttp core（缓存/重试/认证/网络拦截器全部失效）。V2 文档未说明此限制。
- **影响**：引入 FR-5 会导致 302 缓存、Cookie 处理、UA 添加、解压缩、50MB HTTP 缓存（L84-85）等功能全部失效，项目核心功能受损。
- **修订建议**：FR-5 必须明确说明 cronet-okhttp 的限制，评估每个失效功能的影响，给出替代方案或明确放弃 FR-5。

### ERROR-6: FR-1 与现有 RedirectCacheInterceptor 重复且设计位置错误
- **问题**：项目已存在 `app/src/main/java/io/legado/app/help/http/RedirectCacheInterceptor.kt`（L29-105），已实现 302 缓存（LruCache 500 条 + TTL 10 分钟 + Referer/Cookie 维度缓存键）。V2 文档完全未提及此实现，FR-1 提出在 CronetInterceptor 内部新增 302 缓存。
- **影响**：重复实现两套 302 缓存，位置冲突（一个在拦截器链前端 L109，一个在 CronetInterceptor 内部），缓存键不一致（现有 URL+Referer+Cookie vs FR-1 仅 URL），可能互相覆盖或冲突。
- **关键发现**：现有 RedirectCacheInterceptor 实际是死代码——因 OkHttp `followRedirects(true)`（HttpHelper.kt L105）和 Cronet `onRedirectReceived`（AbsCallBack.kt L88）均自动跟随重定向，RedirectCacheInterceptor 收到的 response 是最终 200 响应，`response.code in 300..399` 分支（L67）永不命中。
- **修订建议**：FR-1 应改为"优化现有 RedirectCacheInterceptor，使用 `response.request.url` 获取最终 URL 写入缓存"（首个有效缓存），或移除死代码后在 CronetInterceptor 内新增；缓存键至少加入 Referer 维度。

---

## WARN（建议修订，提升方案质量）

### WARN-1: FR-2 大部分功能已实现，价值被高估
- **问题**：CronetInterceptor.kt L196-201 证书错误（ERR_CERT_/ERR_SSL_）不属于 isProtocolError，不累计 protocolErrorCount；L281 所有 Cronet 错误都 `chain.proceed(original)` 回退 OkHttp。FR-2 说的"证书错误降级 OkHttp 重试"已实现。SSLHelper 已在 HttpHelper.kt L93-95 配置（`sslSocketFactory(SSLHelper.unsafeSSLSocketFactory, SSLHelper.unsafeTrustManager)` + `hostnameVerifier(SSLHelper.unsafeHostnameVerifier)`），OkHttp 降级路径自动复用。
- **影响**：FR-2 实际仅新增日志去重和明确标识，实施价值有限。
- **修订建议**：FR-2 应明确"现有代码已自动回退 OkHttp 且已配置 SSLHelper，本 FR 仅新增证书错误豁免降级计数 + 日志去重"，降低优先级。

### WARN-2: 图片加载下降根因分析不足
- **问题**：用户反馈"图片加载能力下降"，但 V2 文档主要聚焦视频嗅探和 TLS 指纹。图片加载通过 Glide + okHttpClient 间接接入 Cronet，根因可能不同（DNS？Glide 缓存？连接池？）。FR-1~FR-6 均未针对图片加载路径分析。
- **影响**：V2 方案可能无法解决图片加载问题。
- **修订建议**：补充图片加载失败的根因分析，可能需要新增针对 Glide 路径的 FR。

### WARN-3: V2 核心收益依赖"评估阶段"的 FR-5
- **问题**：V2 核心卖点是"直接解决 TLS 指纹"，但 FR-5 只是评估任务（spec.md L124）。如果 FR-5 不可行，V2 没有解决 TLS 指纹问题。
- **影响**：V2 方案的核心收益不确定。
- **修订建议**：V2 应提供"FR-5 不实施时的备选方案"（如：仅靠 FR-6 减少降级频率，让 Cronet 尽量保持启用）。

### WARN-4: FR-1 缓存键设计比现有实现更弱
- **问题**：FR-1 缓存键仅 URL，现有 RedirectCacheInterceptor 缓存键 URL+Referer+Cookie（防盗链感知）。
- **影响**：FR-1 会导致防盗链场景缓存错误 finalUrl。
- **修订建议**：FR-1 应复用现有缓存键设计（至少加 Referer 维度）。

### WARN-5: 缺少端到端成功率的具体数值验收标准
- **问题**：spec.md L197-198 验收标准"修复后嗅探成功率 ≥ 修复前"，无具体数值。
- **影响**：无法量化验证提升效果。
- **修订建议**：补充基线值和目标值（如"嗅探成功率从 X% 提升到 Y%"）。

### WARN-6: FR-1 缓存命中走 `chain.proceed(redirectedRequest)` 实际走 OkHttp 而非 Cronet
- **问题**：CronetInterceptor 作为 application interceptor（HttpHelper.kt L147 `builder.addInterceptor(it)`），`chain.proceed()` 进入下一拦截器（DecompressInterceptor→OkHttp core），不会重入 CronetInterceptor。缓存命中请求用 OkHttp TLS 栈（BoringSSL 未启用），丢失 Cronet TLS 指纹优势。
- **影响**：对全请求校验 TLS 指纹的 CDN，缓存命中后 OkHttp 请求可能被拒。
- **修订建议**：缓存命中后应构造新 Request 并通过 `proceedWithCronet` 走 Cronet（而非 `chain.proceed`）；或在 design.md 明确说明缓存命中走 OkHttp 是有意折中并说明依据。

### WARN-7: FR-1 缓存检查位于降级检查之后，降级期间不查缓存
- **问题**：design.md §1.1 架构顺序为"降级检查→302缓存检查→Cronet引擎"。当 `degradedForSession=true` 时直接走 OkHttp，不查 redirectCache。
- **影响**：降级期间即使有缓存映射也无效，每次请求都付 OkHttp 全链路延迟。
- **修订建议**：将 302 缓存检查提前到降级检查之前（缓存命中可避免 Cronet 全程参与，与降级状态无关）。

### WARN-8: FR-1 风险表称"仅缓存 301/302/307/308 响应"但代码不校验状态码
- **问题**：design.md §6 风险表写"仅缓存 301/302/307/308 响应"，但 §3.1 代码用 `originalUrl != finalUrl` 判断，不区分重定向类型（303/300/305 也会缓存）。
- **影响**：设计与代码不一致；实际会缓存所有重定向（影响较小，但文档误导）。
- **修订建议**：统一文档与代码——要么代码加状态码校验，要么文档改为"缓存所有重定向"。

### WARN-9: FR-3 `DohDns.clearNegativeCache()` 清除全部域名负缓存，应按 host 精准清理
- **问题**：design.md §3.3 `negativeCache.clear()` 清空整个 map。Cronet 的 `ERR_NAME_NOT_RESOLVED` 只涉及当前 host，全量清理会导致其他 host 的 DoH 失败被过早重试。
- **影响**：其他 host 的 30s 负缓存被误清，可能引发 DoH 重复失败探测，增加延迟。
- **修订建议**：新增 `clearNegativeCache(hostname: String)` 方法，用 `negativeCache.remove(cacheKey(hostname))` 精准清理（需暴露 cacheKey 逻辑或用 `negativeCache.remove("ADDR:$hostname")`）。

### WARN-10: FR-3 注释"DoH failure, not Cronet issue"表述误导
- **问题**：Cronet 默认用系统 DNS（非 DohDns），`ERR_NAME_NOT_RESOLVED` 是 Cronet 的系统 DNS 失败，非 DoH 失败。清理 DohDns 负缓存是为 OkHttp 降级路径（OkHttp 用 DohDns）扫除障碍。
- **影响**：误导实施者对错误归因的理解。
- **修订建议**：注释改为"Cronet 系统 DNS 解析失败，清理 DohDns 负缓存以便 OkHttp 降级路径通过 DoH 重试"。

### WARN-11: FR-5 未说明 cronet-okhttp 关键限制
- **问题**：design.md §3.4 评估要点仅列"依赖可用性/集成度差异/改动量/兼容性"，未提及 cronet-okhttp 的核心限制：OkHttp core 被绕过（缓存/重试/认证/网络拦截器全部失效）、Response 缺 `handshake`/`networkResponse`/`cacheResponse`/`sentRequestAtMillis`/`receivedResponseAtMillis` 字段。
- **影响**：评估结论可能低估迁移代价；项目 HttpHelper.kt 依赖 httpCache(L84)/cookieJar network interceptor(L123)/retryOnConnectionFailure(L94)，均会失效。
- **修订建议**：design.md §3.4 评估要点补充限制清单，并逐项评估对现有功能（HTTP 缓存/Cookie/重试/DecompressInterceptor）的影响。

### WARN-12: FR-5 未说明与现有 CronetInterceptor 的冲突处理
- **问题**：若采用 cronet-okhttp 的 Call.Factory 方式，所有请求经 Cronet 传输层，现有 CronetInterceptor（基于 `cronetEngine.newUrlRequestBuilder`）需移除，否则双重 Cronet 调用。design.md 未说明。
- **影响**：实施时可能遗留双重拦截导致请求异常。
- **修订建议**：design.md 明确"采用 Call.Factory 方式则移除 CronetInterceptor；采用 Interceptor 方式则与现有 CronetInterceptor 二选一"。

### WARN-13: FR-6 "动态错误阈值"命名误导，实际无动态阈值
- **问题**：design.md §3.5 标注"动态降级阈值（根据错误类型区分）"，但代码注释显示阈值仍为固定 5 次，仅区分"累计/不累计"（连接拒绝/NAME_NOT_RESOLVED/证书错误不累计）。现有代码已有此模式（L214 连接拒绝不累计）。
- **影响**：夸大 FR-6 创新度，误导评估。
- **修订建议**：重命名为"降级计数豁免清单扩展"（FR-2/3 新增证书错误和 NAME_NOT_RESOLVED 豁免），与"动态阈值"区分。

### WARN-14: FR-6 RECOVERY_PROBE_INTERVAL_MS 5min→3min 缺数据支撑
- **问题**：design.md 将恢复探测间隔从 5min 改 3min，但未提供真机日志数据证明 5min 过长。现有代码已有 HTTP2=1min/其他=5min/震荡=15min 三档细分。
- **影响**：盲目缩短可能增加探测频率，弱网下加剧乒乓（虽有震荡抑制兜底）。
- **修订建议**：补充真机日志统计（5min 内 Cronet 恢复的实际占比），数据驱动调整；或保持 5min 不变，仅靠 FR-2/3 减少误降级次数。

### WARN-15: tasks.md 缺少单元测试实施任务
- **问题**：design.md §5.1 列出单元测试项（302 缓存/证书错误判定/NAME_NOT_RESOLVED 判定/健康度检测），但 tasks.md 阶段七只有真机测试（7.1-7.8），无单元测试任务。
- **影响**：纯逻辑方法（isCertificateError/isNameNotResolvedError/getValidRedirectCache/putRedirectCache）缺自动化覆盖，回归风险高。
- **修订建议**：tasks.md 阶段二/三/四各新增"单元测试"子任务，覆盖判定方法和缓存 LRU/TTL 逻辑。

### WARN-16: tasks.md 阶段 1.1 未包含读取 RedirectCacheInterceptor.kt
- **问题**：阶段 1.1"读取当前 CronetInterceptor.kt + DohDns.kt + SSLHelper.kt + HttpHelper.kt 完整源码"，遗漏 RedirectCacheInterceptor.kt。
- **影响**：实施者不了解现有 302 缓存，可能重复实现或冲突。
- **修订建议**：阶段 1.1 加入 RedirectCacheInterceptor.kt，并在 AOAdapt 中记录"现有 302 缓存失效原因分析"。

### WARN-17: tasks.md 阶段 7.6/7.7 缺量化测量方法
- **问题**：7.6"嗅探成功率对比"和 7.7"图片加载稳定性对比"仅写"对比修复前后"，无具体测量脚本/样本量/通过阈值。
- **影响**：真机测试主观性强，难以客观判定通过。
- **修订建议**：明确测试样本（≥N 个订阅源/≥M 张图片）、测量脚本（用 ai_tests/scripts/）、通过阈值（成功率≥X% / 失败率≤Y%）。

---

## INFO（信息性，供参考）

- **INFO-1**: FR-1 `response.request.url` 方案技术正确。经核实 AbsCallBack.kt `toResponse`（L449-461），`newRequest = request.newBuilder().url(responseInfo.url).build()`，`response.request.url` 返回跟随所有重定向后的最终 URL（`onResponseStarted` 时 `info.url` 为最终 URL）。
- **INFO-2**: FR-2 正确识别 SSLHelper 已在 HttpHelper.kt L93-95 配置，OkHttp 降级路径自动复用，无需额外注入。SSLHelper.kt 实现完整，符合标准方案。
- **INFO-3**: FR-3 正确识别 DohDns.kt L106 `negativeCache = ConcurrentHashMap<String, Long>()` 无 clear 方法，需新增。但 DohDns.kt 已有 `negativeCache.remove(key)` 用法（L186/L217），可参考实现 host 级精准清理。
- **INFO-4**: 现有 CronetInterceptor.kt 降级逻辑已高度成熟（DEGRADE_THRESHOLD=5 / RECOVERY_SUCCESS_THRESHOLD=2 / STARTUP_GRACE_MS=300 / 震荡抑制 30s→15min / HTTP2 细分 1min / lastFailedHostHint / 启动宽限期），FR-6 的增量价值有限，建议 FR-6 聚焦"减少误降级"（FR-2/3 豁免）而非"缩短恢复间隔"。
- **INFO-5**: 现有 RedirectCacheInterceptor（LruCache 500/TTL 10min/Referer+Cookie 维度 key）在 OkHttp followRedirects=true 和 Cronet 内部跟随重定向的双重作用下，`response.code in 300..399` 不可触发，实际为死代码。FR-1 是首个有效的 302 缓存方案，建议评估是否同步移除现有 RedirectCacheInterceptor 以减少拦截器开销。
- **INFO-6**: design.md §7.1 称"FR-1/2/3/6 不修改现有 protocolErrorCount/degradedForSession 核心逻辑"，但 FR-2/3 在现有 `isProtocolError` 判断（L196）之前插入新分支，会改变错误流转路径。这是改进而非破坏，但 design.md 表述"不修改核心逻辑"不够准确，应说明"在核心逻辑前插入前置豁免分支"。

---

## 总体评估

### 方案可行性：中
- FR-1/FR-2/FR-3 可行但有重复或价值有限问题；FR-5 存在逻辑矛盾且会破坏拦截器链；FR-6 可行但 cronetEngineHealthy 有死锁。

### 是否能提升嗅探能力：部分是
- FR-6（减少误降级）+ FR-3（NAME_NOT_RESOLVED 不累计）能让 Cronet 尽量保持启用，保留 BoringSSL TLS 指纹，可提升嗅探能力。但 FR-5（核心解决方案）逻辑矛盾且破坏拦截器链，不可行。

### 是否能提升图片加载能力：不确定
- 文档未分析图片加载失败的根因，FR-1~FR-6 均未针对 Glide 路径。需要补充根因分析。

## 推荐调整方向（V3 修订）

1. **放弃 FR-5**（逻辑矛盾 + 破坏拦截器链 + API 命名错误），将 FR-6 提升为核心 FR，聚焦"减少误降级让 Cronet 保持启用"
2. **FR-1 改为优化现有 RedirectCacheInterceptor**（用 `response.request.url` 缓存最终 URL），首个有效缓存；缓存键加 Referer 维度；缓存检查提前到降级检查之前
3. **修复 FR-2 isCertificateError**（改前缀匹配 ERR_CERT_/ERR_SSL_）
4. **FR-3 改为 host 级精准清理**（`clearNegativeCache(hostname)`）
5. **FR-6 精简**：移除 cronetEngineHealthy（死锁）和 5min→3min（缺数据），仅保留 FR-2/3 豁免不累计降级
6. **补充图片加载根因分析**，可能需要新增针对 Glide 路径的 FR
7. **补充端到端成功率基线值和目标值**
8. **tasks.md 补单元测试任务 + 阶段 1.1 加 RedirectCacheInterceptor.kt + 7.6/7.7 量化方法**

---

## 关键文件路径

- 设计文档：`docs/specs/sniff-stability-fix-20260731/`（README/spec/design/tasks）
- 现有 302 缓存（design.md 未提及）：`app/src/main/java/io/legado/app/help/http/RedirectCacheInterceptor.kt`
- Cronet 重定向跟随逻辑：`app/src/main/java/io/legado/app/lib/cronet/AbsCallBack.kt`（L88-130 onRedirectReceived / L449-461 toResponse）
- 降级核心逻辑：`app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt` L78-286
- OkHttp 客户端配置：`app/src/main/java/io/legado/app/help/http/HttpHelper.kt` L84-154
- SSLHelper：`app/src/main/java/io/legado/app/help/http/SSLHelper.kt`
- DoH 负缓存：`app/src/main/java/io/legado/app/help/http/DohDns.kt` L106/L186/L217
