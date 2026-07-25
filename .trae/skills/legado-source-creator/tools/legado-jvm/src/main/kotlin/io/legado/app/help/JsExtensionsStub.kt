package io.legado.app.help

import cn.hutool.core.codec.Base64
import cn.hutool.core.util.HexUtil
import cn.hutool.crypto.digest.DigestUtil
import cn.hutool.crypto.digest.HMac
import cn.hutool.crypto.symmetric.SymmetricCrypto
import io.legado.app.constant.AppConst
import io.legado.app.constant.AppPattern
import io.legado.app.data.entities.BaseSourceInterface
import io.legado.app.exception.NoStackTraceException
import io.legado.app.help.ConcurrentRateLimiter
import io.legado.app.help.crypto.AsymmetricCrypto
import io.legado.app.help.crypto.Sign
import io.legado.app.help.http.CookieManager.cookieJarHeader
import io.legado.app.help.http.CookieStoreStub
import io.legado.app.help.http.StrResponse
import io.legado.app.model.Debug
import io.legado.app.model.analyzeRule.AnalyzeUrl
import io.legado.app.model.analyzeRule.QueryTTF
import io.legado.app.model.analyzeRule.RuleData
import io.legado.app.model.analyzeRule.RuleDataInterface
import io.legado.app.utils.ChineseUtils
import io.legado.app.utils.EncodingDetect
import io.legado.app.utils.GSON
import io.legado.app.utils.HtmlFormatter
import io.legado.app.utils.JsURL
import io.legado.app.utils.StringUtils
import io.legado.app.utils.fromJsonObject
import io.legado.ruleengine.UserInterventionException
import io.legado.ruleengine.WebViewRequest
import io.legado.ruleengine.WebViewRequiredException
import org.jsoup.Connection
import org.jsoup.Jsoup
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.File
import java.net.URLEncoder
import java.nio.charset.Charset
import java.security.MessageDigest
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.SimpleTimeZone
import java.util.UUID
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream
import java.util.concurrent.CompletableFuture

/**
 * JsExtensions 的 JVM Stub 实现。
 *
 * 策略统计：
 * - 完整实现：86 个（纯 JVM 逻辑或依赖已抽取的类）
 * - Stub 降级：38 个（依赖 Android 平台，降级为 HTTP 或空实现）
 * - 不可用：8 个（纯 UI 交互，抛出 UnsupportedOperationException）
 *
 * 源码参照：app/src/main/java/io/legado/app/help/JsExtensions.kt
 *          app/src/main/java/io/legado/app/help/JsEncodeUtils.kt
 */
@Suppress("unused")
object JsExtensionsStub : JsExtensionsInterface {

    // 修复 GAP-36: source/ruleData 改为 ThreadLocal，避免多源并发调试时被覆盖
    // 简化说明: 使用 ThreadLocal 隔离每个线程的 source/ruleData | 已知上限: 线程池复用线程时需重新 configure | 升级路径: 改为 class 实例化模式
    private val sourceThreadLocal = ThreadLocal<Any?>()
    private val ruleDataThreadLocal = ThreadLocal<RuleDataInterface>()

    // 修复编译冲突: private 属性重命名为 _source/_ruleData，避免与 getSource()/getRuleData() 方法签名冲突
    private val _source: Any? get() = sourceThreadLocal.get()
    private val _ruleData: RuleDataInterface get() = ruleDataThreadLocal.get() ?: RuleData()

    fun getRuleData(): RuleDataInterface = _ruleData

    // 简化说明：使用临时目录替代 appCtx.externalCache | 已知上限：重启后文件丢失 | 升级路径：配置持久化目录
    private val cacheDir = File(System.getProperty("java.io.tmpdir"), "legado-jvm-cache").apply { mkdirs() }

    @Synchronized
    fun configure(source: Any?, ruleData: RuleDataInterface) {
        sourceThreadLocal.set(source)
        ruleDataThreadLocal.set(ruleData)
    }

    // ==================== 抽象方法 ====================

    override fun getSource(): Any? = _source

    override fun getTag(): String? = _source?.toString()

    // ==================== HTTP 方法 ====================

    override fun ajax(url: Any): String? = ajax(url, null)

    override fun ajax(url: Any, callTimeout: Long?): String? {
        val urlStr = if (url is List<*>) {
            url.firstOrNull().toString()
        } else {
            url.toString()
        }
        return kotlin.runCatching {
            val analyzeUrl = AnalyzeUrl(
                mUrl = urlStr,
                source = _source as? BaseSourceInterface,
                ruleData = _ruleData,
                callTimeout = callTimeout
            )
            analyzeUrl.getStrResponse().body
        }.onFailure {
            log("ajax($urlStr) error: ${it.localizedMessage}")
        }.getOrElse {
            it.stackTraceToString()
        }
    }

    override fun ajaxAll(urlList: Array<String>): Array<StrResponse> = ajaxAll(urlList, false)

    // 修复 GAP-07: 使用 CompletableFuture 并发执行，替代串行循环 | 已知上限：无协程取消检查 | 升级路径：接入协程上下文
    override fun ajaxAll(urlList: Array<String>, skipRateLimit: Boolean): Array<StrResponse> {
        if (urlList.isEmpty()) return emptyArray()
        val futures = urlList.map { url ->
            CompletableFuture.supplyAsync {
                kotlin.runCatching {
                    val analyzeUrl = AnalyzeUrl(
                        mUrl = url,
                        source = _source as? BaseSourceInterface,
                        ruleData = _ruleData
                    )
                    analyzeUrl.getStrResponse(useWebView = false)
                }.getOrElse {
                    StrResponse(url, it.stackTraceToString())
                }
            }
        }
        return futures.map { it.join() }.toTypedArray()
    }

    override fun ajaxTestAll(urlList: Array<String>, timeout: Int): Array<StrResponse> =
        ajaxTestAll(urlList, timeout, false)

    // 修复 GAP-07: 使用 CompletableFuture 并发执行，替代串行循环 | 已知上限：无协程取消检查 | 升级路径：接入协程上下文
    override fun ajaxTestAll(urlList: Array<String>, timeout: Int, skipRateLimit: Boolean): Array<StrResponse> {
        if (urlList.isEmpty()) return emptyArray()
        val futures = urlList.map { url ->
            CompletableFuture.supplyAsync {
                kotlin.runCatching {
                    val analyzeUrl = AnalyzeUrl(
                        mUrl = url,
                        source = _source as? BaseSourceInterface,
                        ruleData = _ruleData,
                        callTimeout = timeout.toLong()
                    )
                    analyzeUrl.getStrResponse(useWebView = false)
                }.getOrElse {
                    StrResponse(url, it.stackTraceToString())
                }
            }
        }
        return futures.map { it.join() }.toTypedArray()
    }

