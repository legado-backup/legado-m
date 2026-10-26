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
 * 交付源内调试开关 回归测试（tasks 4.8.7 / spec Requirement E-5）。
 *
 * 断言要点（带期望值）：
 * 1. **诊断输出默认关闭**（未设 `diag` ⇒ `diagOn()=false`，且 `diagLog` 零输出）；
 * 2. 开启后 `diagLog` 真正输出技术细节；
 * 3. 开关通过**源持久化变量**保存与清除（`source.putVariable` ⇒ 覆盖安装后仍保留）；
 * 4. 登录页渲染出「诊断输出：开启/关闭」与切换按钮（用户可见入口）。
 */
class SourceDiagSwitchTest {

    private val fixture = File("src/test/resources/fixtures/js_source_video_20261026.json")

    /** 一次求值的结果：表达式返回值 + 记录到的日志 + 最终变量值。 */
    private data class Result(val value: String, val logs: List<String>, val variable: String)

    private fun eval(actions: String, initialVar: String = ""): Result {
        assertTrue("夹具不存在：${fixture.absolutePath}", fixture.exists())
        val js = JsonParser.parseString(fixture.readText())
            .asJsonArray[0].asJsonObject.get("mainJs")?.asString.orEmpty()
        assertTrue("夹具 mainJs 为空（夹具与交付源不同步）", js.isNotBlank())

        val scope = RhinoScriptEngine.getRuntimeScope(ScriptBindings())
        RhinoScriptEngine.eval(
            """
            var __rec = { variable: "$initialVar", logs: [] };
            var java = {
              ajax: function () { return ""; },
              log: function (m) { __rec.logs.push(String(m)); },
              startBrowser: function () { }
            };
            var cookie = {
              getCookie: function () { return ""; }, getWebCookie: function () { return ""; },
              setCookie: function () { }, replaceCookie: function () { },
              removeCookie: function () { }, setWebCookie: function () { }
            };
            var source = {
              getVariable: function () { return __rec.variable; },
              putVariable: function (v) { __rec.variable = String(v); },
              removeLoginInfo: function () { }
            };
            """.trimIndent(),
            scope
        )
        RhinoScriptEngine.eval(js, scope)
        val value = RhinoScriptEngine.eval(actions, scope)?.toString().orEmpty()
        val logsJoined = RhinoScriptEngine.eval("__rec.logs.join('\u0001')", scope)?.toString().orEmpty()
        val variable = RhinoScriptEngine.eval("__rec.variable", scope)?.toString().orEmpty()
        return Result(
            value = value,
            logs = if (logsJoined.isEmpty()) emptyList() else logsJoined.split('\u0001'),
            variable = variable,
        )
    }

    // ============ 1. 默认关闭 ============

    @Test
    fun diag_isOffByDefault() {
        assertEquals("未设置 diag 时必须判为关闭", "false", eval("String(diagOn());").value)
        val rec = eval("diagLog('不该出现的诊断行');")
        assertEquals(
            "默认关闭时 diagLog 必须零输出（不产生 logcat 噪音）",
            0,
            rec.logs.count { it.startsWith("[hg-diag]") },
        )
    }

    @Test
    fun diag_enabled_emitsTechnicalDetail() {
        val rec = eval("diagLog('state=locked vidLen=8');", initialVar = "diag=1")
        val diagLines = rec.logs.filter { it.startsWith("[hg-diag]") }
        assertEquals("开启后应输出 1 条诊断日志", 1, diagLines.size)
        assertTrue("诊断行须携带技术细节（便于排查）", diagLines.first().contains("state=locked"))
    }

    // ============ 2. 持久化（覆盖安装后保留） ============

    @Test
    fun diag_toggle_persistsAndClearsSourceVariable() {
        val afterOn = eval("JSON.stringify(loginAction('toggleDiag', {}, {}));", initialVar = "")
        assertEquals(
            "首次点击（关闭 ⇒ 开启）必须写入源持久化变量 diag=1",
            "diag=1",
            afterOn.variable,
        )
        assertTrue(
            "开启后的界面文案应说明已开启，并明确不输出凭据值",
            afterOn.value.contains("已开启") && afterOn.value.contains("凭据"),
        )

        val afterOff = eval("JSON.stringify(loginAction('toggleDiag', {}, {}));", initialVar = "diag=1")
        assertEquals("再次点击（开启 ⇒ 关闭）必须清掉 diag 键", "", afterOff.variable)
        assertTrue("关闭后的文案应说明恢复默认", afterOff.value.contains("已关闭"))
    }

    @Test
    fun diag_survivesOtherKeys() {
        // 与播放方式共存：切换诊断不得抹掉 playmode
        val rec = eval("JSON.stringify(loginAction('toggleDiag', {}, {}));", initialVar = "playmode=browser")
        assertEquals(
            "切换诊断必须保留其它源变量（playmode）",
            "playmode=browser;diag=1",
            rec.variable,
        )
    }

    // ============ 3. 用户可见入口 ============

    @Test
    fun loginUi_showsDiagStateAndToggleButton() {
        val off = eval("JSON.stringify(loginUi({}));", initialVar = "")
        assertTrue("登录页应回显诊断输出当前状态", off.value.contains("诊断输出"))
        assertTrue("默认应显示为关闭", off.value.contains("关闭"))
        assertTrue("应提供切换按钮", off.value.contains("toggleDiag"))

        val on = eval("JSON.stringify(loginUi({}));", initialVar = "diag=1")
        assertTrue("已开启时应回显为开启", on.value.contains("诊断输出：开启"))
    }
}