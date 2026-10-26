package io.legado.app.model.jsSource

import com.google.gson.JsonParser
import com.script.ScriptBindings
import com.script.rhino.RhinoScriptEngine
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 登录界面「文案 ↔ 可操作路径」一致性 + 三态结论可信（tasks 4.8.5 / spec Requirement E-3）。
 *
 * 为什么用 Rhino 跑真交付源：`loginUi` 完全住在源的 `mainJs` 里（宿主只负责渲染 rows），
 * JVM 侧断言不到 → 必须把交付源加载进 Rhino 直接调 `loginUi(state)`。
 *
 * 断言要点（带期望值）：
 * 1. **三态**：`loggedIn` = `""` / `"false"` / `"true"` 对应「无法判定」/「未放行」/「已放行」，
 *    且**互不串味**（旧实现只有两态，请求失败会被显示成"未登录"）；
 * 2. **两条真实可操作路径**都在界面里：网页登录（含扫码步骤）+ 手机号/短信验证码说明；
 * 3. **兜底路径**（整段 Cookie 粘贴）保留 —— 站内滑块/扫码在内置浏览器不可用时仍可登录；
 * 4. 整个界面**不出现任何凭据值**（只允许键名与数量）。
 */
class LoginUiPathAlignmentTest {

    private val fixture = File("src/test/resources/fixtures/js_source_video_20261026.json")

    /** 在 Rhino 里加载交付源，返回 `loginUi(state)` 的 JSON 文本。 */
    private fun renderLoginUi(stateJson: String): String {
        assertTrue("夹具不存在：${fixture.absolutePath}", fixture.exists())
        val js = JsonParser.parseString(fixture.readText())
            .asJsonArray[0].asJsonObject.get("mainJs")?.asString.orEmpty()
        assertTrue("夹具 mainJs 为空（夹具与交付源不同步）", js.isNotBlank())

        val scope = RhinoScriptEngine.getRuntimeScope(ScriptBindings())
        RhinoScriptEngine.eval(
            """
            var __store = { sid_guard: "sentinel-value-must-not-leak", sessionid: "sentinel-2" };
            var java = {
              ajax: function () { return ""; },
              log: function () { },
              startBrowser: function () { }
            };
            var cookie = {
              getCookie: function () {
                var out = []; for (var k in __store) out.push(k + "=" + __store[k]); return out.join("; ");
              },
              getWebCookie: function () { return ""; },
              setCookie: function () { }, replaceCookie: function () { },
              removeCookie: function () { }, setWebCookie: function () { }
            };
            var source = {
              getVariable: function () { return ""; }, putVariable: function () { }, removeLoginInfo: function () { }
            };
            """.trimIndent(),
            scope
        )
        RhinoScriptEngine.eval(js, scope)
        return RhinoScriptEngine.eval("JSON.stringify(loginUi($stateJson))", scope).toString()
    }

    /** 取界面里所有 label/button 的文案（拼成一行便于 contains 断言）。 */
    private fun labelsOf(uiJson: String): String {
        val rows = JsonParser.parseString(uiJson).asJsonObject.getAsJsonArray("rows")
        return rows.map { it.asJsonObject.get("name")?.asString.orEmpty() }.joinToString("\n")
    }

    // ============ 1. 三态结论互不串味 ============

    @Test
    fun undeterminedState_isNotShownAsNotLoggedIn() {
        val text = labelsOf(renderLoginUi("""{"loggedIn":"","msg":"尚未检测"}"""))
        assertTrue("空态必须显示「无法判定」", text.contains("无法判定"))
        assertTrue("不得把空态显示成「未放行」", !text.contains("账号状态：未放行"))
        assertTrue("不得把空态显示成「已放行」", !text.contains("账号状态：已放行"))
    }

    @Test
    fun notGrantedState_isShownAsNotGranted() {
        val text = labelsOf(renderLoginUi("""{"loggedIn":"false","msg":"探测完成"}"""))
        assertTrue("false 必须显示「未放行」", text.contains("未放行"))
        assertTrue("不得显示为「无法判定」", !text.contains("账号状态：无法判定"))
    }

    @Test
    fun grantedState_isShownAsGranted() {
        val text = labelsOf(renderLoginUi("""{"loggedIn":"true","msg":"探测完成"}"""))
        assertTrue("true 必须显示「已放行」", text.contains("已放行"))
        assertTrue("不得显示为「未放行」", !text.contains("账号状态：未放行"))
    }

    // ============ 2. 两条真实可操作路径 ============

    @Test
    fun bothLoginPaths_areOperableFromThePage() {
        val text = labelsOf(renderLoginUi("{}"))
        assertTrue("须提供网页登录入口（按钮 action=webLogin）",
            text.contains("打开网页登录"))
        assertTrue("须给扫码的可操作步骤（截图 → App 扫一扫）", text.contains("扫码"))
        assertTrue("须说明短信验证码这条路径", text.contains("验证码"))
        assertTrue("登录完成后须能同步 WebView 凭据", text.contains("同步网页登录凭据"))
        assertTrue("须能一键检测", text.contains("检测登录状态"))
    }

    @Test
    fun cookieFallbackPath_isRetained() {
        val ui = renderLoginUi("{}")
        val text = labelsOf(ui)
        assertTrue("须保留整段 Cookie 兜底路径（站内滑块/扫码不可用时）",
            text.contains("Cookie") && text.contains("保存 Cookie 并检测"))
        // 表单字段必须带 key（宿主渲染协议要求）
        assertTrue("Cookie 输入须声明 key（否则宿主无法回传）", ui.contains("\"key\":\"cookie\""))
    }

    // ============ 3. 界面不泄露凭据值 ============

    @Test
    fun loginUi_neverLeaksCredentialValues() {
        val ui = renderLoginUi("{}")
        assertTrue("不得出现存储层凭据值（哨兵）", !ui.contains("sentinel-value-must-not-leak"))
        assertTrue("不得出现第二个存储层凭据值（哨兵）", !ui.contains("sentinel-2"))
        assertEquals(
            "凭据体检只报数量与键名（数量为 2 个键）",
            true,
            ui.contains("存储层 2 个"),
        )
    }
}
