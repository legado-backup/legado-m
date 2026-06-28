package io.legado.ruleengine

import com.google.gson.JsonArray
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import com.script.buildScriptBindings
import com.script.rhino.RhinoScriptEngine
import io.legado.app.data.entities.BaseSourceInterface
import io.legado.app.data.entities.BookSource
import io.legado.app.data.entities.RssSource
import io.legado.app.help.CacheManagerStub
import io.legado.app.help.JsExtensionsStub
import io.legado.app.help.http.CookieStoreStub
import io.legado.app.model.analyzeRule.AnalyzeRule
import io.legado.app.model.analyzeRule.RuleData
import io.legado.app.utils.GSON
import io.legado.app.utils.GSONStrict
import io.legado.app.utils.fromJsonObject
import java.io.BufferedReader
import java.io.InputStreamReader

// 源码参照: app/src/main/java/io/legado/app/model/Debug.kt
// 简化说明: 从旧 MVP1-4 RuleEngineServer 迁移，替换 MinimalMockJsExtensions/MockSource 为抽取后的 AnalyzeRule/AnalyzeUrl/BookSource/RssSource | 已知上限: 旧命令(decrypt/encrypt/evalCSS/analyzeRule/analyzeElements/analyzeUrl)已弃用，返回提示信息 | 升级路径: 需要时从旧 MVP4 迁移对应实现

fun main(args: Array<String>) {
    val server = RuleEngineServer()
    server.start()
}

/**
 * JVM 仿真服务端入口
 *
 * stdin/stdout JSON 协议:
 * - 输入: 每行一个 JSON 命令
 * - 输出: 每行一个 JSON 响应（流式日志 + 最终结果）
 *
 * 支持命令:
 * 1. ping - 心跳检测
 * 2. debugRssSource - 调试 RSS 源（流式输出）
 * 3. debugBookSource - 调试书源（流式输出）
 * 4. evalJS - 独立 JS 执行
 * 5. batch - 批处理
 * 6. check - 书源全流程校验（域名→搜索→发现→详情→目录→正文）
 * 7. shutdown - 关闭服务
 */
class RuleEngineServer {

    fun start() {
        val reader = BufferedReader(InputStreamReader(System.`in`, "UTF-8"))

        // 输出启动信息
        val startupInfo = JsonObject()
        startupInfo.addProperty("status", "ready")
        val modules = JsonArray()
        modules.add("rhino")
        modules.add("crypto")
        modules.add("jsoup")
        modules.add("analyzeRule")
        modules.add("analyzeUrl")
        startupInfo.add("modules", modules)
        startupInfo.addProperty("version", "legado-jvm")
        println(startupInfo.toString())
        System.out.flush()

        while (true) {
            try {
                val line = reader.readLine() ?: break
                if (line.isBlank()) continue

                val cmd = JsonParser.parseString(line).asJsonObject
                val result = processCommand(cmd)
                // 流式命令（debugBookSource/debugRssSource/batch）返回 null，已自行输出日志
                if (result != null) {
                    println(result.toString())
                    System.out.flush()
                }
            } catch (e: Exception) {
                val errorResult = JsonObject()
                errorResult.addProperty("ok", false)
                errorResult.addProperty("error", e.message ?: "Unknown error")
                errorResult.addProperty("errorClass", e.javaClass.name)
                println(errorResult.toString())
                System.out.flush()
            }
        }
    }

