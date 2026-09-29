package io.legado.app.web.api.routes

import fi.iki.elonen.NanoHTTPD.Method
import io.legado.app.web.TokenManager.Level
import io.legado.app.web.api.ApiRegistry
import io.legado.app.web.api.ApiRouteBootstrap
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

/**
 * 第 5 轮 UX/IA 重构 · 应用设置域补全 4 条路由的注册锚点（`issues-found.md` **IF-22**）。
 *
 * 背景：「应用偏好 / 设置检索 / 主题模式」三类能力的**内核**（`AppSettingsKernel`）与
 * **MCP 工具**（`web/mcp/tools/AppSettingsTools.kt`）**早已具备**，但 **HTTP 路由缺席**
 * （与 IF-20 同类）⇒ 控制台设置页无法落地「应用偏好」分区。
 *
 * 为什么必须用测试钉住：路由被删**不会编译错**，只会让设置页静默退回「去 App 改」的降级文案 ⇒
 * 断言「方法 + 路径 + 级别 + mcpToolName 对拍标注」。级别断言同时锁安全口径：
 * 读=READONLY（偏好读取 / 设置检索）、写=MANAGE（偏好保存 / 主题模式）。
 */
class AppSettingsRoutesTest {

    /** (方法, 路径, 级别, 期望的 mcpToolName 对拍标注) */
    private val appSettingsEndpoints = listOf(
        Quad(Method.GET, "/getAppPrefs", Level.READONLY, "app_prefs_get"),
        Quad(Method.POST, "/saveAppPrefs", Level.MANAGE, "app_prefs_save"),
        Quad(Method.GET, "/searchAppSettings", Level.READONLY, "app_settings_search"),
        Quad(Method.POST, "/setAppThemeMode", Level.MANAGE, "app_theme_mode_set"),
    )

    @Test
    fun appSettingsEndpoints_areRegisteredWithExpectedLevel() {
        ApiRouteBootstrap.install()
        appSettingsEndpoints.forEach { (method, path, level, _) ->
            val route = ApiRegistry.find(method, path)
            assertNotNull(
                "应用设置端点必须仍注册：$method $path（删除不会编译错，会让设置页静默退回降级）",
                route,
            )
            assertEquals("$path 的级别须为 $level（读=READONLY / 写=MANAGE）", level, route!!.level)
        }
    }

    @Test
    fun appSettingsEndpoints_declareMcpToolNamesForParity() {
        ApiRouteBootstrap.install()
        appSettingsEndpoints.forEach { (method, path, _, toolName) ->
            val route = ApiRegistry.find(method, path)
            assertNotNull("应用设置端点须存在：$method $path", route)
            assertEquals("$path 须与 MCP 工具对拍（$toolName）", toolName, route!!.mcpToolName)
        }
    }

    private data class Quad(
        val method: Method,
        val path: String,
        val level: Level,
        val mcpToolName: String,
    )
}