package io.legado.app.constant

import io.legado.app.help.md.MdDocumentBuilder
import io.legado.app.model.localBook.epubcore.direct.TextReaderDocument
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 「有界文档」上限**单一来源**契约（epub-md-rich-rendering · AD-15/§1.3 · 任务 3.1 统一口径）。
 *
 * 为什么要机检而不是"看着统一了"：同一章正文会流经**多条判据链**（md 构建 / 富渲染探测 / 统一文档模型
 * 与其配套的替换·气泡策略）。任一链回退成**写死字面量**时：
 * ①同一章会"一端通过、另一端抛出"（能进阅读页却白屏，或 md 能开而富渲染面直接拒）；
 * ②以后调上界只改到一处 ⇒ 口径静默分裂。
 * 这两类都不会让任何功能用例变红 ⇒ 必须把"引用单一来源 + 不残留字面量"钉在源码层。
 */
class ReaderDocumentLimitsTest {

    @Test
    fun `单一来源取值符合设计口径`() {
        assertEquals("2Mi", 2 * 1024 * 1024, ReaderDocumentLimits.MaxSourceChars)
        assertEquals("20k 块", 20_000, ReaderDocumentLimits.MaxBlocks)
    }

    @Test
    fun `各判据链的常量与单一来源相等`() {
        // 编译期引用 ⇒ 相等是结构保证；这里再显式断言一次，防止日后被改回字面量而无人察觉
        assertEquals(ReaderDocumentLimits.MaxSourceChars, MdDocumentBuilder.MaxChapterChars)
        assertEquals(ReaderDocumentLimits.MaxBlocks, MdDocumentBuilder.MaxChapterBlocks)
        assertEquals(ReaderDocumentLimits.MaxSourceChars, TextReaderDocument.MAX_SOURCE_CHARS)
        assertEquals(ReaderDocumentLimits.MaxBlocks, TextReaderDocument.MAX_BLOCKS)
    }

    @Test
    fun `判据链源码必须引用单一来源且不残留字面量`() {
        val consumers = listOf(
            "help/md/MdDocumentBuilder.kt",
            "model/localBook/epubcore/direct/TextReaderDocument.kt",
            "model/localBook/epubcore/direct/TextReaderSourceBubblePolicy.kt"
        )
        consumers.forEach { rel ->
            val src = SourceFileProbe.sourceText(rel)
            assertTrue("$rel 必须引用 ReaderDocumentLimits（口径单一来源）", src.contains("ReaderDocumentLimits"))
            assertFalse("$rel 不得再写死 2Mi 字面量", src.contains("2 * 1024 * 1024"))
        }
        // 统一文档模型侧还有"块数"字面量的历史写法，同样不得残留
        val doc = SourceFileProbe.sourceText("model/localBook/epubcore/direct/TextReaderDocument.kt")
        assertFalse("TextReaderDocument 不得再写死 20k 字面量", doc.contains("20_000"))
    }

    @Test
    fun `富渲染探测继续复用同一来源而非另立口径`() {
        // 富渲染承载面（在线正文 / txt）与统一文档模型必须**同界**：此处钉住它仍引用 md 构建的同源常量
        val probe = SourceFileProbe.sourceText("ui/book/read/textweb/TextRichContentProbe.kt")
        assertTrue(
            "富渲染探测必须引用 MdDocumentBuilder 的同源上限",
            probe.contains("MdDocumentBuilder.MaxChapterChars") &&
                probe.contains("MdDocumentBuilder.MaxChapterBlocks")
        )
        assertFalse("富渲染探测不得另立 2Mi 字面量", probe.contains("2 * 1024 * 1024"))
    }
}