package io.legado.app.ui.book.read.textweb

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 沙箱状态日志限频门禁行为用例（G-01 配对 / G-42 行为断言）。
 *
 * 真值表：时间窗内一律抑制（含状态名变化的情形——真机实测 634 行/6 秒属两状态名交替，
 * 故"变化就放行"的口径无效）；达到或超过间隔才放行。
 */
class RenderStateLogGateTest {

    @Test
    fun zeroElapsed_isRejected() {
        assertFalse(RenderStateLogGate.shouldLog(0L))
    }

    @Test
    fun justBelowInterval_isRejected() {
        assertFalse(RenderStateLogGate.shouldLog(RenderStateLogGate.MIN_INTERVAL_MS - 1))
    }

    @Test
    fun exactlyAtInterval_isAllowed() {
        assertTrue(RenderStateLogGate.shouldLog(RenderStateLogGate.MIN_INTERVAL_MS))
    }

    @Test
    fun wellBeyondInterval_isAllowed() {
        assertTrue(RenderStateLogGate.shouldLog(5_000L))
    }

    @Test
    fun customInterval_isRespected() {
        assertTrue(RenderStateLogGate.shouldLog(100L, 100L))
        assertFalse(RenderStateLogGate.shouldLog(99L, 100L))
    }
}
