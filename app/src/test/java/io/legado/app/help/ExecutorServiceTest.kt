package io.legado.app.help

import org.junit.Assert.assertNotSame
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/**
 * core-flow-test-coverage 批次 6（PERF-1）—— 执行器职责分离行为用例（G-01 配对 / G-42 行为断言）。
 *
 * 背景：此前只有一个 `globalExecutor`（单线程池），**日志写盘 / Glide 位图回收 / 正文解析
 * 共用同一条队列** ⇒ 列表滑动时的位图回收与高频日志写盘会把正文解析任务排在后面
 *（用户可感：打开书 / 翻页偶发变慢）。修复＝按职责拆三条队列。
 *
 * 本用例锁两层：
 * ① **同一性**：三者必须是不同执行器实例（防止日后被合回一组）；
 * ② **并发行为**：日志线程被刻意占住时，业务任务仍须立即执行 —— 若三者又被合回
 *    同一个单线程池，这条断言的 latch 会超时失败（真实的回归检测能力）。
 */
class ExecutorServiceTest {

    @Test
    fun logExecutorIsNotGlobalExecutor() {
        assertNotSame(globalExecutor, logExecutor)
    }

    @Test
    fun glideExecutorIsNotGlobalExecutor() {
        assertNotSame(globalExecutor, glideExecutor)
    }

    @Test
    fun glideExecutorIsNotLogExecutor() {
        assertNotSame(logExecutor, glideExecutor)
    }

    @Test
    fun modelTaskRunsWhileLogExecutorIsBlocked() {
        assertTrue("业务任务必须不被日志执行器阻塞", runModelTaskWhileBlocking(logExecutor))
    }

    @Test
    fun modelTaskRunsWhileGlideExecutorIsBlocked() {
        assertTrue("业务任务必须不被位图回收执行器阻塞", runModelTaskWhileBlocking(glideExecutor))
    }

    /**
     * 占住 [blocker] 所在线程后，验证 `globalExecutor` 上的任务仍能立即跑完。
     *
     * @return 业务任务是否在 2 秒内完成（同一单线程池时会超时 ⇒ false）
     */
    private fun runModelTaskWhileBlocking(blocker: java.util.concurrent.ExecutorService): Boolean {
        val blockerStarted = CountDownLatch(1)
        val releaseBlocker = CountDownLatch(1)
        blocker.execute {
            blockerStarted.countDown()
            releaseBlocker.await(5, TimeUnit.SECONDS)
        }
        try {
            assertTrue("占位任务应已开始执行", blockerStarted.await(2, TimeUnit.SECONDS))
            val modelDone = CountDownLatch(1)
            globalExecutor.execute { modelDone.countDown() }
            return modelDone.await(2, TimeUnit.SECONDS)
        } finally {
            releaseBlocker.countDown()
        }
    }
}
