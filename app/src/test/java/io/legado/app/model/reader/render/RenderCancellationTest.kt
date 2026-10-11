package io.legado.app.model.reader.render

import kotlin.coroutines.cancellation.CancellationException
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 渲染链路取消语义单测（epub-md-rich-rendering 补充任务 S8 配对；AD-28⑨）。
 *
 * 覆盖：①`runRenderCatching` 对 [CancellationException] **重抛**（不得被当作业务失败收敛）；
 * ②普通异常仍正常收敛为 `Result.failure`；③成功路径不受影响；
 * ④`rethrowIfCancellation` 对普通异常不抛。
 */
class RenderCancellationTest {

    @Test
    fun `取消异常必须重抛而非被收敛为失败结果`() {
        assertThrows(CancellationException::class.java) {
            RenderCancellation.runRenderCatching<Unit> { throw CancellationException("cancelled") }
        }
    }

    @Test
    fun `普通异常仍收敛为失败结果`() {
        val result = RenderCancellation.runRenderCatching<Unit> { throw IllegalStateException("boom") }
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull() is IllegalStateException)
    }

    @Test
    fun `成功路径返回成功结果`() {
        val result = RenderCancellation.runRenderCatching { 42 }
        assertEquals(42, result.getOrNull())
    }

    @Test
    fun `重抛判据对普通异常不抛`() {
        RenderCancellation.rethrowIfCancellation(IllegalStateException("boom"))
    }
}