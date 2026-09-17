package io.legado.app.help.dlna

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * dlna-cast-cache-unify AD-04/REQ-4/REQ-5：档位解析与自动分档纯逻辑单测。
 *
 * 覆盖：推荐档区间边界（6/7/8/11/12/16GB 与不可知）、旧值归并（向上取最近档）、
 * 按共享缓存容量收敛窗口、自动/自定义两种模式的生效口径。
 */
class CastTuningTest {

    private fun gb(value: Int) = value.toLong() * 1024

    @Test
    fun `12GB 及以上取激进档`() {
        val expected = CastTuning(512, 15, 6)
        assertEquals(expected, CastTuner.recommend(gb(12)))
        assertEquals(expected, CastTuner.recommend(gb(16)))
    }

    @Test
    fun `8 到 11GB 取中档`() {
        val expected = CastTuning(256, 10, 4)
        assertEquals(expected, CastTuner.recommend(gb(8)))
        assertEquals(expected, CastTuner.recommend(gb(11)))
    }

    @Test
    fun `7GB 及以下取兜底档`() {
        assertEquals(CastTuner.FALLBACK, CastTuner.recommend(gb(7)))
        assertEquals(CastTuner.FALLBACK, CastTuner.recommend(gb(4)))
    }

    @Test
    fun `内存不可知取兜底档`() {
        assertEquals(CastTuner.FALLBACK, CastTuner.recommend(0))
        assertEquals(CastTuner.FALLBACK, CastTuner.recommend(-1))
    }

    @Test
    fun `旧档值向上归并到最近合法档`() {
        // 旧版档位：内存 32/64/128/256、窗口 3/5/10、并发 2/3/4
        assertEquals(64, CastTuner.nearestTier(32, DlnaConstants.CACHE_MB_TIERS))
        assertEquals(128, CastTuner.nearestTier(128, DlnaConstants.CACHE_MB_TIERS))
        // 超过最大档 → 取最大档
        assertEquals(512, CastTuner.nearestTier(1024, DlnaConstants.CACHE_MB_TIERS))
        assertEquals(5, CastTuner.nearestTier(3, DlnaConstants.PREFETCH_WINDOW_TIERS))
        assertEquals(3, CastTuner.nearestTier(2, DlnaConstants.PREFETCH_CONCURRENCY_TIERS))
    }

    @Test
    fun `窗口按共享缓存容量收敛`() {
        // 100MB 容量 / 单片 8MB → 上限 12 片 → 15 收敛到 10
        assertEquals(10, CastTuner.clampWindow(15, 100L * 1024 * 1024))
        // 120MB → 上限 15 片 → 不收敛
        assertEquals(15, CastTuner.clampWindow(15, 120L * 1024 * 1024))
        // 50MB → 上限 6 片 → 落最小档 5
        assertEquals(5, CastTuner.clampWindow(15, 50L * 1024 * 1024))
        // 容量未知（0）→ 不限制
        assertEquals(15, CastTuner.clampWindow(15, 0L))
        // 容量极小（连一片 8MB 都放不下）→ 退到容量上限，避免"写完即被淘汰"
        assertEquals(2, CastTuner.clampWindow(15, 20L * 1024 * 1024))
    }

    @Test
    fun `收敛判定可被面板识别`() {
        assertTrue(CastTuner.windowClamped(15, 100L * 1024 * 1024))
        assertFalse(CastTuner.windowClamped(15, 120L * 1024 * 1024))
    }

    @Test
    fun `自定义模式使用用户档位并归并旧值`() {
        val tuning = CastTuner.resolve(
            mode = DlnaConstants.TUNING_MODE_CUSTOM,
            manual = CastTuning(32, 3, 2),
            totalMemoryMb = gb(16),
            sharedCapacityBytes = 0L
        )
        assertEquals(CastTuning(64, 5, 3), tuning)
    }

    @Test
    fun `自动模式忽略手动值并使用推荐档`() {
        val tuning = CastTuner.resolve(
            mode = DlnaConstants.TUNING_MODE_AUTO,
            manual = CastTuning(64, 5, 3),
            totalMemoryMb = gb(16),
            sharedCapacityBytes = 0L
        )
        assertEquals(CastTuning(512, 15, 6), tuning)
    }

    @Test
    fun `自动档也要按共享容量收敛窗口`() {
        val tuning = CastTuner.resolve(
            mode = DlnaConstants.TUNING_MODE_AUTO,
            manual = CastTuning(64, 5, 3),
            totalMemoryMb = gb(16),
            sharedCapacityBytes = 100L * 1024 * 1024
        )
        assertEquals(512, tuning.cacheMb)
        assertEquals(10, tuning.prefetchWindow)
        assertEquals(6, tuning.prefetchConcurrency)
    }

    @Test
    fun `模式为空按自动档处理`() {
        val tuning = CastTuner.resolve(
            mode = null,
            manual = CastTuning(64, 5, 3),
            totalMemoryMb = gb(8),
            sharedCapacityBytes = 0L
        )
        assertEquals(CastTuning(256, 10, 4), tuning)
    }
}