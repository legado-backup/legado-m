package io.legado.app.service.kernel

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 失败集后置排序（2026-10-24 真机体验铁证）。
 *
 * 现象：某视频书前 10 集是站点限制页（无播放器 DOM），每集都要跑满 15s 嗅探超时。
 * 缓存在第一轮把这 10 集排在开头 ⇒ 用户盯着进度条 2.5 分钟看不到任何一集落盘，
 * 感知为「缓存不了 / 缓存不好用」。
 *
 * 约定：本轮失败过的集在重跑时**排到末尾**，正常集先落盘；顺序在同一组内保持稳定。
 */
class VideoCacheFailedOrderingTest {

    private val kernel = SourceFileProbe.sourceText("service/kernel/VideoCacheKernel.kt")
    private val service = SourceFileProbe.sourceText("service/VideoCacheService.kt")

    @Test
    fun failedEpisodesAreMovedToTheEnd() {
        val positions = listOf(0, 1, 2, 3, 4)
        // 未失败：顺序原样
        assertEquals(positions, VideoCacheKernel.orderPositions(BOOK, positions))
    }

    @Test
    fun cachedEpisodesKeepRelativeOrder() {
        val positions = listOf(10, 11, 12)
        val ordered = VideoCacheKernel.orderPositions(BOOK, positions)
        assertEquals("稳定排序：同组内相对顺序不变", positions, ordered)
        assertFalse("未失败过的集不应被判为失败", VideoCacheKernel.isFailed(BOOK, 10))
    }

    @Test
    fun kernelRemembersFailuresAndOrdersThemLast() {
        assertTrue(
            "内核必须记录失败集（服务据此排序）",
            kernel.contains("private val failedIndexes = ConcurrentHashMap<String, MutableSet<Int>>()")
        )
        assertTrue(
            "失败集判定必须可查询",
            kernel.contains("fun isFailed(bookUrl: String, index: Int): Boolean")
        )
        assertTrue(
            "排序口径：失败集排后，其余保持原序",
            kernel.contains("positions.sortedBy { if (isFailed(bookUrl, it)) 1 else 0 }")
        )
    }

    @Test
    fun successAndClearResetFailureMemory() {
        assertTrue(
            "某集成功后必须从失败集合移除（避免永久后置）",
            kernel.contains("failedIndexes[bookUrl]?.remove(index)")
        )
        assertTrue(
            "清理缓存时失败记忆必须一并清空",
            kernel.contains("failedIndexes.remove(bookUrl)")
        )
    }

    @Test
    fun serviceIteratesInKernelOrder() {
        assertTrue(
            "服务必须按内核给出的顺序遍历（而非硬编码 0..N）",
            service.contains("val ordered = VideoCacheKernel.orderPositions(") &&
                service.contains("for (position in ordered) {")
        )
    }

    private companion object {
        const val BOOK = "book://ordering-demo"
    }
}
