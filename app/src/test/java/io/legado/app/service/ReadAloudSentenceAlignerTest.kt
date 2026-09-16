package io.legado.app.service

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * P1/B1-③ 朗读句首对齐工具单测（纯 JVM）。
 *
 * 口径：向前找最近的句末标点 → 起点推进到其后并跳过空白/闭引号；无标点返回原偏移；
 * 返回值恒 `0 <= 返回值 <= offset`。
 */
class ReadAloudSentenceAlignerTest {

    private val text = "第一句。第二句内容。"

    @Test
    fun offsetZero_returnsZero() {
        assertEquals(0, ReadAloudSentenceAligner.alignToSentenceStart(text, 0))
    }

    @Test
    fun midSentence_alignsToSentenceStart() {
        // offset 落在"第二句"内部 → 对齐到该句起点（索引 4）
        assertEquals(4, ReadAloudSentenceAligner.alignToSentenceStart(text, 7))
    }

    @Test
    fun alreadyAtSentenceStart_returnsSameOffset() {
        // offset 恰为第 2 句起点 → 不变
        assertEquals(4, ReadAloudSentenceAligner.alignToSentenceStart(text, 4))
    }

    @Test
    fun noPunctuation_returnsOriginalOffset() {
        val noPunct = "没有标点的长段落内容继续"
        assertEquals(5, ReadAloudSentenceAligner.alignToSentenceStart(noPunct, 5))
    }

    @Test
    fun skipsWhitespaceAndClosingQuote() {
        // 索引：他说：“走吧。” 然后离开 → （。在 6，闭引号 7，空格 8，然 9）
        val withQuote = "他说：“走吧。” 然后离开"
        assertEquals(9, ReadAloudSentenceAligner.alignToSentenceStart(withQuote, 12))
    }

    @Test
    fun offsetBeyondLength_isClamped() {
        val short = "句子。"
        assertEquals(short.length, ReadAloudSentenceAligner.alignToSentenceStart(short, 100))
    }

    @Test
    fun emptyText_returnsOffset() {
        assertEquals(3, ReadAloudSentenceAligner.alignToSentenceStart("", 3))
    }

    @Test
    fun resultNeverExceedsOffset() {
        val samples = listOf("a。bb。ccc", "只有内容", "。xx", "x，y；z！w")
        samples.forEach { s ->
            (0..s.length).forEach { off ->
                val r = ReadAloudSentenceAligner.alignToSentenceStart(s, off)
                assert(r in 0..off) { "offset=$off 结果 $r 越界（text=$s）" }
            }
        }
    }
}