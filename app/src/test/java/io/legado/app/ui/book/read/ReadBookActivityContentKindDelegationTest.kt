package io.legado.app.ui.book.read

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-91：阅读页 `isTextRichMode()` 的**内容形态判定**必须走单源（`ReaderTemplateManager.isTextLikeContent`）。
 *
 * 与 `ReadStyleDialog.templateInScope()` 共用同一判据 ⇒ 二者不可能再分叉（此前两处各自内联同一串判据）。
 */
class ReadBookActivityContentKindDelegationTest {

    private val src = SourceFileProbe.sourceText("ui/book/read/ReadBookActivity.kt")

    @Test
    fun `text rich mode delegates to the single source`() {
        assertEquals(
            "文本渲染模式判定必须调用单源",
            1,
            Regex("""ReaderTemplateManager\.isTextLikeContent\(""").findAll(src).count()
        )
        assertEquals(
            "不得再内联内容形态判据（isEpub || isAudio …）",
            0,
            Regex("""book\.isEpub \|\| book\.isAudio""").findAll(src).count()
        )
    }
}
