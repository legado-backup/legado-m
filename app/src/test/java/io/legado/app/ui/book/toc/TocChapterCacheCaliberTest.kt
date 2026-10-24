package io.legado.app.ui.book.toc

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * book-info-unified-cache AD-04：目录页「是否已缓存」已收敛到单一入口（视频不再恒判未缓存）。
 */
class TocChapterCacheCaliberTest {

    private val src = SourceFileProbe.sourceText("ui/book/toc/TocComposeScreen.kt")

    @Test
    fun delegatesToSingleResolver() {
        assertEquals(true, src.contains("CachedChapterResolver.isCached(book, chapter, cacheFileNames)"))
        // 旧实现（含视频漏判的 hasContent 分支）不得残留
        assertEquals(false, src.contains("BookHelp.hasContent(book, chapter)"))
    }
}
