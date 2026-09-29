package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_STORAGE
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * ⑯ 文件与存储域声明单测（二期 · tasks 2.20 / 2.28）。
 *
 * 断言：元数据（domain / level / readOnlyHint / 危险标记）、schema 必填、AD-10 结构红线，
 * 以及**已注册进目录**（McpToolCatalog）。
 */
class StorageToolsTest {

    private val tools: List<McpTool> = StorageTools.tools

    @Test
    fun fileList_isReadonlyWithOptionalParams() {
        val tool = tools.single { it.name == "file_list" }
        assertEquals(MCP_DOMAIN_STORAGE, tool.domain)
        assertEquals(TokenManager.Level.READONLY, tool.level)
        assertTrue("只读工具须标 readOnlyHint", tool.readOnlyHint)
        assertFalse("文件列举不是危险操作", tool.dangerous)
        assertEquals(0, tool.inputSchema.getAsJsonArray("required").size())
        assertEquals(setOf("path", "limit"), tool.inputSchema.getAsJsonObject("properties").keySet())
    }

    @Test
    fun writeTools_areManageWithoutReadOnlyHint() {
        listOf("file_delete", "download_manage").forEach { name ->
            val tool = tools.single { it.name == name }
            assertEquals("写工具须为 MANAGE 级：$name", TokenManager.Level.MANAGE, tool.level)
            assertFalse("写工具 readOnlyHint 须为 false：$name", tool.readOnlyHint)
        }
        // file_delete 的批量为必填数组参数（端侧二次确认口径写在 description 里）
        val fileDelete = tools.single { it.name == "file_delete" }
        assertEquals(
            listOf("paths"),
            fileDelete.inputSchema.getAsJsonArray("required").map { it.asString },
        )
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        DomainDeclarationAssert.assertMetadataConsistent(
            tools, MCP_DOMAIN_STORAGE,
            "storage_", "file_", "download_", "cache_"
        )
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
        assertEquals("文件与存储域须 6 个工具", 6, tools.size)
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/StorageTools.kt")
    }
}