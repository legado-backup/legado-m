package io.legado.app.web.mcp

import com.google.gson.JsonObject
import com.google.gson.JsonParser
import io.legado.app.web.TokenManager
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * MCP 协议核单测（web-mcp-productization 二期 · tasks 1.10 / REQ-2-101 ~ REQ-2-108）。
 *
 * 覆盖：四方法主路径 / 错误码逐码 / 双闸（401 与 403）/ 信封字段齐备 / 通知 202 / 方法分支
 * （GET 405 / DELETE 204）/ 分页字段。
 *
 * **不在此处跑真实工具**（`tools/call` 的成功与异常路径由 [McpToolExecutorTest] 用合成工具覆盖）——
 * 域工具的执行体全都要落 DB / Android 运行时，JVM 单测里跑它们只会测到"环境不可用"。
 */
class McpServerTest {

    private fun post(body: String?, level: TokenManager.Level = TokenManager.Level.READONLY) =
        McpHttpContext(method = "POST", level = level, body = body)

    private fun json(response: McpHttpResponse): JsonObject =
        JsonParser.parseString(response.body).asJsonObject

    private fun rpc(method: String, params: JsonObject? = null, id: Int = 1): String {
        val obj = JsonObject().apply {
            addProperty("jsonrpc", "2.0")
            addProperty("id", id)
            addProperty("method", method)
            params?.let { add("params", it) }
        }
        return McpJson.gson.toJson(obj)
    }

    // ---------------------------------------------------------------- 传输分支

    @Test
    fun get_returns405WithAllowHeader() = runBlocking {
        val resp = McpServer.handle(McpHttpContext(method = "GET", level = TokenManager.Level.ADMIN))
        assertEquals("REQ-2-102：GET/SSE 不支持时须返 405", 405, resp.status)
        assertEquals("POST, DELETE", resp.headers["Allow"])
    }

    @Test
    fun delete_returns204() = runBlocking {
        val resp = McpServer.handle(McpHttpContext(method = "DELETE", level = TokenManager.Level.ADMIN))
        assertEquals("REQ-2-102：DELETE 会话关闭返 204", 204, resp.status)
        assertEquals("204 必须空体", "", resp.body)
    }

    @Test
    fun put_returns405() = runBlocking {
        val resp = McpServer.handle(McpHttpContext(method = "PUT", level = TokenManager.Level.ADMIN))
        assertEquals(405, resp.status)
    }

    // ---------------------------------------------------------------- 第一闸

    @Test
    fun noToken_returns401_unauthorized_notEnteringProtocol() = runBlocking {
        val resp = McpServer.handle(post(rpc("initialize"), TokenManager.Level.NONE))
        assertEquals("REQ-2-301 / SC-2-02：无令牌 initialize 须 401", 401, resp.status)
        val body = json(resp)
        assertEquals("unauthorized", body.get("errorMsg").asString)
        assertEquals(401, body.get("code").asInt)
        assertFalse("401 响应体不得出现 JSON-RPC result（协议层未进入）", body.has("result"))
    }

    // ---------------------------------------------------------------- 解析错误

    @Test
    fun blankBody_returns400_parseError() = runBlocking {
        val resp = McpServer.handle(post(""))
        assertEquals(400, resp.status)
        assertEquals(MCP_RPC_PARSE_ERROR, json(resp).getAsJsonObject("error").get("code").asInt)
    }

    @Test
    fun invalidJson_returns400_parseError() = runBlocking {
        val resp = McpServer.handle(post("not-a-json"))
        assertEquals(400, resp.status)
        assertEquals(MCP_RPC_PARSE_ERROR, json(resp).getAsJsonObject("error").get("code").asInt)
    }

    @Test
    fun missingMethod_returns32600_invalidRequest() = runBlocking {
        val resp = McpServer.handle(post("""{"jsonrpc":"2.0","id":7}"""))
        assertEquals(200, resp.status)
        assertEquals(MCP_RPC_INVALID_REQUEST, json(resp).getAsJsonObject("error").get("code").asInt)
    }