    private fun processCommand(cmd: JsonObject): JsonObject? {
        val command = cmd.get("cmd")?.asString ?: return errorResult("Missing cmd field")
        return when (command) {
            "ping" -> {
                val result = JsonObject()
                result.addProperty("ok", true)
                result.addProperty("pong", true)
                result
            }
            "evalJS" -> {
                val jsCode = cmd.get("code")?.asString ?: ""
                val contextVar = cmd.get("context")?.asString ?: ""
                evalJS(jsCode, contextVar)
            }
            "debugBookSource" -> {
                handleDebugBookSource(cmd)
                null
            }
            "debugRssSource" -> {
                handleDebugRssSource(cmd)
                null
            }
            "batch" -> {
                handleBatch(cmd)
                null
            }
            "check" -> {
                handleCheckSource(cmd)
            }
            "shutdown" -> {
                val result = JsonObject()
                result.addProperty("ok", true)
                result.addProperty("message", "shutting down")
                println(result.toString())
                System.out.flush()
                System.exit(0)
                result
            }
            else -> {
                errorResult("Unknown or deprecated command: $command. Supported: ping, evalJS, debugRssSource, debugBookSource, batch, check, shutdown")
            }
        }
    }

    // ==================== evalJS 命令 ====================

    /**
     * 独立 JS 执行
     * 使用 RhinoScriptEngine 直接执行 JS 代码
     * 注入与真机 AnalyzeRule.evalJS 对齐的 13 个上下文变量
     */
    private fun evalJS(jsCode: String, contextVar: String): JsonObject {
        val result = JsonObject()
        try {
            val source = JsExtensionsStub.getSource()
            val baseUrl = when (source) {
                is BookSource -> source.bookSourceUrl
                is RssSource -> source.sourceUrl
                is BaseSourceInterface -> source.getKey()
                else -> ""
            }
            val bindings = buildScriptBindings { bindings ->
                bindings["result"] = contextVar
                bindings["baseUrl"] = baseUrl
                bindings["book"] = null
                bindings["source"] = source
                bindings["chapter"] = null
                bindings["title"] = ""
                bindings["src"] = ""
                bindings["java"] = JsExtensionsStub
                bindings["cookie"] = CookieStoreStub
                bindings["cache"] = CacheManagerStub
                bindings["bookUrl"] = ""
                bindings["originalVal"] = ""
                bindings["ruleData"] = JsExtensionsStub.getRuleData()
                // 补充与真机 AnalyzeRule.evalJS 对齐的变量
                bindings["nextChapterUrl"] = ""
                bindings["rssArticle"] = null
                bindings["fromBookInfo"] = false
            }
            val scope = RhinoScriptEngine.getRuntimeScope(bindings)
            val rawResult = RhinoScriptEngine.eval(jsCode, scope)
            // 修复 NativeJavaObject 序列化 Bug
            val unwrappedResult = AnalyzeRule.unwrapRhinoResult(rawResult)

            result.addProperty("ok", true)
            result.addProperty("resultType", if (unwrappedResult == null) "null" else unwrappedResult.javaClass.simpleName)
            val resultStr = when (unwrappedResult) {
                null -> "null"
                is String -> unwrappedResult
                is Number -> unwrappedResult.toString()
                is Boolean -> unwrappedResult.toString()
                else -> unwrappedResult.toString()
            }
            result.addProperty("result", resultStr)
            result.addProperty("confidence", assessConfidence(jsCode))
        } catch (e: Exception) {
            result.addProperty("ok", false)
            result.addProperty("error", e.message ?: "Unknown error")
            result.addProperty("errorClass", e.javaClass.name)
            result.addProperty("confidence", assessConfidence(jsCode))
        }
        return result
    }

    private fun assessConfidence(jsCode: String): String {
        val lower = jsCode.lowercase()
        val hasES6Syntax = jsCode.contains("\\blet\\b".toRegex()) ||
            jsCode.contains("\\bconst\\b".toRegex()) ||
            jsCode.contains("=>") ||
            jsCode.contains("`")
        return when {
            lower.contains("webview") || lower.contains("webjs") -> "unverifiable"
            hasES6Syntax -> "low"
            lower.contains("ajax") && (lower.contains("cookie") || lower.contains("header")) -> "low"
            lower.contains("ajax") -> "medium"
            else -> "high"
        }
    }

    // ==================== 调试命令 ====================

