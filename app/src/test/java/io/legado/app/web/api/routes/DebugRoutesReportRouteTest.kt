package io.legado.app.web.api.routes

import fi.iki.elonen.NanoHTTPD.Method
import io.legado.app.web.TokenManager.Level
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * 巡检报告读出口径的**路由声明**护栏（缺口4 后半）：行为断言直接读真实注册表
 * `DebugRoutes.routes`（非源码文本），锁定「方法 / 路径 / 所需级别 / MCP 投影名」四项契约 ——
 * 级别是鉴权唯一真源（REQ-1-106），投影名须与 `SourceTools.kt` 的工具同名（REST↔MCP 对拍）。
 */
class DebugRoutesReportRouteTest {

    private val route = DebugRoutes.routes.single { it.path == "/getCheckSourceReport" }

    @Test
    fun reportRoute_isReadonly() {
        assertEquals(Method.GET, route.method)
        assertEquals("巡检报告是只读读出，不得要求 MANAGE/ADMIN", Level.READONLY, route.level)
    }

    @Test
    fun reportRoute_projectsToSourceMcpTool() {
        assertEquals("投影名须与 SourceTools 的工具同名", "source_check_report", route.mcpToolName)
    }
}
