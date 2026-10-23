package io.legado.app.service.kernel

import io.legado.app.data.entities.BookChapter
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * video-cache-and-multiep V1：缓存进度与集数口径的纯逻辑锁定。
 */
class VideoCacheKernelTest {

    private fun chapter(index: Int, isVolume: Boolean = false, title: String = "第${index}集") =
        BookChapter(url = "https://example.com/player/$index", title = title, index = index, isVolume = isVolume)

    @Test
    fun `percent is zero when total is zero`() {
        val progress = VideoCacheKernel.Progress(total = 0, cached = 0)
        assertEquals(0, progress.percent)
    }

    @Test
    fun `percent rounds down and clamps to hundred`() {
        assertEquals(33, VideoCacheKernel.Progress(total = 3, cached = 1).percent)
        assertEquals(100, VideoCacheKernel.Progress(total = 3, cached = 3).percent)
        assertEquals(100, VideoCacheKernel.Progress(total = 3, cached = 5).percent)
    }

    @Test
    fun `episodes exclude volume rows and keep order`() {
        val chapters = listOf(
            chapter(0, isVolume = true, title = "线路一"),
            chapter(1),
            chapter(2),
            chapter(3, isVolume = true, title = "线路二"),
            chapter(4),
        )
        val episodes = VideoCacheKernel.episodesOf(chapters)
        assertEquals(listOf(1, 2, 4), episodes.map { it.index })
    }

    @Test
    fun `episodes of empty list is empty`() {
        assertTrue(VideoCacheKernel.episodesOf(emptyList()).isEmpty())
    }

    @Test
    fun `isCached is false before index built`() {
        assertFalse(VideoCacheKernel.isCached("https://example.com/book/never-used", 0))
    }
}
