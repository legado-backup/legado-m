package io.legado.app.help.http

import io.legado.ruleengine.WebViewRequest
import io.legado.ruleengine.WebViewRequiredException

// 源码参照: app/src/main/java/io/legado/app/help/http/BackstageWebView.kt
// 简化说明: JVM 环境无法执行 WebView，抛出 WebViewRequiredException 携带请求信息，由 Python 客户端用 Selenium 渲染 | 已知上限: 无法执行 JS 渲染 | 升级路径: Python 客户端 Selenium 委托

class BackstageWebView(
    val url: String? = null,
    val html: String? = null,
    val tag: String? = null,
    val javaScript: String? = null,
    val sourceRegex: String? = null,
    val headerMap: Map<String, String>? = null,
    val delayTime: Long = 0,
    val cacheFirst: Boolean = false,
    val timeout: Int = 10000,
    val result: String? = null,
    val isRule: Boolean = false
) {
    fun getStrResponse(): StrResponse {
        val requestType = if (sourceRegex != null) "sniff" else "load"
        val request = WebViewRequest(
            url = url,
            html = html,
            js = javaScript,
            sourceRegex = sourceRegex,
            type = requestType
        )
        throw WebViewRequiredException(
            stage = "backstageWebView",
            requests = listOf(request),
            message = "需要 WebView 渲染: url=${url?.take(80)}, js=${javaScript?.take(50)}, type=$requestType"
        )
    }
}
