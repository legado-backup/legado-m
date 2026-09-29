package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_BACKUP
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * ⑪ 备份域声明单测（二期 · tasks 2.16 / 2.27）。
 *
 * 本批次落地 `backup_export` / `backup_preview` 两个只读工具；
 * `backup_restore`（admin + 端侧确认闸门）随 §7.3 落地 —— 级别与危险标记届时按
 * [dangerousTools_mustBeAdminLevel] 的耐久不变量校验。
 */
class BackupToolsTest {

    private val tools: List<McpTool> = BackupTools.tools

    @Test
    fun exportAndPreview_areReadonlyWithoutParams() {
        listOf("backup_export", "backup_preview").forEach { name ->
            val tool = tools.single { it.name == name }
            assertEquals("$name 应为只读", TokenManager.Level.READONLY, tool.level)
            assertTrue("$name 应标 readOnlyHint", tool.readOnlyHint)
            assertEquals("$name 无入参", 0, tool.inputSchema.getAsJsonArray("required").size())
        }
    }

    @Test
    fun dangerousTools_mustBeAdminLevel() {
        tools.filter { it.dangerous }.forEach { tool ->
            assertEquals("危险工具级别必须为 ADMIN：${tool.name}", TokenManager.Level.ADMIN, tool.level)
        }
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        DomainDeclarationAssert.assertMetadataConsistent(tools, MCP_DOMAIN_BACKUP, "backup_")
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/BackupTools.kt")
    }
}
