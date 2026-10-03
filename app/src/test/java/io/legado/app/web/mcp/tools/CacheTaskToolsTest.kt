package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_CACHE
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * ㉒ 缓存与任务域声明单测（二期 · tasks 2.24 / 2.28）。
 *
 * 断言：元数据（domain / level / readOnlyHint）、schema 必填、AD-10 结构红线，
 * 以及**已注册进目录**（McpToolCatalog）。跨域复用的 4 项（storage_manage / download_list /
 * download_manage / cache_stats）**不在本域**声明，由 ⑯ StorageToolsTest 覆盖。
 */
class CacheTaskToolsTest {

    private val tools: List<McpTool> = CacheTaskTools.tools

    @Test
    fun cacheSyncList_isReadonlyWithoutParams() {
        val tool = tools.single { it.name == "cache_sync_list" }
        assertEquals(MCP_DOMAIN_CACHE, tool.domain)
        assertEquals(TokenManager.Level.READONLY, tool.level)
        assertTrue("只读工具须标 readOnlyHint", tool.readOnlyHint)
        assertFalse("云缓存列表不是危险操作", tool.dangerous)
        assertEquals(0, tool.inputSchema.getAsJsonArray("required").size())
        assertEquals(0, tool.inputSchema.getAsJsonObject("properties").keySet().size)
    }

    @Test
    fun writeTools_areManageWithoutReadOnlyHint() {
        listOf("cache_download", "cache_sync_run").forEach { name ->
            val tool = tools.single { it.name == name }
            assertEquals("写工具须为 MANAGE 级：$name", TokenManager.Level.MANAGE, tool.level)
            assertFalse("写工具 readOnlyHint 须为 false：$name", tool.readOnlyHint)
        }
        // cache_sync_run 的两个必填参数（备份名 / 方向）
        val syncRun = tools.single { it.name == "cache_sync_run" }
        assertEquals(
            listOf("name", "direction"),
            syncRun.inputSchema.getAsJsonArray("required").map { it.asString },
        )
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        DomainDeclarationAssert.assertMetadataConsistent(tools, MCP_DOMAIN_CACHE, "cache_")
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
        assertEquals("缓存与任务域须 4 个工具（跨域复用项不重复声明）", 4, tools.size)
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/CacheTaskTools.kt")
    }
}