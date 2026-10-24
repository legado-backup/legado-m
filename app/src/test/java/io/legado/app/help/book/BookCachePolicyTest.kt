package io.legado.app.help.book

import io.legado.app.constant.BookType
import io.legado.app.data.entities.Book
import io.legado.app.data.entities.BookChapter
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * book-info-unified-cache AD-02 / AD-04：缓存卡类型分派与「已缓存」单一判定的行为锁定。
 */
class BookCachePolicyTest {

    private fun book(type: Int = 0, origin: String = "s1"): Book =
        Book(bookUrl = "u1", origin = origin).apply { this.type = type }

    private fun chapter(title: String = "第1集", url: String = "https://a.example/1"): BookChapter =
        BookChapter(index = 0, title = title, url = url)

    @Test
    fun kindDispatchByContentType() {
        assertEquals(
            CacheBarKind.VIDEO,
            CacheBarKind.of(isVideo = true, isAudio = false, isImage = false, isLocal = false, hasToc = true)
        )
        assertEquals(
            CacheBarKind.AUDIO,
            CacheBarKind.of(isVideo = false, isAudio = true, isImage = false, isLocal = false, hasToc = true)
        )
        assertEquals(
            CacheBarKind.IMAGE,
            CacheBarKind.of(isVideo = false, isAudio = false, isImage = true, isLocal = false, hasToc = true)
        )
        assertEquals(
            CacheBarKind.TEXT,
            CacheBarKind.of(isVideo = false, isAudio = false, isImage = false, isLocal = false, hasToc = true)
        )
    }

    @Test
    fun localOrNoTocIsUnsupported() {
        assertEquals(
            CacheBarKind.UNSUPPORTED,
            CacheBarKind.of(isVideo = false, isAudio = false, isImage = false, isLocal = true, hasToc = true)
        )
        assertEquals(
            CacheBarKind.UNSUPPORTED,
            CacheBarKind.of(isVideo = true, isAudio = false, isImage = false, isLocal = false, hasToc = false)
        )
    }

    @Test
    fun videoChapterMatchedByMp4Names() {
        val videoBook = book(type = BookType.video)
        val ch = chapter()
        val names = setOf(BookVideoCache.primaryNameOf(ch))
        assertTrue(CachedChapterResolver.isCached(videoBook, ch, names))
        assertFalse(CachedChapterResolver.isCached(videoBook, ch, emptySet()))
    }

    @Test
    fun sourceVideoIdentityUpgradesToMp4Caliber() {
        // JS 源常见：book.type 运行时未写 video 位；仅凭 type 会按文本口径判 ⇒ 漏判
        val bookWithoutVideoBit = book(type = 0)
        val ch = chapter()
        val names = setOf(BookVideoCache.primaryNameOf(ch))
        // 文本口径（不传 sourceIsVideo）在 JVM 会触 Android 缓存目录 ⇒ 不在此断言；
        // 只锁定「书源视频身份可让 .mp4 口径生效」这一行为
        assertTrue(
            CachedChapterResolver.isCached(bookWithoutVideoBit, ch, names, sourceIsVideo = true)
        )
        assertEquals(false, CachedChapterResolver.isCached(null, ch, names, sourceIsVideo = true))
    }

    @Test
    fun localBookIsAlwaysCached() {
        val localBook = book(type = BookType.local)
        assertEquals(true, CachedChapterResolver.isCached(localBook, chapter(), emptySet()))
    }

    @Test
    fun cachedIndexesReturnsRealIndexes() {
        val videoBook = book(type = BookType.video)
        val chapters = listOf(
            chapter(title = "第1集", url = "https://a.example/1"),
            chapter(title = "第2集", url = "https://a.example/2"),
            chapter(title = "第3集", url = "https://a.example/3"),
        )
        val names = setOf(
            BookVideoCache.primaryNameOf(chapters[1]),
            BookVideoCache.primaryNameOf(chapters[2]),
        )
        assertEquals(setOf(1, 2), CachedChapterResolver.cachedIndexes(videoBook, chapters, names))
        assertEquals(0, CachedChapterResolver.cachedIndexes(videoBook, emptyList(), names).size)
    }
}