    override fun connect(urlStr: String): StrResponse = connect(urlStr, null, null)

    override fun connect(urlStr: String, header: String?): StrResponse = connect(urlStr, header, null)

    // 修复说明: 将 analyzeUrl 定义移到 runCatching 外，catch 块中 url 改用 analyzeUrl.url（与真机 connect 行为一致，真机用 analyzeUrl.url 而非原始 urlStr）
    override fun connect(urlStr: String, header: String?, callTimeout: Long?): StrResponse {
        val headerMap = GSON.fromJsonObject<Map<String, String>>(header).getOrNull()
        val analyzeUrl = AnalyzeUrl(
            mUrl = urlStr,
            headerMapF = headerMap,
            source = _source as? BaseSourceInterface,
            ruleData = _ruleData,
            callTimeout = callTimeout
        )
        return kotlin.runCatching {
            analyzeUrl.getStrResponse()
        }.onFailure {
            log("connect($urlStr,$header) error: ${it.localizedMessage}")
        }.getOrElse {
            StrResponse(analyzeUrl.url, it.stackTraceToString())
        }
    }

    override fun get(urlStr: String, headers: Map<String, String>): Connection.Response =
        get(urlStr, headers, null)

    // 简化说明：委托 AnalyzeUrl，支持 URL 模板/Cookie/请求体编码/SSL信任(HttpHelper)/限流(ConcurrentRateLimiter)/followRedirects(false) | 已知上限：无协程取消检查 | 升级路径：接入协程上下文
    override fun get(urlStr: String, headers: Map<String, String>, timeout: Int?): Connection.Response {
        val requestHeaders = if ((_source as? BaseSourceInterface)?.enabledCookieJar == true) {
            headers.toMutableMap().apply { put(cookieJarHeader, "1") }
        } else headers
        val rateLimiter = ConcurrentRateLimiter(_source as? BaseSourceInterface)
        return rateLimiter.withLimitBlocking {
            kotlin.runCatching {
                val urlWithOptions = "$urlStr,{\"followRedirects\":false}"
                val analyzeUrl = AnalyzeUrl(
                    mUrl = urlWithOptions,
                    headerMapF = requestHeaders,
                    source = _source as? BaseSourceInterface,
                    ruleData = _ruleData,
                    callTimeout = timeout?.toLong()
                )
                JsoupResponseAdapter(urlStr, Connection.Method.GET, analyzeUrl.getStrResponse())
            }.onFailure {
                log("get($urlStr) error: ${it.localizedMessage}")
            }.getOrElse {
                JsoupResponseAdapter(urlStr, Connection.Method.GET, StrResponse(urlStr, it.stackTraceToString()))
            }
        }
    }

    override fun head(urlStr: String, headers: Map<String, String>): Connection.Response =
        head(urlStr, headers, null)

    // 简化说明：委托 AnalyzeUrl，通过 URL 选项设置 HEAD 方法，支持 URL 模板/Cookie/请求体编码/SSL信任(HttpHelper)/限流(ConcurrentRateLimiter)/followRedirects(false) | 已知上限：无协程取消检查 | 升级路径：接入协程上下文
    override fun head(urlStr: String, headers: Map<String, String>, timeout: Int?): Connection.Response {
        val requestHeaders = if ((_source as? BaseSourceInterface)?.enabledCookieJar == true) {
            headers.toMutableMap().apply { put(cookieJarHeader, "1") }
        } else headers
        val rateLimiter = ConcurrentRateLimiter(_source as? BaseSourceInterface)
        return rateLimiter.withLimitBlocking {
            kotlin.runCatching {
                val urlWithOptions = "$urlStr,{\"method\":\"HEAD\",\"followRedirects\":false}"
                val analyzeUrl = AnalyzeUrl(
                    mUrl = urlWithOptions,
                    headerMapF = requestHeaders,
                    source = _source as? BaseSourceInterface,
                    ruleData = _ruleData,
                    callTimeout = timeout?.toLong()
                )
                JsoupResponseAdapter(urlStr, Connection.Method.HEAD, analyzeUrl.getStrResponse())
            }.onFailure {
                log("head($urlStr) error: ${it.localizedMessage}")
            }.getOrElse {
                JsoupResponseAdapter(urlStr, Connection.Method.HEAD, StrResponse(urlStr, it.stackTraceToString()))
            }
        }
    }

    override fun post(urlStr: String, body: String, headers: Map<String, String>): Connection.Response =
        post(urlStr, body, headers, null)

    // 简化说明：委托 AnalyzeUrl，通过 URL 选项设置 POST 方法和请求体，支持 URL 模板/Cookie/请求体编码/SSL信任(HttpHelper)/限流(ConcurrentRateLimiter)/followRedirects(false) | 已知上限：无协程取消检查 | 升级路径：接入协程上下文
    override fun post(urlStr: String, body: String, headers: Map<String, String>, timeout: Int?): Connection.Response {
        val requestHeaders = if ((_source as? BaseSourceInterface)?.enabledCookieJar == true) {
            headers.toMutableMap().apply { put(cookieJarHeader, "1") }
        } else headers
        val rateLimiter = ConcurrentRateLimiter(_source as? BaseSourceInterface)
        return rateLimiter.withLimitBlocking {
            kotlin.runCatching {
                val urlOption = mapOf("method" to "POST", "body" to body, "followRedirects" to false)
                val urlWithOptions = "$urlStr,${GSON.toJson(urlOption)}"
                val analyzeUrl = AnalyzeUrl(
                    mUrl = urlWithOptions,
                    headerMapF = requestHeaders,
                    source = _source as? BaseSourceInterface,
                    ruleData = _ruleData,
                    callTimeout = timeout?.toLong()
                )
                JsoupResponseAdapter(urlStr, Connection.Method.POST, analyzeUrl.getStrResponse())
            }.onFailure {
                log("post($urlStr) error: ${it.localizedMessage}")
            }.getOrElse {
                JsoupResponseAdapter(urlStr, Connection.Method.POST, StrResponse(urlStr, it.stackTraceToString()))
            }
        }
    }

    // ==================== WebView 方法（抛出 WebViewRequiredException，由 Python 客户端 Selenium 委托）====================

