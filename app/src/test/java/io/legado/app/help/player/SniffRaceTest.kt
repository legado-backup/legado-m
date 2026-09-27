package io.legado.app.help.player

import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * W2 / REQ-14（AD-05）：嗅探赛马器不变量。
 *
 * 协议与预置决策：并发上限 **2**（只统计网络类策略）、先到先用、低置信不抢占、全灭等总超时、
 * 先到即结构化取消其余（无协程泄漏）、连续失败 3 次冷却 60s。
 *
 * 纯 JVM：策略以 lambda 注入（`SniffRace.strategy`），不依赖 media3 / Android 运行时。
 */
class SniffRaceTest {

    private val url = "https://example.invalid/video"
    private val headers = mapOf("Referer" to "https://example.invalid/")

    @Test
    fun emptyStrategiesReturnNull() = runBlocking {
        assertNull(SniffRace.race<String>(url, headers, emptyList(), totalTimeoutMs = 200L))
    }

    @Test
    fun firstAuthoritativeResultWins() = runBlocking {
        val result = SniffRace.race(
            url, headers,
            strategies = listOf(
                SniffRace.strategy("Slow", 0.9f, 500L) { _, _ -> delay(300); "slow" },
                SniffRace.strategy("Fast", 0.9f, 500L) { _, _ -> delay(20); "fast" }
            ),
            totalTimeoutMs = 1_000L
        )
        assertEquals("先到者胜出", "Fast", result?.strategyName)
        assertEquals("fast", result?.value)
    }

    @Test
    fun losingStrategiesAreCancelledStructurally() = runBlocking {
        val loserCancelled = AtomicBoolean(false)
        val result = SniffRace.race(
            url, headers,
            strategies = listOf(
                SniffRace.strategy("Slow", 0.9f, 5_000L) { _, _ ->
                    try {
                        delay(5_000)
                        "slow"
                    } catch (e: CancellationException) {
                        loserCancelled.set(true)
                        throw e
                    }
                },
                SniffRace.strategy("Fast", 0.9f, 500L) { _, _ -> delay(20); "fast" }
            ),
            totalTimeoutMs = 1_000L
        )
        assertEquals("Fast", result?.strategyName)
        delay(120)
        assertTrue("胜出后败者必须被结构化取消（防协程泄漏）", loserCancelled.get())
    }

    @Test
    fun lowConfidenceResultCannotPreempt() = runBlocking {
        val result = SniffRace.race(
            url, headers,
            strategies = listOf(
                // 低置信兜底：瞬时返回，但不得抢占
                SniffRace.strategy("Extension", 0.4f, 80L, canWin = false, networkBound = false) { _, _ -> "hint" },
                SniffRace.strategy("Range", 0.9f, 500L) { _, _ -> delay(60); "authoritative" }
            ),
            totalTimeoutMs = 1_000L
        )
        assertEquals("低置信不得抢占权威结果", "Range", result?.strategyName)
        assertEquals("authoritative", result?.value)
    }

    @Test
    fun lowConfidenceResultIsUsedAsFallback() = runBlocking {
        val result = SniffRace.race(
            url, headers,
            strategies = listOf(
                SniffRace.strategy<String>("Extension", 0.4f, 80L, canWin = false, networkBound = false) { _, _ -> "hint" },
                SniffRace.strategy<String>("Range", 0.9f, 100L) { _, _ -> delay(2_000); null }
            ),
            totalTimeoutMs = 300L
        )
        assertEquals("全灭时采用低置信兜底（省去空等）", "Extension", result?.strategyName)
        assertEquals("hint", result?.value)
    }

    @Test
    fun allMissReturnsNull() = runBlocking {
        val result = SniffRace.race(
            url, headers,
            strategies = listOf(
                SniffRace.strategy<String>("A", 0.9f, 200L) { _, _ -> null },
                SniffRace.strategy<String>("B", 0.5f, 200L) { _, _ -> null }
            ),
            totalTimeoutMs = 1_000L
        )
        assertNull("全灭且无兜底 ⇒ null（等价原串行链 UNKNOWN 结果）", result)
    }

    @Test
    fun networkBoundStrategiesRespectConcurrencyCap() = runBlocking {
        val active = AtomicInteger(0)
        val maxActive = AtomicInteger(0)
        fun netStrategy(name: String) = SniffRace.strategy<String>(name, 0.9f, 2_000L) { _, _ ->
            val now = active.incrementAndGet()
            maxActive.updateAndGet { maxOf(it, now) }
            try {
                delay(120)
                null
            } finally {
                active.decrementAndGet()
            }
        }
        SniffRace.race(
            url, headers,
            strategies = listOf(netStrategy("A"), netStrategy("B"), netStrategy("C")),
            maxConcurrent = SniffRace.DEFAULT_MAX_CONCURRENT,
            totalTimeoutMs = 3_000L
        )
        assertEquals("并发上限须为 2（预置决策 design §9.2#1）", 2, SniffRace.DEFAULT_MAX_CONCURRENT)
        assertTrue(
            "网络类策略并发实测 $maxActive 超出上限 ${SniffRace.DEFAULT_MAX_CONCURRENT}",
            maxActive.get() <= SniffRace.DEFAULT_MAX_CONCURRENT
        )
    }

    @Test
    fun instantStrategyIsNotStarvedByNetworkPermits() = runBlocking {
        // 两路网络策略占满额度且都很慢：瞬时策略必须仍能立即产出兜底
        val start = System.currentTimeMillis()
        val result = SniffRace.race(
            url, headers,
            strategies = listOf(
                SniffRace.strategy<String>("A", 0.9f, 5_000L) { _, _ -> delay(5_000); null },
                SniffRace.strategy<String>("B", 0.9f, 5_000L) { _, _ -> delay(5_000); null },
                SniffRace.strategy<String>("Extension", 0.4f, 80L, canWin = false, networkBound = false) { _, _ -> "hint" }
            ),
            maxConcurrent = 2,
            totalTimeoutMs = 300L
        )
        val elapsed = System.currentTimeMillis() - start
        assertEquals("Extension", result?.strategyName)
        assertTrue("瞬时策略不得被网络额度饿死（实测 ${elapsed}ms）", elapsed < 1_500)
    }

    // ------------------------------------------------------------ 资源闸（冷却）

    @Test
    fun limiterCoolsDownAfterThreeConsecutiveFailures() {
        var now = 10_000L
        val limiter = SniffRaceLimiter(clock = { now })
        repeat(SniffRaceLimiter.MAX_CONSECUTIVE_FAILURES - 1) { limiter.noteFailure() }
        assertTrue("未达阈值仍可赛马", limiter.canRace())
        limiter.noteFailure()
        assertFalse("连续 3 次失败 ⇒ 进入冷却", limiter.canRace())
        now += SniffRaceLimiter.COOLDOWN_MS + 1
        assertTrue("冷却到期恢复赛马", limiter.canRace())
    }

    @Test
    fun limiterPresetValuesMatchDesignDecision() {
        assertEquals(3, SniffRaceLimiter.MAX_CONSECUTIVE_FAILURES)
        assertEquals(60_000L, SniffRaceLimiter.COOLDOWN_MS)
    }

    @Test
    fun limiterSuccessResetsFailureStreak() {
        val limiter = SniffRaceLimiter()
        limiter.noteFailure()
        limiter.noteFailure()
        limiter.noteSuccess()
        limiter.noteFailure()
        limiter.noteFailure()
        assertTrue("成功须打断连续失败（2 次后清零再 2 次不触发冷却）", limiter.canRace())
    }
}