package io.legado.app.ui.book.read.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * NEW-91：样式弹层的**模板作用域判定**必须走单源（`ReaderTemplateManager.isTextLikeContent`）。
 *
 * 该判定原为内联副本；若与阅读页口径分叉，会出现「弹层说已接管、正文其实没换」的静默欺骗
 * （KDoc 明载此风险）——本用例钉住"只转发、不再内联"。
 */
class ReadStyleDialogContentKindDelegationTest {

    private val src = SourceFileProbe.sourceText("ui/book/read/config/ReadStyleDialog.kt")

    @Test
    fun `scope check delegates to the single source`() {
        assertEquals(
            "模板作用域判定必须调用单源",
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
