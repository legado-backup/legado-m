package io.legado.app.model.localBook.epubcore.template

import io.legado.app.constant.BookType
import io.legado.app.data.entities.Book
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * NEW-91：模板作用域的**内容形态判据**（`ContentKind.TEXT_LIKE`）单源化守护。
 *
 * 缺陷背景：该判据原在 `ReadStyleDialog.templateInScope()` 与 `ReadBookActivity.isTextRichMode()`
 * **各存一份内联副本**（`isEpub || isAudio || isVideo || isImage || isPdf`），而策略里定义的
 * `ContentKind.TEXT_LIKE` 只出现在注释里当"口径来源" ⇒ 只改一处即出现「弹层说已接管、正文其实没换」
 * 的静默欺骗（本仓库既有教训：同一规则出现两份必然失守）。现已收口为纯策略单源。
 */
class ReaderTemplateContentKindPolicyTest {

    private fun book(originName: String) = Book(
        name = "t",
        author = "a",
        bookUrl = "u",
        type = BookType.local,
        origin = BookType.localTag,
        originName = originName
    )

    @Test
    fun `text like content is recognized`() {
        assertTrue(
            "本地 txt 须属模板作用域",
            ReaderTemplateAvailabilityPolicy.isTextLikeContent(book("sample.txt"))
        )
        assertTrue(
            "本地 md 须属模板作用域",
            ReaderTemplateAvailabilityPolicy.isTextLikeContent(book("sample.md"))
        )
    }

    @Test
    fun `non text like content is rejected`() {
        assertFalse(
            "出版 EPUB 不属模板作用域",
            ReaderTemplateAvailabilityPolicy.isTextLikeContent(book("sample.epub"))
        )
        assertFalse(
            "无书上下文须保守判否（宁可不接管排版）",
            ReaderTemplateAvailabilityPolicy.isTextLikeContent(null)
        )
    }

    @Test
    fun `policy owns the only implementation`() {
        val src = SourceFileProbe.sourceText(
            "model/localBook/epubcore/template/ReaderTemplateAvailabilityPolicy.kt"
        )
        assertEquals(
            "判据实现必须唯一留在纯策略内",
            1,
            Regex("""fun isTextLikeContent\(""").findAll(src).count()
        )
    }
}
