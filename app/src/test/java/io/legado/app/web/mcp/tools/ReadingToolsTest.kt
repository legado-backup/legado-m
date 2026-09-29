package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_READING
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * ② 阅读域声明单测（二期 · tasks 2.9 / 2.27）。
 *
 * 关键点：**读/写级别必须区分**（取目录/正文 = READONLY；刷新目录 = MANAGE），
 * 且 `book_get_content` 的 `bookUrl` + `chapterIndex` 为必填、`offset`/`length` 可选（决策 #13 分页口径）。
 */
class ReadingToolsTest {

    private val tools: List<McpTool> = ReadingTools.tools

    @Test
    fun requiredParams_areDeclaredExactly() {
        val chapters = tools.single { it.name == "book_get_chapters" }
        assertEquals(setOf("bookUrl"), chapters.inputSchema.getAsJsonArray("required").map { it.asString }.toSet())
        assertEquals(TokenManager.Level.READONLY, chapters.level)

        val content = tools.single { it.name == "book_get_content" }
        assertEquals(
            setOf("bookUrl", "chapterIndex"),
            content.inputSchema.getAsJsonArray("required").map { it.asString }.toSet()
        )
        assertEquals(
            setOf("bookUrl", "chapterIndex", "offset", "length"),
            content.inputSchema.getAsJsonObject("properties").keySet()
        )
        assertEquals(TokenManager.Level.READONLY, content.level)
    }

    @Test
    fun refreshToc_isManage_notReadonly() {
        val refresh = tools.single { it.name == "book_refresh_toc" }
        assertEquals("刷新目录会落库 ⇒ 必须 MANAGE", TokenManager.Level.MANAGE, refresh.level)
        assertFalse("非只读工具不得标 readOnlyHint", refresh.readOnlyHint)
        assertFalse("刷新目录不触发端侧确认（非危险）", refresh.dangerous)
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        DomainDeclarationAssert.assertMetadataConsistent(tools, MCP_DOMAIN_READING, "book_", "read_", "auto_read_", "epub_")
        tools.forEach { tool ->
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
        assertTrue("阅读域当前批次应已声明 ≥3 个工具", tools.size >= 3)
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/ReadingTools.kt")
    }
}
