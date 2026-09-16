package io.legado.app.help

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R12.1 规则作用域（targetScope）过滤单测。
 *
 * 背景：`targetScope` 此前在 B 侧是「未接线字段」——编辑器可选但匹配/渲染完全不消费。
 * 本测试锁定接线后的语义：仅标题 / 仅正文 / 全部。
 */
class HighlightScopeFilterTest {

    /** 第 1 行为标题行，第 2 行为正文行 */
    private val text = "第一章 起始\n正文第一章内容\n"

    /** 与 [text] 等长：前 7 字符（含换行）属标题行，其余属正文行 */
    private val titleFlags = BooleanArray(text.length) { it <= 6 }

    private fun rule(scope: Int) = HighlightRuleMatcher.Rule(
        id = "r",
        pattern = "第一章",
        isRegex = true,
        style = HighlightStyle(textColor = 0xFFFF0000.toInt()),
        targetScope = scope
    )

    @Test
    fun scopeAll_keepsTitleAndBodyMatches() {
        val matches = HighlightRuleMatcher.match(text, listOf(rule(HighlightRuleMatcher.SCOPE_ALL)), titleFlags)
        assertEquals(2, matches.size)
        assertEquals(listOf(0, 9), matches.map { it.start })
    }

    @Test
    fun scopeTitle_keepsOnlyTitleLineMatches() {
        val matches = HighlightRuleMatcher.match(text, listOf(rule(HighlightRuleMatcher.SCOPE_TITLE)), titleFlags)
        assertEquals(1, matches.size)
        assertEquals(0, matches.first().start)
    }

    @Test
    fun scopeBody_keepsOnlyBodyLineMatches() {
        val matches = HighlightRuleMatcher.match(text, listOf(rule(HighlightRuleMatcher.SCOPE_BODY)), titleFlags)
        assertEquals(1, matches.size)
        assertEquals(9, matches.first().start)
    }

    @Test
    fun scopeBody_spanningTitleAndBody_isDropped() {
        // 跨行命中（含标题行字符）在「仅正文」下必须整条丢弃，避免标题被误标
        val spanning = HighlightRuleMatcher.Rule(
            id = "span",
            pattern = "起始\\n正文",
            isRegex = true,
            style = HighlightStyle(textColor = 0xFFFF0000.toInt()),
            targetScope = HighlightRuleMatcher.SCOPE_BODY
        )
        val matches = HighlightRuleMatcher.match(text, listOf(spanning), titleFlags)
        assertTrue("跨标题/正文的命中未被丢弃", matches.isEmpty())
    }

    @Test
    fun noTitleFlags_keepsLegacyBehaviour() {
        // 未提供标记（旧调用路径）→ 不做过滤，行为与改动前一致
        val matches = HighlightRuleMatcher.match(text, listOf(rule(HighlightRuleMatcher.SCOPE_BODY)))
        assertEquals(2, matches.size)
    }

    @Test
    fun literalRule_alsoHonoursScope() {
        val literal = HighlightRuleMatcher.Rule(
            id = "lit",
            pattern = "第一章",
            isRegex = false,
            style = HighlightStyle(textColor = 0xFFFF0000.toInt()),
            targetScope = HighlightRuleMatcher.SCOPE_TITLE
        )
        val matches = HighlightRuleMatcher.match(text, listOf(literal), titleFlags)
        assertEquals(1, matches.size)
        assertEquals(0, matches.first().start)
    }
}