package io.legado.app.utils

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B1 · R5「翻页动画速度四档」单测。
 *
 * 需求口径：四档可调，**新装默认 300ms**（标准档）；非法/越界档位必须安全回落标准档，
 * 不得出现 0ms（动画消失）或负值（异常）。
 */
class PageTurnAnimSpeedTest {

    @Test
    fun fourTiers_mapToExpectedMillis() {
        assertEquals(4, PageTurnAnimSpeed.tierCount)
        assertEquals(450, PageTurnAnimSpeed.msOf(PageTurnAnimSpeed.SLOW))
        assertEquals(300, PageTurnAnimSpeed.msOf(PageTurnAnimSpeed.STANDARD))
        assertEquals(180, PageTurnAnimSpeed.msOf(PageTurnAnimSpeed.FAST))
        assertEquals(100, PageTurnAnimSpeed.msOf(PageTurnAnimSpeed.FASTEST))
    }

    @Test
    fun defaultTier_isStandardAnd300ms() {
        assertEquals("默认档位必须为标准档", PageTurnAnimSpeed.STANDARD, PageTurnAnimSpeed.DEFAULT_TIER)
        assertEquals("新装默认动画时长必须为 300ms", 300, PageTurnAnimSpeed.msOf(PageTurnAnimSpeed.DEFAULT_TIER))
        assertEquals(300, PageTurnAnimSpeed.STANDARD_MS)
    }

    @Test
    fun illegalTier_fallsBackToStandard() {
        assertEquals(300, PageTurnAnimSpeed.msOf(-1))
        assertEquals(300, PageTurnAnimSpeed.msOf(4))
        assertEquals(300, PageTurnAnimSpeed.msOf(Int.MAX_VALUE))
        assertEquals(300, PageTurnAnimSpeed.msOf(Int.MIN_VALUE))
    }
}