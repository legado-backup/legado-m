package io.legado.ruleengine

import io.legado.app.exception.NoStackTraceException

/**
 * WebView 渲染需求异常
 *
 * 当 BackstageWebView / JsExtensionsStub.webView() 等方法需要 WebView 渲染时抛出。
 * debug() 捕获后返回 DebugResult(needsWebView=true)。
 *
 * @param stage 触发阶段（如 "sort", "content", "js_webView"）
 * @param requests WebView 请求详情列表
 */
class WebViewRequiredException(
    val stage: String,
    val requests: List<WebViewRequest>,
    message: String
) : NoStackTraceException(message)
