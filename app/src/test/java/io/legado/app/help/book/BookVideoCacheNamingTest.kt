package io.legado.app.help.book

import io.legado.app.data.entities.BookChapter
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 视频缓存命名与统计口径（2026-10-24 真机铁证回归）。
 *
 * 真机现场：目录已有 76 个 `c-{md5}.mp4`，离线缓存页却显示「已下载 10/86」，
 * 因为统计沿用了文本口径（`chapter.getFileName()` → `.nb`）。本用例锁定：
 * 视频集只认 `.mp4` 主名/兼容名，卷行永不计入。
 */
class BookVideoCacheNamingTest {

    private fun chapter(
        index: Int,
        url: String = "https://example.com/play/$index",
        title: String = "第${index}集",
        volume: Boolean = false
    ) = BookChapter(
        url = url,
        title = title,
        index = index,
        bookUrl = "book://demo",
        isVolume = volume
    )

    @Test
    fun primaryNameUsesMd5AndMp4Suffix() {
        val ch = chapter(5)
        val name = BookVideoCache.primaryNameOf(ch)
        assertEquals("主名形如 c-{16位md5}.mp4", 4, name.takeLast(4).length)
        assertEquals(".mp4", name.takeLast(4))
        assertTrue("主名必须带 c- 前缀", name.startsWith("c-"))
        // 不同集（URL 不同）必须得到不同文件名，否则会互相覆盖
        assertFalse(
            "不同集的主名不得相同",
            BookVideoCache.primaryNameOf(chapter(6)) == name
        )
    }

    @Test
    fun legacyNameCarriesIndexAndSuffix() {
        val ch = chapter(7)
        val legacy = BookVideoCache.legacyNameOf(ch)
        assertEquals(".mp4", legacy.takeLast(4))
        assertTrue("兼容名以 5 位集号开头", legacy.startsWith("00007-"))
    }

    @Test
    fun directoryMatchCountsOnlyRealEpisodes() {
        val real = chapter(8)
        val volume = chapter(0, url = "", title = "线路一", volume = true)
        val dirNames = setOf(
            BookVideoCache.primaryNameOf(real),
            BookVideoCache.primaryNameOf(volume)
        )
        // 期望值断言：正片命中 1 次，卷行命中 0 次（卷行即便有同名文件也不算已缓存）
        assertEquals(1, dirNames.count { BookVideoCache.isCachedIn(setOf(it), real) })
        assertEquals(0, dirNames.count { BookVideoCache.isCachedIn(setOf(it), volume) })
    }

    @Test
    fun textCacheFileDoesNotImpersonateVideoCache() {
        val ch = chapter(9)
        assertEquals(".nb", ch.getFileName().takeLast(3))
        assertEquals(
            "目录里只有 .nb 时视频命中数必须为 0",
            0,
            setOf(ch.getFileName()).count { BookVideoCache.isCachedIn(setOf(it), ch) }
        )
    }
}
