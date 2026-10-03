package io.legado.app.web.mcp

import com.google.gson.JsonParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 工具入参读取单测（web-mcp-productization 二期 · tasks 2.2）。
 *
 * 口径：**类型不匹配一律按"缺失"处理**（不抛类型转换异常），必填由 `requireXxx` 显式声明 ⇒
 * "缺参"与"类型错"收敛到同一条结构化参数错误路径（REQ-2-204）。
 */
class McpToolArgsTest {

    private fun args(json: String): McpArgs =
        McpArgs(JsonParser.parseString(json).asJsonObject)

    // ---------------------------------------------------------------- str

    @Test
    fun str_readsPrimitive_andNullsOutMismatches() {
        val a = args("""{"s":"v","num":3,"flag":true,"obj":{},"arr":[],"nil":null}""")
        assertEquals("v", a.str("s"))
        assertEquals("3", a.str("num"))
        assertEquals("true", a.str("flag"))
        assertNull("对象不是字符串参数", a.str("obj"))
        assertNull("数组不是字符串参数", a.str("arr"))
        assertNull("JSON null 视为未提供", a.str("nil"))
        assertNull("不存在的键返回 null", a.str("missing"))
    }

    @Test
    fun requireStr_throwsOnMissingOrEmpty_orReturnsValue() {
        val a = args("""{"empty":"","k":"ok"}""")
        assertNull(a.str("none"))
        assertTrue(
            "缺失必填须抛 McpParamException（→ -32602）",
            runCatching { a.requireStr("none") }.exceptionOrNull() is McpParamException
        )
        assertTrue(
            "空串同样按缺失处理（AI 常传空串占位）",
            runCatching { a.requireStr("empty") }.exceptionOrNull() is McpParamException
        )
        assertEquals("ok", a.requireStr("k"))
    }

    // ---------------------------------------------------------------- int / long

    @Test
    fun int_usesDefaultOrThrows() {
        val a = args("""{"n":5,"bad":"abc"}""")
        assertEquals(5, a.int("n"))
        assertEquals(7, a.int("missing", 7))
        assertEquals("非法格式回退默认值", 7, a.int("bad", 7))
        assertEquals(5, a.requireInt("n"))
        assertTrue(runCatching { a.requireInt("bad") }.exceptionOrNull() is McpParamException)
    }

    @Test
    fun long_readsAndDefaults() {
        val a = args("""{"big":1712345678901}""")
        assertEquals(1712345678901L, a.long("big"))
        assertEquals(9L, a.long("missing", 9L))
    }

    // ---------------------------------------------------------------- bool

    @Test
    fun bool_acceptsBooleanAndStringForms() {
        val a = args("""{"t":true,"f":false,"one":1,"zero":0,"yes":"yes","no":"no","x":"other"}""")
        assertTrue(a.bool("t"))
        assertFalse(a.bool("f"))
        assertTrue(a.bool("one"))
        assertFalse(a.bool("zero"))
        assertTrue(a.bool("yes"))
        assertFalse(a.bool("no"))
        assertEquals("无法识别时回退默认值", true, a.bool("x", true))
        assertEquals("缺失时回退默认值", false, a.bool("missing"))
    }

    // ---------------------------------------------------------------- 列表

    @Test
    fun strList_readsArrayOrEmpty() {
        val a = args("""{"urls":["a","b"],"single":"x","obj":{}}""")
        assertEquals(listOf("a", "b"), a.strList("urls"))
        assertEquals("非数组 → 空列表", emptyList<String>(), a.strList("single"))
        assertEquals(emptyList<String>(), a.strList("obj"))
        assertEquals(emptyList<String>(), a.strList("missing"))
    }

    @Test
    fun raw_exposesUnderlyingObject() {
        val obj = JsonParser.parseString("""{"a":1}""").asJsonObject
        assertEquals(obj, McpArgs(obj).raw())
    }
}
