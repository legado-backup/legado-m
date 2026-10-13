package io.legado.app.help.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * AI 工具名写入边界单测（铁证 2026-10-13：`aiEnabledToolNames` 曾被写成 155MB）。
 *
 * 覆盖：正常透传 / 空白项剔除 / 首尾空格裁剪 / 超长项截断 / 条数上限 / 顺序稳定。
 */
class AiToolNameLimitsTest {

    @Test
    fun `正常工具名原样保留且顺序稳定`() {
        val out = AiToolNameLimits.sanitize(listOf("book_search", "book_info", "chapter_list"))
        assertEquals(listOf("book_search", "book_info", "chapter_list"), out.toList())
    }

    @Test
    fun `空白项剔除且首尾空格裁剪`() {
        val out = AiToolNameLimits.sanitize(listOf("", "  ", "  book_search  ", "\t"))
        assertEquals(listOf("book_search"), out.toList())
    }

    @Test
    fun `超长单项按上限截断`() {
        val huge = "x".repeat(200_000)
        val out = AiToolNameLimits.sanitize(listOf(huge))
        assertEquals(1, out.size)
        assertEquals(AiToolNameLimits.MAX_NAME_LENGTH, out.first().length)
    }

    @Test
    fun `条数按上限收敛`() {
        val many = (1..2000).map { "tool_$it" }
        val out = AiToolNameLimits.sanitize(many)
        assertEquals(AiToolNameLimits.MAX_NAMES, out.size)
        assertEquals("tool_1", out.first())
    }

    @Test
    fun `重复项去重`() {
        val out = AiToolNameLimits.sanitize(listOf("a", "a", "b"))
        assertEquals(2, out.size)
        assertTrue(out.containsAll(listOf("a", "b")))
    }

    @Test
    fun `超大入参不会退化出巨量内容`() {
        // 模拟畸形 MCP 入参：200 个 4KB 长字符串（≈ 800KB）——旧实现会**原样落盘**，
        // 而真实事故是这类入参被反复写入后累积到 155MB。本用例只断言"落盘总量被压到极小"。
        val malformed = (1..200).map { "tool_$it" + "y".repeat(4_000) }
        val out = AiToolNameLimits.sanitize(malformed)
        val totalBytes = out.sumOf { it.length }
        assertTrue(
            "落盘总量必须被压到极小：$totalBytes",
            totalBytes <= AiToolNameLimits.MAX_NAMES * AiToolNameLimits.MAX_NAME_LENGTH
        )
    }
}