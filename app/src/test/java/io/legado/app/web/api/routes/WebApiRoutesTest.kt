package io.legado.app.web.api.routes

import fi.iki.elonen.NanoHTTPD.Method
import io.legado.app.web.TokenManager.Level
import io.legado.app.web.api.ApiRoute
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 四组路由声明单测（一期 · 5.4 / REQ-1-106 / design §1.2.2 路由级别表）。
 *
 * 这是「**级别唯一真源**」的**逐条**证据：28 个端点的 (方法, 路径, 级别) 全部与设计表一致
 * —— 而非只抽一两条。级别错了就等于鉴权错了，所以这里不抽样、全量断言。
 */
class WebApiRoutesTest {

    /** 四组声明合起来=改造前的 28 个旧端点（一一对应）。 */
    private val allRoutes: Array<ApiRoute> =
        BookRoutes.routes + SourceRoutes.routes + RuleRoutes.routes + BackupRoutes.routes

    /** 设计表（design §1.2.2）：方法 + 路径 → 期望级别。 */
    private val expectedLevels: Map<String, Level> = mapOf(
        // 书库与书籍
        "GET /getBookshelf" to Level.READONLY,
        "GET /getChapterList" to Level.READONLY,
        "GET /refreshToc" to Level.READONLY,
        "GET /getBookContent" to Level.READONLY,
        "GET /cover" to Level.READONLY,
        "GET /image" to Level.READONLY,
        "GET /getReadConfig" to Level.READONLY,
        "POST /saveBook" to Level.MANAGE,
        "POST /deleteBook" to Level.MANAGE,
        "POST /saveBookProgress" to Level.MANAGE,
        "POST /addLocalBook" to Level.MANAGE,
        "POST /saveReadConfig" to Level.MANAGE,
        // 源域（书源 + 订阅源）
        "GET /getBookSource" to Level.READONLY,
        "GET /getBookSources" to Level.READONLY,
        "POST /saveBookSource" to Level.MANAGE,
        "POST /saveBookSources" to Level.MANAGE,
        "POST /deleteBookSources" to Level.MANAGE,
        "GET /getRssSource" to Level.READONLY,
        "GET /getRssSources" to Level.READONLY,
        "POST /saveRssSource" to Level.MANAGE,
        "POST /saveRssSources" to Level.MANAGE,
        "POST /deleteRssSources" to Level.MANAGE,
        // 规则域
        "GET /getReplaceRules" to Level.READONLY,
        "POST /saveReplaceRule" to Level.MANAGE,
        "POST /deleteReplaceRule" to Level.MANAGE,
        "POST /testReplaceRule" to Level.MANAGE,
        // 备份域（高敏 ⇒ admin）
        "GET /backup" to Level.ADMIN,
        "GET /backupPreview" to Level.ADMIN,
    )

    @Test
    fun fourGroups_declareExactly28Routes() {
        assertEquals("书源/书籍域", 12, BookRoutes.routes.size)
        assertEquals("源域", 10, SourceRoutes.routes.size)
        assertEquals("规则域", 4, RuleRoutes.routes.size)
        assertEquals("备份域", 2, BackupRoutes.routes.size)
        assertEquals("合计须等于改造前的 28 个旧端点", 28, allRoutes.size)
    }

    @Test
    fun everyRouteLevel_matchesDesignTable_exhaustively() {
        assertEquals("设计表须覆盖全部 28 条", 28, expectedLevels.size)
        val actual = allRoutes.associate { it.key to it.level }
        assertEquals("端点集合须与设计表完全一致", expectedLevels.keys, actual.keys)
        expectedLevels.forEach { (key, expected) ->
            assertEquals("级别不符（REQ-1-106 唯一真源）：$key", expected, actual[key])
        }
    }

    @Test
    fun addLocalBook_isManage_despiteUploadBookPage() {
        // SC-1-03 陷阱：页面在 /uploadBook/ 下，但属写端点 ⇒ 必须 manage
        val route = allRoutes.first { it.path == "/addLocalBook" }
        assertEquals(Method.POST, route.method)
        assertEquals(Level.MANAGE, route.level)
    }

    @Test
    fun nonReadonlyRoutes_requireTokenEvenInNonStrictMode() {
        // 关键不变量：过渡期（strict=false）**只对 READONLY 端点放行**。
        // 若按"读写"判，则 GET /backup（ADMIN）会被当读放行 ⇒ 未授权即可整包导出（真实漏洞）。
        allRoutes.forEach { route ->
            if (route.level == Level.READONLY) {
                assertTrue("READONLY 端点过渡期可放行：${route.key}", !route.requiresAuthWhenNonStrict)
            } else {
                assertTrue(
                    "级别 > READONLY 的端点过渡期也必须强制令牌：${route.key}（${route.level}）",
                    route.requiresAuthWhenNonStrict
                )
            }
        }
    }

    @Test
    fun backupEndpoints_areReadButStillRequireAuth() {
        // 高敏读端点的定点证据：GET + ADMIN ⇒ 过渡期仍强制令牌
        listOf("/backup", "/backupPreview").forEach { path ->
            val route = allRoutes.first { it.path == path }
            assertTrue("$path 应为 GET（读）", !route.isWrite)
            assertEquals("$path 级别须为 ADMIN", Level.ADMIN, route.level)
            assertTrue("$path 过渡期仍须强制令牌", route.requiresAuthWhenNonStrict)
        }
    }

    @Test
    fun writeRoutes_areAllManageOrAdmin() {
        allRoutes.filter { it.isWrite }.forEach { route ->
            assertTrue(
                "写端点级别须 ≥ MANAGE：${route.key}（实际 ${route.level}）",
                route.level == Level.MANAGE || route.level == Level.ADMIN
            )
        }
    }

    @Test
    fun routeKeys_areUnique_withinAndAcrossGroups() {
        assertEquals("（方法+路径）在四组合并后必须唯一", allRoutes.size, allRoutes.map { it.key }.toSet().size)
    }

    @Test
    fun projectableRoutes_carryMcpToolName() {
        val projectable = allRoutes.filter { it.mcpToolName != null }
        assertTrue("二期可投影路由不应为空（为 MCP 投影铺路）", projectable.isNotEmpty())
        projectable.forEach { route ->
            assertTrue(
                "mcpToolName 应非空且非空白：${route.key}",
                !route.mcpToolName.isNullOrBlank()
            )
        }
    }

    // ---------------------------------------------------------------- 二期：/mcp 传输入口

    @Test
    fun mcpTransport_isRegisteredAsThreeRoutesAtReadonly() {
        // REQ-2-107 / SC-2-16：`/mcp` 是**注册进去的一条路由**（三方法同名路径），
        // 不是新的 HTTP 服务 ⇒ `HttpServer.kt` 零改动。
        assertEquals("POST/GET/DELETE 三方法", 3, McpRoutes.routes.size)
        McpRoutes.routes.forEach { route ->
            assertEquals(McpRoutes.PATH, route.path)
            assertEquals("路由级门槛为 READONLY（双闸在协议核内）", Level.READONLY, route.level)
            assertEquals("传输入口不投影为工具", null, route.mcpToolName)
        }
        assertEquals(
            setOf(Method.POST, Method.GET, Method.DELETE),
            McpRoutes.routes.map { it.method }.toSet()
        )
    }

    @Test
    fun mcpRoutes_doNotCollideWithBusinessRoutes() {
        val keys = (allRoutes + McpRoutes.routes).map { it.key }
        assertEquals("加入 /mcp 后（方法+路径）仍须唯一", keys.size, keys.toSet().size)
    }
}
