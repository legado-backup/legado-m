package io.legado.app.model.localBook.epubcore.direct

import io.legado.app.constant.ReaderDocumentLimits
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 统一文档模型的**有界文档**契约（epub-md-rich-rendering · AD-15/§1.3 · 任务 3.1 配对）。
 *
 * 为什么必须：`TextReaderDocument` 是"显示 / 朗读 / 气泡"共用的统一正文模型，它一旦与其它判据链
 * （md 构建 / 富渲染探测 / 气泡策略）**上界不一致**，同一章就会"一端通过、另一端抛出"
 * （能进阅读页却白屏，或 md 能开而富渲染面直接拒）。此处用**真实行为**（恰达上界放行、超一字符即拒）
 * 与**源码引用**双重钉住，避免日后有人把常量改回字面量而无人察觉。
 */
class TextReaderDocumentLimitsTest {

    @Test
    fun `上界取单一来源`() {
        assertEquals(ReaderDocumentLimits.MaxSourceChars, TextReaderDocument.MAX_SOURCE_CHARS)
        assertEquals(ReaderDocumentLimits.MaxBlocks, TextReaderDocument.MAX_BLOCKS)
    }

    @Test
    fun `字符恰达上界放行且超一字符即拒`() {
        // 边界口径：`<=` 放行、`>` 拒（显式抛出，不静默截断 —— 与设计「超限给显式错误不截断」一致）
        val atLimit = TextReaderDocument.prepare("标题", "字".repeat(ReaderDocumentLimits.MaxSourceChars))
        assertTrue("恰达上界应可构建", atLimit.blocks.isNotEmpty())
        assertThrows(IllegalStateException::class.java) {
            TextReaderDocument.prepare("标题", "字".repeat(ReaderDocumentLimits.MaxSourceChars + 1))
        }
    }

    @Test
    fun `文档模型与气泡策略都必须引用同一来源`() {
        listOf(
            "model/localBook/epubcore/direct/TextReaderDocument.kt",
            "model/localBook/epubcore/direct/TextReaderSourceBubblePolicy.kt"
        ).forEach { rel ->
            val src = SourceFileProbe.sourceText(rel)
            assertTrue("$rel 必须引用 ReaderDocumentLimits", src.contains("ReaderDocumentLimits"))
            assertTrue("$rel 不得再写死 2Mi 字面量", !src.contains("2 * 1024 * 1024"))
        }
    }
}