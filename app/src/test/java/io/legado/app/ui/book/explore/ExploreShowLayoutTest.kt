package io.legado.app.ui.book.explore

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * video-cache-and-multiep R11 / V7：单源发现页布局模式纯策略锁定。
 */
class ExploreShowLayoutTest {

    @Test
    fun normalize_clampsOutOfRange() {
        assertEquals(ExploreShowLayout.LIST, ExploreShowLayout.normalize(0))
        assertEquals(ExploreShowLayout.LIST, ExploreShowLayout.normalize(-5))
        assertEquals(ExploreShowLayout.DUAL, ExploreShowLayout.normalize(9))
    }

    @Test
    fun normalize_keepsValidModes() {
        for (mode in 1..4) {
            assertEquals(mode, ExploreShowLayout.normalize(mode))
        }
    }

    @Test
    fun columns_mapsEachMode() {
        assertEquals(1, ExploreShowLayout.columns(ExploreShowLayout.LIST))
        assertEquals(2, ExploreShowLayout.columns(ExploreShowLayout.WATERFALL))
        assertEquals(3, ExploreShowLayout.columns(ExploreShowLayout.TRIPLE))
        assertEquals(2, ExploreShowLayout.columns(ExploreShowLayout.DUAL))
    }

    @Test
    fun columns_outOfRangeFallsBackToList() {
        assertEquals(1, ExploreShowLayout.columns(0))
        assertEquals(2, ExploreShowLayout.columns(99))
    }

    @Test
    fun isWaterfall_onlyForWaterfallMode() {
        assertTrue(ExploreShowLayout.isWaterfall(ExploreShowLayout.WATERFALL))
        assertFalse(ExploreShowLayout.isWaterfall(ExploreShowLayout.DUAL))
        assertFalse(ExploreShowLayout.isWaterfall(ExploreShowLayout.LIST))
        assertFalse(ExploreShowLayout.isWaterfall(ExploreShowLayout.TRIPLE))
    }

    @Test
    fun isGrid_falseOnlyForList() {
        assertFalse(ExploreShowLayout.isGrid(ExploreShowLayout.LIST))
        assertTrue(ExploreShowLayout.isGrid(ExploreShowLayout.WATERFALL))
        assertTrue(ExploreShowLayout.isGrid(ExploreShowLayout.TRIPLE))
        assertTrue(ExploreShowLayout.isGrid(ExploreShowLayout.DUAL))
    }

    @Test
    fun default_isWaterfall() {
        assertEquals(ExploreShowLayout.WATERFALL, ExploreShowLayout.DEFAULT)
        assertTrue(ExploreShowLayout.isGrid(ExploreShowLayout.DEFAULT))
    }
}