    private fun handleDebugBookSource(cmd: JsonObject) {
        val sourceJson = cmd.get("sourceJson")?.asString ?: ""
        val key = cmd.get("key")?.asString ?: ""
        // 修复9.4 GAP-25: 支持校验模式
        val validateMode = cmd.get("validateMode")?.asBoolean ?: false

        val logger = DebugLogger()
        val debugger = BookSourceDebugger(sourceJson, key, logger)
        debugger.debug(validateMode)
    }

    private fun handleDebugRssSource(cmd: JsonObject) {
        val sourceJson = cmd.get("sourceJson")?.asString ?: ""
        val key = cmd.get("key")?.asString ?: ""
        // 修复9.4 GAP-25: 支持校验模式
        val validateMode = cmd.get("validateMode")?.asBoolean ?: false

        val logger = DebugLogger()
        val debugger = RssSourceDebugger(sourceJson, key, logger)
        debugger.debug(validateMode)
    }

    /**
     * 书源全流程校验
     * 输入: {"cmd":"check","sourceJson":"..."}
     * 输出: 单个 JsonObject，包含域名/搜索/发现/详情/目录/正文各阶段结果
     */
    private fun handleCheckSource(cmd: JsonObject): JsonObject {
        val sourceJson = cmd.get("sourceJson")?.asString ?: ""
        val source = parseBookSource(sourceJson)
            ?: return errorResult("Invalid source JSON")
        return CheckSourceDebugger.checkAll(source)
    }

    // ==================== batch 命令 ====================

    /**
     * 批处理命令
     * 输入: {"cmd":"batch","sourceType":"rss|book","sources":[{"sourceJson":"...","key":"..."},...]}
     * 输出: 每个源的结果 + 进度 + 最终汇总
     */
    private fun handleBatch(cmd: JsonObject) {
        val sourceType = cmd.get("sourceType")?.asString ?: "rss"
        val sourcesArray = cmd.getAsJsonArray("sources") ?: JsonArray()
        val total = sourcesArray.size()
        val results = JsonArray()

        for ((index, sourceEntry) in sourcesArray.withIndex()) {
            val sourceObj = sourceEntry.asJsonObject
            val sourceJson = sourceObj.get("sourceJson")?.asString ?: ""
            val key = sourceObj.get("key")?.asString ?: ""
            val current = index + 1

            val sourceName = try {
                val parsed = JsonParser.parseString(sourceJson).asJsonObject
                parsed.get("sourceName")?.asString
                    ?: parsed.get("bookSourceName")?.asString
                    ?: "unknown_$current"
            } catch (e: Exception) {
                "unknown_$current"
            }

            val batchLogger = DebugLogger()
            val result = when (sourceType) {
                "book" -> BookSourceDebugger(sourceJson, key, batchLogger).debug()
                else -> RssSourceDebugger(sourceJson, key, batchLogger).debug()
            }

            val itemResult = JsonObject()
            itemResult.addProperty("sourceName", sourceName)
            itemResult.addProperty("success", result.success)
            itemResult.addProperty("needsWebView", result.needsWebView)
            itemResult.addProperty("needsUserIntervention", result.needsUserIntervention)
            itemResult.add("summary", result.summary)
            if (result.errorStage != null) {
                itemResult.addProperty("errorStage", result.errorStage)
                itemResult.addProperty("errorMessage", result.errorMessage ?: "")
            }
            if (result.webViewRequests.isNotEmpty()) {
                itemResult.add("webViewRequests", GSON.toJsonTree(result.webViewRequests))
            }
            results.add(itemResult)

            // 输出进度
            val progress = JsonObject()
            progress.addProperty("type", "batch_progress")
            progress.addProperty("current", current)
            progress.addProperty("total", total)
            progress.addProperty("sourceName", sourceName)
            progress.addProperty("success", result.success)
            progress.addProperty("needsWebView", result.needsWebView)
            progress.addProperty("needsUserIntervention", result.needsUserIntervention)
            println(progress.toString())
            System.out.flush()
        }

        // 输出最终汇总
        val complete = JsonObject()
        complete.addProperty("type", "batch_complete")
        complete.add("results", results)
        val successCount = results.count { it.asJsonObject.get("success")?.asBoolean == true }
        val needsWebViewCount = results.count { it.asJsonObject.get("needsWebView")?.asBoolean == true }
        val needsUserInterventionCount = results.count { it.asJsonObject.get("needsUserIntervention")?.asBoolean == true }
        complete.addProperty("successCount", successCount)
        complete.addProperty("needsWebViewCount", needsWebViewCount)
        complete.addProperty("needsUserInterventionCount", needsUserInterventionCount)
        complete.addProperty("totalCount", total)
        println(complete.toString())
        System.out.flush()
    }

