package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_AUTOTASK
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Test

/**
 * ⑫ 自动任务域声明单测（二期 · tasks 2.17 / 2.28）。
 *
 * 断言：元数据（domain / level / readOnlyHint）、写工具一律 MANAGE、AD-10 结构红线，以及**已注册进目录**。
 */
class AutoTaskToolsTest {

    private val tools: List<McpTool> = AutoTaskTools.tools

    @Test
    fun autoTaskRuleGet_isReadonlyWithExpectedMetadata() {
        val tool = tools.single { it.name == "auto_task_rule_get" }
        assertEquals(MCP_DOMAIN_AUTOTASK, tool.domain)
        assertEquals(TokenManager.Level.READONLY, tool.level)
        assertEquals("只读工具须标 readOnlyHint", true, tool.readOnlyHint)
        assertFalse("规则列表不是危险操作", tool.dangerous)
        assertEquals(0, tool.inputSchema.getAsJsonArray("required").size())
        assertEquals(0, tool.inputSchema.getAsJsonObject("properties").keySet().size)
    }

    @Test
    fun writeTools_areManage() {
        listOf(
            "auto_task_rule_save",
            "auto_task_rule_delete",
            "auto_task_run",
            "auto_task_batch_op",
        ).forEach { name ->
            val tool = tools.single { it.name == name }
            assertEquals("$name 须为 MANAGE 级", TokenManager.Level.MANAGE, tool.level)
            assertFalse("MANAGE 级工具不得向 AI 声明只读：$name", tool.readOnlyHint)
        }
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        DomainDeclarationAssert.assertMetadataConsistent(tools, MCP_DOMAIN_AUTOTASK, "auto_task_")
        assertEquals(7, tools.size)
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/AutoTaskTools.kt")
    }
}