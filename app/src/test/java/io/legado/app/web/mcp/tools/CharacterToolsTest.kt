package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_CHARACTER
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Test

/**
 * ⑲ 角色域声明单测（二期 · tasks 2.23 / 2.28）。
 *
 * 断言：元数据（domain / level / readOnlyHint / 危险标记）、schema 必填、
 * AD-10 结构红线，以及**已注册进目录**。
 */
class CharacterToolsTest {

    private val tools: List<McpTool> = CharacterTools.tools

    @Test
    fun characterList_isReadonlyWithExpectedMetadata() {
        val tool = tools.single { it.name == "character_list" }
        assertEquals(MCP_DOMAIN_CHARACTER, tool.domain)
        assertEquals(TokenManager.Level.READONLY, tool.level)
        assertEquals("只读工具须标 readOnlyHint", true, tool.readOnlyHint)
        assertFalse("角色列表读取不是危险操作", tool.dangerous)
        assertEquals(1, tool.inputSchema.getAsJsonArray("required").size())
        assertEquals(setOf("bookUrl"), tool.inputSchema.getAsJsonObject("properties").keySet())
    }

    @Test
    fun writeTools_areManageAndNotReadonly() {
        val save = tools.single { it.name == "character_save" }
        assertEquals(MCP_DOMAIN_CHARACTER, save.domain)
        assertEquals(TokenManager.Level.MANAGE, save.level)
        assertFalse("MANAGE 级工具不得向 AI 声明只读", save.readOnlyHint)
        assertEquals(setOf("character"), save.inputSchema.getAsJsonArray("required").map { it.asString }.toSet())

        val voiceRoute = tools.single { it.name == "character_voice_route" }
        assertEquals(TokenManager.Level.MANAGE, voiceRoute.level)
        assertFalse("MANAGE 级工具不得向 AI 声明只读", voiceRoute.readOnlyHint)
        assertEquals(setOf("characterId"), voiceRoute.inputSchema.getAsJsonArray("required").map { it.asString }.toSet())
        assertEquals(
            setOf("characterId", "bookUrl", "speechRouteJson"),
            voiceRoute.inputSchema.getAsJsonObject("properties").keySet()
        )
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        DomainDeclarationAssert.assertMetadataConsistent(tools, MCP_DOMAIN_CHARACTER, "character_")
        assertEquals(5, tools.size)
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/CharacterTools.kt")
    }
}