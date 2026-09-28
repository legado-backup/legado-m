package io.legado.app.web

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * WebRateLimiter 单测（一期 · 1.3.3 / REQ-1-110）。
 *
 * 通过注入 `now` 完全控制时间，免 sleep：窗口内放行 → 超限拒绝 → 跨窗口复位；不同键互不影响。
 */
class WebRateLimiterTest {

    @Before
    fun setUp() {
        WebRateLimiter.reset()
    }

    @Test
    fun withinWindow_allowsUpToLimit_thenRejects() {
        val key = "READONLY:test"
        val now = 1_000_000L
        repeat(WebRateLimiter.LIMIT) { i ->
            assertTrue("第 ${i + 1} 次应放行", WebRateLimiter.tryAcquire(key, now))
        }
        assertFalse("第 ${WebRateLimiter.LIMIT + 1} 次须被限流", WebRateLimiter.tryAcquire(key, now))
        assertFalse("窗口内持续超限仍拒绝", WebRateLimiter.tryAcquire(key, now + 1))
    }

    @Test
    fun afterWindow_resetsCounter() {
        val key = "MANAGE:test"
        val now = 2_000_000L
        repeat(WebRateLimiter.LIMIT + 1) { WebRateLimiter.tryAcquire(key, now) }
        assertFalse("窗口末尾应仍限流", WebRateLimiter.tryAcquire(key, now))
        assertTrue(
            "跨过窗口长度后计数须复位",
            WebRateLimiter.tryAcquire(key, now + WebRateLimiter.WINDOW_MS)
        )
    }

    @Test
    fun distinctKeys_areIndependent() {
        val now = 3_000_000L
        repeat(WebRateLimiter.LIMIT + 1) { WebRateLimiter.tryAcquire("k1", now) }
        assertFalse("k1 已超限", WebRateLimiter.tryAcquire("k1", now))
        assertTrue("k2 不受 k1 影响", WebRateLimiter.tryAcquire("k2", now))
    }

    @Test
    fun keyOf_separatesLevelAndTokenDigest() {
        val a = WebRateLimiter.keyOf(TokenManager.Level.READONLY, "token-a")
        val b = WebRateLimiter.keyOf(TokenManager.Level.MANAGE, "token-a")
        val c = WebRateLimiter.keyOf(TokenManager.Level.READONLY, "token-b")
        assertNotEquals("同令牌不同级别须分开计数", a, b)
        assertNotEquals("同级别不同令牌须分开计数", a, c)
        assertFalse("键中不得出现令牌明文", a.contains("token-a"))
        assertEquals("同输入键须稳定", a, WebRateLimiter.keyOf(TokenManager.Level.READONLY, "token-a"))
    }
}
