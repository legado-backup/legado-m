package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_BACKUP
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * ⑪ 备份域声明单测（二期 · tasks 2.16 / 2.27 / §7.3）。
 *
 * 本文件覆盖 5 个工具：`backup_export` / `backup_preview`（只读）＋ `backup_restore`
 * （**ADMIN + dangerous**，端侧确认闸门）/ `backup_config_get`（只读）/ `backup_config_save`（MANAGE）。
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
    fun backupRestore_isAdminAndDangerous() {
        val tool = tools.single { it.name == "backup_restore" }
        assertEquals(MCP_DOMAIN_BACKUP, tool.domain)
        assertEquals("恢复级别必须为 ADMIN", TokenManager.Level.ADMIN, tool.level)
        assertTrue("恢复为破坏性操作，须标 dangerous", tool.dangerous)
        assertFalse("ADMIN 工具不标 readOnlyHint", tool.readOnlyHint)
    }

    @Test
    fun configTools_levels() {
        assertEquals(
            "备份配置读取应为只读",
            TokenManager.Level.READONLY,
            tools.single { it.name == "backup_config_get" }.level
        )
        assertEquals(
            "备份配置保存应为 MANAGE",
            TokenManager.Level.MANAGE,
            tools.single { it.name == "backup_config_save" }.level
        )
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        DomainDeclarationAssert.assertMetadataConsistent(tools, MCP_DOMAIN_BACKUP, "backup_")
        assertEquals("备份域共 5 个工具", 5, tools.size)
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/BackupTools.kt")
    }
}
