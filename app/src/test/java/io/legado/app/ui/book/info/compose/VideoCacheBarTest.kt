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

    @Test
    fun `in-shelf wait window is bounded`() {
        // 入架等待必须有限（无限等待会让"点击缓存"永远挂在 pending 态）
        assertTrue("入架等待须为正", IN_SHELF_WAIT_MS > 0)
        assertTrue("入架等待须≤15s（弱网余量上限）", IN_SHELF_WAIT_MS <= 15_000L)
    }

    @Test
    fun `search book also renders the bar when video`() {
        // 搜索书（未入架）详情页同样需要缓存入口 → 可见性只看类型，不看是否已入架
        assertTrue(videoCacheBarVisible(true))
    }
}