    // ==================== 辅助方法 ====================

    private fun errorResult(msg: String): JsonObject {
        val result = JsonObject()
        result.addProperty("ok", false)
        result.addProperty("error", msg)
        return result
    }
}

// ==================== SourceWrapper 适配器 ====================

/**
 * BookSource/RssSource 适配 BaseSourceInterface
 *
 * 简化说明: BookSource/RssSource 移除了 BaseSource 继承，通过此包装器适配 AnalyzeRule/AnalyzeUrl 的 source 参数 | 已知上限: getHeaderMap 不支持 @js:/<js> 请求头规则 | 升级路径: 通过 AnalyzeRule 注入 evalJS
 */
private fun wrapBookSource(source: BookSource): BaseSourceInterface = object : BaseSourceInterface {
    override var concurrentRate: String? get() = source.concurrentRate; set(value) { source.concurrentRate = value }
    override var loginUrl: String? get() = source.loginUrl; set(value) { source.loginUrl = value }
    override var loginUi: String? get() = source.loginUi; set(value) { source.loginUi = value }
    override var header: String? get() = source.header; set(value) { source.header = value }
    override var enabledCookieJar: Boolean? get() = source.enabledCookieJar; set(value) { source.enabledCookieJar = value }
    override var jsLib: String? get() = source.jsLib; set(value) { source.jsLib = value }
    override fun getTag() = source.bookSourceName
    override fun getKey() = source.bookSourceUrl
}

private fun wrapRssSource(source: RssSource): BaseSourceInterface = object : BaseSourceInterface {
    override var concurrentRate: String? get() = source.concurrentRate; set(value) { source.concurrentRate = value }
    override var loginUrl: String? get() = source.loginUrl; set(value) { source.loginUrl = value }
    override var loginUi: String? get() = source.loginUi; set(value) { source.loginUi = value }
    override var header: String? get() = source.header; set(value) { source.header = value }
    override var enabledCookieJar: Boolean? get() = source.enabledCookieJar; set(value) { source.enabledCookieJar = value }
    override var jsLib: String? get() = source.jsLib; set(value) { source.jsLib = value }
    override fun getTag() = source.sourceName
    override fun getKey() = source.sourceUrl
}

/**
 * 解析 header JSON 字符串为 Map
 * 简化说明: 移除 JS 执行，直接解析 JSON | 已知上限: 不支持 @js:/<js> 头部规则 | 升级路径: 委托 AnalyzeRule.evalJS
 */
private object SourceHeaderHelper {
    fun parse(header: String?): Map<String, String>? {
        if (header.isNullOrBlank()) return null
        val result = HashMap<String, String>()
        GSONStrict.fromJsonObject<Map<String, String>>(header).getOrNull()?.let { map ->
            result.putAll(map)
        } ?: GSON.fromJsonObject<Map<String, String>>(header).getOrNull()?.let { map ->
            result.putAll(map)
        }
        return result
    }
}

/**
 * 解析 BookSource JSON
 */
internal fun parseBookSource(sourceJson: String): BookSource? {
    return GSON.fromJsonObject<BookSource>(sourceJson).getOrNull()
}

