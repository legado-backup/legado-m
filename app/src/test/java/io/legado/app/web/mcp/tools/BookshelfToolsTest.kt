package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_BOOKSHELF
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Test

/**
 * ① 书架与书籍域声明单测（二期 · tasks 2.8 / 2.27）。
 *
 * 断言：元数据（domain / level / 危险标记）、schema 必填、AD-10 结构红线，以及**已注册进目录**。
 */
class BookshelfToolsTest {

    private val tools: List<McpTool> = BookshelfTools.tools

    @Test
    fun bookshelfList_isReadonlyWithExpectedMetadata() {
        val tool = tools.single { it.name == "bookshelf_list" }
        assertEquals(MCP_DOMAIN_BOOKSHELF, tool.domain)
        assertEquals(TokenManager.Level.READONLY, tool.level)
        assertEquals("只读工具须标 readOnlyHint", true, tool.readOnlyHint)
        assertFalse("书架列表不是危险操作", tool.dangerous)
        assertEquals(0, tool.inputSchema.getAsJsonArray("required").size())
        assertEquals(setOf("limit", "keyword"), tool.inputSchema.getAsJsonObject("properties").keySet())
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        DomainDeclarationAssert.assertMetadataConsistent(tools, MCP_DOMAIN_BOOKSHELF, "bookshelf_")
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/BookshelfTools.kt")
    }
}
