package io.legado.app.ui.main.explore

import io.legado.app.ui.book.explore.ExploreShowLayout
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * video-cache-and-multiep R11 / V7：新版发现页（`ExploreModernListScreen`）布局路由。
 *
 * 目标：`2=瀑布 / 3=三列 / 4=双列` 都必须走网格或瀑布容器，`1=列表` 才走 LazyColumn；
 * 双列（4）曾被旧实现漏判而回落单列 —— 这正是本用例要永久拦住的回归。
 */
class ExploreModernLayoutRoutingTest {

    @Test
    fun gridModesRouteToGridContainer() {
        assertTrue(ExploreShowLayout.isGrid(ExploreShowLayout.WATERFALL))
        assertTrue(ExploreShowLayout.isGrid(ExploreShowLayout.TRIPLE))
        assertTrue(ExploreShowLayout.isGrid(ExploreShowLayout.DUAL))
    }

    @Test
    fun dualModeUsesTwoColumns() {
        assertEquals(2, ExploreShowLayout.columns(ExploreShowLayout.DUAL))
        assertEquals(3, ExploreShowLayout.columns(ExploreShowLayout.TRIPLE))
        assertEquals(2, ExploreShowLayout.columns(ExploreShowLayout.WATERFALL))
    }

    @Test
    fun listModeStaysOffGrid() {
        assertFalse(ExploreShowLayout.isGrid(ExploreShowLayout.LIST))
        assertEquals(1, ExploreShowLayout.columns(ExploreShowLayout.LIST))
    }
}
