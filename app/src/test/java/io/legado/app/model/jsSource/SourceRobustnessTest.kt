package io.legado.app.model.jsSource

import com.google.gson.JsonParser
import com.script.ScriptBindings
import com.script.rhino.RhinoScriptEngine
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 交付源「源侧健壮性」回归测试（tasks 4.8.6 / spec Requirement E-4）。
 *
 * 覆盖三种异常情形（验证标准原文）：
 * 1. **站点抖动**：单次请求失败/超时后必须**有界重试**（默认 2 次，带单次超时上界），
 *    重试成功即用成功结果；全部失败则返回最后一条错误文本（**不得**死循环或抛未捕获异常）。
 * 2. **下发风控键**：源必须**按键删除**风控 Cookie（`removeCookie(url, key)`），
 *    且**永不**触发整域清除（`removeCookie(url)` 单参形式）—— 后者会连带清掉 WebView 登录态。
 * 3. **空页面**：页面无内联数据时不崩溃 —— 列表链返回空数组，正文链抛出**可读**失败原因。
 *
 * **为什么用 Rhino 跑真脚本**：这些行为都住在交付源的 `mainJs` 里（不是平台 Kotlin 类），
 * 只有把交付源加载进 Rhino、桩掉网络与 cookie 才能断言真实源行为。
 * 夹具：`app/src/test/resources/fixtures/js_source_video_20261026.json`（与交付源同源，改动需同步）。
 */
class SourceRobustnessTest {

    private val fixture = File("src/test/resources/fixtures/js_source_video_20261026.json")

    /** 一次执行的观测结果：脚本返回值 + 请求次数 + 单次超时入参 + cookie 删除调用。 */
    private data class Trace(
        val value: String,
        val ajaxCount: Int,
        val timeouts: List<String>,
        /** 形如 `2:ttwid`（两参调用，删 ttwid）或 `1:+undefined`（单参 = 整域清除） */
        val removeCalls: List<String>,
        val storeKeys: List<String>,
    )

    /**
     * @param responses `java.ajax` 的顺序应答队列（越界时重复最后一条）
     * @param initialStore 初始 Cookie 存储层（键→值）
     */
    private fun run(script: String, responses: List<String>, initialStore: Map<String, String> = emptyMap()): Trace {
        assertTrue("夹具不存在：${fixture.absolutePath}", fixture.exists())
        val js = JsonParser.parseString(fixture.readText())
            .asJsonArray[0].asJsonObject.get("mainJs")?.asString.orEmpty()
        assertTrue("夹具 mainJs 为空（夹具与交付源不同步）", js.isNotBlank())

        val scope = RhinoScriptEngine.getRuntimeScope(ScriptBindings())
        RhinoScriptEngine.eval(
            """
            var __RESP = ${toJsArray(responses)};
            var __i = 0;
            var __ajaxN = 0;
            var __timeouts = [];
            var __rm = [];
            var __store = ${toJsObject(initialStore)};
            var java = {
              ajax: function (url, timeout) {
                __ajaxN++;
                __timeouts.push(String(timeout));
                var r = __RESP[Math.min(__i, __RESP.length - 1)];
                __i++;
                return r;
              },
              log: function () { },
              startBrowser: function () { }
            };
            var cookie = {
              getCookie: function () {
                var out = []; for (var k in __store) out.push(k + "=" + __store[k]); return out.join("; ");
              },
              getWebCookie: function () { return ""; },
              setCookie: function () { }, replaceCookie: function () { },
              removeCookie: function (u, k) {
                __rm.push(String(arguments.length) + ":" + String(k));
                if (arguments.length < 2) { __store = {}; } else { delete __store[k]; }
              },
              setWebCookie: function () { }
            };
            var source = {
              getVariable: function () { return ""; }, putVariable: function () { }, removeLoginInfo: function () { }
            };
            """.trimIndent(),
            scope
        )
        RhinoScriptEngine.eval(js, scope)
        val value = RhinoScriptEngine.eval(script, scope)?.toString().orEmpty()
        fun read(expr: String) = RhinoScriptEngine.eval(expr, scope)?.toString().orEmpty()
        fun split(joined: String) = if (joined.isEmpty()) emptyList() else joined.split('\u0001')
        return Trace(
            value = value,
            ajaxCount = read("String(__ajaxN)").toInt(),
            timeouts = split(read("__timeouts.join('\u0001')")),
            removeCalls = split(read("__rm.join('\u0001')")),
            storeKeys = split(read("(function(){var ks=[];for(var k in __store)ks.push(k);return ks.join('\u0001');})()")),
        )
    }

