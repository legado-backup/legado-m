package io.legado.app.web.mcp

import fi.iki.elonen.NanoHTTPD
import fi.iki.elonen.NanoHTTPD.Method
import io.legado.app.web.TokenManager
import io.legado.app.web.api.ApiContext
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * MCP NanoHTTPD 适配层单测（web-mcp-productization 二期 · tasks 4.2）。
 *
 * 锁"**契约桥接**"三件事：① 级别从 [ApiContext] 原样透传（不重解析令牌）；
 * ② 状态码 / 响应体 / `Allow` 头落到 [NanoHTTPD.Response] 上不失真；
 * ③ 返回的是 [NanoHTTPD.Response] ⇒ 走 `ApiEnvelope.dispatch` 的逃生舱，`HttpServer.kt` 零改动（SC-2-16）。
 */
class McpHttpHandlerTest {

    private fun ctx(
        method: Method,
        body: String? = null,
        level: TokenManager.Level = TokenManager.Level.READONLY,
    ) = ApiContext(method, "/mcp", emptyMap(), body, emptyMap(), level)

    private fun bodyOf(response: NanoHTTPD.Response): String =
        response.data.readBytes().toString(Charsets.UTF_8)

    @Test
    fun post_withoutToken_is401() = runBlocking {
        val resp = McpHttpHandler.handle(ctx(Method.POST, """{"jsonrpc":"2.0","id":1,"method":"initialize"}""", TokenManager.Level.NONE))
        assertEquals(401, resp.status.requestStatus)
        // NanoHTTPD 会为 JSON 补 `; charset=UTF-8` ⇒ 只断言 MIME 主干
        assertEquals(true, resp.mimeType.startsWith("application/json"))
    }

    @Test
    fun post_initialize_is200_withJsonRpcBody() = runBlocking {
        val resp = McpHttpHandler.handle(ctx(Method.POST, """{"jsonrpc":"2.0","id":1,"method":"initialize"}"""))
        assertEquals(200, resp.status.requestStatus)
        val text = bodyOf(resp)
        assertEquals(true, text.contains("2025-06-18"))
        assertEquals(true, text.contains("serverInfo"))
    }

    @Test
    fun get_is405_withAllowHeader() = runBlocking {
        val resp = McpHttpHandler.handle(ctx(Method.GET, level = TokenManager.Level.ADMIN))
        assertEquals(405, resp.status.requestStatus)
        assertEquals("POST, DELETE", resp.getHeader("Allow"))
    }

    @Test
    fun delete_is204_withEmptyBody() = runBlocking {
        val resp = McpHttpHandler.handle(ctx(Method.DELETE, level = TokenManager.Level.ADMIN))
        assertEquals(204, resp.status.requestStatus)
        assertEquals("", bodyOf(resp))
    }

    @Test
    fun level_isPassedThrough_notReparsedFromToken() = runBlocking {
        // 用 ADMIN 级上下文发 tools/list ⇒ 应看到全部工具（若适配层丢了级别，只会看到 readonly 面）
        val resp = McpHttpHandler.handle(ctx(Method.POST, """{"jsonrpc":"2.0","id":1,"method":"tools/list"}""", TokenManager.Level.ADMIN))
        val text = bodyOf(resp)
        assertEquals(true, text.contains("bookshelf_list"))
        assertEquals(true, text.contains("tools"))
    }
}