    override fun webView(html: String?, url: String?, js: String?): String? = webView(html, url, js, false)

    // 简化说明：JVM 无法执行 WebView，抛出 WebViewRequiredException 携带请求信息 | 已知上限：无法执行 JS 渲染 | 升级路径：Python 客户端 Selenium 委托
    override fun webView(html: String?, url: String?, js: String?, cacheFirst: Boolean): String? {
        val targetUrl = url ?: return html
        throw WebViewRequiredException(
            stage = "js_webView",
            requests = listOf(WebViewRequest(
                url = targetUrl,
                html = html,
                js = js,
                sourceRegex = null,
                type = "load"
            )),
            message = "JS 调用 webView() 需要渲染: url=$targetUrl"
        )
    }

    override fun webViewGetSource(html: String?, url: String?, js: String?, sourceRegex: String): String? =
        webViewGetSource(html, url, js, sourceRegex, false, 0)

    override fun webViewGetSource(html: String?, url: String?, js: String?, sourceRegex: String, cacheFirst: Boolean): String? =
        webViewGetSource(html, url, js, sourceRegex, cacheFirst, 0)

    // 简化说明：JVM 无法嗅探资源，抛出 WebViewRequiredException | 已知上限：无法监听网络请求 | 升级路径：Python 客户端 Selenium CDP 委托
    override fun webViewGetSource(
        html: String?,
        url: String?,
        js: String?,
        sourceRegex: String,
        cacheFirst: Boolean,
        delayTime: Long
    ): String? {
        val targetUrl = url ?: return html
        throw WebViewRequiredException(
            stage = "js_webViewGetSource",
            requests = listOf(WebViewRequest(
                url = targetUrl,
                html = html,
                js = js,
                sourceRegex = sourceRegex,
                type = "sniff"
            )),
            message = "JS 调用 webViewGetSource() 需要嗅探资源: url=$targetUrl, regex=$sourceRegex"
        )
    }

    override fun webViewGetOverrideUrl(html: String?, url: String?, js: String?, overrideUrlRegex: String): String? =
        webViewGetOverrideUrl(html, url, js, overrideUrlRegex, false, 0)

    override fun webViewGetOverrideUrl(html: String?, url: String?, js: String?, overrideUrlRegex: String, cacheFirst: Boolean): String? =
        webViewGetOverrideUrl(html, url, js, overrideUrlRegex, cacheFirst, 0)

    // 简化说明：JVM 无法检测跳转，抛出 WebViewRequiredException | 已知上限：无法检测跳转 | 升级路径：Python 客户端 Selenium 委托
    override fun webViewGetOverrideUrl(
        html: String?,
        url: String?,
        js: String?,
        overrideUrlRegex: String,
        cacheFirst: Boolean,
        delayTime: Long
    ): String? {
        val targetUrl = url ?: return html
        throw WebViewRequiredException(
            stage = "js_webViewGetOverrideUrl",
            requests = listOf(WebViewRequest(
                url = targetUrl,
                html = html,
                js = js,
                sourceRegex = overrideUrlRegex,
                type = "overrideUrl"
            )),
            message = "JS 调用 webViewGetOverrideUrl() 需要检测跳转: url=$targetUrl, regex=$overrideUrlRegex"
        )
    }

    // ==================== UI 方法（抛出 UserInterventionException，标记需用户介入）====================

    override fun openVideoPlayer(url: String, title: String) = openVideoPlayer(url, title, false)

    override fun openVideoPlayer(url: String, title: String, isFloat: Boolean) {
        throw UnsupportedOperationException("JVM 环境不支持 openVideoPlayer，需真机执行")
    }

    override fun startBrowser(url: String, title: String) = startBrowser(url, title, null)

    // 简化说明：JVM 无法打开浏览器，抛出 UserInterventionException | 已知上限：无法 UI 交互 | 升级路径：用户在 Legado App 中手动操作
    override fun startBrowser(url: String, title: String, html: String?) {
        throw UserInterventionException(
            stage = "login",
            message = "源需要登录/人工验证: url=$url, title=$title\n建议：在 Legado App 中手动登录后导出 Cookie"
        )
    }

    override fun startBrowserAwait(url: String, title: String): StrResponse =
        startBrowserAwait(url, title, true, null)

    override fun startBrowserAwait(url: String, title: String, refetchAfterSuccess: Boolean): StrResponse =
        startBrowserAwait(url, title, refetchAfterSuccess, null)

    // 简化说明：JVM 无法等待用户操作，抛出 UserInterventionException | 已知上限：无法 UI 交互 | 升级路径：用户在 Legado App 中手动操作
    override fun startBrowserAwait(url: String, title: String, refetchAfterSuccess: Boolean, html: String?): StrResponse {
        throw UserInterventionException(
            stage = "login",
            message = "源需要登录/人工验证: url=$url, title=$title\n建议：在 Legado App 中手动登录后导出 Cookie"
        )
    }

    // 简化说明：JVM 无法显示验证码图片，抛出 UserInterventionException | 已知上限：无法 UI 交互 | 升级路径：用户在 Legado App 中手动输入
    override fun getVerificationCode(imageUrl: String): String {
        throw UserInterventionException(
            stage = "verification",
            message = "源需要验证码: imageUrl=$imageUrl\n建议：在 Legado App 中手动输入验证码"
        )
    }

    // ==================== Cookie 方法 ====================

    override fun getCookie(tag: String): String = getCookie(tag, null)

    // 简化说明：委托 CookieStoreStub | 已知上限：内存存储，重启丢失 | 升级路径：持久化到文件
    override fun getCookie(tag: String, key: String?): String {
        return if (key != null) {
            CookieStoreStub.getKey(tag, key)
        } else {
            CookieStoreStub.getCookie(tag)
        }
    }

    // ==================== 文件方法（Stub 降级）====================

    // 简化说明：简化为 HTTP 下载或本地读取 | 已知上限：无缓存 | 升级路径：添加缓存
    // 修复说明: IllegalStateException 改为 NoStackTraceException，与真机 importScript 行为一致（真机用 NoStackTraceException 避免堆栈采集开销）
    override fun importScript(path: String): String {
        val result = when {
            path.startsWith("http") -> cacheFile(path)
            else -> readTxtFile(path)
        }
        if (result.isBlank()) throw NoStackTraceException("$path 内容获取失败或者为空")
        return result
    }

    override fun cacheFile(urlStr: String): String = cacheFile(urlStr, 0)

