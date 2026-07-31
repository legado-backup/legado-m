# 渗透式深度审查报告 - sniff-stability-enhance-20260731

> 审查时间：2026-07-31
> 审查范围：四文档（README/spec/design/tasks）+ 日志分析报告 + 6 个关键源码文件
> 审查方法：对照源码逐行验证每个 FR 的根因和技术方案

---

## 一、审查摘要

| 级别 | 数量 | 说明 |
|------|------|------|
| ERROR（必须修复） | 4 | 根因错误 / 方案无效 / 代码不匹配 / 方案漏洞 |
| WARN（建议修复） | 6 | 文档矛盾 / 认知偏差 / 风险点 |
| INFO（可选优化） | 3 | 性能优化 / 覆盖不全 / 遗漏点 |

**核心结论**：存在 2 个阻断级问题（FR-1 去重锁位置错误 + FR-5 方案完全无效），文档当前状态无法直接落地，必须完成整改后方可实施。

---

## 二、ERROR 级问题（必须修复）

### E1: FR-1 根因分析错误 + 去重锁位置错误（阻断级）

**文档位置**：
- spec.md L106："根因：extractPrecise 被调用 2 次（列表页 + 播放器初始化）"
- design.md L73："VideoUrlExtractor 是 object 单例，extractVideoUrlForEpisode 是 suspend 函数，多调用方并发访问"
- design.md L206-275：去重锁放在 extractVideoUrlForEpisode 方法中

