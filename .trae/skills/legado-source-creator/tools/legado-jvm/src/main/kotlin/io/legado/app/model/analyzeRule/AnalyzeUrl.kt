package io.legado.app.model.analyzeRule

import cn.hutool.core.codec.PercentCodec
import cn.hutool.core.net.RFC3986
import cn.hutool.core.util.HexUtil
import com.script.buildScriptBindings
import com.script.rhino.RhinoScriptEngine
import com.script.rhino.runScriptWithContext
import io.legado.app.constant.AppConst.UA_NAME
import io.legado.app.constant.AppPattern
import io.legado.app.data.entities.BaseSourceInterface
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookChapter
import io.legado.app.help.CacheManagerStub
import io.legado.app.help.ConcurrentRateLimiter
import io.legado.app.help.JsExtensionsInterface
import io.legado.app.help.JsExtensionsStub
import io.legado.app.help.config.AppConfig
import io.legado.app.help.http.BackstageWebView
import io.legado.app.help.http.CookieManager
import io.legado.app.help.http.CookieManager.mergeCookies
import io.legado.app.help.http.CookieStoreStub
import io.legado.app.help.http.RequestMethod
import io.legado.app.help.http.StrResponse
import io.legado.app.help.http.addHeaders
import io.legado.app.help.http.get
import io.legado.app.help.http.getProxyClient
import io.legado.app.help.http.newCallResponse
import io.legado.app.help.http.newCallStrResponse
import io.legado.app.help.http.postForm
import io.legado.app.help.http.postJson
import io.legado.app.help.http.postMultipart
import io.legado.app.help.source.getShareScope
import io.legado.app.model.Debug
import io.legado.app.utils.EncoderUtils
import io.legado.app.utils.GSON
import io.legado.app.utils.GSONStrict
import io.legado.app.utils.NetworkUtilsStub
import io.legado.app.utils.fromJsonArray
import io.legado.app.utils.fromJsonObject
import io.legado.app.utils.get
import io.legado.app.utils.isJson
import io.legado.app.utils.isJsonArray
import io.legado.app.utils.isJsonObject
import io.legado.app.utils.isXml
import io.legado.app.utils.parseIpsFromString
import io.legado.app.utils.stackTraceStr
import kotlinx.coroutines.runBlocking
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import okhttp3.Dns
import okhttp3.Request
import okhttp3.ResponseBody.Companion.toResponseBody
import java.io.ByteArrayInputStream
import java.io.InputStream
import java.net.URLEncoder
import java.nio.charset.Charset
import java.util.Base64
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit
import java.util.regex.Pattern
import kotlin.coroutines.ContinuationInterceptor
import kotlin.coroutines.CoroutineContext
import kotlin.coroutines.EmptyCoroutineContext
import kotlin.math.max

/**
 * Created by GKF on 2018/1/24.
 * 搜索URL规则解析
 */
