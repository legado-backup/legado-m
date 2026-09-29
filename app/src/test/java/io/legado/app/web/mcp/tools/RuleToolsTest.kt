package io.legado.app.web.mcp.tools

import io.legado.app.web.TokenManager
import io.legado.app.web.mcp.MCP_DOMAIN_RULE
import io.legado.app.web.mcp.McpTool
import io.legado.app.web.mcp.McpToolCatalog
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * ⑧⑨ 规则域声明单测（二期 · tasks 2.14 / 2.27）。
 *
 * 关键点：`replace_rule_get` 只读、`test_replace_rule` 为写级别（spec §4.2 级别规则：`*_test` → manage），
 * 且后者必须显式声明 `rule` + `text` 两个必填参数（否则 AI 无法表达"测什么"）。
 */
class RuleToolsTest {

    private val tools: List<McpTool> = RuleTools.tools

    /** 规则域工具名前缀白名单（域内含 replace_rule / highlight_rule / txt_toc_rule / paragraph_rule / dict_* / rule_* 等子域）。 */
    private val rulePrefixes = listOf(
        "replace_rule", "test_", "highlight_rule", "txt_toc_rule",
        "paragraph_rule", "book_paragraph_rule", "dict_", "rule_",
    )

    @Test
    fun replaceRuleGet_isReadonlyWithoutParams() {
        val tool = tools.single { it.name == "replace_rule_get" }
        assertEquals(TokenManager.Level.READONLY, tool.level)
        assertTrue(tool.readOnlyHint)
        assertEquals(0, tool.inputSchema.getAsJsonArray("required").size())
    }

    @Test
    fun testReplaceRule_isManageWithTwoRequiredParams() {
        val tool = tools.single { it.name == "test_replace_rule" }
        assertEquals(TokenManager.Level.MANAGE, tool.level)
        assertFalse("写级别工具不得标 readOnlyHint（保守口径）", tool.readOnlyHint)
        assertEquals(
            setOf("rule", "text"),
            tool.inputSchema.getAsJsonArray("required").map { it.asString }.toSet()
        )
    }

    @Test
    fun declarationsAreMetadataConsistent_andRegisteredInCatalog() {
        assertEquals("工具名在本域内须唯一", tools.size, tools.map { it.name }.toSet().size)
        tools.forEach { tool ->
            assertEquals("域文件内的 domain 必须一致", MCP_DOMAIN_RULE, tool.domain)
            assertTrue(
                "规则域工具名须带域内前缀：${tool.name}",
                rulePrefixes.any { tool.name.startsWith(it) }
            )
            assertNotNull("域文件声明的工具须被目录聚合：${tool.name}", McpToolCatalog.find(tool.name))
        }
    }

    @Test
    fun dangerousTools_mustBeAdminLevel() {
        tools.filter { it.dangerous }.forEach { tool ->
            assertEquals("危险工具级别必须为 ADMIN：${tool.name}", TokenManager.Level.ADMIN, tool.level)
        }
    }

    @Test
    fun invokeGoesThroughKernel_notDaoNorController() {
        DomainDeclarationAssert.assertKernelOnly("tools/RuleTools.kt")
    }
}