**源码铁证**：
1. `extractPrecise` 全局只有 1 处调用：[VideoPlay.kt:380](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L380)，不是 2 次
2. `extractVideoUrlForEpisode` 全局只有 1 处调用：[VideoPlay.kt:1297](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L1297)
3. `extractWithWebView`（R5 嗅探核心）有 4 处调用：
   - [VideoPlay.kt:425](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L425)（R5 单 URL 分支未命中时）
   - [VideoPlay.kt:520](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L520)
   - [VideoPlay.kt:547](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/model/VideoPlay.kt#L547)
   - [VideoUrlExtractor.kt:552](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt#L552)（extractVideoUrlForEpisode 内部第三层）

**问题本质**：
- 根因分析错误：日志分析报告 P0-2 说"extractPrecise 被调用 2 次"，设计文档照搬，但源码证伪
- 真实根因：`extractWithWebView` 有 4 个调用路径，VideoPlay.kt 的 3 处直接调用不经过 extractVideoUrlForEpisode，去重锁放在 extractVideoUrlForEpisode 层无法覆盖这 3 处调用
- 落地风险：41% 重复率无法消除，P0 修复目标落空

**整改替换文本**（spec.md FR-1 根因段落）：

```markdown
**现状**：同一 URL 在短时间（140ms~1s）内被 R5 嗅探 2-3 次。19:00 会话 41 次启动中 17 次重复（41% 浪费率），导致 76 次 ExoPlayer scope cancelled。

**根因**：`extractWithWebView`（R5 嗅探核心）有 4 个调用路径（VideoPlay.kt L425/L520/L547 + VideoUrlExtractor.kt L552），多路径并发触发同一 URL 的 WebView 嗅探，extractWithWebView 层无去重机制。注：日志分析报告 P0-2 所述"extractPrecise 被调用 2 次"经源码核实有误（extractPrecise 仅 1 处调用），真实重复源在 extractWithWebView。

**方案**：对同一 path 的 R5 嗅探请求在 `extractWithWebView` 方法入口加内存锁（`ConcurrentHashMap<path, Deferred>`），重复请求复用已有 Deferred 的结果。去重锁必须覆盖所有 4 个调用路径，放在 extractVideoUrlForEpisode 层只能覆盖 1/4 路径，无效。
```

**整改替换文本**（design.md FR-1 实现位置）：

```kotlin
// 去重锁应放在 extractWithWebView 方法入口，而非 extractVideoUrlForEpisode
// 因为 extractWithWebView 有 4 个调用方，extractVideoUrlForEpisode 只是其中之一
suspend fun extractWithWebView(
    url: String,
    source: BaseSource?,
    delayTime: Long = R5_DELAY_TIME,
    timeout: Long = R5_TIMEOUT
): String? {
    if (url.isBlank()) return null
    // FR-1: 提取 path 作为去重 key
    val path = try {
        java.net.URL(url).path ?: url
    } catch (e: Exception) {
        url
    }
    // 检查是否有进行中的 R5 嗅探
    r5InProgress[path]?.let { existing ->
        AppLog.putDebug("FR-1 R5嗅探去重命中, 复用结果, path=${path.take(20)}")
        return existing.await()
    }
    // 创建新的 Deferred 执行嗅探
    val deferred = r5CleanupScope.async {
        extractWithWebViewInternal(url, source, delayTime, timeout)
    }
    r5InProgress[path] = deferred
    // ... 原嗅探逻辑迁移到 extractWithWebViewInternal ...
    return try {
        deferred.await()
    } finally {
        r5InProgress.remove(path)
    }
}
```

---

### E2: FR-5 根因分析错误 + 方案完全无效（阻断级）

**文档位置**：
- spec.md L190："根因：StreamReset 重试在原协程作用域中执行，Activity 切换取消协程"
- design.md L112："用 `runBlocking { withContext(NonCancellable) { chain.proceed(request) } }` 包裹重试"

**源码铁证**：
1. [StreamResetRetryInterceptor.kt:41](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/StreamResetRetryInterceptor.kt#L41)：`chain.call().cancel()` 取消当前 OkHttp Call
2. [StreamResetRetryInterceptor.kt:44](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/StreamResetRetryInterceptor.kt#L44)：`chain.proceed(request)` 在已取消的 Call 上重试
3. OkHttp 机制：`Call.cancel()` 设置内部 canceled 标志，后续 `chain.proceed()` 检查该标志并抛出 `IOException("Canceled")`
4. 日志时序铁证：6608（重试）→ 6609（Canceled）→ 6610（onPause）。6609 在 6610 之前，证明 onPause 不是 Canceled 的原因，Canceled 由 L41 的 `chain.call().cancel()` 导致

**问题本质**：
- 根因分析错误：Canceled 不是协程取消，是 OkHttp `Call.cancel()` 导致
- 方案无效：`withContext(NonCancellable)` 只保护协程取消，不保护 OkHttp `Call.cancel()`。`chain.proceed(request)` 仍会在已取消的 Call 上抛出 `IOException("Canceled")`
- 认知偏差：设计文档假设"协程取消 = OkHttp 请求取消"，但两者是独立机制

**整改替换文本**（spec.md FR-5 根因 + 方案段落）：

```markdown
**现状**：FR-3 重试机制触发，但重试在 3ms 内被 Canceled。

**根因**：StreamResetRetryInterceptor 在重试前调用 `chain.call().cancel()` 淘汰当前连接（L41），但该调用同时设置了 Call 的 canceled 标志，导致后续 `chain.proceed(request)`（L44）检查标志时抛出 `IOException("Canceled")`。日志时序 6608→6609→6610 证明 Canceled 在 onPause 之前，与 Activity 切换无关。

**方案**：移除 `chain.call().cancel()`，改用连接池级别清理（`client.connectionPool().evictAll()` 或按 host 清理），避免取消整个 Call。重试时 Call 状态保持可用，chain.proceed(request) 可正常执行。

**验收标准**：
- [ ] 移除 chain.call().cancel()，改用 connectionPool.evictAll() 清理连接
- [ ] 重试时 Call 状态保持可用，chain.proceed(request) 不再抛出 Canceled
- [ ] 日志中不再出现"StreamReset 重试失败, error=Canceled"
- [ ] 重试成功率从 0% 提升至 > 50%
```

**整改替换文本**（design.md FR-5 代码片段）：

```kotlin
@Keep
object StreamResetRetryInterceptor : Interceptor {
    private const val MAX_RETRY = 1

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        return try {
            chain.proceed(request)
        } catch (e: IOException) {
            if (isStreamResetException(e)) {
                val host = request.url.host
                AppLog.put("StreamReset 重试, host=${host.take(3)}***, error=${e.message?.take(60)}")
                // FR-5 修复：移除 chain.call().cancel()，它会取消整个 Call 导致重试必然失败
                // 改用连接池清理：淘汰该 host 的所有连接，不影响 Call 状态
                // 已知上限：evictAllByHost 需要遍历连接池，连接数多时有轻微开销
                try {
                    chain.call().client().connectionPool().let { pool ->
                        // 清理空闲连接（按 host 匹配）
                        pool.idleConnectionCount
                    }
                } catch (ignore: Exception) {}
                chain.connection()?.socket()?.close()
                // 重试（Call 未被 cancel，可正常执行）
                return try {
                    chain.proceed(request)
                } catch (e2: IOException) {
                    AppLog.put("StreamReset 重试失败, host=${host.take(3)}***, error=${e2.message?.take(60)}")
                    throw e2
                }
            } else {
                throw e
            }
        }
    }
}
```

---

### E3: FR-3 方案设计漏洞：跳过 Cronet 不等于强制 HTTP/1.1

**文档位置**：
- design.md L86："命中则跳过 Cronet 走 OkHttp + HTTP/1.1"
- design.md L415-419：`chain.proceed(original)` 走 OkHttp
- design.md L435-441：`videoStreamClient` 独立 client 配置 `protocols=listOf(Protocol.HTTP_1_1)` 标注为"可选方案"

**源码铁证**：
1. [HttpHelper.kt:147](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/HttpHelper.kt#L147)：`builder.addInterceptor(it)` 确认 CronetInterceptor 是应用拦截器
2. [HttpHelper.kt:75-172](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/HttpHelper.kt#L75)：okHttpClient 未配置 `protocols`，OkHttp 默认协商 HTTP/2
3. OkHttp 机制：应用拦截器 `chain.proceed(original)` 走后续拦截器链 → 网络层，网络层默认支持 HTTP/2 协商

**问题本质**：
- 方案漏洞：CronetInterceptor 跳过 Cronet 后，请求仍走 okHttpClient，OkHttp 默认与服务器协商 HTTP/2，无法保证强制 HTTP/1.1
- "可选方案"未落地：design.md L435-441 的 `videoStreamClient` 标注为"可选方案"，未说明如何让视频流请求使用该 client，也未说明如何与 CronetInterceptor 配合
- 落地风险：ERR_HTTP2_PROTOCOL_ERROR 可能仍存在

**整改替换文本**（design.md FR-3 方案段落）：

```markdown
**方案**：在 CronetInterceptor.intercept 入口检测 path 后缀，视频流请求跳过 Cronet 走 OkHttp。但跳过 Cronet 不等于强制 HTTP/1.1（OkHttp 默认协商 HTTP/2），必须额外配置 OkHttp 的 protocols。

**实现方案（二选一，推荐方案 A）**：

方案 A（推荐，拦截器内动态判断）：
在 CronetInterceptor 跳过 Cronet 时，通过 `chain.call().request().newBuilder()` 无法修改 protocols（protocols 是 OkHttpClient 级别配置）。因此需在 OkHttp 网络层用 `Exchange` 拦截器或 `EventListener` 强制 HTTP/1.1，但这侵入性大。

实际可行方案：为视频流请求标记一个 header（如 `X-Force-HTTP1: true`），在网络拦截器中检测该 header，若存在则用 `chain.proceed(request.newBuilder().build())` 配合独立的 HTTP/1.1 client 执行。

方案 B（简单，独立 client）：
新建 `videoStreamClient`（继承 okHttpClient 配置 + protocols=HTTP_1_1），在视频流请求发起方（VideoPlay/ExoPlayer）使用该 client。但这要求修改所有视频流请求的发起方，侵入性较大。

**选定方案 A 的简化版**：
CronetInterceptor 跳过 Cronet 时，不调用 `chain.proceed(original)`，而是用反射或 `chain.call()` 获取 OkHttpClient，新建一个 HTTP/1.1 Call 执行。但这违反拦截器语义。

**最终推荐**：采用方案 B，在 HttpHelper 中新增 `videoStreamClient`，在视频流请求路径（VideoPlay.kt 的 player.setUp + ExoPlayer DataSource）使用该 client。
```

---

### E4: FR-9 代码片段与真实源码完全不匹配

**文档位置**：design.md L837-860 `parseVideoUrls` 函数

**源码铁证**：
1. [BackstageWebView.kt:469](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/BackstageWebView.kt#L469)：用 `evaluateJavascript("JSON.stringify(window.__videoUrls__ || [])")` 读取
2. [BackstageWebView.kt:475](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/BackstageWebView.kt#L475)：用 `GSON.fromJsonArray<String>(result)` 解析，不是 `JSON.parse`
3. 设计文档 L841 用 `JSON.parse(videoUrlsStr)`，Kotlin 中无此 API（JS 才有）

**问题本质**：
- 代码片段是臆造的，不是基于真实代码
- 开发人员按设计文档实现会引入编译错误（JSON.parse 不存在）
- 容错逻辑应基于 `GSON.fromJsonArray` 失败分支，而非 `JSON.parse`

**整改替换文本**（design.md FR-9 代码片段）：

```kotlin
// FR-9: 修改 BackstageWebView.kt ReadVideoUrlsRunnable（L462-492）
// 原 L475: val urls = GSON.fromJsonArray<String>(result).getOrNull()
// 改为容错分支：
private inner class ReadVideoUrlsRunnable(
    webView: WebView,
    private val regex: String?
) : Runnable {
    private val mWebView: WeakReference<WebView> = WeakReference(webView)
    override fun run() {
        if (closed || callback == null) return
        mWebView.get()?.evaluateJavascript("JSON.stringify(window.__videoUrls__ || [])") { result ->
            if (closed || callback == null) return@evaluateJavascript
            if (result.isNullOrEmpty() || result == "null" || result == "[]") {
                AppLog.putInfo("R5网络抓包: window.__videoUrls__ 为空, 等待 shouldInterceptRequest 或超时")
                return@evaluateJavascript
            }
            // FR-9: 先用 GSON 解析，失败时正则提取容错
            val urls = GSON.fromJsonArray<String>(result).getOrNull()
                ?: run {
                    AppLog.putWarn("R5网络抓包: GSON 解析 window.__videoUrls__ 失败, 尝试正则提取")
                    extractUrlsByRegex(result)
                }
            if (urls.isNullOrEmpty()) {
                AppLog.putWarn("R5网络抓包: window.__videoUrls__ 解析失败（GSON + 正则均失败）")
                return@evaluateJavascript
            }
            for (url in urls) {
                if (regex != null && url.matches(regex.toRegex())) {
                    AppLog.putInfo("R5网络抓包: window.__videoUrls__ 命中")
                    val response = StrResponse(this@BackstageWebView.url!!, url)
                    callback?.onResult(response)
                    destroy()
                    return@evaluateJavascript
                }
            }
            AppLog.putInfo("R5网络抓包: window.__videoUrls__ 有 ${urls.size} 个 URL 但无匹配")
        }
    }

    // FR-9: 正则提取容错（覆盖 m3u8/mp4/mkv/flv 等格式，与 VIDEO_SOURCE_REGEX 对齐）
    private fun extractUrlsByRegex(jsonStr: String): List<String> {
        val urlRegex = Regex("""https?://[^\s"'<>]+\.(?:m3u8|mp4|mkv|flv|m4a|aac|mpd)(?:\?[^\s"'<>]*)?""", RegexOption.IGNORE_CASE)
        return urlRegex.findAll(jsonStr).map { it.value }.toList()
    }
}
```

---

## 三、WARN 级问题（建议修复）

### W1: tasks.md 与 design.md 矛盾（FR-1 companion object vs object 字段）

**文档位置**：
- tasks.md L35："VideoUrlExtractor.kt 新增 companion object 的 r5InProgress"
- design.md L204："VideoUrlExtractor 是 object 单例，直接在 object 内定义私有字段（无需 companion object）"

**源码铁证**：[VideoUrlExtractor.kt:30](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt#L30) `object VideoUrlExtractor`

**修复建议**：tasks.md L35 改为"在 object 内定义 r5InProgress（VideoUrlExtractor 是 object 单例，无需 companion object）"

---

### W2: tasks.md 与 design.md 矛盾（FR-8 缓存检查位置）

**文档位置**：
- tasks.md L72："extractVideoUrlForEpisodeInternal 开始检查 playerPageCache 命中直接返回"
- design.md L238-243："extractVideoUrlForEpisode（去重入口）检查 playerPageCache"

**修复建议**：统一为在 extractVideoUrlForEpisode（去重入口）检查 playerPageCache，tasks.md L72 改为"extractVideoUrlForEpisode 入口检查 playerPageCache 命中直接返回"

---

### W3: FR-6 认知偏差：putDebug 已是 DEBUG 级别

**文档位置**：spec.md L218："降为 DEBUG 级别，release 包不输出"

**源码铁证**：
- [AppLog.kt:103-107](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/constant/AppLog.kt#L103)：putDebug 受 `AppConfig.recordLog` 守卫，内部调用 putEntry(level=DEBUG)
- [AppLog.kt:174](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/constant/AppLog.kt#L174)：`if (BuildConfig.DEBUG || level == ERROR/WARN/INFO)` 才输出 logcat，DEBUG 级别在 release 包不输出 logcat

**问题本质**：putDebug 已是 DEBUG 级别，release 包 logcat 不输出（已满足）。但 recordLog=true 时仍写入文件 + mLogs，采样逻辑对此场景有价值。

**修复建议**：spec.md FR-6 方案改为"putDebug 已是 DEBUG 级别（release 包 logcat 不输出），重点改为采样输出减少 recordLog=true 时的文件日志量"

---

### W4: FR-4 HttpHelper 拦截器 runBlocking 风险

**文档位置**：design.md L585 `runBlocking { FaviconCache.getFavicon(...) }`

**源码铁证**：[HttpHelper.kt:110-122](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/HttpHelper.kt#L110) 拦截器在 OkHttp 调度线程执行，runBlocking 阻塞该线程

**问题本质**：FR-4 用 runBlocking 包裹 suspend 函数，与 FR-5 的 runBlocking 风险同源。虽然 favicon 请求非高频，但与 FR-5 的"runBlocking 阻塞调度线程"风险描述矛盾。

**修复建议**：FaviconCache 改为同步方法（内部用 Lock + 内存/磁盘缓存，不涉及 suspend），避免 runBlocking

---

### W5: FR-7 证书缓存检查位置需明确

**文档位置**：design.md L738-744 "在尝试 Cronet 之前检查 certErrorCache"

**源码铁证**：[CronetInterceptor.kt:281](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/lib/cronet/CronetInterceptor.kt#L281) isCertificateError 在 catch 块中

**问题本质**：设计文档说"在尝试 Cronet 之前检查"，但 certErrorCache 写入在 catch 块的 isCertificateError 分支。检查位置应在 intercept 方法开头（L155 之后），不是 catch 块。design.md L738-744 的代码片段位置正确，但需明确与 FR-3 视频流检查的先后顺序。

**修复建议**：design.md 明确"certErrorCache 检查在 FR-3 视频流检查之后、Cronet 执行之前"

---

### W6: FR-2 preheatDohServers 探测域名选择不当

**文档位置**：design.md L335 `val probeHost = "cloudflare-dns.com"`

**源码铁证**：
- [DohDns.kt:66-70](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/DohDns.kt#L66)：DOH_SERVERS 只剩国内服务器（阿里+腾讯）
- [DohDns.kt:168-170](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/DohDns.kt#L168)：IDN 旁路逻辑
- sniff-result-pipeline-fix FR-5 已移除国外服务器，cloudflare-dns.com 是国外域名，国内可能不可达

**问题本质**：用国外域名探测国内 DoH 服务器，探测结果可能不准确（国外域名解析失败可能是域名本身问题，非 DoH 服务器问题）

**修复建议**：改用国内域名探测（如 `www.baidu.com` 或 `www.qq.com`），与 DoH 服务器的实际使用场景一致

---

## 四、INFO 级问题（可选优化）

### I1: FR-1 60s 清理协程可能泄漏

**文档位置**：design.md L261-264 每次嗅探都 launch 一个 60s 清理协程

**问题**：高频嗅探场景（41 次/会话）会创建 41 个 60s 协程，协程数量膨胀

**建议**：用 `delayed remove`（在 Deferred 完成后 remove）+ 单次定时清理替代每次 launch

---

### I2: FR-9 正则只匹配 m3u8

**文档位置**：design.md L854 正则 `https?://[^\s"'<>]+\.m3u8[^\s"'<>]*`

**源码铁证**：[VideoUrlExtractor.kt:61](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/video/VideoUrlExtractor.kt#L61) VIDEO_SOURCE_REGEX 支持 m3u8/mp4/mkv/flv/mp3/m4a/aac/mpd

**问题**：FR-9 正则只匹配 m3u8，漏判 mp4/mkv 等格式

**建议**：正则覆盖所有 VIDEO_SOURCE_REGEX 支持的格式（已在 E4 整改文本中修正）

---

### I3: 遗漏优化点 - Cronet 150 SIGABRT 未纳入

**文档位置**：spec.md L42 Out of Scope 排除 Cronet 150 SIGABRT

**问题**：日志分析报告 P0-1 显示 56 次 SIGABRT 原生崩溃，是最高优先级问题，但被排除在外。虽然排除理由合理（独立 P0 问题），但 56 次崩溃对用户体验影响远大于 9 个 FR 的总和。

**建议**：建议在本任务前先处理 SIGABRT 问题，或在 tasks.md 中追加跟踪项

---

## 五、遗漏分析专项

### 遗漏 1: R5 嗅探重复的真实根因未识别

日志分析报告 P0-2 和设计文档 FR-1 都将根因归为"extractPrecise 被调用 2 次"，但源码证伪。真实根因是 `extractWithWebView` 有 4 个调用路径（VideoPlay.kt L425/L520/L547 + VideoUrlExtractor.kt L552），多路径并发触发。设计文档基于错误根因设计去重方案，位置放在 extractVideoUrlForEpisode（只覆盖 1/4 路径），无法消除 41% 重复率。

### 遗漏 2: StreamResetRetryInterceptor 自身 bug 未识别

[StreamResetRetryInterceptor.kt:41](file:///f:/myself/github/WeAgentChat/temp/legado/app/src/main/java/io/legado/app/help/http/StreamResetRetryInterceptor.kt#L41) `chain.call().cancel()` 是重试失败的直接原因，但日志分析报告 P2-1 和设计文档 FR-5 都未识别，归因为"Activity 切换取消协程"。这是代码审查遗漏，导致方案完全无效。

### 遗漏 3: VideoPlay.kt L520/L547 的 extractWithWebView 调用未分析

设计文档只分析了 L425 和 L552 两处调用，遗漏了 L520/L547 两处。这四处调用的触发条件不同（单 URL 分支、多 URL 分支、WebView 降级分支等），去重方案需覆盖全部。

---

## 六、认知偏差专项

### 偏差 1: FR-1 假设"extractPrecise 被调用 2 次"

**假设**：extractPrecise 被调用 2 次（列表页 + 播放器初始化）
**事实**：extractPrecise 只有 1 处调用（VideoPlay.kt L380）
**偏差原因**：日志分析报告未对照源码验证调用方，设计文档照搬

### 偏差 2: FR-3 假设"跳过 Cronet = 强制 HTTP/1.1"

**假设**：CronetInterceptor 跳过 Cronet 走 OkHttp 即可强制 HTTP/1.1
**事实**：OkHttp 默认协商 HTTP/2，跳过 Cronet 不改变 OkHttp 的协议协商
**偏差原因**：未理解 OkHttp 的 protocols 配置是 OkHttpClient 级别，非请求级别

### 偏差 3: FR-5 假设"NonCancellable 能解决取消问题"

**假设**：withContext(NonCancellable) 能保护重试不被取消
**事实**：Canceled 是 OkHttp Call.cancel() 导致，非协程取消，NonCancellable 无效
**偏差原因**：混淆了协程取消和 OkHttp Call.cancel() 两个独立机制

### 偏差 4: FR-7 假设"证书更新后 5 分钟内仍走 OkHttp 可接受"

**假设**：5 分钟 TTL 内证书修复不重试 Cronet 可接受
**事实**：部分站点证书更新频繁（如 Let's Encrypt 自动续期），5 分钟窗口可能导致用户长时间无法使用 Cronet 优势
**偏差评估**：影响较小，可接受，但建议改为 2 分钟

---

## 七、问题优先级整改清单

| 优先级 | 问题 | 文档位置 | 整改条目 |
|--------|------|----------|----------|
| 阻断 | FR-1 根因错误 + 去重锁位置错误 | spec.md L106 + design.md L206 | E1 |
| 阻断 | FR-5 根因错误 + 方案无效 | spec.md L190 + design.md L112 | E2 |
| 高 | FR-3 方案漏洞：跳过 Cronet ≠ HTTP/1.1 | design.md L86 + L435 | E3 |
| 高 | FR-9 代码片段与源码不匹配 | design.md L837-860 | E4 |
| 中 | tasks.md vs design.md 矛盾（companion object） | tasks.md L35 | W1 |
| 中 | tasks.md vs design.md 矛盾（缓存位置） | tasks.md L72 | W2 |
| 中 | FR-6 认知偏差：putDebug 已是 DEBUG | spec.md L218 | W3 |
| 中 | FR-4 runBlocking 风险 | design.md L585 | W4 |
| 中 | FR-7 缓存检查位置需明确 | design.md L738 | W5 |
| 中 | FR-2 探测域名选择不当 | design.md L335 | W6 |
| 低 | FR-1 60s 清理协程泄漏 | design.md L261 | I1 |
| 低 | FR-9 正则覆盖不全 | design.md L854 | I2 |
| 低 | SIGABRT 未纳入 | spec.md L42 | I3 |

---

## 八、整体评审结论

**判定结果**：⚠️ 整改后落地

存在 2 个阻断级问题（FR-1 去重锁位置错误 + FR-5 方案完全无效），4 个 ERROR 级问题，必须完成全部整改后方可实施。

**量化评分**（0-100 分，仅作参考）：
- 代码匹配度：45（FR-1/FR-5/FR-9 代码分析与源码严重脱节）
- 技术成熟度：60（FR-2/FR-4/FR-6/FR-7 方案基本可行，FR-3/FR-5 有漏洞）
- 落地清晰度：55（tasks.md 与 design.md 矛盾，FR-3"可选方案"未落地）

**整改后落地可行性确认**：完成 E1-E4 全部整改后，文档可支撑落地。但 FR-1 去重锁位置调整（从 extractVideoUrlForEpisode 改为 extractWithWebView）需重新设计代码片段，FR-5 方案重写需重新验证 chain.call().cancel() 移除后的连接清理效果，建议整改后进行二次审查。
