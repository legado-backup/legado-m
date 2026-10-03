package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_APPEARANCE
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * ㉑ 外观资源域声明单测（二期 · tasks 2.24 / 2.27）。
 *
 * 断言：元数据（domain / level / 危险标记）、schema 必填、AD-10 结构红线、**已注册进目录**，
 * 以及 AD-17 渲染实现不暴露（源码扫描）。
 */
class AppearanceToolsTest {

    private val tools: List<McpTool> = AppearanceTools.tools

    @Test
    fun themePackList_isReadonly() {
        val tool = tools.single { it.name == "theme_pack_list" }
        assertEquals(MCP_DOMAIN_APPEARANCE, tool.domain)
        assertEquals(TokenManager.Level.READONLY, tool.level)
        assertTrue("只读工具须标 readOnlyHint", tool.readOnlyHint)
        assertFalse("主题包列表不是危险操作", tool.dangerous)
        assertEquals("无入参工具 required 须为空", 0, tool.inputSchema.getAsJsonArray("required").size())
        assertEquals("无入参工具 properties 须为空", emptySet<String>(), tool.inputSchema.getAsJsonObject("properties").keySet())
    }

    @Test
    fun themePackInstall_isAdminAndDangerous() {
        val tool = tools.single { it.name == "theme_pack_install" }
        assertEquals(MCP_DOMAIN_APPEARANCE, tool.domain)
        assertEquals("安装主题包级别必须为 ADMIN", TokenManager.Level.ADMIN, tool.level)
        assertTrue("安装主题包为破坏性操作，须标 dangerous", tool.dangerous)
        assertFalse("ADMIN 工具不标 readOnlyHint", tool.readOnlyHint)
        assertEquals("须要求 filePath", 1, tool.inputSchema.getAsJsonArray("required").size())
        assertEquals(setOf("filePath"), tool.inputSchema.getAsJsonObject("properties").keySet())
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        DomainDeclarationAssert.assertMetadataConsistent(
            tools, MCP_DOMAIN_APPEARANCE,
            "theme_pack_", "ai_theme_", "appearance_kit_", "top_bar_pack_", "nav_bar_pack_",
            "bubble_template_", "share_template_", "cover_collection_", "book_info_layout_"
        )
        assertEquals("外观资源域共 18 个工具", 18, tools.size)
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/AppearanceTools.kt")
    }

    @Test
    fun noRenderingImplementation_inDomainFile() {
        val code = DomainDeclarationAssert.source("tools/AppearanceTools.kt")
        listOf("setStatusBarColor", "immersive", "LauncherIcon", "toM3Scheme", "withContrastGuard").forEach { token ->
            assertFalse("AD-17：外观域不得声明 / 调用渲染实现（命中 $token）", code.contains(token))
        }
    }
}