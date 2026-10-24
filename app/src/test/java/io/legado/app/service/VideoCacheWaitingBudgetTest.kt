package io.legado.app.service

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * video-cache-and-multiep：视频缓存启动期的「目录等待预算」不变量。
 *
 * 真机故障背景（2026-10-24）：详情页「点击缓存自动入架」时书籍已入库但目录尚未落库，
 * 缓存服务立刻启动会因「目录为空」fail-fast —— 用户感知即「缓存不了」。
 * 因此服务必须轮询等待目录落库，本测试锁定预算范围（过短无效、过长无反馈）。
 */
class VideoCacheWaitingBudgetTest {

    @Test
    fun waitBudgetCoversTocLoadWindow() {
        val totalMs = VideoCacheService.EPISODE_WAIT_POLLS * VideoCacheService.EPISODE_WAIT_STEP_MS
        assertTrue("等待预算须 ≥ 10s（覆盖详情页入架→目录落库）", totalMs >= 10_000L)
        assertTrue("等待预算须 ≤ 30s（超时须尽快给出失败反馈）", totalMs <= 30_000L)
    }

    @Test
    fun pollIntervalIsReasonablySmall() {
        assertEquals("轮询间隔应 500ms（兼顾响应速度与查库压力）", 500L, VideoCacheService.EPISODE_WAIT_STEP_MS)
        assertTrue("轮询次数须为正", VideoCacheService.EPISODE_WAIT_POLLS > 0)
    }
}
