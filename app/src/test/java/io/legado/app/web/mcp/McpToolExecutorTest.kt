package io.legado.app.web.mcp

import com.google.gson.JsonObject
import com.google.gson.JsonParser
import io.legado.app.web.TokenManager
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * MCP 工具执行器单测（web-mcp-productization 二期 · tasks 2.25 / REQ-2-104 ~ REQ-2-106）。
 *
 * 用**合成工具**覆盖四条路径（正常 / 超时 / 异常 / 截断）——域工具的 `invoke` 都要落 DB 与
 * Android 运行时，JVM 单测里只能测到"环境不可用"，故执行器行为一律用合成工具证明。
 */
class McpToolExecutorTest {

    private fun tool(
        name: String = "probe_tool",
        invoke: suspend (McpArgs) -> Any?,
    ) = McpTool(
        name = name,
        title = name,
        description = "测试用合成工具",
        domain = MCP_DOMAIN_META,
        level = TokenManager.Level.READONLY,
        inputSchema = McpJsonSchema.empty(),
        invoke = invoke,
    )

    private fun args(json: String = "{}"): McpArgs =
        JsonParser.parseString(json).asJsonObject.let { McpArgs(it) }

    // ---------------------------------------------------------------- 信封字段

    @Test
    fun execute_success_carriesAllEnvelopeFields() = runBlocking {
        val envelope = McpToolExecutor.execute(tool { mapOf("v" to 1) }, args(), "req-1")
        listOf("ok", "data", "error", "elapsedMs", "requestId").forEach { key ->
            assertTrue("REQ-2-104：信封须恒含字段 $key", envelope.has(key))
        }
        assertTrue(envelope.get("ok").asBoolean)
        assertFalse("成功时 isError 须为 false", envelope.get("isError").asBoolean)
        assertTrue(envelope.get("error").isJsonNull)
        assertEquals("req-1", envelope.get("requestId").asString)
        assertEquals(1, envelope.getAsJsonObject("data").get("v").asInt)
        // MCP 标准内容块（外部客户端渲染用）
        val firstBlock = envelope.getAsJsonArray("content")[0].asJsonObject
        assertEquals("text", firstBlock.get("type").asString)
        assertTrue(firstBlock.get("text").asString.contains("\"v\""))
    }

    @Test
    fun execute_nullReturn_dataIsExplicitNull() = runBlocking {
        val envelope = McpToolExecutor.execute(tool { null }, args(), "req-null")
        assertTrue(envelope.get("ok").asBoolean)
        assertTrue("data 须显式存在且为 null（字段集是不变量）", envelope.has("data"))
        assertTrue(envelope.get("data").isJsonNull)
    }

    // ---------------------------------------------------------------- 超时（REQ-2-106）

    @Test
    fun execute_timeout_returnsStructuredTimeout_notBareException() = runBlocking {
        val envelope = McpToolExecutor.execute(
            tool { delay(5_000); "never" },
            args(),
            "req-timeout",
            timeoutMs = 50L
        )
        assertFalse("超时须为结构化错误信封（ok=false），而非抛出裸异常", envelope.get("ok").asBoolean)
        assertTrue(envelope.get("isError").asBoolean)
        assertTrue(
            "超时话术须可识别：${envelope.get("error").asString}",
            envelope.get("error").asString.contains("超时")
        )
        assertTrue("超时须带 requestId 便于回溯", envelope.get("requestId").asString.isNotBlank())
    }

    // ---------------------------------------------------------------- 异常

    @Test
    fun execute_toolThrows_capturedAsEnvelopeWithMessage() = runBlocking {
        val envelope = McpToolExecutor.execute(tool { error("boom") }, args(), "req-err")
        assertFalse(envelope.get("ok").asBoolean)
        assertTrue(envelope.get("isError").asBoolean)
        assertEquals("boom", envelope.get("error").asString)
    }

    @Test
    fun execute_paramException_isRethrown_notSwallowedIntoEnvelope() = runBlocking {
        // 参数错误属 JSON-RPC 层语义（-32602），必须向上抛，不能变成"工具执行结果"
        val ex = runCatching {
            McpToolExecutor.execute(tool { throw McpParamException("缺少必填参数：x") }, args(), "req-param")
        }.exceptionOrNull()
        assertTrue("McpParamException 须向上抛", ex is McpParamException)
    }

    // ---------------------------------------------------------------- 1MB 截断（REQ-2-105）

    @Test
    fun execute_oversizedPayload_truncatedWithFlag() = runBlocking {
        // 约 2MB 载荷 ⇒ 必然超限
        val huge = "x".repeat(2 * 1024 * 1024)
        val envelope = McpToolExecutor.execute(tool { mapOf("blob" to huge) }, args(), "req-big")
        assertTrue("超限须置 truncated:true", envelope.get("truncated").asBoolean)
        assertTrue(
            "截断后体积须落回上限内",
            McpJson.utf8Size(McpJson.gson.toJson(envelope)) <= McpToolExecutor.MAX_RESPONSE_BYTES
        )
        assertTrue("截断后 data 退化为字符串（前缀文本）", envelope.get("data").isJsonPrimitive)
    }

    @Test
    fun execute_normalPayload_notTruncated() = runBlocking {
        val envelope = McpToolExecutor.execute(tool { mapOf("blob" to "small") }, args(), "req-small")
        assertFalse("未超限不得带 truncated", envelope.has("truncated"))
    }

    // ---------------------------------------------------------------- 信封直测（不经工具）

    @Test
    fun envelope_errorMessageIsString_notObject() {
        val envelope: JsonObject = McpToolExecutor.envelope(
            ok = false,
            data = null,
            errorMsg = "出错了",
            elapsedMs = 12L,
            requestId = "r"
        )
        assertEquals("出错了", envelope.get("error").asString)
        assertEquals(12L, envelope.get("elapsedMs").asLong)
    }
}