    private fun toJsArray(items: List<String>): String =
        items.joinToString(",", "[", "]") { escape(it) }

    private fun toJsObject(map: Map<String, String>): String =
        map.entries.joinToString(",", "{", "}") { (k, v) -> "\"$k\":" + escape(v) }

    private fun escape(s: String): String =
        "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n") + "\""

    /** Legado 在 ajax 失败时返回带 `\tat ` 的堆栈串 —— 与宿主真实行为一致。 */
    private val err = "\tat fake.Host.ajax(fake.kt:1)\njava.lang.RuntimeException: request failed"

    // ============ 场景 1：站点抖动（有界重试） ============

    @Test
    fun jitter_retriesOnceThenUsesSuccess() {
        val t = run("getText('https://site/x')", listOf(err, "<html>OK</html>"))
        assertEquals("首次失败后重试应取到成功结果", "<html>OK</html>", t.value)
        assertEquals("默认重试 2 次（第 2 次成功）", 2, t.ajaxCount)
    }

    @Test
    fun jitter_allFail_boundedAndReturnsLastError() {
        val t = run("getText('https://site/x')", listOf(err))
        assertEquals("全部失败时必须有界重试（恰好 2 次，不得死循环）", 2, t.ajaxCount)
        assertTrue("全部失败应返回最后一条错误文本（供上层判失败）", t.value.contains("request failed"))
        assertEquals("每次请求都必须带单次超时上界（8000ms）", listOf("8000", "8000"), t.timeouts)
    }

    // ============ 场景 2：下发风控键（按键清除、零整域清） ============

    @Test
    fun botCookie_removedPerKey_neverDomainWide() {
        val t = run(
            "dropBotCookies(); (function(){var ks=[];for(var k in __store)ks.push(k);return ks.join(',');})()",
            listOf(""),
            mapOf("ttwid" to "a", "sessionid" to "b"),
        )
        assertEquals("风控键 ttwid 必须被删；登录态键 sessionid 必须保留", "sessionid", t.value)
        assertEquals(listOf("sessionid"), t.storeKeys)
        assertEquals("必须用两参按键删除", listOf("2:ttwid"), t.removeCalls)
        assertTrue(
            "严禁出现单参（整域清除）调用 —— 会连带清掉 WebView 域层的登录态",
            t.removeCalls.none { it.startsWith("1:") },
        )
    }

    @Test
    fun botCookie_absent_isNoop() {
        val t = run(
            "dropBotCookies(); (function(){var ks=[];for(var k in __store)ks.push(k);return ks.join(',');})()",
            listOf(""),
            mapOf("sessionid" to "b"),
        )
        assertEquals("无风控键时必须零副作用（不删任何键）", "sessionid", t.value)
        assertEquals("无风控键时不得发起任何删除调用", 0, t.removeCalls.size)
    }

    // ============ 场景 3：空页面（不崩溃 + 原因可读） ============

    @Test
    fun emptyPage_routerDataIsNull() {
        val t = run("String(getRouterData('https://site/x') === null)", listOf("<html>no inline data</html>"))
        assertEquals("页面无内联数据必须判为 null（不得抛异常）", "true", t.value)
    }

    @Test
    fun emptyPage_exploreReturnsEmptyList() {
        val t = run("JSON.stringify(explore(BASE + '/category/x', 1))", listOf("<html>no inline data</html>"))
        assertEquals("发现链遇空页面应返回空数组（不崩溃）", "[]", t.value)
    }

    @Test
    fun emptyPage_getContent_throwsReadableReason() {
        val script = "(function(){ try { getContent({url: BASE + '/player/1/v1', index: 0}, {}, ''); " +
            "return 'no-throw'; } catch (e) { return String(e.message || e); } })()"
        val t = run(script, listOf("<html>empty play page</html>"))
        assertTrue("空播放页必须抛出异常（而不是返回空串让宿主播错集）", t.value != "no-throw")
        assertTrue("失败原因必须可读（含「取回失败」）", t.value.contains("取回失败"))
        assertTrue("失败原因必须给出下一步动作（含「重试」）", t.value.contains("重试"))
    }
}
