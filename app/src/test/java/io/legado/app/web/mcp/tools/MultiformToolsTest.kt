package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_MULTIFORM
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * ⑰ 多形态域声明单测（二期 · tasks 2.21 / 2.28）。
 *
 * 断言：元数据（domain / level / readOnlyHint / 危险标记）、schema 必填与形态、
 * **video_play 能力边界措辞**（端侧指令 + AI 看不到画面，不含夸大措辞）、AD-10 结构红线，以及**已注册进目录**。
 */
class MultiformToolsTest {

    private val tools: List<McpTool> = MultiformTools.tools

    @Test
    fun mangaChapters_isReadonlyWithExpectedMetadata() {
        val tool = tools.single { it.name == "manga_chapters" }
        assertEquals(MCP_DOMAIN_MULTIFORM, tool.domain)
        assertEquals(TokenManager.Level.READONLY, tool.level)
        assertEquals("只读工具须标 readOnlyHint", true, tool.readOnlyHint)
        assertFalse("章节目录不是危险操作", tool.dangerous)
        assertEquals(1, tool.inputSchema.getAsJsonArray("required").size())
        assertEquals(setOf("bookUrl"), tool.inputSchema.getAsJsonObject("properties").keySet())
    }

    @Test
    fun writeTools_areManageAndNotReadonly() {
        val play = tools.single { it.name == "video_play" }
        assertEquals(MCP_DOMAIN_MULTIFORM, play.domain)
        assertEquals(TokenManager.Level.MANAGE, play.level)
        assertFalse("MANAGE 级工具不得向 AI 声明只读", play.readOnlyHint)
        assertFalse("video_play 不是危险操作（端侧指令）", play.dangerous)
        assertEquals(setOf("action"), play.inputSchema.getAsJsonArray("required").map { it.asString }.toSet())
        // 能力边界措辞（spec §4.2.2 / design AD-2-07）：只能写"下发端侧控制指令"，且必须写明 AI 看不到画面
        assertTrue("video_play 须写明端侧指令语义", play.description.contains("端侧指令"))
        assertTrue("video_play 须写明 AI 看不到画面", play.description.contains("看不到画面"))

        val mangaConfigSave = tools.single { it.name == "manga_config_save" }
        assertEquals(TokenManager.Level.MANAGE, mangaConfigSave.level)
        assertFalse("MANAGE 级工具不得向 AI 声明只读", mangaConfigSave.readOnlyHint)
        assertEquals(0, mangaConfigSave.inputSchema.getAsJsonArray("required").size())

        val videoConfigSave = tools.single { it.name == "video_config_save" }
        assertEquals(TokenManager.Level.MANAGE, videoConfigSave.level)
        assertFalse("MANAGE 级工具不得向 AI 声明只读", videoConfigSave.readOnlyHint)
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        DomainDeclarationAssert.assertMetadataConsistent(
            tools, MCP_DOMAIN_MULTIFORM, "manga_", "image_gallery_", "video_"
        )
        assertEquals(12, tools.size)
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/MultiformTools.kt")
    }
}