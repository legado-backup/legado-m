package io.legado.app.model.analyzeRule

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * IF-01 回归守护（fix-rss-json-js-parse tasks 0.3 / 2.1 / 2.3）
 *
 * 复现「JSON 响应体 + JS 解密合成列表」型源恒取不到数据：
 * - `<js>` 返回 **JSON 数组字符串**（`JSON.stringify(list)`）⇒ 修复前 `getElements` 恒 1 项
 *   （`String` 被 `listOf(it)` 吞）——**本次修复的真缺口**；
 * - `<js>` 直接返回 JS 数组 ⇒ 修复前即为 N 项（Rhino `NativeArray` 本身实现 `java.util.List`），
 *   故本类保留该用例作**存量行为守护**；
 * - 逐项规则在 JSON 体下需显式 `@CSS:` 前缀才能按 CSS 解析（AD-02，既有能力）。
 *
 * 注意：`<js>` 块内必须是完整表达式，**顶层 `return` 会被 Rhino 编译拒绝**（编译失败 ⇒ 返回 null），
 * 故统一使用 IIFE `(function(){ … })()`（与真实源写法一致）。
 */
class AnalyzeRuleElementsTest {

    private val jsonBody = """{"status":1,"data":"x"}"""

    // ===== getElements 端到端（JSON 体 + <js> 列表规则） =====

    @Test
    fun getElements_jsReturnsArray_expandToN() {
        val rule = """<js>(function(){return ['<div class="rc"><h3>A</h3></div>','<div class="rc"><h3>B</h3></div>']})()</js>"""
        val list = AnalyzeRule().setContent(jsonBody).getElements(rule)
        assertEquals(2, list.size)
    }

    @Test
    fun getElements_jsReturnsJsonArrayString_expandToN() {
        val rule = """<js>(function(){return '[{"t":"A"},{"t":"B"},{"t":"C"}]'})()</js>"""
        val list = AnalyzeRule().setContent(jsonBody).getElements(rule)
        assertEquals(3, list.size)
    }

    @Test
    fun getElements_jsReturnsJsonObjectString_keptSingleElement() {
        // 对象串（非数组）不展开 —— 保持既有 1 元素语义
        val rule = """<js>(function(){return '{"items":[1,2]}'})()</js>"""
        val list = AnalyzeRule().setContent(jsonBody).getElements(rule)
        assertEquals(1, list.size)
    }

    @Test
    fun getElements_jsReturnsSingleHtmlString_keptSingleElement() {
        // 单块 HTML 串不展开（源侧需自行给容器选择器或返回数组）—— 保持既有 1 元素语义
        val rule = """<js>(function(){return '<div class="rc"><h3>A</h3></div>'})()</js>"""
        val list = AnalyzeRule().setContent(jsonBody).getElements(rule)
        assertEquals(1, list.size)
    }

    @Test
    fun getElements_jsThenCssSelector_chainExpandToN() {
        // 兜底逃生口：`<js>…</js>@CSS:<容器选择器>`。
        // ⚠️ 必须显式 `@CSS:` —— body 为 JSON 时，链式后续段的自动模式判定也会给出 JSONPath（陷阱 64），
        // 不加前缀则该段失效（实测 0 项）。
        val rule = """<js>(function(){return '<div class="rc"><h3>A</h3></div><div class="rc"><h3>B</h3></div>'})()</js>@CSS:div.rc"""
        val list = AnalyzeRule().setContent(jsonBody).getElements(rule)
        assertEquals(2, list.size)
    }

    @Test
    fun perItemRule_cssPrefix_parsesHtmlItem() {
        val rule = """<js>(function(){return ['<div class="rc"><h3>A</h3></div>']})()</js>"""
        val list = AnalyzeRule().setContent(jsonBody).getElements(rule)
        assertEquals(1, list.size)
        val itemRule = AnalyzeRule().setContent(list[0])
        assertEquals("A", itemRule.getString("@CSS:h3@text"))
    }

    // ===== jsonArrayStringToList 纯函数契约 =====

    @Test
    fun jsonArrayString_objects_expandToN() {
        val list = jsonArrayStringToList("""[{"t":"A"},{"t":"B"}]""")
        assertEquals(2, list?.size)
    }

    @Test
    fun jsonArrayString_strings_expandToN() {
        val list = jsonArrayStringToList("""["a","b","c"]""")
        assertEquals(3, list?.size)
    }

    @Test
    fun jsonArrayString_emptyArray_returnsEmptyList() {
        val list = jsonArrayStringToList("[]")
        assertTrue(list != null && list.isEmpty())
    }

    @Test
    fun plainHtmlString_returnsNull() {
        assertNull(jsonArrayStringToList("""<div class="rc"><h3>A</h3></div>"""))
    }

    @Test
    fun plainTextString_returnsNull() {
        assertNull(jsonArrayStringToList("hello"))
    }

    @Test
    fun truncatedArrayString_returnsNull() {
        assertNull(jsonArrayStringToList("[abc"))
        assertNull(jsonArrayStringToList("[1,2"))
    }

    @Test
    fun lenientOrMalformedArrayString_doesNotThrow() {
        // 契约：任何输入都不抛异常（内部 runCatching）。
        // 注：JsonPath(JsonSmart) 对部分非法写法宽容（实测 `['a']` 可解析为 ["a"]），
        // 故此处只断言「不抛异常」，非法/未命中一律回落 null 由调用方保持原语义。
        jsonArrayStringToList("['a']")
        jsonArrayStringToList("[1,2,]")
        jsonArrayStringToList("[<div>]")
    }

    @Test
    fun jsonObjectString_returnsNull() {
        assertNull(jsonArrayStringToList("""{"t":"A"}"""))
    }
}
