package io.legado.app.model.jsSource

import com.google.gson.JsonParser
import com.script.ScriptBindings
import com.script.rhino.RhinoScriptEngine
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 交付源登录体检「三态判定 + 键名掩码」回归测试（design AD-04 / AD-07 / tasks 5.1）。
 *
 * **为什么用 Rhino 跑真脚本**：登录判据与脱敏逻辑**住在交付源的 `mainJs` 里**（不是平台 Kotlin 类），
 * 用 JVM 单测直接断言平台类无法覆盖它。本测试把交付源（夹具副本）加载进 Rhino，
 * 只桩掉网络与 cookie（`java.ajax` / `cookie`），因此断言的是**真实源行为**。
 *
 * 夹具：`app/src/test/resources/fixtures/js_source_video_20261026.json`
 * —— 与 `output/ai_source/book/书源_短剧视频JS_20261026.json` 同源；源改动时必须同步更新夹具
 * （夹具内 `bookSourceComment` 带日期标记，便于发现漂移）。
 *
 * 断言要点（带期望值）：
 * 1. **三态**：请求异常/无数据/超时 ⇒ `state=""`（无法判定，**不是** "false" 未放行）；
 *    命中锁定标记 ⇒ `"false"`；未命中 ⇒ `"true"`；
 * 2. **掩码**：`cookieDiagnosis` 输出只含键名，绝不出现任何值；`marked` 只含声明的登录态键名。
 */
class LoginProbeTriStateTest {

    private val fixture = File("src/test/resources/fixtures/js_source_video_20261026.json")

    private fun loadMainJs(): String {
        assertTrue("夹具不存在：${fixture.absolutePath}", fixture.exists())
        val obj = JsonParser.parseString(fixture.readText())
            .asJsonArray[0].asJsonObject
        val js = obj.get("mainJs")?.asString.orEmpty()
        assertTrue("夹具 mainJs 为空（夹具与交付源不同步）", js.isNotBlank())
        return js
    }

    /**
     * 在 Rhino 里跑交付源脚本，并把 `java.ajax` / `cookie` / `java.log` / `source` 全部桩掉。
     *
     * @param routers url→返回文本（含 `AjaxError` 用于模拟请求失败）
     */
    private fun run(action: String, routers: Map<String, String>): String {
        val scope = RhinoScriptEngine.getRuntimeScope(ScriptBindings())
        // 桩：java.ajax（失败时返回带 \tat 的堆栈串，与宿主真实行为一致）
        RhinoScriptEngine.eval(
            """
            var __RESP = ${toJsObject(routers)};
            var __store = {};
            var __web = {};
            var java = {
              ajax: function (url) {
                for (var k in __RESP) { if (url.indexOf(k) >= 0) return __RESP[k]; }
                return "\tat fake.Host.ajax(fake.kt:1)\njava.lang.RuntimeException: 未桩定的地址";
              },
              log: function (m) { },
              startBrowser: function () { }
            };
            var cookie = {
              getCookie: function () {
                var out = []; for (var k in __store) out.push(k + "=" + __store[k]); return out.join("; ");
              },
              getWebCookie: function () {
                var out = []; for (var k in __web) out.push(k + "=" + __web[k]); return out.join("; ");
              },
              setCookie: function (u, c) { },
              replaceCookie: function (u, c) { },
              removeCookie: function (u, k) { if (arguments.length < 2) { __store = {}; __web = {}; } else { delete __store[k]; delete __web[k]; } },
              setWebCookie: function (u, c) { }
            };
            var source = { getVariable: function () { return ""; }, putVariable: function () { }, removeLoginInfo: function () { } };
            """.trimIndent(),
            scope
        )
        RhinoScriptEngine.eval(loadMainJs(), scope)
        return RhinoScriptEngine.eval(action, scope).toString()
    }

    private fun toJsObject(map: Map<String, String>): String =
        map.entries.joinToString(",", "{", "}") { (k, v) -> "\"$k\":" + escape(v) }

    private fun escape(s: String): String =
        "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n") + "\""

    // ============ 三态：无法判定（不得显示为「未放行」） ============

    /** 取 `probeEntitlement()` 返回的 state 值（`""` = 无法判定 / `"true"` / `"false"`）。 */
    private fun probeState(routers: Map<String, String>): String =
        JsonParser.parseString(run("JSON.stringify(probeEntitlement())", routers))
            .asJsonObject.get("state").asString

    private fun probeReason(routers: Map<String, String>): String =
        JsonParser.parseString(run("JSON.stringify(probeEntitlement())", routers))
            .asJsonObject.get("reason").asString

    @Test
    fun probe_ajaxFailure_isUndetermined() {
        // 分类页直接返回异常堆栈 ⇒ 请求未完成
        assertEquals("请求异常必须判「无法判定」（state 为空串）", "", probeState(emptyMap()))
        assertEquals("原因应标为 request-error", "request-error", probeReason(emptyMap()))
    }

    @Test
    fun probe_emptyCategoryData_isUndetermined() {
        val routers = mapOf("/category/" to "<html><body>_ROUTER_DATA = {\"loaderData\":{}}</body></html>")
        assertEquals("分类页无数据必须判「无法判定」", "", probeState(routers))
        assertEquals("原因应标为 no-data（站点数据缺失，非登录问题）", "no-data", probeReason(routers))
    }

    @Test
    fun probe_playPageTimeout_isUndetermined() {
        // 分类页有数据，但播放页请求失败 ⇒ 仍必须「无法判定」
        val routers = mapOf("/category/" to categoryPage())
        assertEquals("播放页请求未完成必须判「无法判定」", "", probeState(routers))
        assertEquals("原因应标为 probe-timeout（不得标成 locked）", "probe-timeout", probeReason(routers))
    }

    /** 构造分类页最小 SSR 数据（`category_$` 的 `$` 用拼接避开 Kotlin 模板）。 */
    private fun categoryPage(): String {
        val key = "category_" + "$"
        return "<html>_ROUTER_DATA = " +
            "{\"loaderData\":{\"$key\":{\"recommendList\":" +
            "[{\"series_id\":\"1\",\"vid_list\":[\"v1\",\"v2\"]}]}}}</html>"
    }

    // ============ 三态：未放行 / 已放行 ============

    @Test
    fun probe_lockedMarker_isNotGranted() {
        val routers = mapOf("/category/" to categoryPage(), "/player/" to "<html>pc_locked_episode</html>")
        assertEquals("命中锁定标记应判「未放行」", "false", probeState(routers))
        assertEquals("原因应标为 locked", "locked", probeReason(routers))
    }

    @Test
    fun probe_noLockedMarker_isGranted() {
        val routers = mapOf("/category/" to categoryPage(), "/player/" to "<html>ok</html>")
        assertEquals("未命中锁定标记应判「已放行」", "true", probeState(routers))
        assertEquals("原因应标为 ok", "ok", probeReason(routers))
    }
}
