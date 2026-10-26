package io.legado.app.model.jsSource

import com.google.gson.JsonParser
import com.script.ScriptBindings
import com.script.rhino.RhinoScriptEngine
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * 交付源登录体检「键名掩码」回归测试（design AD-04 / spec Requirement C-2a / tasks 5.1）。
 *
 * **红线**：诊断输出只允许出现**键名**，绝不出现任何 Cookie 值（项目 output-safety 硬约束）。
 * 本测试在 Rhino 里跑真交付源的 `cookieDiagnosis()`，往 store/WebView 两层塞入
 * **可辨识的哨兵值**，断言输出里查不到任何哨兵串。
 */
class LoginProbeMaskingTest {

    private val fixture = File("src/test/resources/fixtures/js_source_video_20261026.json")

    /** 哨兵值：只要泄露就一定能被字符串匹配抓到。 */
    private val sentinelA = "SENTINEL_VALUE_ALPHA_1234567890"
    private val sentinelB = "SENTINEL_VALUE_BETA_0987654321"

    private fun runDiagnosis(): String {
        assertTrue("夹具不存在：${fixture.absolutePath}", fixture.exists())
        val js = JsonParser.parseString(fixture.readText())
            .asJsonArray[0].asJsonObject.get("mainJs")?.asString.orEmpty()
        assertTrue("夹具 mainJs 为空（夹具与交付源不同步）", js.isNotBlank())

        val scope = RhinoScriptEngine.getRuntimeScope(ScriptBindings())
        RhinoScriptEngine.eval(
            """
            var __store = { "sid_guard": "$sentinelA", "ttwid": "$sentinelB" };
            var __web = { "sessionid": "$sentinelA" };
            var java = { ajax: function () { return ""; }, log: function () { }, startBrowser: function () { } };
            var cookie = {
              getCookie: function () {
                var out = []; for (var k in __store) out.push(k + "=" + __store[k]); return out.join("; ");
              },
              getWebCookie: function () {
                var out = []; for (var k in __web) out.push(k + "=" + __web[k]); return out.join("; ");
              },
              setCookie: function () { }, replaceCookie: function () { },
              removeCookie: function () { }, setWebCookie: function () { }
            };
            var source = { getVariable: function () { return ""; }, putVariable: function () { }, removeLoginInfo: function () { } };
            """.trimIndent(),
            scope
        )
        RhinoScriptEngine.eval(js, scope)
        return RhinoScriptEngine.eval("JSON.stringify(cookieDiagnosis())", scope).toString()
    }

    @Test
    fun diagnosis_neverLeaksAnyValue() {
        val out = runDiagnosis()
        assertEquals("诊断输出泄露 store 层值（C-2a 红线）：出现次数须为 0", 0, countOf(out, sentinelA))
        assertEquals("诊断输出泄露 WebView 层值（C-2a 红线）：出现次数须为 0", 0, countOf(out, sentinelB))
    }

    @Test
    fun diagnosis_containsOnlyKeyNames() {
        val diag = parseDiagnosis()
        assertEquals("store 层键名集合", setOf("sid_guard", "ttwid"), diag.store.toSet())
        assertEquals("WebView 层键名集合", setOf("sessionid"), diag.web.toSet())
        assertEquals("两层并集", setOf("sid_guard", "ttwid", "sessionid"), diag.union.toSet())
    }

    @Test
    fun diagnosis_marksLoginKeysByOrigin() {
        val diag = parseDiagnosis()
        assertEquals("store 层键应标记为 store", "store", diag.origin["sid_guard"])
        assertEquals("仅 WebView 层的键应标记为 web", "web", diag.origin["sessionid"])
    }

    @Test
    fun diagnosis_marked_containsOnlyDeclaredLoginKeys() {
        val diag = parseDiagnosis()
        assertEquals(
            "登录态键名清单只应含源内声明的登录键（sid_guard + sessionid）；风控键 ttwid 不得进入",
            setOf("sid_guard", "sessionid"),
            diag.marked.toSet(),
        )
        assertTrue(
            "风控键必须被排除在登录态清单之外",
            "ttwid" !in diag.marked,
        )
    }

    private fun countOf(text: String, needle: String): Int {
        var count = 0
        var idx = text.indexOf(needle)
        while (idx >= 0) {
            count++
            idx = text.indexOf(needle, idx + needle.length)
        }
        return count
    }

    /** 解析后的诊断结果（只取键名相关字段，便于带期望值断言）。 */
    private data class Diag(
        val store: List<String>,
        val web: List<String>,
        val union: List<String>,
        val origin: Map<String, String>,
        val marked: List<String>,
    )

    private fun parseDiagnosis(): Diag {
        val obj = JsonParser.parseString(runDiagnosis()).asJsonObject
        fun arr(key: String) = obj.getAsJsonArray(key).map { it.asString }
        val originObj = obj.getAsJsonObject("origin")
        val origin = originObj.keySet().associateWith { originObj.get(it).asString }
        return Diag(
            store = arr("store"),
            web = arr("web"),
            union = arr("union"),
            origin = origin,
            marked = arr("marked"),
        )
    }
}