    @Test
    fun unknownMethod_returns32601() = runBlocking {
        val resp = McpServer.handle(post(rpc("tools/nope")))
        assertEquals(200, resp.status)
        assertEquals(MCP_RPC_METHOD_NOT_FOUND, json(resp).getAsJsonObject("error").get("code").asInt)
    }

    // ---------------------------------------------------------------- initialize

    @Test
    fun initialize_returnsProtocolVersionAndCapabilities() = runBlocking {
        val resp = McpServer.handle(post(rpc("initialize")))
        assertEquals(200, resp.status)
        val result = json(resp).getAsJsonObject("result")
        assertEquals("REQ-2-103：协议版本须与 AiMcpClient 常量一致", "2025-06-18", result.get("protocolVersion").asString)
        assertFalse(result.getAsJsonObject("capabilities").getAsJsonObject("tools").get("listChanged").asBoolean)
        assertNotNull(result.getAsJsonObject("serverInfo").get("name"))
        assertTrue("serverInfo.version 须非空", result.getAsJsonObject("serverInfo").get("version").asString.isNotBlank())
    }

    @Test
    fun initialize_echoesRequestId() = runBlocking {
        val resp = McpServer.handle(post(rpc("initialize", id = 42)))
        assertEquals(42, json(resp).get("id").asInt)
    }

    // ---------------------------------------------------------------- 通知

    @Test
    fun initializedNotification_returns202_emptyBody() = runBlocking {
        val notification = """{"jsonrpc":"2.0","method":"notifications/initialized"}"""
        val resp = McpServer.handle(post(notification))
        assertEquals("REQ-2-101：通知返 202", 202, resp.status)
        assertEquals("", resp.body)
    }

    @Test
    fun unknownNotification_returns202_withoutError() = runBlocking {
        val notification = """{"jsonrpc":"2.0","method":"notifications/whatever"}"""
        val resp = McpServer.handle(post(notification))
        assertEquals("通知（无 id）不需要响应体", 202, resp.status)
    }

    // ---------------------------------------------------------------- tools/list（第二闸·列表侧）

    @Test
    fun toolsList_adminSeesAll_debugSeesL3Too() = runBlocking {
        val resp = McpServer.handle(post(rpc("tools/list"), TokenManager.Level.ADMIN))
        val tools = json(resp).getAsJsonObject("result").getAsJsonArray("tools")
        assertEquals(McpToolCatalog.all().size, tools.size())
    }

    @Test
    fun toolsList_readonlyCannotSeeManageOrAdmin() = runBlocking {
        val resp = McpServer.handle(post(rpc("tools/list"), TokenManager.Level.READONLY))
        val tools = json(resp).getAsJsonObject("result").getAsJsonArray("tools")
        assertEquals(McpToolCatalog.visibleFor(TokenManager.Level.READONLY).size, tools.size())
        tools.forEach { element ->
            val name = element.asJsonObject.get("name").asString
            val tool = McpToolCatalog.find(name)
            assertNotNull(name, tool)
            assertEquals("readonly 令牌不得看见高于 READONLY 的工具：$name", TokenManager.Level.READONLY, tool!!.level)
        }
    }

    @Test
    fun toolsList_eachToolCarriesStandardFields() = runBlocking {
        val resp = McpServer.handle(post(rpc("tools/list"), TokenManager.Level.ADMIN))
        val tools = json(resp).getAsJsonObject("result").getAsJsonArray("tools")
        assertTrue("目录不应为空", tools.size() > 0)
        tools.forEach { element ->
            val tool = element.asJsonObject
            assertTrue(tool.get("name").asString.isNotBlank())
            assertTrue("REQ-2-207：每个工具须有一句话说明", tool.get("description").asString.isNotBlank())
            assertNotNull("REQ-2-204：须带 inputSchema", tool.get("inputSchema"))
            assertTrue("REQ-2-204：schema 须含 required 数组", tool.getAsJsonObject("inputSchema").has("required"))
            assertNotNull("annotations.readOnlyHint 须齐备", tool.getAsJsonObject("annotations").get("readOnlyHint"))
            assertTrue("REQ-2-203：须带 domain 域元数据", tool.get("domain").asString.isNotBlank())
        }
    }