    // 简化说明：委托 CacheManagerStub | 已知上限：缓存不持久 | 升级路径：持久化缓存
    override fun cacheFile(urlStr: String, saveTime: Int): String {
        val key = md5Encode16(urlStr)
        val cachePath = CacheManagerStub.get(key)
        return if (cachePath.isNullOrBlank() || !getFile(cachePath).exists()) {
            val path = downloadFile(urlStr)
            log("首次下载 $urlStr >> $path")
            CacheManagerStub.put(key, path, saveTime)
            readTxtFile(path)
        } else {
            readTxtFile(cachePath)
        }
    }

    // 修复说明: 1) 用 analyzeUrl.type 替代 getSuffix(url)，与真机行为一致（真机优先用 analyzeUrl.type，回退到 UrlUtil.getSuffix）；2) 改用 analyzeUrl.getInputStream() 流式下载，避免大文件 OOM（真机用流式 copyTo）
    override fun downloadFile(url: String): String {
        val analyzeUrl = AnalyzeUrl(
            mUrl = url,
            source = _source as? BaseSourceInterface,
            ruleData = _ruleData
        )
        val type = analyzeUrl.type ?: getSuffix(url)
        val path = "${md5Encode16(url)}.$type"
        val file = getFile(path)
        file.delete()
        kotlin.runCatching {
            file.parentFile?.mkdirs()
            analyzeUrl.getInputStream().use { iStream ->
                file.outputStream().buffered().use { oStream ->
                    iStream.copyTo(oStream)
                }
            }
        }.getOrElse {
            file.delete()
            throw it
        }
        return path
    }

    @Deprecated("Deprecated", ReplaceWith("downloadFile(url)"))
    override fun downloadFile(content: String, url: String): String {
        // 简化说明：委托 AnalyzeUrl.type 获取文件类型 | 已知上限：无 ensureActive 协程取消检查 | 升级路径：接入协程上下文
        val type = AnalyzeUrl(
            mUrl = url,
            source = _source as? BaseSourceInterface,
            ruleData = _ruleData
        ).type ?: return ""
        val path = "${md5Encode16(url)}.$type"
        val file = getFile(path)
        file.parentFile?.mkdirs()
        HexUtil.decodeHex(content).let {
            if (it.isNotEmpty()) {
                file.writeBytes(it)
            }
        }
        return path
    }

    // 简化说明：使用临时目录替代 appCtx.externalCache | 已知上限：重启后文件丢失 | 升级路径：配置持久化目录
    override fun getFile(path: String): File {
        val aPath = if (path.startsWith(File.separator)) {
            cacheDir.absolutePath + path
        } else {
            cacheDir.absolutePath + File.separator + path
        }
        val file = File(aPath)
        val safePath = cacheDir.parentFile?.canonicalPath ?: cacheDir.canonicalPath
        if (!file.canonicalPath.startsWith(safePath)) {
            throw SecurityException("非法路径")
        }
        return file
    }

    override fun readFile(path: String): ByteArray? {
        val file = getFile(path)
        if (file.exists()) {
            return file.readBytes()
        }
        return null
    }

    override fun readTxtFile(path: String): String {
        val file = getFile(path)
        if (file.exists()) {
            val charsetName = EncodingDetect.getEncode(file)
            return String(file.readBytes(), charset(charsetName))
        }
        return ""
    }

    override fun readTxtFile(path: String, charsetName: String): String {
        val file = getFile(path)
        if (file.exists()) {
            return String(file.readBytes(), Charset.forName(charsetName))
        }
        return ""
    }

    override fun deleteFile(path: String): Boolean {
        val file = getFile(path)
        return file.deleteRecursively()
    }

    override fun unzipFile(zipPath: String): String = unArchiveFile(zipPath, "zip")

    // 简化说明：Rar/7z 解压暂不支持 | 已知上限：1-3% 源受影响 | 升级路径：集成 commons-compress
    override fun un7zFile(zipPath: String): String = unArchiveFile(zipPath, "7z")

    // 简化说明：Rar/7z 解压暂不支持 | 已知上限：1-3% 源受影响 | 升级路径：集成 commons-compress
    override fun unrarFile(zipPath: String): String = unArchiveFile(zipPath, "rar")

    // 简化说明：Rar/7z 解压暂不支持 | 已知上限：1-3% 源受影响 | 升级路径：集成 commons-compress
    override fun unArchiveFile(zipPath: String): String = unArchiveFile(zipPath, "unknown")

    private fun unArchiveFile(zipPath: String, archiveType: String): String {
        if (zipPath.isEmpty()) return ""
        if (archiveType != "zip") {
            log("⚠️ 降级: $archiveType 解压暂不支持, zipPath=$zipPath")
        }
        return ""
    }

    override fun getTxtInFolder(path: String): String {
        if (path.isEmpty()) return ""
        val folder = getFile(path)
        val contents = StringBuilder()
        folder.listFiles()?.let {
            for (f in it) {
                val charsetName = EncodingDetect.getEncode(f)
                contents.append(String(f.readBytes(), charset(charsetName))).append("\n")
            }
            if (contents.isNotEmpty()) contents.deleteCharAt(contents.length - 1)
        }
        // 修复说明: 添加 folder.delete()，与真机 getTxtInFolder 行为一致（真机用 FileUtils.delete 删除文件夹）
        folder.deleteRecursively()
        return contents.toString()
    }

    // ==================== 压缩方法 ====================

    override fun getZipStringContent(url: String, path: String): String {
        val byteArray = getZipByteArrayContent(url, path) ?: return ""
        val charsetName = EncodingDetect.getEncode(byteArray)
        return String(byteArray, Charset.forName(charsetName))
    }

    override fun getZipStringContent(url: String, path: String, charsetName: String): String {
        val byteArray = getZipByteArrayContent(url, path) ?: return ""
        return String(byteArray, Charset.forName(charsetName))
    }

    override fun getRarStringContent(url: String, path: String): String {
        val byteArray = getRarByteArrayContent(url, path) ?: return ""
        val charsetName = EncodingDetect.getEncode(byteArray)
        return String(byteArray, Charset.forName(charsetName))
    }

    override fun getRarStringContent(url: String, path: String, charsetName: String): String {
        val byteArray = getRarByteArrayContent(url, path) ?: return ""
        return String(byteArray, Charset.forName(charsetName))
    }

    override fun get7zStringContent(url: String, path: String): String {
        val byteArray = get7zByteArrayContent(url, path) ?: return ""
        val charsetName = EncodingDetect.getEncode(byteArray)
        return String(byteArray, Charset.forName(charsetName))
    }

