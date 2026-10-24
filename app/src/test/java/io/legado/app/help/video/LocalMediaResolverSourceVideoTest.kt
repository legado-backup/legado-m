package io.legado.app.help.video

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * book-info-unified-cache AD-06：视频身份复合判定（书源类型兜底 `book.type` 未写位）。
 */
class LocalMediaResolverSourceVideoTest {

    private val src = SourceFileProbe.sourceText("help/video/LocalMediaResolver.kt")

    @Test
    fun bothEntriesAcceptSourceVideoIdentity() {
        assertEquals(true, src.contains("fun hasLocal(book: Book, chapter: BookChapter, sourceIsVideo: Boolean = false)"))
        assertEquals(true, src.contains("fun localUri(book: Book, chapter: BookChapter, sourceIsVideo: Boolean = false)"))
    }

    @Test
    fun videoBranchUsesCompositeIdentity() {
        assertEquals(true, src.contains("book.isVideo || sourceIsVideo -> BookVideoCache.has(book, chapter)"))
        assertEquals(true, src.contains("if (!(book.isVideo || sourceIsVideo) || chapter.isVolume) return null"))
    }
}
