package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_RSS
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

/**
 * ⑥ 订阅域声明单测（二期 · tasks 2.12 / 2.27）。
 *
 * 本批次只落地读工具（`rss_source_get`）；其余随 §2.28 的新 Kernel 方法在后续批次追加。
 */
class RssToolsTest {

    private val tools: List<McpTool> = RssTools.tools

    @Test
    fun rssSourceGet_isReadonlyWithOptionalUrl() {
        val tool = tools.single { it.name == "rss_source_get" }
        assertEquals(TokenManager.Level.READONLY, tool.level)
        assertEquals(setOf("url"), tool.inputSchema.getAsJsonObject("properties").keySet())
        assertEquals("url 可选（省略即返回全部）", 0, tool.inputSchema.getAsJsonArray("required").size())
    }

    @Test
    fun dangerousTools_mustBeAdminLevel() {
        tools.filter { it.dangerous }.forEach { tool ->
            assertEquals("危险工具级别必须为 ADMIN：${tool.name}", TokenManager.Level.ADMIN, tool.level)
        }
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        DomainDeclarationAssert.assertMetadataConsistent(tools, MCP_DOMAIN_RSS, "rss_")
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/RssTools.kt")
    }
}