    override fun get7zStringContent(url: String, path: String, charsetName: String): String {
        val byteArray = get7zByteArrayContent(url, path) ?: return ""
        return String(byteArray, Charset.forName(charsetName))
    }

    // 简化说明：委托 AnalyzeUrl.getByteArray() | 已知上限：无 ensureActive 协程取消检查 | 升级路径：接入协程上下文
    override fun getZipByteArrayContent(url: String, path: String): ByteArray? {
        val bytes = if (isAbsUrl(url)) {
            val analyzeUrl = AnalyzeUrl(
                mUrl = url,
                source = _source as? BaseSourceInterface,
                ruleData = _ruleData
            )
            analyzeUrl.getByteArray()
        } else {
            HexUtil.decodeHex(url)
        }
        val bos = ByteArrayOutputStream()
        ZipInputStream(ByteArrayInputStream(bytes)).use { zis ->
            var entry = zis.nextEntry
            while (entry != null) {
                if (entry.name == path) {
                    zis.copyTo(bos)
                    return bos.toByteArray()
                }
                entry = zis.nextEntry
            }
        }
        log("getZipContent 未发现内容")
        return null
    }

    // 简化说明：Rar/7z 解压暂不支持 | 已知上限：1-3% 源受影响 | 升级路径：集成 commons-compress
    override fun getRarByteArrayContent(url: String, path: String): ByteArray? {
        log("⚠️ 降级: Rar 解压暂不支持, url=$url, path=$path")
        return null
    }

    // 简化说明：Rar/7z 解压暂不支持 | 已知上限：1-3% 源受影响 | 升级路径：集成 commons-compress
    override fun get7zByteArrayContent(url: String, path: String): ByteArray? {
        log("⚠️ 降级: 7z 解压暂不支持, url=$url, path=$path")
        return null
    }

    // ==================== Base64 方法 ====================

    override fun base64Decode(str: String?): String {
        return Base64.decodeStr(str)
    }

    override fun base64Decode(str: String?, charset: String): String {
        return Base64.decodeStr(str, Charset.forName(charset))
    }

    // 简化说明：android.util.Base64 替换为 java.util.Base64 | 已知上限：flags 参数简化处理 | 升级路径：完整实现 flags 映射
    override fun base64Decode(str: String, flags: Int): String {
        return String(decodeBase64(str, flags))
    }

    override fun base64DecodeToByteArray(str: String?): ByteArray? {
        if (str.isNullOrBlank()) return null
        return decodeBase64(str, 0)
    }

    override fun base64DecodeToByteArray(str: String?, flags: Int): ByteArray? {
        if (str.isNullOrBlank()) return null
        return decodeBase64(str, flags)
    }

    override fun base64Encode(str: String): String? {
        return encodeBase64(str.toByteArray(), 2)
    }

    override fun base64Encode(str: String, flags: Int): String? {
        return encodeBase64(str.toByteArray(), flags)
    }

    // ==================== Hex 方法 ====================

    override fun hexDecodeToByteArray(hex: String): ByteArray? {
        return HexUtil.decodeHex(hex)
    }

    override fun hexDecodeToString(hex: String): String? {
        return HexUtil.decodeHexStr(hex)
    }

    override fun hexEncodeToString(utf8: String): String? {
        return HexUtil.encodeHexStr(utf8)
    }

    // ==================== 转换方法 ====================

    override fun strToBytes(str: String): ByteArray {
        return str.toByteArray(Charset.forName("UTF-8"))
    }

    override fun strToBytes(str: String, charset: String): ByteArray {
        return str.toByteArray(Charset.forName(charset))
    }

    override fun bytesToStr(bytes: ByteArray): String {
        return String(bytes, Charset.forName("UTF-8"))
    }

    override fun bytesToStr(bytes: ByteArray, charset: String): String {
        return String(bytes, Charset.forName(charset))
    }

    // ==================== 时间方法 ====================

    override fun timeFormatUTC(time: Long, format: String, sh: Int): String? {
        val utc = SimpleTimeZone(sh, "UTC")
        return SimpleDateFormat(format, Locale.getDefault()).run {
            timeZone = utc
            format(Date(time))
        }
    }

    // 修复说明: 使用 AppConst.dateFormat（读取 LEGADO_DATE_FORMAT 环境变量，默认 "yyyy/MM/dd HH:mm"），与真机 timeFormat 行为一致
    override fun timeFormat(time: Long): String {
        return AppConst.dateFormat.format(Date(time))
    }

    // ==================== 编码方法 ====================

    override fun encodeURI(str: String): String {
        return try {
            URLEncoder.encode(str, "UTF-8")
        } catch (e: Exception) {
            ""
        }
    }

    override fun encodeURI(str: String, enc: String): String {
        return try {
            URLEncoder.encode(str, enc)
        } catch (e: Exception) {
            ""
        }
    }

    override fun htmlFormat(str: String): String {
        return HtmlFormatter.formatKeepImg(str)
    }

    override fun t2s(text: String): String {
        return ChineseUtils.t2s(text)
    }

    override fun s2t(text: String): String {
        return ChineseUtils.s2t(text)
    }

    // ==================== 字体方法 ====================

    @Deprecated("Deprecated", ReplaceWith("queryTTF(data)"))
    override fun queryBase64TTF(data: String?): QueryTTF? {
        log("queryBase64TTF(String)方法已过时,并将在未来删除；请使用queryTTF(Any)替代")
        return queryTTF(data)
    }

    @OptIn(ExperimentalStdlibApi::class)
    override fun queryTTF(data: Any?, useCache: Boolean): QueryTTF? {
        // 简化说明：AppCacheManager 替换为 CacheManagerStub | 已知上限：缓存不持久 | 升级路径：持久化缓存
        try {
            var key: String? = null
            var qTTF: QueryTTF?
            when (data) {
                is String -> {
                    if (useCache) {
                        key = MessageDigest.getInstance("SHA-256").digest(data.toByteArray())
                            .toHexString()
                        qTTF = CacheManagerStub.getQueryTTF(key)
                        if (qTTF != null) return qTTF
                    }
                    val font: ByteArray? = when {
                        isAbsUrl(data) -> {
                            // 简化说明：委托 AnalyzeUrl.getByteArray() | 已知上限：无 ensureActive 协程取消检查 | 升级路径：接入协程上下文
                            val analyzeUrl = AnalyzeUrl(
                                mUrl = data,
                                source = _source as? BaseSourceInterface,
                                ruleData = _ruleData
                            )
                            analyzeUrl.getByteArray()
                        }
                        else -> base64DecodeToByteArray(data)
                    }
                    font ?: return null
                    qTTF = QueryTTF(font)
                }
                is ByteArray -> {
                    if (useCache) {
                        key = MessageDigest.getInstance("SHA-256").digest(data).toHexString()
                        qTTF = CacheManagerStub.getQueryTTF(key)
                        if (qTTF != null) return qTTF
                    }
                    qTTF = QueryTTF(data)
                }
                else -> return null
            }
            if (key != null) CacheManagerStub.put(key, qTTF)
            return qTTF
        } catch (e: Exception) {
            log("[queryTTF] 获取字体处理类出错: ${e.localizedMessage}")
            throw e
        }
    }

