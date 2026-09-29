package io.legado.app.web.api.routes

import fi.iki.elonen.NanoHTTPD.Method
import io.legado.app.web.TokenManager.Level
import io.legado.app.web.api.ApiRegistry
import io.legado.app.web.api.ApiRouteBootstrap
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

/**
 * 三期补记 · 7 条控制台端点路由的注册锚点（issues-found **IF-12**）。
 *
 * 背景：这 7 项能力的内核**二期就已存在**（[io.legado.app.service.kernel.BookmarkKernel] /
 * [io.legado.app.service.kernel.TtsKernel]），但三期做 D/E 组端点时**只漏了路由** ⇒ 控制台 P8/P9
 * 长期挂着「后端未提供 HTTP 端点」的降级文案（把"我们漏接线"写成了"后端不支持"）。
 *
 * 为什么必须用测试钉住：路由被删**不会编译错**，只会让控制台页面静默退回降级/空壳 ⇒ 必须断言
 * 「方法 + 路径 + 级别」。级别断言同时锁住安全口径：读=READONLY（可免令牌只读）、写=MANAGE。
 */
class ConsoleEndpointAdditionsTest {

    private val patchEndpoints = listOf(
        Triple(Method.GET, "/getSceneBookmarks", Level.READONLY),
        Triple(Method.POST, "/saveSceneBookmark", Level.MANAGE),
        Triple(Method.POST, "/deleteSceneBookmark", Level.MANAGE),
        Triple(Method.POST, "/deleteBookmark", Level.MANAGE),
        Triple(Method.GET, "/getHttpTtsList", Level.READONLY),
        Triple(Method.POST, "/saveHttpTts", Level.MANAGE),
        Triple(Method.POST, "/deleteHttpTts", Level.MANAGE),
    )

    @Test
    fun patchEndpoints_areRegisteredWithExpectedLevel() {
        ApiRouteBootstrap.install()
        patchEndpoints.forEach { (method, path, level) ->
            val route = ApiRegistry.find(method, path)
            assertNotNull(
                "补记端点必须仍注册：$method $path（删除不会编译错，会让控制台 P8/P9 静默退回降级文案）",
                route,
            )
            assertEquals("$path 的级别须为 $level（读=READONLY / 写=MANAGE）", level, route!!.level)
        }
    }

    /** 补记端点**不新增 MCP 工具**（口径见 `McpToolCatalogTest`）：故不得带 `mcpToolName` 对拍标注。 */
    @Test
    fun patchEndpoints_doNotDeclareMcpToolNames() {
        ApiRouteBootstrap.install()
        patchEndpoints.forEach { (method, path, _) ->
            val route = ApiRegistry.find(method, path)
            assertNotNull("补记端点须存在：$method $path", route)
            assertEquals(
                "$path 不应声明 mcpToolName（本批只补 HTTP 路由，未新增 MCP 工具）",
                null,
                route!!.mcpToolName,
            )
        }
    }
}