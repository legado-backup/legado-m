package io.legado.app.help.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Q-N4 文本净化的**纯逻辑**不变量：输入归一 / 输出剥围栏 / 差异统计与「安全结论」。
 *
 * 为什么这三段必须单测：它们决定了两个用户可见结论 ——
 * ①「是否提示 AI 没改任何内容」②「是否提示结果含新增内容、可能被改写」。
 * 判错会让用户误信被改写的文本（比功能不可用更危险）。
 */
class AiPurifyHelperTest {

    // ── normalizeSelectedText ───────────────────────────────────────────────

    @Test
    fun normalizeSelectedText_trimsEachLineAndDropsBlankLines() {
        assertEquals(
            "第一行\n第二行",
            AiPurifyHelper.normalizeSelectedText("  第一行  \n\n\t第二行 \n")
        )
    }

    @Test
    fun normalizeSelectedText_blankInputStaysBlank() {
        assertEquals("", AiPurifyHelper.normalizeSelectedText("  \n \n "))
    }

    // ── normalizeModelOutput ────────────────────────────────────────────────

    @Test
    fun normalizeModelOutput_stripsMarkdownFence() {
        assertEquals("净化结果", AiPurifyHelper.normalizeModelOutput("```text\n净化结果\n```"))
        assertEquals("净化结果", AiPurifyHelper.normalizeModelOutput("```\n净化结果\n```\n"))
    }

    @Test
    fun normalizeModelOutput_keepsPlainTextAndTrims() {
        assertEquals("净化结果", AiPurifyHelper.normalizeModelOutput("  净化结果  "))
        assertEquals("", AiPurifyHelper.normalizeModelOutput("   "))
    }

    // ── diffStat / canAutoApply ─────────────────────────────────────────────

    @Test
    fun diffStat_identicalTextIsUnchanged() {
        val diff = AiPurifyHelper.diffStat("一模一样", "一模一样")
        assertEquals(0, diff.removed)
        assertEquals(0, diff.added)
        assertFalse(diff.changed)
    }

    @Test
    fun diffStat_pureDeletionIsSafeToApply() {
        val diff = AiPurifyHelper.diffStat("正文内容附带广告尾巴", "正文内容")
        assertTrue("应统计为删除", diff.removed > 0)
        assertEquals("纯删除不应产生新增", 0, diff.added)
        assertTrue(diff.changed)
        assertTrue("纯删除 ⇒ 安全结果", AiPurifyHelper.PurifyResult("a", "b", diff).canAutoApply)
    }

    @Test
    fun diffStat_insertionIsNotSafeToApply() {
        val diff = AiPurifyHelper.diffStat("正文内容", "正文内容被改写成另一段话")
        assertTrue("应统计为新增", diff.added > 0)
        assertFalse("含新增 ⇒ 不得判为安全结果", AiPurifyHelper.PurifyResult("a", "b", diff).canAutoApply)
    }

    @Test
    fun diffStat_replacementCountsBothSidesAndKeepsUnsafe() {
        val diff = AiPurifyHelper.diffStat("广告正文", "正文广告")
        assertTrue(diff.removed > 0)
        assertTrue(diff.added > 0)
        assertEquals(minOf(diff.removed, diff.added), diff.replaced)
        assertFalse(AiPurifyHelper.PurifyResult("a", "b", diff).canAutoApply)
    }

    @Test
    fun diffStat_fallsBackToCommonPrefixSuffixForHugeText() {
        val source = "a".repeat(AiPurifyHelper.MAX_INPUT_CHARS + 100)
        val cleaned = "a".repeat(AiPurifyHelper.MAX_INPUT_CHARS)
        val diff = AiPurifyHelper.diffStat(source, cleaned)
        assertEquals("尾部删除 100 字符", 100, diff.removed)
        assertEquals(0, diff.added)
    }

    @Test
    fun diffStat_hugeTextWithTailAdditionIsUnsafe() {
        val source = "b".repeat(AiPurifyHelper.MAX_INPUT_CHARS + 50)
        val cleaned = source + "新增内容"
        val diff = AiPurifyHelper.diffStat(source, cleaned)
        assertEquals(0, diff.removed)
        assertEquals(4, diff.added)
        assertFalse(AiPurifyHelper.PurifyResult("a", "b", diff).canAutoApply)
    }
}