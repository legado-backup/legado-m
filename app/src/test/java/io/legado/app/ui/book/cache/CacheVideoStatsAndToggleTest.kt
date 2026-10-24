package io.legado.app.ui.book.cache

import io.legado.app.data.entities.BookChapter
import io.legado.app.help.book.BookVideoCache
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 离线缓存页的视频口径（2026-10-24 真机铁证）。
 *
 * 现场：该书目录里已有 76 个 `c-{md5}.mp4`，列表却显示「已下载 10/86」——统计走了文本口径
 * （`chapter.getFileName()` 默认 `.nb`），且行尾 ▶ 走 `CacheBook.start`（文本管线），
 * 对视频书点了等于没反应 ⇒ 用户感知「缓存不了 / 缓存不好用」。
 */
class CacheVideoStatsAndToggleTest {

    private val cacheViewModel = SourceFileProbe.sourceText("ui/book/cache/CacheViewModel.kt")
    private val cacheActivity = SourceFileProbe.sourceText("ui/book/cache/CacheActivity.kt")
    private val router = SourceFileProbe.sourceText("ui/book/cache/CacheTaskRouter.kt")

    private fun chapter(index: Int, url: String, title: String, volume: Boolean = false) =
        BookChapter(
            url = url,
            title = title,
            index = index,
            bookUrl = "book://demo",
            isVolume = volume
        )

    @Test
    fun primaryNameIsCountedForVideoEpisodes() {
        val ch = chapter(1, "https://example.com/play/1", "第1集")
        val primary = BookVideoCache.primaryNameOf(ch)
        assertEquals("视频落盘后缀必须是 mp4", ".mp4", primary.takeLast(4))
        assertTrue(
            "目录中存在主名时必须命中视频统计口径",
            BookVideoCache.isCachedIn(setOf(primary, "unrelated.mp4"), ch)
        )
    }

    @Test
    fun legacyNameIsCountedForVideoEpisodes() {
        val ch = chapter(2, "https://example.com/play/2", "第2集")
        val legacy = BookVideoCache.legacyNameOf(ch)
        assertEquals("兼容名后缀必须是 mp4", ".mp4", legacy.takeLast(4))
        assertTrue(BookVideoCache.isCachedIn(setOf(legacy), ch))
    }

    @Test
    fun textSuffixNameDoesNotCountAsVideoCache() {
        val ch = chapter(3, "https://example.com/play/3", "第3集")
        val textName = ch.getFileName()
        assertEquals("文本口径文件名是 .nb", ".nb", textName.takeLast(3))
        assertFalse(
            "目录里只有同名 .nb 时不得算作视频已缓存（旧口径误报根因）",
            BookVideoCache.isCachedIn(setOf(textName), ch)
        )
        // 同一目录集合下命中数量必须为 0（带期望值的口径断言）
        assertEquals(0, setOf(textName).count { BookVideoCache.isCachedIn(setOf(it), ch) })
    }

    @Test
    fun volumeRowsAreNeverCounted() {
        val volume = chapter(0, "", "线路一", volume = true)
        assertEquals(
            "卷行（线路名）不是一集，恒不计入已缓存",
            0,
            setOf(BookVideoCache.primaryNameOf(volume)).count {
                BookVideoCache.isCachedIn(setOf(it), volume)
            }
        )
    }

    @Test
    fun cacheViewModelUsesVideoSemantics() {
        assertTrue(
            "离线缓存页统计必须对视频书切换口径",
            cacheViewModel.contains("if (book.isVideo) {") &&
                cacheViewModel.contains("BookVideoCache.isCachedIn(cacheNames, chapter)")
        )
    }

    @Test
    fun videoBooksStartTheVideoCacheService() {
        assertTrue(
            "视频书的开始/停止必须走 VideoCacheKernel（CacheBook 是文本管线，点了等于没反应）",
            router.contains("VideoCacheKernel.start(context, book.bookUrl, from)") &&
                router.contains("VideoCacheKernel.stop(context, book.bookUrl)")
        )
        assertTrue(
            "行尾图标运行态与点击判定同源，避免图标/动作错配",
            cacheActivity.contains("runningOf = { CacheTaskRouter.isRunning(it) }") &&
                cacheActivity.contains("if (CacheTaskRouter.isRunning(it)) {")
        )
    }
}