// 简化说明: 从源码抽取，移除 Glide/ExoPlayer/Android 依赖，JsExtensions 通过委托实现 | 已知上限: WebView 降级抛异常、无限流 | 升级路径: 集成 Selenium、接入 ConcurrentRateLimiter
@Suppress("unused", "MemberVisibilityCanBePrivate")
class AnalyzeUrl(
    private val mUrl: String,
    private val key: String? = null,
    private val page: Int? = null,
    private val speakText: String? = null,
    private val speakSpeed: Int? = null,
    private var baseUrl: String = "",
    private val source: BaseSourceInterface? = null,
    private val ruleData: RuleDataInterface? = null,
    private val chapter: BookChapter? = null,
    private val readTimeout: Long? = null,
    private val callTimeout: Long? = null,
    private var coroutineContext: CoroutineContext = EmptyCoroutineContext,
    headerMapF: Map<String, String>? = null,
    hasLoginHeader: Boolean = true,
    private val infoMap: MutableMap<String, String>? = null
) : JsExtensionsInterface by (JsExtensionsStub.also { it.configure(source, ruleData ?: RuleData()) }) {
    constructor(mUrl: String) : this(mUrl, null)

    var ruleUrl = ""
        private set
    var url: String = ""
        private set
    var type: String? = null
        private set
    val headerMap = LinkedHashMap<String, String>()
    private var body: String? = null
    var urlNoQuery: String = ""
        private set
    private var encodedForm: String? = null
    private var encodedQuery: String? = null
    private var charset: String? = null
    private var method = RequestMethod.GET
    private var proxy: String? = null
    private var retry: Int = 0
    private var useWebView: Boolean = false
    private var webJs: String? = null
    private var bodyJs: String? = null
    private var dnsIp: String? = null
    private var followRedirects: Boolean? = null
    private val enabledCookieJar = source?.enabledCookieJar == true
    private val domain: String
    private var webViewDelayTime: Long = 0
    private val concurrentRateLimiter = ConcurrentRateLimiter(source)

    // 服务器ID
    var serverID: Long? = null
        private set

    // ajax防递归检查
    private var ajaxRecursionGuard = false

    /**
     * override ajax：委托AnalyzeUrl自身构造请求，而非走JsExtensionsStub.ajax(Jsoup.connect)
     * 简化说明：防递归+委托自身 | 已知上限：不支持callTimeout参数 | 升级路径：添加ajax(url, callTimeout) override
     */
    override fun ajax(url: Any): String? {
        val urlStr = if (url is List<*>) {
            url.firstOrNull().toString()
        } else {
            url.toString()
        }
        if (ajaxRecursionGuard) {
            return JsExtensionsStub.also { it.configure(source, ruleData ?: RuleData()) }.ajax(urlStr)
        }
        return try {
            ajaxRecursionGuard = true
            val analyzeUrl = AnalyzeUrl(urlStr, source = source, ruleData = ruleData, baseUrl = this.baseUrl)
            analyzeUrl.getStrResponse(useWebView = false).body
        } catch (e: Exception) {
            null
        } finally {
            ajaxRecursionGuard = false
        }
    }

    init {
        coroutineContext = coroutineContext.minusKey(ContinuationInterceptor)
        val urlMatcher = paramPattern.matcher(baseUrl)
        if (urlMatcher.find()) baseUrl = baseUrl.substring(0, urlMatcher.start())
        // 诊断日志: AnalyzeUrl初始化
        System.err.println("[DIAG] AnalyzeUrl init: baseUrl=${baseUrl.take(100)}, method=${method}, body=${body?.take(50)}")
        (headerMapF ?: runScriptWithContext(coroutineContext) {
            source?.getHeaderMap(hasLoginHeader)
        })?.let {
            headerMap.putAll(it)
            if (it.containsKey("proxy")) {
                proxy = it["proxy"]
                headerMap.remove("proxy")
            }
        }
        // 支持@js:和<js>头部规则，委托AnalyzeRule.evalJS执行
        // 简化说明：在init中创建AnalyzeRule执行JS头部 | 已知上限：ruleData可能为null，JS中book变量为空 | 升级路径：延迟到AnalyzeRule上下文完整后执行
        val jsHeaders = headerMap.entries.filter { it.value.startsWith("@js:") || it.value.contains("<js>") }
        if (jsHeaders.isNotEmpty()) {
            val analyzeRule = AnalyzeRule(ruleData, source)
            jsHeaders.forEach { (key, value) ->
                val jsCode = if (value.startsWith("@js:")) {
                    value.substringAfter("@js:").removeSuffix("</js>")
                } else {
                    value.substringAfter("<js>").removeSuffix("</js>")
                }
                analyzeRule.evalJS(jsCode)?.let { result ->
                    headerMap[key] = result.toString()
                }
            }
        }
        initUrl()
        domain = NetworkUtilsStub.getSubDomain(source?.getKey() ?: url)
    }

    /**
     * 处理url
     */
    fun initUrl() {
        ruleUrl = mUrl
        //执行@js,<js></js>
        analyzeJs()
        //替换参数
        replaceKeyPageJs()
        //处理URL
        analyzeUrl()
        // 诊断日志: URL处理结果
        System.err.println("[DIAG] initUrl结果: url=${url?.take(150)}, method=${method}, encodedForm=${encodedForm?.take(50)}")
    }

    /**
     * 执行@js,<js></js>
     */
    private fun analyzeJs() {
        var start = 0
        val jsMatcher = AppPattern.JS_PATTERN.matcher(ruleUrl)
        var result = ruleUrl
        while (jsMatcher.find()) {
            if (jsMatcher.start() > start) {
                ruleUrl.substring(start, jsMatcher.start()).trim().let {
                    if (it.isNotEmpty()) {
                        result = it.replace("@result", result)
                    }
                }
            }
            result = evalJS(jsMatcher.group(2) ?: jsMatcher.group(1), result).toString()
            start = jsMatcher.end()
        }
        if (ruleUrl.length > start) {
            ruleUrl.substring(start).trim().let {
                if (it.isNotEmpty()) {
                    result = it.replace("@result", result)
                }
            }
        }
        ruleUrl = result
    }

    /**
     * 替换关键字,页数,JS
     */
    private fun replaceKeyPageJs() { //先替换内嵌规则再替换页数规则，避免内嵌规则中存在大于小于号时，规则被切错
        //js
        if (ruleUrl.contains("{{") && ruleUrl.contains("}}")) {
            val analyze = RuleAnalyzer(ruleUrl) //创建解析
            //替换所有内嵌{{js}}
            val url = analyze.innerRule("{{", "}}") {
                val jsEval = evalJS(it) ?: ""
                when (jsEval) {
                    is String -> jsEval
                    is Double if jsEval % 1.0 == 0.0 -> String.format("%.0f", jsEval)
                    else -> jsEval.toString()
                }
            }
            if (url.isNotEmpty()) ruleUrl = url
        }
        //page
        page?.let {
            val matcher = pagePattern.matcher(ruleUrl)
            while (matcher.find()) {
                val pages = matcher.group(1)!!.split(",")
                ruleUrl = if (page < pages.size) { //pages[pages.size - 1]等同于pages.last()
                    ruleUrl.replace(matcher.group(), pages[page - 1].trim { it <= ' ' })
                } else {
                    ruleUrl.replace(matcher.group(), pages.last().trim { it <= ' ' })
                }
            }
        }
    }

    /**
     * 解析Url
     */
    private fun analyzeUrl() {
        //replaceKeyPageJs已经替换掉额外内容，此处url是基础形式，可以直接切首个','之前字符串。
        val urlMatcher = paramPattern.matcher(ruleUrl)
        val urlNoOption =
            if (urlMatcher.find()) ruleUrl.substring(0, urlMatcher.start()) else ruleUrl
        url = NetworkUtilsStub.getAbsoluteURL(baseUrl, urlNoOption)
        NetworkUtilsStub.getBaseUrl(url)?.let {
            baseUrl = it
        }
        if (urlNoOption.length != ruleUrl.length) {
            val urlOptionStr = ruleUrl.substring(urlMatcher.end())
            var urlOption = GSONStrict.fromJsonObject<UrlOption>(urlOptionStr).getOrNull()
            if (urlOption == null) {
                urlOption = GSON.fromJsonObject<UrlOption>(urlOptionStr).getOrNull()
                if (urlOption != null) {
                    log("链接参数 JSON 格式不规范，请改为规范格式")
                }
            }
            urlOption?.let { option ->
                option.getMethod()?.let {
                    method = when (it.uppercase()) {
                        "POST" -> RequestMethod.POST
                        "HEAD" -> RequestMethod.HEAD
                        else -> RequestMethod.GET
                    }
                }
                option.getHeaderMap()?.forEach { entry ->
                    headerMap[entry.key.toString()] = entry.value.toString()
                }
                option.getBody()?.let {
                    body = it
                }
                type = option.getType()
                charset = option.getCharset()
                retry = option.getRetry()
                useWebView = option.useWebView()
                webJs = option.getWebJs()
                bodyJs = option.getBodyJs()
                dnsIp = option.getDnsIp()
                followRedirects = option.getFollowRedirects()
                option.getJs()?.let { jsStr ->
                    evalJS(jsStr, url)?.toString()?.let {
                        url = it
                    }
                }
                serverID = option.getServerID()
                webViewDelayTime = max(0, option.getWebViewDelayTime() ?: 0)
            }
        }
        urlNoQuery = url
        when (method) {
            RequestMethod.POST -> body?.let {
                if (!it.isJson() && !it.isXml() && headerMap["Content-Type"].isNullOrEmpty()) {
                    analyzeFields(it)
                }
            }

            else -> {
                val pos = url.indexOf('?')
                if (pos != -1) {
                    analyzeQuery(url.substring(pos + 1))
                    urlNoQuery = url.substring(0, pos)
                }
            }
        }
    }

    /**
     * 解析QueryMap <key>=<value>
     * name=
     * name=name
     * name=<BASE64> eg name=bmFtZQ==
     */
    private fun analyzeFields(fieldsTxt: String) {
        encodedForm = encodeParams(fieldsTxt, charset, false)
    }

    private fun analyzeQuery(query: String) {
        encodedQuery = encodeParams(query, charset, true)
    }

    private fun encodeParams(params: String, charset: String?, isQuery: Boolean): String {
        val checkEncoded = charset.isNullOrEmpty()
        val charset = when {
            charset.isNullOrEmpty() -> Charsets.UTF_8
            charset == "escape" -> null
            else -> charset(charset)
        }
        if (isQuery && charset != null) {
            if (NetworkUtilsStub.encodedQuery(params)) {
                return params
            }
            return queryEncoder.encode(params, charset)
        }
        val len = params.length
        val sb = StringBuilder()
        var pos = 0
        while (pos <= len) {
            if (sb.isNotEmpty()) {
                sb.append("&")
            }
            var ampOffset = params.indexOf("&", pos)
            if (ampOffset == -1) {
                ampOffset = len
            }
            val eqOffset = params.indexOf("=", pos)
            val key: String
            val value: String?
            if (eqOffset == -1 || eqOffset > ampOffset) {
                key = params.substring(pos, ampOffset)
                value = null
            } else {
                key = params.substring(pos, eqOffset)
                value = params.substring(eqOffset + 1, ampOffset)
            }
            sb.appendEncoded(key, checkEncoded, charset)
            if (value != null) {
                sb.append("=")
                sb.appendEncoded(value, checkEncoded, charset)
            }
            pos = ampOffset + 1
        }
        return sb.toString()
    }

    private fun StringBuilder.appendEncoded(
        value: String,
        checkEncoded: Boolean,
        charset: Charset?
    ) {
        if (checkEncoded && NetworkUtilsStub.encodedForm(value)) {
            append(value)
        } else if (charset == null) {
            append(EncoderUtils.escape(value))
        } else {
            append(URLEncoder.encode(value, charset))
        }
    }


    /**
     * 执行JS
     */
    fun evalJS(jsStr: String, result: Any? = null): Any? {
        val bindings = buildScriptBindings { bindings ->
            bindings["java"] = this
            bindings["baseUrl"] = baseUrl
            bindings["cookie"] = CookieStoreStub
            bindings["cache"] = CacheManagerStub
            bindings["page"] = page
            bindings["key"] = key
            bindings["speakText"] = speakText
            bindings["speakSpeed"] = speakSpeed
            bindings["book"] = ruleData as? Book
            bindings["source"] = source
            bindings["result"] = result
            bindings["infoMap"] = infoMap
        }
        val sharedScope = source?.getShareScope(coroutineContext)
        val scope = if (sharedScope == null) {
            RhinoScriptEngine.getRuntimeScope(bindings)
        } else {
            bindings.apply {
                prototype = sharedScope
            }
        }
        val evalResult = RhinoScriptEngine.eval(jsStr, scope, coroutineContext)
        // 修复 NativeJavaObject 序列化 Bug：Rhino JS 返回 Java 对象时需要 unwrap
        val unwrappedResult = AnalyzeRule.unwrapRhinoResult(evalResult)
        return unwrappedResult
    }

    fun put(key: String, value: String): String {
        if (key == "bookName" || key == "title") {
            Debug.log("≡变量 $key 在特定情况下会被覆盖，建议使用其他键名")
        }
        chapter?.putVariable(key, value)
            ?: ruleData?.putVariable(key, value)
        return value
    }

    fun get(key: String): String {
        when (key) {
            "bookName" -> (ruleData as? Book)?.let {
                return it.name
            }

            "title" -> chapter?.let {
                return it.title
            }
        }
        return chapter?.getVariable(key)?.takeIf { it.isNotEmpty() }
            ?: ruleData?.getVariable(key)?.takeIf { it.isNotEmpty() }
            ?: ""
    }

    /**
     * 访问网站,返回StrResponse
     */
    suspend fun getStrResponseAwait(
        jsStr: String? = null,
        sourceRegex: String? = null,
        useWebView: Boolean = true,
        isTest: Boolean = false,
        skipRateLimit: Boolean = false
    ): StrResponse {
        if (type != null) {
            return StrResponse(url, HexUtil.encodeHexStr(getByteArrayAwait()))
        }
        if (skipRateLimit) {
            return executeStrRequest(jsStr, sourceRegex, useWebView, isTest)
        }
        concurrentRateLimiter.withLimit {
            return executeStrRequest(jsStr, sourceRegex, useWebView, isTest)
        }
    }

    private suspend fun executeStrRequest(
        jsStr: String? = null,
        sourceRegex: String? = null,
        useWebView: Boolean = true,
        isTest: Boolean = false
    ): StrResponse {
        setCookie()
        val startTime = System.currentTimeMillis()
        val strResponse: StrResponse
        try {
            if (this.useWebView && useWebView) {
                strResponse = when (method) {
                    RequestMethod.POST -> {
                        val res = getClient().newCallStrResponse(retry) {
                            addHeaders(headerMap)
                            url(urlNoQuery)
                            if (!encodedForm.isNullOrEmpty() || body.isNullOrBlank()) {
                                postForm(encodedForm ?: "")
                            } else {
                                postJson(body)
                            }
                        }
                        BackstageWebView(
                            url = res.url,
                            html = res.body,
                            tag = source?.getKey(),
                            javaScript = webJs ?: jsStr,
                            sourceRegex = sourceRegex,
                            headerMap = headerMap,
                            delayTime = webViewDelayTime
                        ).getStrResponse()
                    }

                    else -> BackstageWebView(
                        url = url,
                        tag = source?.getKey(),
                        javaScript = webJs ?: jsStr,
                        sourceRegex = sourceRegex,
                        headerMap = headerMap,
                        delayTime = webViewDelayTime
                    ).getStrResponse()
                }
            } else {
                strResponse = getClient().newCallStrResponse(retry) {
                    addHeaders(headerMap)
                    when (method) {
                        RequestMethod.POST -> {
                            url(urlNoQuery)
                            val contentType = headerMap["Content-Type"]
                            val body = body
                            if (!encodedForm.isNullOrEmpty() || body.isNullOrBlank()) {
                                postForm(encodedForm ?: "")
                            } else if (!contentType.isNullOrBlank()) {
                                val requestBody = body.toRequestBody(contentType.toMediaType())
                                post(requestBody)
                            } else {
                                postJson(body)
                            }
                        }

                        RequestMethod.HEAD -> {
                            get(urlNoQuery, encodedQuery)
                            head()
                        }

                        else -> get(urlNoQuery, encodedQuery)
                    }
                }.let {
                    val isXml = it.raw.body.contentType()?.toString()
                        ?.matches(AppPattern.xmlContentTypeRegex) == true
                    if (isXml && it.body?.trim()?.startsWith("<?xml", true) == false) {
                        StrResponse(it.raw, "<?xml version=\"1.0\"?>" + it.body)
                    } else if (bodyJs != null) {
                        val body = evalJS(bodyJs!!, it.body).toString()
                        StrResponse(it.raw, body)
                    } else it
                }
            }
            val connectionTime = System.currentTimeMillis() - startTime
            strResponse.putCallTime(connectionTime.toInt())
            return strResponse
        } catch (e: Exception) {
            if (!isTest) {
                throw e
            }
            val errorCode = when (e) {
                is java.net.SocketTimeoutException -> -2  // 超时错误
                is java.net.UnknownHostException -> -3   // 未找到域名
                is java.net.ConnectException -> -4       // 连接被拒绝
                is java.net.SocketException -> -5        // Socket错误（包括连接重置）
                is javax.net.ssl.SSLException -> -6      // SSL证书或握手错误
                is java.io.InterruptedIOException -> {
                    if (e.message?.contains("timeout") == true) {
                        -1  // 超过设定时间
                    } else -7
                }
                else -> -7  // 其它错误
            }
            return StrResponse(url, e.message).apply {
                putCallTime(errorCode)
            }
        }
    }

    @JvmOverloads
    fun getStrResponse(
        jsStr: String? = null,
        sourceRegex: String? = null,
        useWebView: Boolean = true,
    ): StrResponse {
        // 简化说明：runBlocking 桥接非suspend方法到suspend Await | 已知上限：阻塞调用线程 | 升级路径：调用方改为suspend
        return runBlocking(coroutineContext) {
            getStrResponseAwait(jsStr, sourceRegex, useWebView)
        }
    }

    /**
     * 访问网站,返回Response
     */
    suspend fun getResponseAwait(): Response {
        concurrentRateLimiter.withLimit {
            setCookie()
            val response = getClient().newCallResponse(retry) {
                addHeaders(headerMap)
                when (method) {
                    RequestMethod.POST -> {
                        url(urlNoQuery)
                        val contentType = headerMap["Content-Type"]
                        val body = body
                        if (!encodedForm.isNullOrEmpty() || body.isNullOrBlank()) {
                            postForm(encodedForm ?: "")
                        } else if (!contentType.isNullOrBlank()) {
                            val requestBody = body.toRequestBody(contentType.toMediaType())
                            post(requestBody)
                        } else {
                            postJson(body)
                        }
                    }

                    else -> get(urlNoQuery, encodedQuery)
                }
            }
            return response
        }
    }

    /**
     * 返回一个errResponse
     */
    fun getErrResponse(e: Throwable): Response = Response.Builder()
        .request(Request.Builder().url(url).build())
        .protocol(okhttp3.Protocol.HTTP_1_1)
        .code(500)
        .message(e.message ?: "Error Response")
        .body(e.stackTraceStr.toResponseBody(null))
        .build()

    /**
     * 返回一个errStrResponse
     */
    fun getErrStrResponse(e: Throwable): StrResponse =
        StrResponse(getErrResponse(e), e.stackTraceStr)

    private fun getClient(): OkHttpClient {
        val client = getProxyClient(proxy)
        if (readTimeout == null && callTimeout == null && dnsIp == null && followRedirects == null) {
            return client
        }
        // 简化说明: AppConfig.isCronet 固定 false，移除 Cronet DNS 处理 | 已知上限: 无 Cronet 支持 | 升级路径: 接入 Cronet
        if (dnsIp != null) {
            customIp[urlNoQuery] = dnsIp!!
        }
        return client.newBuilder().run {
            if (readTimeout != null) {
                readTimeout(readTimeout, TimeUnit.MILLISECONDS)
                callTimeout(max(60 * 1000L, readTimeout * 2), TimeUnit.MILLISECONDS)
            }
            if (callTimeout != null) {
                callTimeout(callTimeout, TimeUnit.MILLISECONDS)
            }
            if (dnsIp != null) {
                val inetAddress = dnsIp!!.parseIpsFromString()
                dns { hostname ->
                    inetAddress ?: Dns.SYSTEM.lookup(hostname)
                }
            }
            val fr = followRedirects
            if (fr != null) {
                followRedirects(fr)
                followSslRedirects(fr)
            }
            build()
        }
    }

    private fun extractHostFromUrl(url: String): String? {
        return AppPattern.domainRegex.find(url)?.groupValues?.getOrNull(1)
    }


    fun getResponse(): Response {
        // 简化说明：runBlocking 桥接非suspend方法到suspend Await | 已知上限：阻塞调用线程 | 升级路径：调用方改为suspend
        return runBlocking(coroutineContext) {
            getResponseAwait()
        }
    }

    private fun getByteArrayIfDataUri(): ByteArray? {
        if (!urlNoQuery.startsWith("data:")) {
            return null
        }
        val dataUriFindResult = AppPattern.dataUriRegex.find(urlNoQuery)
        if (dataUriFindResult != null) {
            val dataUriBase64 = dataUriFindResult.groupValues[1]
            // 简化说明: android.util.Base64.decode 替换为 java.util.Base64.getDecoder().decode | 已知上限: 无 URL_SAFE flag 支持 | 升级路径: 无
            val byteArray = Base64.getDecoder().decode(dataUriBase64)
            return byteArray
        }
        return null
    }

    /**
     * 访问网站,返回ByteArray
     */
    suspend fun getByteArrayAwait(): ByteArray {
        getByteArrayIfDataUri()?.let {
            return it
        }
        return getResponseAwait().body.bytes()
    }

    fun getByteArray(): ByteArray {
        // 简化说明：runBlocking 桥接非suspend方法到suspend Await | 已知上限：阻塞调用线程 | 升级路径：调用方改为suspend
        return runBlocking(coroutineContext) {
            getByteArrayAwait()
        }
    }

    /**
     * 访问网站,返回InputStream
     */
    suspend fun getInputStreamAwait(): InputStream {
        getByteArrayIfDataUri()?.let {
            return ByteArrayInputStream(it)
        }
        return getResponseAwait().body.byteStream()
    }

    fun getInputStream(): InputStream {
        // 简化说明：runBlocking 桥接非suspend方法到suspend Await | 已知上限：阻塞调用线程 | 升级路径：调用方改为suspend
        return runBlocking(coroutineContext) {
            getInputStreamAwait()
        }
    }

    /**
     * 上传文件
     */
    suspend fun upload(fileName: String, file: Any, contentType: String): StrResponse {
        return getProxyClient(proxy).newCallStrResponse(retry) {
            url(urlNoQuery)
            val bodyMap = GSON.fromJsonObject<HashMap<String, Any>>(body).getOrNull()!!
            bodyMap.forEach { entry ->
                if (entry.value.toString() == "fileRequest") {
                    bodyMap[entry.key] = mapOf(
                        Pair("fileName", fileName),
                        Pair("file", file),
                        Pair("contentType", contentType)
                    )
                }
            }
            postMultipart(type, bodyMap)
        }
    }

    /**
     * 设置cookie 优先级
     * urlOption临时cookie > 数据库cookie
     */
    private fun setCookie() {
        val cookie = kotlin.run {
            /* 每次调用getXX cookieJar已经保存过了
            if (enabledCookieJar) {
                val key = "${domain}_cookieJar"
                CacheManagerStub.getFromMemory(key)?.let {
                    return@run it
                }
            }
            */
            CookieStoreStub.getCookie(domain)
        }
        if (cookie.isNotEmpty()) {
            mergeCookies(cookie, headerMap["Cookie"])?.let {
                headerMap.put("Cookie", it)
            }
        }
        if (enabledCookieJar) {
            headerMap[CookieManager.cookieJarHeader] = "1"
        } else {
            headerMap.remove(CookieManager.cookieJarHeader)
        }
    }

    /**
     * 保存cookieJar中的cookie在访问结束时就保存,不等到下次访问
     */
    private fun saveCookie() {
        //书源启用保存cookie时 添加内存中的cookie到数据库
        if (enabledCookieJar) {
            val key = "${domain}_cookieJar"
            CacheManagerStub.getFromMemory(key)?.let {
                if (it is String) {
                    CookieStoreStub.replaceCookie(domain, it)
                    CacheManagerStub.deleteMemory(key)
                }
            }
        }
    }

    fun getUserAgent(): String {
        return headerMap.get(UA_NAME, true) ?: AppConfig.userAgent
    }

    fun isPost(): Boolean {
        return method == RequestMethod.POST
    }

    override fun getSource(): BaseSourceInterface? {
        return source
    }

    override fun getTag(): String? {
        return source?.getTag()
    }

    companion object {
        val paramPattern: Pattern = Pattern.compile("\\s*,\\s*(?=\\{)")
        private val pagePattern = Pattern.compile("<(.*?)>")
        private val queryEncoder =
            RFC3986.UNRESERVED.orNew(PercentCodec.of("!$%&()*+,/:;=?@[\\]^`{|}"))
        val customIp by lazy { ConcurrentHashMap<String, String>() }
    }

    data class UrlOption(
        private var method: String? = null,
        private var charset: String? = null,
        private var headers: Any? = null,
        private var body: Any? = null,
        /**
         * 源Url
         **/
        private var origin: String? = null,
        /**
         * 重试次数
         **/
        private var retry: Int? = null,
        /**
         * 类型
         **/
        private var type: String? = null,
        /**
         * 是否使用webView
         **/
        private var webView: Any? = null,
        /**
         * webView中执行的js
         **/
        private var webJs: String? = null,
        /**
         * 自定义的域名ip
         **/
        private var dnsIp: String? = null,
        /**
         * 解析完url参数时执行的js
         * 执行结果会赋值给url
         */
        private var js: String? = null,
        /**
         * 得到访问结果后执行的js,对结果进行二次处理
         * 执行结果返回为body
         */
        private var bodyJs: String? = null,
        /**
         * 服务器id
         */
        private var serverID: Long? = null,
        /**
         * webview等待页面加载完毕的延迟时间（毫秒）
         */
        private var webViewDelayTime: Long? = null,
        /**
         * 是否跟随重定向
         */
        private var followRedirects: Boolean? = null,
    ) {
        fun setMethod(value: String?) {
            method = if (value.isNullOrBlank()) null else value
        }

        fun getMethod(): String? {
            return method
        }

        fun setCharset(value: String?) {
            charset = if (value.isNullOrBlank()) null else value
        }

        fun getCharset(): String? {
            return charset
        }

        fun setOrigin(value: String?) {
            origin = if (value.isNullOrBlank()) null else value
        }

        fun getOrigin(): String? {
            return origin
        }

        fun setRetry(value: String?) {
            retry = if (value.isNullOrEmpty()) null else value.toIntOrNull()
        }

        fun getRetry(): Int {
            return retry ?: 0
        }

        fun setType(value: String?) {
            type = if (value.isNullOrBlank()) null else value
        }

        fun getType(): String? {
            return type
        }

        fun useWebView(): Boolean {
            return when (webView) {
                null, "", false, "false" -> false
                else -> true
            }
        }

        fun useWebView(boolean: Boolean) {
            webView = if (boolean) true else null
        }

        fun setHeaders(value: String?) {
            headers = if (value.isNullOrBlank()) {
                null
            } else {
                GSON.fromJsonObject<Map<String, Any>>(value).getOrNull()
            }
        }

        fun getHeaderMap(): Map<*, *>? {
            return when (val value = headers) {
                is Map<*, *> -> value
                is String -> GSON.fromJsonObject<Map<String, Any>>(value).getOrNull()
                else -> null
            }
        }

        fun setBody(value: String?) {
            body = when {
                value.isNullOrBlank() -> null
                value.isJsonObject() -> GSON.fromJsonObject<Map<String, Any>>(value).getOrNull()
                value.isJsonArray() -> GSON.fromJsonArray<Map<String, Any>>(value).getOrNull()
                else -> value
            }
        }

        fun getBody(): String? {
            return body?.let {
                it as? String ?: GSON.toJson(it)
            }
        }

        fun setWebJs(value: String?) {
            webJs = if (value.isNullOrBlank()) null else value
        }

        fun getWebJs(): String? {
            return webJs
        }
        fun setDnsIp(value: String?) {
            dnsIp = if (value.isNullOrBlank()) null else value
        }

        fun getDnsIp(): String? {
            return dnsIp
        }

        fun setJs(value: String?) {
            js = if (value.isNullOrBlank()) null else value
        }

        fun getJs(): String? {
            return js
        }

        fun setBodyJs(value: String?) {
            bodyJs = if (value.isNullOrBlank()) null else value
        }

        fun getBodyJs(): String? {
            return bodyJs
        }

        fun setServerID(value: String?) {
            serverID = if (value.isNullOrBlank()) null else value.toLong()
        }

        fun getServerID(): Long? {
            return serverID
        }

        fun setWebViewDelayTime(value: String?) {
            webViewDelayTime = if (value.isNullOrBlank()) null else value.toLong()
        }

        fun getWebViewDelayTime(): Long? {
            return webViewDelayTime
        }

        fun setFollowRedirects(value: Boolean?) {
            followRedirects = value
        }

        fun getFollowRedirects(): Boolean? {
            return followRedirects
        }
    }

    data class ConcurrentRecord(
        /**
         * 开始访问时间
         */
        var time: Long,
        /**
         * 限制次数
         */
        var accessLimit : Int,
        /**
         * 间隔时间
         */
        var interval : Int,
        /**
         * 正在访问的个数
         */
        var frequency: Int
    )

}
