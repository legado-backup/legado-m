package io.legado.app.web.api.routes

import fi.iki.elonen.NanoHTTPD.Method
import io.legado.app.web.TokenManager.Level
import io.legado.app.web.api.ApiRegistry
import io.legado.app.web.api.ApiRouteBootstrap
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

/**
 * 第 5 轮 UX/IA 重构 · 订阅管理补全 9 条路由的注册锚点（`issues-found.md` **IF-20**）。
 *
 * 背景：订阅**收藏 / 分组 / OPML / 导入 / 文章详情**五类能力的**内核**（`RssSourceKernel`）与
 * **MCP 工具**（`web/mcp/tools/RssTools.kt`）**早已具备**，但 **HTTP 路由缺席**（设计列项遗漏，
 * 与 IF-12 同类）⇒ 控制台「订阅」页的收藏与分组导入分区无法接线。
 *
 * 为什么必须用测试钉住：路由被删**不会编译错**，只会让控制台静默退回「能力现状」降级文案 ⇒
 * 断言「方法 + 路径 + 级别 + mcpToolName 对拍标注」。级别断言同时锁安全口径：读=READONLY、写=MANAGE。
 */
class RssRoutesTest {

    /** (方法, 路径, 级别, 期望的 mcpToolName 对拍标注) */
    private val rssEndpoints = listOf(
        Quad(Method.GET, "/getRssFavorites", Level.READONLY, "rss_favorite_list"),
        Quad(Method.POST, "/saveRssFavorite", Level.MANAGE, "rss_favorite_save"),
        Quad(Method.POST, "/deleteRssFavorite", Level.MANAGE, "rss_favorite_delete"),
        Quad(Method.GET, "/getRssGroups", Level.READONLY, "rss_groups_get"),
        Quad(Method.POST, "/saveRssGroup", Level.MANAGE, "rss_group_save"),
        Quad(Method.POST, "/importRssSources", Level.MANAGE, "rss_source_import"),
        Quad(Method.GET, "/exportRssOpml", Level.READONLY, "rss_opml_export"),
        Quad(Method.POST, "/importRssOpml", Level.MANAGE, "rss_opml_import"),
        Quad(Method.GET, "/getRssArticleInfo", Level.READONLY, "rss_article_info"),
    )

    @Test
    fun rssEndpoints_areRegisteredWithExpectedLevel() {
        ApiRouteBootstrap.install()
        rssEndpoints.forEach { (method, path, level, _) ->
            val route = ApiRegistry.find(method, path)
            assertNotNull(
                "订阅补全端点必须仍注册：$method $path（删除不会编译错，会让控制台订阅页静默退回降级）",
                route,
            )
            assertEquals("$path 的级别须为 $level（读=READONLY / 写=MANAGE）", level, route!!.level)
        }
    }

    /**
     * 与 IF-12 的 9 条补记**口径不同**：本批工具在 `RssTools.kt` 中**确实存在** ⇒
     * 必须保留 `mcpToolName` 对拍标注（AD-10：仅作 REST ↔ MCP 对拍，工具元数据真源在域文件）。
     */
    @Test
    fun rssEndpoints_declareMcpToolNamesForParity() {
        ApiRouteBootstrap.install()
        rssEndpoints.forEach { (method, path, _, toolName) ->
            val route = ApiRegistry.find(method, path)
            assertNotNull("订阅补全端点须存在：$method $path", route)
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