package io.legado.app.web.api.routes

import fi.iki.elonen.NanoHTTPD.Method
import io.legado.app.web.TokenManager.Level
import io.legado.app.web.api.ApiRouteBootstrap
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

/**
 * B12：外部端到端巡检接入内置统一能力的**路由级护栏**。
 *
 * 级别：启动腿是**动作类** ⇒ 必须 `MANAGE`（`READONLY` 会在过渡期免令牌放行，等于任何同网设备
 * 都能触发全库校验）；且**不投影 MCP**（不新增约定工具 ⇒ 工具计数契约不变）。
 * 读报告腿保持只读 + MCP 投影不变（三端同一份结果的读出口径）。
 */
class DebugRoutesStartCheckSourceTest {

    private fun routeOf(path: String, method: Method = Method.POST) =
        DebugRoutes.routes.first { it.path == path && it.method == method }

    @Test
    fun `启动巡检端点须MANAGE且不投影MCP`() {
        ApiRouteBootstrap.install()
        val route = routeOf("/startCheckSource")
        assertEquals("动作类端点须 MANAGE", Level.MANAGE, route.level)
        assertNull("不新增 MCP 工具 ⇒ 工具计数契约不变", route.mcpToolName)
    }

    @Test
    fun `读报告端点仍为READONLY且保留MCP投影`() {
        ApiRouteBootstrap.install()
        val route = routeOf("/getCheckSourceReport", Method.GET)
        assertEquals(Level.READONLY, route.level)
        assertEquals("source_check_report", route.mcpToolName)
        assertNotNull(route)
    }
}
