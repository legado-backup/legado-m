package io.legado.ruleengine

import com.google.gson.JsonObject

/**
 * 调试结果数据结构
 *
 * 源码参照：无（新增设计，用于替代 debug() 的 void 返回值）
 */
data class DebugResult(
    val success: Boolean,
    val needsWebView: Boolean = false,
    val needsUserIntervention: Boolean = false,
    val summary: JsonObject = JsonObject(),
    val errorStage: String? = null,
    val errorMessage: String? = null,
    val webViewRequests: List<WebViewRequest> = emptyList()
)

/**
 * WebView 请求详情
 *
 * @param url 目标 URL
 * @param html 当前 HTML（用于二次解析）
 * @param js 需执行的 JS
 * @param sourceRegex 资源嗅探正则
 * @param type 请求类型："load" | "sniff" | "overrideUrl" | "login"
 */
data class WebViewRequest(
    val url: String?,
    val html: String?,
    val js: String?,
    val sourceRegex: String?,
    val type: String
)