/**
 * 解析 RssSource JSON
 */
internal fun parseRssSource(sourceJson: String): RssSource? {
    return GSON.fromJsonObject<RssSource>(sourceJson).getOrNull()
}

/**
 * 包装 BookSource 为 BaseSourceInterface
 */
internal fun wrapSource(source: BookSource): BaseSourceInterface = wrapBookSource(source)

/**
 * 包装 RssSource 为 BaseSourceInterface
 */
internal fun wrapSource(source: RssSource): BaseSourceInterface = wrapRssSource(source)

// ==================== DebugLogger ====================

/**
 * 真机级调试日志输出器
 * 原始文件: io.legado.app.model.Debug
 *
 * 输出格式: JSON 行（流式协议）
 * - 日志: {"type":"log","state":1,"msg":"[00:00.001] ︾开始解析搜索页","ts":"..."}
 * - HTML: {"type":"log","state":10,"msg":"...","html":"<html>...","ts":"..."}
 * - 错误: {"type":"error","state":-1,"msg":"...","stackTrace":"...","failedStage":"..."}
 * - 结果: {"type":"result","state":1000,"success":true,"summary":{...}}
 *
 * state 状态码:
 * - 1: 普通日志
 * - 10: 搜索页HTML
 * - 20: 详情页HTML
 * - 30: 目录页HTML
 * - 40: 正文页HTML
 * - -1: 错误
 * - 1000: 完成
 */
class DebugLogger(
    private val startTime: Long = System.currentTimeMillis()
) {
    private val timeFormat = java.text.SimpleDateFormat("[mm:ss.SSS]", java.util.Locale.getDefault())

    fun log(
        msg: String = "",
        state: Int = 1,
        html: String? = null,
        showTime: Boolean = true
    ) {
        val printMsg = if (showTime) {
            val elapsed = System.currentTimeMillis() - startTime
            "${timeFormat.format(java.util.Date(elapsed))} $msg"
        } else {
            msg
        }

        val response = JsonObject()
        response.addProperty("type", "log")
        response.addProperty("state", state)
        response.addProperty("msg", printMsg)
        if (html != null) {
            response.addProperty("html", html)
        }
        response.addProperty("ts", System.currentTimeMillis().toString())

        println(response.toString())
        System.out.flush()
    }

    fun error(
        msg: String,
        stackTrace: String? = null,
        failedStage: String? = null
    ) {
        val elapsed = System.currentTimeMillis() - startTime
        val printMsg = "${timeFormat.format(java.util.Date(elapsed))} $msg"

        val response = JsonObject()
        response.addProperty("type", "error")
        response.addProperty("state", -1)
        response.addProperty("msg", printMsg)
        if (stackTrace != null) {
            response.addProperty("stackTrace", stackTrace)
        }
        if (failedStage != null) {
            response.addProperty("failedStage", failedStage)
        }
        response.addProperty("ts", System.currentTimeMillis().toString())

        println(response.toString())
        System.out.flush()
    }

    fun result(success: Boolean, summary: JsonObject) {
        val elapsed = System.currentTimeMillis() - startTime
        val printMsg = "${timeFormat.format(java.util.Date(elapsed))} ${if (success) "︽解析完成" else "解析失败"}"

        val response = JsonObject()
        response.addProperty("type", "result")
        response.addProperty("state", 1000)
        response.addProperty("success", success)
        response.addProperty("msg", printMsg)
        response.add("summary", summary)
        response.addProperty("ts", System.currentTimeMillis().toString())

        println(response.toString())
        System.out.flush()
    }

    fun separator() {
        val response = JsonObject()
        response.addProperty("type", "log")
        response.addProperty("state", 1)
        response.addProperty("msg", "")
        response.addProperty("ts", System.currentTimeMillis().toString())
        println(response.toString())
        System.out.flush()
    }
}
