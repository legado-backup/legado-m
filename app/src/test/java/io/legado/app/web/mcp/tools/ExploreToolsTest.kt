package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_EXPLORE
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * ⑱ 发现域声明单测（二期 · tasks 2.22 / 2.28）。
 *
 * 断言：元数据（domain / level / readOnlyHint / 危险标记）、schema 必填与形态、
 * **explore_books 慢源结构化超时措辞**（返回失败原因，不静默返回空）、AD-10 结构红线，以及**已注册进目录**。
 */
class ExploreToolsTest {

    private val tools: List<McpTool> = ExploreTools.tools

    @Test
    fun readonlyTools_haveExpectedMetadataAndSchema() {
        val sources = tools.single { it.name == "explore_sources" }
        assertEquals(MCP_DOMAIN_EXPLORE, sources.domain)
        assertEquals(TokenManager.Level.READONLY, sources.level)
        assertEquals("只读工具须标 readOnlyHint", true, sources.readOnlyHint)
        assertFalse("发现首页读取不是危险操作", sources.dangerous)
        assertEquals(0, sources.inputSchema.getAsJsonArray("required").size())
        assertEquals(emptySet<String>(), sources.inputSchema.getAsJsonObject("properties").keySet())

        val books = tools.single { it.name == "explore_books" }
        assertEquals(TokenManager.Level.READONLY, books.level)
        assertEquals("只读工具须标 readOnlyHint", true, books.readOnlyHint)
        assertEquals(setOf("sourceUrl", "url"), books.inputSchema.getAsJsonArray("required").map { it.asString }.toSet())
        assertEquals(
            setOf("sourceUrl", "url", "page"),
            books.inputSchema.getAsJsonObject("properties").keySet()
        )
        // 慢源口径（spec §4.2.2 / tasks 2.22）：结构化超时——返回失败原因，不静默返回空
        assertTrue("须写明慢源结构化超时", books.description.contains("超时"))
        assertTrue("须写明不静默返回空", books.description.contains("不静默返回空"))
    }

    @Test
    fun writeTools_areManageAndNotReadonly() {
        val suiteSave = tools.single { it.name == "discovery_suite_save" }
        assertEquals(MCP_DOMAIN_EXPLORE, suiteSave.domain)
        assertEquals(TokenManager.Level.MANAGE, suiteSave.level)
        assertFalse("MANAGE 级工具不得向 AI 声明只读", suiteSave.readOnlyHint)
        assertEquals(setOf("suite"), suiteSave.inputSchema.getAsJsonArray("required").map { it.asString }.toSet())

        val cacheSave = tools.single { it.name == "explore_cache_config_save" }
        assertEquals(TokenManager.Level.MANAGE, cacheSave.level)
        assertFalse("MANAGE 级工具不得向 AI 声明只读", cacheSave.readOnlyHint)
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        DomainDeclarationAssert.assertMetadataConsistent(tools, MCP_DOMAIN_EXPLORE, "explore_", "discovery_")
        assertEquals(7, tools.size)
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/ExploreTools.kt")
    }
}