    @Test
    fun toolsList_noNextCursorWhenUnderPageSize() = runBlocking {
        val resp = McpServer.handle(post(rpc("tools/list"), TokenManager.Level.ADMIN))
        val result = json(resp).getAsJsonObject("result")
        assertFalse("工具数远小于单页上限时不应出现 nextCursor", result.has("nextCursor"))
    }

    // ---------------------------------------------------------------- tools/call（第二闸·调用侧）

    @Test
    fun toolsCall_missingName_returns32602() = runBlocking {
        val resp = McpServer.handle(post(rpc("tools/call", JsonObject())))
        assertEquals(200, resp.status)
        assertEquals(MCP_RPC_INVALID_PARAMS, json(resp).getAsJsonObject("error").get("code").asInt)
    }

    @Test
    fun toolsCall_unknownTool_returns32602() = runBlocking {
        val params = JsonObject().apply { addProperty("name", "no_such_tool") }
        val resp = McpServer.handle(post(rpc("tools/call", params)))
        assertEquals(200, resp.status)
        assertEquals(MCP_RPC_INVALID_PARAMS, json(resp).getAsJsonObject("error").get("code").asInt)
    }

    @Test
    fun toolsCall_readonlyOnManageTool_returns403_insufficientLevel() = runBlocking {
        // SC-2-04：readonly 令牌强行调用 manage 工具 → 403 + 明示所需级别
        val tool = McpToolCatalog.all().first { it.level == TokenManager.Level.MANAGE }
        val params = JsonObject().apply {
            addProperty("name", tool.name)
            add("arguments", JsonObject())
        }
        val resp = McpServer.handle(post(rpc("tools/call", params), TokenManager.Level.READONLY))
        assertEquals("SC-2-04：级别不足须返 403", 403, resp.status)
        val error = json(resp).getAsJsonObject("error")
        assertEquals(MCP_RPC_INSUFFICIENT_LEVEL, error.get("code").asInt)
        assertTrue(
            "违规提示须明示所需级别：${error.get("message").asString}",
            error.get("message").asString.contains(TokenManager.Level.MANAGE.name)
        )
    }

    @Test
    fun toolsCall_missingRequiredParam_returns32602() = runBlocking {
        // REQ-2-204：缺失必填参数须返结构化参数错误（在触碰业务前就被拦下 —— 故 JVM 单测可断言）
        val params = JsonObject().apply {
            addProperty("name", "book_get_content")
            add("arguments", JsonObject())
        }
        val resp = McpServer.handle(post(rpc("tools/call", params), TokenManager.Level.ADMIN))
        assertEquals(200, resp.status)
        assertEquals(MCP_RPC_INVALID_PARAMS, json(resp).getAsJsonObject("error").get("code").asInt)
    }

    @Test
    fun toolsCall_unknownButValidName_doesNotLeakExecutionDetails() = runBlocking {
        val params = JsonObject().apply { addProperty("name", "book_save_info") }
        // `book_save_info` 在域文件中尚未声明（§2 分批落地）⇒ 应报"工具不存在"，而不是崩
        val resp = McpServer.handle(post(rpc("tools/call", params), TokenManager.Level.ADMIN))
        val error = json(resp).getAsJsonObject("error")
        assertEquals(MCP_RPC_INVALID_PARAMS, error.get("code").asInt)
        assertNull("不得回传异常堆栈字段", error.get("stackTrace"))
    }
}
