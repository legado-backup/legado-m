package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_AI
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * ⑳ AI 智能域声明单测（二期 · tasks 2.24 / 2.28）。
 *
 * 断言：元数据（domain / level / 危险标记）、schema 必填、AD-10 结构红线、AD-18 无凭据字段，
 * 以及**已注册进目录**。
 */
class AiToolsTest {

    private val tools: List<McpTool> = AiTools.tools

    @Test
    fun chatSessions_isReadonly() {
        val tool = tools.single { it.name == "ai_chat_sessions" }
        assertEquals(MCP_DOMAIN_AI, tool.domain)
        assertEquals(TokenManager.Level.READONLY, tool.level)
        assertEquals("只读工具须标 readOnlyHint", true, tool.readOnlyHint)
        assertFalse("会话列表不是危险操作", tool.dangerous)
        assertEquals(0, tool.inputSchema.getAsJsonArray("required").size())
    }

    @Test
    fun writeTools_areManage() {
        listOf("ai_chat_send", "ai_worldbook_save", "ai_agent_config_save").forEach { name ->
            val tool = tools.single { it.name == name }
            assertEquals("写工具须为 MANAGE 级：$name", TokenManager.Level.MANAGE, tool.level)
            assertEquals("写工具不应声明只读：$name", false, tool.readOnlyHint)
        }
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        DomainDeclarationAssert.assertMetadataConsistent(tools, MCP_DOMAIN_AI, "ai_")
        assertEquals("AI 域工具数应为 17", 17, tools.size)
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/AiTools.kt")
    }

    @Test
    fun noCredentialFields_inDomainFile() {
        val source = DomainDeclarationAssert.source("tools/AiTools.kt")
        assertFalse("AD-18：域文件不得出现 apiKey", source.contains("apiKey"))
        assertFalse("AD-18：域文件不得出现 api_key", source.contains("api_key"))
        assertFalse("AD-18：域文件不得出现 headers 字段", source.contains("\"headers\""))
        assertTrue("AD-18：Provider 列表须声明不返回凭据", source.contains("不返回任何 API Key"))
    }
}