    override fun queryTTF(data: Any?): QueryTTF? {
        return queryTTF(data, true)
    }

    // 简化说明：replaceFont 多字节字符未完整实现 | 已知上限：<1% 源受影响 | 升级路径：完整 Base64 解码 + 字体映射表
    override fun replaceFont(
        text: String,
        errorQueryTTF: QueryTTF?,
        correctQueryTTF: QueryTTF?,
        filter: Boolean
    ): String {
        if (errorQueryTTF == null || correctQueryTTF == null) return text
        val contentArray = text.toCharArray().map { it.toString() }.toMutableList()
        val intArray = IntArray(1)
        contentArray.forEachIndexed { index, s ->
            val oldCode = s.codePointAt(0)
            if (errorQueryTTF.isBlankUnicode(oldCode)) {
                return@forEachIndexed
            }
            var glyf = errorQueryTTF.getGlyfByUnicode(oldCode)
            if (errorQueryTTF.getGlyfIdByUnicode(oldCode) == 0) glyf = null
            if (filter && glyf == null) {
                contentArray[index] = ""
                return@forEachIndexed
            }
            val code = correctQueryTTF.getUnicodeByGlyf(glyf)
            if (code != 0) {
                intArray[0] = code
                contentArray[index] = String(intArray, 0, 1)
            }
        }
        return contentArray.joinToString("")
    }

    override fun replaceFont(
        text: String,
        errorQueryTTF: QueryTTF?,
        correctQueryTTF: QueryTTF?
    ): String {
        return replaceFont(text, errorQueryTTF, correctQueryTTF, false)
    }

    // ==================== 工具方法 ====================

    // 修复说明: 移植 AppPattern.titleNumPattern + StringUtils.stringToInt，与真机 toNumChapter 行为一致（将"第X章"中的中文数字转为阿拉伯数字）
    override fun toNumChapter(s: String?): String? {
        s ?: return null
        val matcher = AppPattern.titleNumPattern.matcher(s)
        if (matcher.find()) {
            val intStr = StringUtils.stringToInt(matcher.group(2))
            return "${matcher.group(1)}${intStr}${matcher.group(3)}"
        }
        return s
    }

    override fun toURL(urlStr: String): JsURL {
        return JsURL(urlStr)
    }

    override fun toURL(url: String, baseUrl: String?): JsURL {
        return JsURL(url, baseUrl)
    }

    // 简化说明：Toast 降级为 stdout | 已知上限：无 UI 提示 | 升级路径：集成 GUI 框架
    override fun toast(msg: Any?) {
        println("${getTag()}: $msg")
    }

    override fun longToast(msg: Any?) {
        println("${getTag()}: $msg")
    }

    // 修复说明: 接入 Debug 回调 + 写入日志文件，与真机 log 行为一致（真机调用 Debug.log(sourceUrl, msg) + AppLog.putDebug）
    override fun log(msg: Any?): Any? {
        val sourceKey = (_source as? BaseSourceInterface)?.getKey()
        if (sourceKey != null) {
            Debug.log(sourceKey, msg.toString())
        } else {
            Debug.log(msg.toString())
        }
        return msg
    }

    override fun logType(any: Any?) {
        if (any == null) {
            log("null")
        } else {
            log(any.javaClass.name)
        }
    }

    override fun randomUUID(): String {
        return UUID.randomUUID().toString()
    }

    override fun androidId(): String {
        return System.getenv("LEGADO_ANDROID_ID") ?: "000000000000000"
    }

    // 简化说明：WebSettings 不可用，返回固定 UA | 已知上限：UA 不随设备变化 | 升级路径：从配置中读取
    override fun getWebViewUA(): String {
        return "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    }

    // ==================== UI/Url 方法（不可用）====================

    override fun openUrl(url: String) = openUrl(url, null)

    override fun openUrl(url: String, mimeType: String?) {
        throw UnsupportedOperationException("JVM 环境不支持 openUrl，需真机执行")
    }

    // ==================== 配置方法（Stub 降级）====================

    // 简化说明：ReadBookConfig 不可用，返回空 JSON | 已知上限：无配置 | 升级路径：从配置文件读取
    override fun getReadBookConfig(): String {
        return "{}"
    }

    override fun getReadBookConfigMap(): Map<String, Any> {
        return emptyMap()
    }

    // 简化说明：AppConfig 不可用，返回默认值 | 已知上限：无主题 | 升级路径：从配置中读取
    override fun getThemeMode(): String {
        return "0"
    }

    // 简化说明：ThemeConfig 不可用，返回空 JSON | 已知上限：无主题 | 升级路径：从配置中读取
    override fun getThemeConfig(): String {
        return "{}"
    }

    override fun getThemeConfigMap(): Map<String, Any?> {
        return emptyMap()
    }

    // ==================== JsEncodeUtils 继承方法 ====================

    // ----- MD5 -----

    override fun md5Encode(str: String): String {
        return DigestUtil.md5Hex(str)
    }

    override fun md5Encode16(str: String): String {
        var reStr = md5Encode(str)
        return reStr.substring(8, 24)
    }

    // ----- 对称加密 -----

    // 简化说明：SymmetricCryptoAndroid 替换为 hutool SymmetricCrypto | 已知上限：encryptBase64 编码方式可能不同 | 升级路径：创建 SymmetricCryptoJvm 适配类
    override fun createSymmetricCrypto(transformation: String, key: ByteArray?, iv: ByteArray?): SymmetricCrypto {
        val crypto = SymmetricCrypto(transformation, key)
        return if (iv != null && iv.isNotEmpty()) crypto.setIv(iv) else crypto
    }

    override fun createSymmetricCrypto(transformation: String, key: ByteArray): SymmetricCrypto {
        return createSymmetricCrypto(transformation, key, null)
    }

    override fun createSymmetricCrypto(transformation: String, key: String): SymmetricCrypto {
        return createSymmetricCrypto(transformation, key, null)
    }

    override fun createSymmetricCrypto(transformation: String, key: String, iv: String?): SymmetricCrypto {
        return createSymmetricCrypto(transformation, key.encodeToByteArray(), iv?.encodeToByteArray())
    }

    // ----- 非对称加密 -----

    override fun createAsymmetricCrypto(transformation: String): AsymmetricCrypto {
        return AsymmetricCrypto(transformation)
    }

    // ----- 签名 -----

    override fun createSign(algorithm: String): Sign {
        return Sign(algorithm)
    }

    // ----- AES -----

    @Deprecated("过于繁琐弃用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decrypt(str)"))
    override fun aesDecodeToByteArray(str: String, key: String, transformation: String, iv: String): ByteArray? {
        return createSymmetricCrypto(transformation, key, iv).decrypt(str)
    }

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decryptStr(str)"))
    override fun aesDecodeToString(str: String, key: String, transformation: String, iv: String): String? {
        return createSymmetricCrypto(transformation, key, iv).decryptStr(str)
    }

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decryptStr(data)"))
    override fun aesDecodeArgsBase64Str(data: String, key: String, mode: String, padding: String, iv: String): String? {
        // 修复说明: 使用 mapBase64Flags(Base64.NO_WRAP=2) 解码 key 和 iv，与真机 Base64.decode(key, Base64.NO_WRAP) 行为一致
        val codec = mapBase64Flags(2)
        return createSymmetricCrypto(
            "AES/${mode}/${padding}",
            codec.decoder.decode(key),
            codec.decoder.decode(iv)
        ).decryptStr(data)
    }

