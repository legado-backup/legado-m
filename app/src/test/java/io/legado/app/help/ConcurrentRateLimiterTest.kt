package io.legado.app.help

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B12 缓存并发率 纯函数单测
 */
class ConcurrentRateLimiterTest {

    @Test
    fun isValidRate_null_isValid() {
        assertTrue(ConcurrentRateLimiter.isValidRate(null))
        assertTrue(ConcurrentRateLimiter.isValidRate(""))
        assertTrue(ConcurrentRateLimiter.isValidRate("  "))
    }

    @Test
    fun isValidRate_number_isValid() {
        assertTrue(ConcurrentRateLimiter.isValidRate("1500"))
        assertTrue(ConcurrentRateLimiter.isValidRate("100"))
    }

    @Test
    fun isValidRate_slashFormat_isValid() {
        assertTrue(ConcurrentRateLimiter.isValidRate("20/60000"))
        assertTrue(ConcurrentRateLimiter.isValidRate("1/1000"))
    }

    @Test
    fun isValidRate_invalid_isRejected() {
        assertFalse(ConcurrentRateLimiter.isValidRate("abc"))
        assertFalse(ConcurrentRateLimiter.isValidRate("20/0"))
        assertFalse(ConcurrentRateLimiter.isValidRate("0"))
        assertFalse(ConcurrentRateLimiter.isValidRate("-1500"))
        assertFalse(ConcurrentRateLimiter.isValidRate("20/"))
    }

    @Test
    fun effectiveRate_takesStricterSlashFormat() {
        // 1500 间隔 ≈ 0.67/s；20/60000 = 0.33/s，更严格
        assertEquals("20/60000", ConcurrentRateLimiter.effectiveRate("1500", "20/60000"))
    }

    @Test
    fun effectiveRate_takesStricterNumberFormat() {
        // 3000 间隔 = 0.33/s < 1500 = 0.67/s，更严格
        assertEquals("3000", ConcurrentRateLimiter.effectiveRate("3000", "1500"))
    }

    @Test
    fun effectiveRate_nullRateReturnsOther() {
        assertEquals("1500", ConcurrentRateLimiter.effectiveRate(null, "1500"))
        assertEquals("1500", ConcurrentRateLimiter.effectiveRate("1500", null))
    }

    @Test
    fun effectiveRate_blankOrZeroIsUnlimited() {
        // blank/0 视为不限制（吞吐无穷），返回另一侧
        assertEquals("1500", ConcurrentRateLimiter.effectiveRate("", "1500"))
        assertEquals("1500", ConcurrentRateLimiter.effectiveRate("0", "1500"))
        // 两侧均不限制时返回第一侧
        assertEquals("0", ConcurrentRateLimiter.effectiveRate("0", ""))
    }

    @Test
    fun effectiveRate_sameRateReturnsEither() {
        assertEquals("1500", ConcurrentRateLimiter.effectiveRate("1500", "1500"))
    }
}
