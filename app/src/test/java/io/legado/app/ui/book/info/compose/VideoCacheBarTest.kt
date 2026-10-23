package io.legado.app.ui.book.info.compose

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * video-cache-and-multiep R2：详情页缓存条的展示与进度口径。
 */
class VideoCacheBarTest {

    @Test
    fun `bar is visible only for video source books`() {
        assertTrue(videoCacheBarVisible(true))
        assertFalse(videoCacheBarVisible(false))
    }

    @Test
    fun `percent is zero without episodes`() {
        assertEquals(0, videoCacheBarPercent(0, 0))
        assertEquals(0, videoCacheBarPercent(5, 0))
    }

    @Test
    fun `percent rounds down and clamps`() {
        assertEquals(33, videoCacheBarPercent(1, 3))
        assertEquals(100, videoCacheBarPercent(3, 3))
        assertEquals(100, videoCacheBarPercent(9, 3))
        assertEquals(0, videoCacheBarPercent(-1, 3))
    }
}
