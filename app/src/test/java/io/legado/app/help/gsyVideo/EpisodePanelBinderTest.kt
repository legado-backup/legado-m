package io.legado.app.help.gsyVideo

import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * 选集面板绑定器纯函数契约（episode-switch-loading-and-legacy-inline C3）。
 *
 * 弹框网格高度必须等于「min(内容高, 视口上限)」：内容高按 5 列向上取整，
 * 行间计入间距、行尾不计。内嵌面板不设上限（wrap_content）⇒ 本条只覆盖弹框分支。
 */
class EpisodePanelBinderTest {

    @Test
    fun singleRowHeightHasNoGap() {
        // 5 集 = 1 行；1×40 + 0×6 = 40
        assertEquals(
            40,
            EpisodePanelBinder.gridHeightPx(
                itemCount = 5, columns = 5, itemHeightPx = 40f, gapPx = 6f, limitPx = 1000f
            )
        )
    }

    @Test
    fun twoRowsIncludeOneGap() {
        // 10 集 = 2 行；2×40 + 1×6 = 86
        assertEquals(
            86,
            EpisodePanelBinder.gridHeightPx(
                itemCount = 10, columns = 5, itemHeightPx = 40f, gapPx = 6f, limitPx = 1000f
            )
        )
    }

    @Test
    fun partialLastRowStillCountsAsRow() {
        // 7 集 = 2 行（第 2 行只有 2 格）；2×40 + 6 = 86
        assertEquals(
            86,
            EpisodePanelBinder.gridHeightPx(
                itemCount = 7, columns = 5, itemHeightPx = 40f, gapPx = 6f, limitPx = 1000f
            )
        )
    }

    @Test
    fun limitCapsContentHeight() {
        // 内容 86 但视口只剩 50 ⇒ 50（弹框不遮挡视频）
        assertEquals(
            50,
            EpisodePanelBinder.gridHeightPx(
                itemCount = 10, columns = 5, itemHeightPx = 40f, gapPx = 6f, limitPx = 50f
            )
        )
    }

    @Test
    fun zeroItemsStillReservesOneRow() {
        assertEquals(
            40,
            EpisodePanelBinder.gridHeightPx(
                itemCount = 0, columns = 5, itemHeightPx = 40f, gapPx = 6f, limitPx = 1000f
            )
        )
    }
}
