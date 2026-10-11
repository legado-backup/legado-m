package io.legado.app.model.localBook

import io.legado.app.constant.AppPattern
import io.legado.app.help.md.MdChapterizer
import io.legado.app.help.md.MdDocumentBuilder
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Markdown 书籍内容管线契约单测（epub-md-rich-rendering 阶段 3.6 配对）。
 *
 * `MdFile` 依赖 `LocalBook.getBookInputStream`（content resolver）⇒ 单元测试不可 JVM 化，
 * 但其**内容管线契约**可在此固化，防止"分发接上了、内容却串章 / 送达格式不被渲染路径识别"这类静默问题：
 *
 * ①**章节与目录同源**（3.5 验证标准）：每章 HTML/纯文本只取自该章源区间，不串章；
 * ②**`<usehtml>` 送达契约**：`MdFile.getContent` 的包裹形态必须能被 `AppPattern.useHtmlRegex` 识别
 *   （渲染路径正是靠它分流到 HTML 就地渲染），否则内容会退化成裸标签文本；
 * ③**规模契约**：整本切章后各章区间拼接无损（软切/多章均成立）。
 */
class MdBookPipelineContractTest {

    private val markdown = """
        # 第一章

        正文一

        ## 第一节

        正文二

        # 第二章

        正文三
    """.trimIndent()

    /** 复刻 MdFile.getContent 的送达形态（同一约定，单点核对）。 */
    private fun deliver(html: String): String = "<usehtml>$html</usehtml>"

    @Test
    fun `每章产物只取自本章源区间不串章`() {
        val sections = MdChapterizer.chapterize(markdown)
        assertEquals(3, sections.size)
        val built = sections.map { section ->
            MdDocumentBuilder.build(markdown.substring(section.startOffset, section.endOffset))
        }
        assertTrue(built[0].html.contains("正文一"))
        assertFalse("首章不得含次章内容", built[0].html.contains("正文三"))
        assertTrue(built[1].html.contains("正文二"))
        assertFalse("次章不得含首章内容", built[1].plainText.contains("正文一"))
        assertTrue(built[2].html.contains("正文三"))
        assertFalse("末章不得含首章内容", built[2].html.contains("正文一"))
    }

    @Test
    fun `送达包裹形态被渲染路径的 usehtml 分流规则识别`() {
        val section = MdChapterizer.chapterize(markdown).first()
        val html = MdDocumentBuilder.build(markdown.substring(section.startOffset, section.endOffset)).html
        val delivered = deliver(html)
        assertTrue(
            "必须被 AppPattern.useHtmlRegex 命中，否则内容会按纯文本呈现",
            AppPattern.useHtmlRegex.matches(delivered)
        )
        assertTrue(delivered.startsWith("<usehtml>"))
        assertTrue(delivered.endsWith("</usehtml>"))
    }

    @Test
    fun `切章后各章源区间拼接无损`() {
        val sections = MdChapterizer.chapterize(markdown)
        assertEquals(
            "目录与正文必须同源（区间拼接 == 原文）",
            markdown,
            sections.joinToString("") { markdown.substring(it.startOffset, it.endOffset) }
        )
    }

    @Test
    fun `标题同时出现在目录与章节正文中保持同源`() {
        val section = MdChapterizer.chapterize(markdown).first()
        assertEquals("第一章", section.title)
        val html = MdDocumentBuilder.build(markdown.substring(section.startOffset, section.endOffset)).html
        assertTrue("章首标题须在正文 HTML 中（同源）", html.contains("第一章"))
    }

    @Test
    fun `空章节正文不产出 usehtml 包裹`() {
        // MdFile 对空 HTML 的处置：退回纯文本（此处核对判据：空 HTML 即为空串）
        val built = MdDocumentBuilder.build("")
        assertTrue(built.html.isBlank())
    }

    // === S3① 相对图片内联（MdFile 的接线契约）===

    /** 带相对图片的章节（与 MdFile 从源区间切出的形态一致）。 */
    private fun imageChapter(): String = """
        # 图章

        ![示意图](./img/pic.png)

        正文
    """.trimIndent()

    @Test
    fun `章节相对图片在送达 payload 中保留 img 标签`() {
        val built = MdDocumentBuilder.build(imageChapter())
        val delivered = deliver(built.html)
        assertTrue("img 必须进入送达 payload（渲染路径靠它出图）", delivered.contains("<img "))
        assertTrue(delivered.contains("./img/pic.png"))
        assertTrue("包裹形态不变 ⇒ 仍被分流规则识别", AppPattern.useHtmlRegex.matches(delivered))
    }

    @Test
    fun `送入内联解析器后送达 payload 只含 data URI 不含相对引用`() {
        // 复刻 MdFile 的调用形态（第三个参数即 MdRelativeImageInliner）：只在此断言
        // "接线点存在且改写会进入送达 payload"，真实文件读取由真机 L2 取证。
        val built = MdDocumentBuilder.build(
            imageChapter(),
            imageResolver = MdDocumentBuilder.ImageDestinationResolver { src ->
                if (src == "./img/pic.png") "data:image/png;base64,UElD" else null
            }
        )
        val delivered = deliver(built.html)
        assertTrue(delivered.contains("src=\"data:image/png;base64,UElD\""))
        assertFalse("相对引用不得残留（否则承载面拿不到目录仍会裂图）", delivered.contains("./img/pic.png"))
    }

    @Test
    fun `图片不进入纯文本产物`() {
        val built = MdDocumentBuilder.build(imageChapter())
        assertTrue("alt 文本保留供纯文本/朗读", built.plainText.contains("示意图"))
        assertFalse("纯文本不得含 img 标签", built.plainText.contains("<img"))
    }
}