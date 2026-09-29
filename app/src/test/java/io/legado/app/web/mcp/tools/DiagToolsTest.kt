package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_DIAG
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * ⑬ 诊断域（release 面）声明单测（二期 · tasks 2.19 / 2.28）。
 *
 * 断言：元数据（domain / level / 危险标记）、schema 必填、AD-10 结构红线，以及**已注册进目录**。
 * L3 调试观测工具属 debug 面，不在本文件断言范围。
 */
class DiagToolsTest {

    private val tools: List<McpTool> = DiagTools.tools

    @Test
    fun cacheClear_isAdmin() {
        val tool = tools.single { it.name == "cache_clear" }
        assertEquals(MCP_DOMAIN_DIAG, tool.domain)
        assertEquals("缓存清理级别为 ADMIN", TokenManager.Level.ADMIN, tool.level)
        assertFalse("ADMIN 工具不标 readOnlyHint", tool.readOnlyHint)
        assertFalse("缓存清理只删可重建缓存，不标 dangerous", tool.dangerous)
        assertEquals(0, tool.inputSchema.getAsJsonArray("required").size())
        assertEquals(setOf("kind"), tool.inputSchema.getAsJsonObject("properties").keySet())
    }

    @Test
    fun urlRecordQuery_isReadonly() {
        val tool = tools.single { it.name == "url_record_query" }
        assertEquals(MCP_DOMAIN_DIAG, tool.domain)
        assertEquals(TokenManager.Level.READONLY, tool.level)
        assertTrue("只读工具须标 readOnlyHint", tool.readOnlyHint)
        assertFalse("访问记录查询不是危险操作", tool.dangerous)
        assertEquals(0, tool.inputSchema.getAsJsonArray("required").size())
        assertEquals(
            setOf("keyword", "domain", "limit"),
            tool.inputSchema.getAsJsonObject("properties").keySet()
        )
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        DomainDeclarationAssert.assertMetadataConsistent(tools, MCP_DOMAIN_DIAG, "cache_clear", "url_", "log_")
        assertEquals("诊断域 release 面共 5 个工具", 5, tools.size)
        assertEquals(TokenManager.Level.READONLY, tools.single { it.name == "url_record_query" }.level)
        assertEquals(TokenManager.Level.MANAGE, tools.single { it.name == "url_record_clear" }.level)
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/DiagTools.kt")
    }
}