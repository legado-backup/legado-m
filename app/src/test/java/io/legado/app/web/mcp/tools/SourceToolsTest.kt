package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_SOURCE
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

/**
 * ④ 书源域声明单测（二期 · tasks 2.11 / 2.27）。
 *
 * 本批次只落地**读工具**（`source_get`）——写类工具（`source_save` 的 temp 沙箱、`source_delete` 的
 * 端侧确认）依赖尚不存在的能力，**先声明会让语义不成立**，故明确不提前落地（tasks 2.11 的口径）。
 * 这里连同"未提前声明危险工具"一起断言，防止后续批次误把半成品挂上去。
 */
class SourceToolsTest {

    private val tools: List<McpTool> = SourceTools.tools

    @Test
    fun sourceGet_isReadonlyWithOptionalUrl() {
        val tool = tools.single { it.name == "source_get" }
        assertEquals(TokenManager.Level.READONLY, tool.level)
        assertEquals(setOf("url"), tool.inputSchema.getAsJsonObject("properties").keySet())
        assertEquals("url 是可选参数（省略即返回全部）", 0, tool.inputSchema.getAsJsonArray("required").size())
    }

    @Test
    fun dangerousTools_mustBeAdminLevel() {
        // 耐久不变量（承 spec §4.2 级别规则）：危险操作靠元数据触发端侧确认，
        // 其级别必须同时是 ADMIN —— 否则"批量删源"这类操作可被 manage 令牌调用。
        tools.filter { it.dangerous }.forEach { tool ->
            assertEquals(
                "危险工具级别必须为 ADMIN：${tool.name}",
                TokenManager.Level.ADMIN,
                tool.level
            )
        }
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        DomainDeclarationAssert.assertMetadataConsistent(tools, MCP_DOMAIN_SOURCE, "source_")
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/SourceTools.kt")
    }
}
