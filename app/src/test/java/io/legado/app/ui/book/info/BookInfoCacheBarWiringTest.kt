package io.legado.app.ui.book.info

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * book-info-unified-cache AD-01：三套详情页共用同一张统一缓存卡（旧 `VideoCacheBar` 退役）。
 */
class BookInfoCacheBarWiringTest {

    private val modern =
        SourceFileProbe.sourceText("ui/book/info/compose/BookInfoModernRoute.kt")
    private val immersive =
        SourceFileProbe.sourceText("ui/book/info/compose/BookInfoComposeRoute.kt")
    private val classic =
        SourceFileProbe.sourceText("ui/book/info/BookInfoActivity.kt")

    @Test
    fun allThreePagesRenderUnifiedBar() {
        assertEquals(true, modern.contains("BookCacheBar("))
        assertEquals(true, immersive.contains("BookCacheBar("))
        assertEquals(true, classic.contains("BookCacheBar("))
    }

    @Test
    fun legacyVideoOnlyBarIsRetired() {
        // 用「调用形态」断言（避免误伤 initVideoCacheBar() 这类包含子串的方法名）
        assertEquals(false, modern.contains("VideoCacheBar(book"))
        assertEquals(false, immersive.contains("VideoCacheBar(bookUrl"))
        assertEquals(false, classic.contains("VideoCacheBar(bookUrl"))
    }
}
