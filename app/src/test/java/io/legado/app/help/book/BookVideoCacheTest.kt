package io.legado.app.help.book

import io.legado.app.data.entities.BookChapter
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * video-cache-and-multiep AD-01：视频缓存命名契约（与 .nb 同目录、mp4 后缀、卷行不可缓存）。
 */
class BookVideoCacheTest {

    private fun chapter(index: Int, isVolume: Boolean = false, url: String = "/player/1/$index") =
        BookChapter(url = url, title = "第${index}集", index = index, isVolume = isVolume)

    @Test
    fun `suffix is mp4`() {
        assertEquals("mp4", BookVideoCache.suffix)
    }

    @Test
    fun `volume row is not cacheable`() {
        assertFalse(BookVideoCache.isCacheable(chapter(0, isVolume = true)))
        assertTrue(BookVideoCache.isCacheable(chapter(1)))
    }

    @Test
    fun `primary name carries mp4 suffix and content hash prefix`() {
        val name = BookVideoCache.primaryNameOf(chapter(3))
        assertTrue(name.endsWith(".mp4"))
        assertTrue(name.startsWith("c-"))
    }

    @Test
    fun `legacy name keeps zero padded index and mp4 suffix`() {
        val name = chapter(7).getFileName(BookVideoCache.suffix)
        assertTrue(name.endsWith(".mp4"))
        assertTrue(name.startsWith("00007-"))
    }

    @Test
    fun `primary and legacy names differ so both are probed`() {
        val c = chapter(2)
        assertTrue(BookVideoCache.primaryNameOf(c) != c.getFileName(BookVideoCache.suffix))
    }
}
