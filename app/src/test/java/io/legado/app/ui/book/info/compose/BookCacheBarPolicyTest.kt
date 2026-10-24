package io.legado.app.ui.book.info.compose

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * book-info-unified-cache AD-01：统一缓存卡的进度与完成态口径（原 VideoCacheBar 用例迁移）。
 */
class BookCacheBarPolicyTest {

    @Test
    fun percentIsZeroWithoutTotal() {
        assertEquals(0, bookCachePercent(0, 0))
        assertEquals(0, bookCachePercent(5, 0))
        assertEquals(0, bookCachePercent(5, -3))
    }

    @Test
    fun percentRoundsDownAndClamps() {
        assertEquals(33, bookCachePercent(1, 3))
        assertEquals(100, bookCachePercent(3, 3))
        assertEquals(100, bookCachePercent(9, 3))
        assertEquals(0, bookCachePercent(-1, 3))
    }

    @Test
    fun inShelfWaitWindowIsBounded() {
        // 入架等待必须有限（无限等待会让"点击缓存"永远挂在 pending 态）
        assertTrue("入架等待须为正", IN_SHELF_WAIT_MS > 0)
        assertTrue("入架等待须≤15s（弱网余量上限）", IN_SHELF_WAIT_MS <= 15_000L)
    }

    @Test
    fun doneHidesCacheAction() {
        // 完成态：全部落盘后不再给「缓存」动作（重复点击只会空跑，误导用户）
        assertEquals(true, bookCacheDone(BookCacheStatus(cached = 12, total = 12)))
        assertEquals(false, bookCacheDone(BookCacheStatus(cached = 12, total = 12, running = true)))
        assertEquals(false, bookCacheDone(BookCacheStatus(cached = 5, total = 12)))
        assertEquals(false, bookCacheDone(BookCacheStatus(cached = 0, total = 0)))
    }

    @Test
    fun doneFalseWhileRunning() {
        assertFalse(bookCacheDone(BookCacheStatus(cached = 0, total = 10, running = true)))
    }
}
