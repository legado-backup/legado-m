package io.legado.app.web.mcp

import com.google.gson.JsonParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 入参 JSON Schema 生成器单测（web-mcp-productization 二期 · tasks 2.3 / REQ-2-204）。
 *
 * 关键不变量：`required` **恒存在**（无必填时为空数组）—— 这是"缺失参数须返结构化错误"的
 * 契约基础（客户端据 schema 知道自己漏了什么），也是 [McpToolCatalogTest] 逐工具断言的前提。
 */
class McpJsonSchemaTest {

    @Test
    fun empty_hasRequiredArray_andOpensForExtraProps() {
        val schema = McpJsonSchema.empty()
        assertEquals("object", schema.get("type").asString)
        assertTrue("required 须恒存在", schema.has("required"))
        assertEquals(0, schema.getAsJsonArray("required").size())
        assertEquals(0, schema.getAsJsonObject("properties").size())
        assertTrue("额外参数须放行（AI 多传键不应导致校验失败）", schema.get("additionalProperties").asBoolean)
    }

    @Test
    fun of_requiredAndOptional_landInProperties_withRequiredNames() {
        val schema = McpJsonSchema.of(
            required = mapOf("a" to McpJsonSchema.TYPE_STRING, "b" to McpJsonSchema.TYPE_INTEGER),
            optional = mapOf("c" to McpJsonSchema.TYPE_BOOLEAN),
            descriptions = mapOf("a" to "第一参数")
        )
        val properties = schema.getAsJsonObject("properties")
        assertEquals(setOf("a", "b", "c"), properties.keySet())
        assertEquals(McpJsonSchema.TYPE_STRING, properties.getAsJsonObject("a").get("type").asString)
        assertEquals(McpJsonSchema.TYPE_INTEGER, properties.getAsJsonObject("b").get("type").asString)
        assertEquals(McpJsonSchema.TYPE_BOOLEAN, properties.getAsJsonObject("c").get("type").asString)
        assertEquals("第一参数", properties.getAsJsonObject("a").get("description").asString)
        assertEquals(
            "required 只含必填项",
            setOf("a", "b"),
            schema.getAsJsonArray("required").map { it.asString }.toSet()
        )
    }

    @Test
    fun arrayType_carriesItemsOfString() {
        val properties = McpJsonSchema.of(required = mapOf("urls" to McpJsonSchema.TYPE_ARRAY))
            .getAsJsonObject("properties")
        val items = properties.getAsJsonObject("urls").getAsJsonObject("items")
        assertEquals(McpJsonSchema.TYPE_STRING, items.get("type").asString)
    }

    @Test
    fun schema_isValidJsonRoundTrip() {
        // Schema 会被塞进 tools/list 的 inputSchema 字段 ⇒ 必须可被客户端当 JSON 解析
        val schema = McpJsonSchema.of(required = mapOf("bookUrl" to McpJsonSchema.TYPE_STRING))
        val text = McpJson.gson.toJson(schema)
        assertEquals(schema, JsonParser.parseString(text))
    }

    @Test
    fun singleRequiredString_helper() {
        val schema = McpJsonSchema.singleRequiredString("url", "源地址")
        assertEquals(1, schema.getAsJsonArray("required").size())
        assertEquals("url", schema.getAsJsonArray("required")[0].asString)
        assertEquals("源地址", schema.getAsJsonObject("properties").getAsJsonObject("url").get("description").asString)
        assertFalse(schema.has("additionalProperties") && !schema.get("additionalProperties").asBoolean)
    }
}
