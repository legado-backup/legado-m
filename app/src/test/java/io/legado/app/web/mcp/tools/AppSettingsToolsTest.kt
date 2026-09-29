package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_APP
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * ㉓ 应用设置域声明单测（二期 · tasks 2.24b / 2.28）。
 *
 * 断言：元数据（domain / level / readOnlyHint）、schema 必填、AD-10 结构红线，
 * 以及**已注册进目录**（McpToolCatalog）。凭据类键的拒绝口径由 kernel（[io.legado.app.service.kernel.AppSettingsKernel]）
 * 的白名单保证，本文件只验声明层。
 */
class AppSettingsToolsTest {

    private val tools: List<McpTool> = AppSettingsTools.tools

    @Test
    fun appPrefsGet_isReadonlyWithOptionalKeys() {
        val tool = tools.single { it.name == "app_prefs_get" }
        assertEquals(MCP_DOMAIN_APP, tool.domain)
        assertEquals(TokenManager.Level.READONLY, tool.level)
        assertTrue("只读工具须标 readOnlyHint", tool.readOnlyHint)
        assertFalse("读取偏好不是危险操作", tool.dangerous)
        assertEquals(0, tool.inputSchema.getAsJsonArray("required").size())
        assertEquals(setOf("keys"), tool.inputSchema.getAsJsonObject("properties").keySet())
    }

    @Test
    fun writeTools_areManageWithoutReadOnlyHint() {
        listOf("app_prefs_save", "app_theme_mode_set").forEach { name ->
            val tool = tools.single { it.name == name }
            assertEquals("写工具须为 MANAGE 级：$name", TokenManager.Level.MANAGE, tool.level)
            assertFalse("写工具 readOnlyHint 须为 false：$name", tool.readOnlyHint)
        }
        assertEquals(
            listOf("prefs"),
            tools.single { it.name == "app_prefs_save" }.inputSchema.getAsJsonArray("required").map { it.asString },
        )
        assertEquals(
            listOf("mode"),
            tools.single { it.name == "app_theme_mode_set" }.inputSchema.getAsJsonArray("required").map { it.asString },
        )
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        DomainDeclarationAssert.assertMetadataConsistent(tools, MCP_DOMAIN_APP, "app_")
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
        assertEquals("应用设置域须 4 个工具", 4, tools.size)
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/AppSettingsTools.kt")
    }
}