    @Deprecated("过于繁琐弃用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decrypt(str)"))
    override fun aesBase64DecodeToByteArray(str: String, key: String, transformation: String, iv: String): ByteArray? {
        return createSymmetricCrypto(transformation, key, iv).decrypt(str)
    }

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decryptStr(str)"))
    override fun aesBase64DecodeToString(str: String, key: String, transformation: String, iv: String): String? {
        return createSymmetricCrypto(transformation, key, iv).decryptStr(str)
    }

    @Deprecated("过于繁琐弃用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decrypt(data)"))
    override fun aesEncodeToByteArray(data: String, key: String, transformation: String, iv: String): ByteArray? {
        return createSymmetricCrypto(transformation, key, iv).encrypt(data)
    }

    // 修复说明: 反向引入真机 bug（真机 JsEncodeUtils.kt L226 误用 decryptStr，加密方法调用了解密），与真机行为保持一致；书源可能依赖此 bug 行为
    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decryptStr(data)"))
    override fun aesEncodeToString(data: String, key: String, transformation: String, iv: String): String? {
        return createSymmetricCrypto(transformation, key, iv).decryptStr(data)
    }

    @Deprecated("过于繁琐弃用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).encryptBase64(data).toByteArray()"))
    override fun aesEncodeToBase64ByteArray(data: String, key: String, transformation: String, iv: String): ByteArray? {
        return createSymmetricCrypto(transformation, key, iv).encryptBase64(data).toByteArray()
    }

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).encryptBase64(data)"))
    override fun aesEncodeToBase64String(data: String, key: String, transformation: String, iv: String): String? {
        return createSymmetricCrypto(transformation, key, iv).encryptBase64(data)
    }

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).encryptBase64(data)"))
    override fun aesEncodeArgsBase64Str(data: String, key: String, mode: String, padding: String, iv: String): String? {
        return createSymmetricCrypto("AES/${mode}/${padding}", key, iv).encryptBase64(data)
    }

    // ----- DES -----

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decryptStr(data)"))
    override fun desDecodeToString(data: String, key: String, transformation: String, iv: String): String? {
        return createSymmetricCrypto(transformation, key, iv).decryptStr(data)
    }

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decryptStr(data)"))
    override fun desBase64DecodeToString(data: String, key: String, transformation: String, iv: String): String? {
        return createSymmetricCrypto(transformation, key, iv).decryptStr(data)
    }

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).encrypt(data)"))
    override fun desEncodeToString(data: String, key: String, transformation: String, iv: String): String? {
        return String(createSymmetricCrypto(transformation, key, iv).encrypt(data))
    }

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).encryptBase64(data)"))
    override fun desEncodeToBase64String(data: String, key: String, transformation: String, iv: String): String? {
        return createSymmetricCrypto(transformation, key, iv).encryptBase64(data)
    }

    // ----- 3DES -----

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decryptStr(data)"))
    override fun tripleDESDecodeStr(data: String, key: String, mode: String, padding: String, iv: String): String? {
        return createSymmetricCrypto("DESede/${mode}/${padding}", key, iv).decryptStr(data)
    }

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).decryptStr(data)"))
    override fun tripleDESDecodeArgsBase64Str(data: String, key: String, mode: String, padding: String, iv: String): String? {
        // 修复说明: 使用 mapBase64Flags(Base64.NO_WRAP=2) 解码 key，与真机 Base64.decode(key, Base64.NO_WRAP) 行为一致
        return createSymmetricCrypto(
            "DESede/${mode}/${padding}",
            mapBase64Flags(2).decoder.decode(key),
            iv.encodeToByteArray()
        ).decryptStr(data)
    }

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).encryptBase64(data)"))
    override fun tripleDESEncodeBase64Str(data: String, key: String, mode: String, padding: String, iv: String): String? {
        return createSymmetricCrypto("DESede/${mode}/${padding}", key, iv).encryptBase64(data)
    }

    @Deprecated("过于繁琐弃用,但是web需要调用", ReplaceWith("createSymmetricCrypto(transformation, key, iv).encryptBase64(data)"))
    override fun tripleDESEncodeArgsBase64Str(data: String, key: String, mode: String, padding: String, iv: String): String? {
        // 修复说明: 使用 mapBase64Flags(Base64.NO_WRAP=2) 解码 key，与真机 Base64.decode(key, Base64.NO_WRAP) 行为一致
        return createSymmetricCrypto(
            "DESede/${mode}/${padding}",
            mapBase64Flags(2).decoder.decode(key),
            iv.encodeToByteArray()
        ).encryptBase64(data)
    }

    // ----- 摘要/HMac -----

    override fun digestHex(data: String, algorithm: String): String {
        return DigestUtil.digester(algorithm).digestHex(data)
    }

    // 修复说明: 使用 mapBase64Flags(Base64.NO_WRAP=2) 编码摘要，与真机 Base64.encodeToString(data, Base64.NO_WRAP) 行为一致
    override fun digestBase64Str(data: String, algorithm: String): String {
        return mapBase64Flags(2).encoder.encodeToString(DigestUtil.digester(algorithm).digest(data))
    }

    @Suppress("FunctionName")
    override fun HMacHex(data: String, algorithm: String, key: String): String {
        return HMac(algorithm, key.toByteArray()).digestHex(data)
    }

    @Suppress("FunctionName")
    override fun HMacBase64(data: String, algorithm: String, key: String): String {
        // 修复说明: 使用 mapBase64Flags(Base64.NO_WRAP=2) 编码 HMac，与真机 Base64.encodeToString(data, Base64.NO_WRAP) 行为一致
        return mapBase64Flags(2).encoder.encodeToString(HMac(algorithm, key.toByteArray()).digest(data))
    }

    // 简化说明：包装 StrResponse 为 jsoup Connection.Response，只读适配器 | 已知上限：setter 方法抛 UnsupportedOperationException | 升级路径：实现可变 Response
    private class JsoupResponseAdapter(
        private val urlStr: String,
        private val method: Connection.Method,
        private val strResponse: StrResponse
    ) : Connection.Response {

        override fun statusCode(): Int = strResponse.code()

        override fun statusMessage(): String = strResponse.message()

        override fun charset(): String =
            strResponse.headers()["Content-Type"]?.substringAfter("charset=", "")?.trim()
                ?.ifBlank { null } ?: "UTF-8"

        override fun charset(charset: String): Connection.Response = throw UnsupportedOperationException("Read-only adapter")

        override fun body(): String = strResponse.body ?: ""

        override fun parse(): org.jsoup.nodes.Document = Jsoup.parse(body())

        override fun contentType(): String? = strResponse.headers()["Content-Type"]

        override fun bodyAsBytes(): ByteArray = body().toByteArray()

        override fun bufferUp(): Connection.Response = this

        override fun bodyStream(): java.io.BufferedInputStream =
            java.io.BufferedInputStream(java.io.ByteArrayInputStream(bodyAsBytes()))

        override fun url(): java.net.URL = java.net.URL(urlStr)

        override fun method(): Connection.Method = method

        override fun url(url: java.net.URL): Connection.Response = throw UnsupportedOperationException("Read-only adapter")

        override fun method(method: Connection.Method): Connection.Response = throw UnsupportedOperationException("Read-only adapter")

        override fun header(name: String): String? = strResponse.headers()[name]

        override fun headers(name: String): List<String> = strResponse.headers().values(name)

        override fun headers(): Map<String, String> =
            strResponse.headers().names().associateWith { strResponse.headers()[it] ?: "" }

        override fun multiHeaders(): Map<String, List<String>> = strResponse.headers().toMultimap()

        override fun header(name: String, value: String): Connection.Response = throw UnsupportedOperationException("Read-only adapter")

        override fun addHeader(name: String, value: String): Connection.Response = throw UnsupportedOperationException("Read-only adapter")

        override fun removeHeader(name: String): Connection.Response = throw UnsupportedOperationException("Read-only adapter")

        override fun hasHeader(name: String): Boolean = strResponse.headers()[name] != null

        override fun hasHeaderWithValue(name: String, value: String): Boolean = strResponse.headers()[name] == value

        override fun cookies(): Map<String, String> {
            val cookies = mutableMapOf<String, String>()
            strResponse.headers().values("Set-Cookie").forEach { setCookie ->
                // 解析 Set-Cookie: name=value; Path=/; ...
                val parts = setCookie.split(";")
                if (parts.isNotEmpty()) {
                    val nameValue = parts[0].trim().split("=", limit = 2)
                    if (nameValue.size == 2) {
                        cookies[nameValue[0].trim()] = nameValue[1].trim()
                    }
                }
            }
            return cookies
        }

        override fun cookie(name: String): String? = null

        override fun cookie(name: String, value: String): Connection.Response = throw UnsupportedOperationException("Read-only adapter")

        override fun removeCookie(name: String): Connection.Response = throw UnsupportedOperationException("Read-only adapter")

        override fun hasCookie(name: String): Boolean = false
    }

    // ==================== 私有辅助方法 ====================

    private fun isAbsUrl(str: String): Boolean {
        return str.startsWith("http://") || str.startsWith("https://")
    }

    private fun getSuffix(url: String): String {
        return url.substringAfterLast(".", "txt").substringBefore("?").lowercase()
    }

    // android.util.Base64 flags: NO_PADDING=1, NO_WRAP=2, CRLF=4, URL_SAFE=8
    // 修复说明: 新建 mapBase64Flags 统一映射 android.util.Base64 flags 到 java.util.Base64，供 decodeBase64/encodeBase64 和 AES/摘要方法共用
    /**
     * android.util.Base64 flags 到 java.util.Base64 的映射
     * android.util.Base64 flags: DEFAULT=0, NO_PADDING=1, NO_WRAP=2, CRLF=4, URL_SAFE=8
     * java.util.Base64 对应: URL_SAFE→getUrlEncoder/Decoder, CRLF→getMimeEncoder/Decoder, NO_PADDING→withoutPadding, NO_WRAP→默认无换行
     */
    private data class Base64Mapping(
        val encoder: java.util.Base64.Encoder,
        val decoder: java.util.Base64.Decoder
    )

    private fun mapBase64Flags(flags: Int): Base64Mapping {
        val encoder = when {
            flags and 8 != 0 -> java.util.Base64.getUrlEncoder()
            flags and 4 != 0 -> java.util.Base64.getMimeEncoder()
            else -> java.util.Base64.getEncoder()
        }
        val decoder = when {
            flags and 8 != 0 -> java.util.Base64.getUrlDecoder()
            flags and 4 != 0 -> java.util.Base64.getMimeDecoder()
            else -> java.util.Base64.getDecoder()
        }
        val finalEncoder = if (flags and 1 != 0) encoder.withoutPadding() else encoder
        return Base64Mapping(finalEncoder, decoder)
    }

    private fun decodeBase64(str: String, flags: Int): ByteArray {
        return mapBase64Flags(flags).decoder.decode(str)
    }

    private fun encodeBase64(bytes: ByteArray, flags: Int): String {
        return mapBase64Flags(flags).encoder.encodeToString(bytes)
    }

}
