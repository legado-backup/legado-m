package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_STATS
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Test

/**
 * ⑩ 统计域声明单测（二期 · tasks 2.15 / 2.28）。
 *
 * 断言：元数据（domain / level / readOnlyHint）、schema 形态、AD-10 结构红线，以及**已注册进目录**。
 */
class StatsToolsTest {

    private val tools: List<McpTool> = StatsTools.tools

    @Test
    fun readRecordsList_isReadonlyWithExpectedMetadata() {
        val tool = tools.single { it.name == "read_records_list" }
        assertEquals(MCP_DOMAIN_STATS, tool.domain)
        assertEquals(TokenManager.Level.READONLY, tool.level)
        assertEquals("只读工具须标 readOnlyHint", true, tool.readOnlyHint)
        assertFalse("阅读记录列表不是危险操作", tool.dangerous)
        assertEquals(0, tool.inputSchema.getAsJsonArray("required").size())
        assertEquals(setOf("limit"), tool.inputSchema.getAsJsonObject("properties").keySet())
    }

    @Test
    fun readGoalSave_isManageAndNotReadonly() {
        val tool = tools.single { it.name == "read_goal_save" }
        assertEquals(MCP_DOMAIN_STATS, tool.domain)
        assertEquals(TokenManager.Level.MANAGE, tool.level)
        assertFalse("MANAGE 级工具不得向 AI 声明只读", tool.readOnlyHint)
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        DomainDeclarationAssert.assertMetadataConsistent(tools, MCP_DOMAIN_STATS, "read_")
        assertEquals(5, tools.size)
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/StatsTools.kt")
    }
}