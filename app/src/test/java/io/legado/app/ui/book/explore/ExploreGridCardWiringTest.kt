package io.legado.app.ui.book.explore

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * explore-grid-card-layout：网格卡「图在上、文字在下」结构 + 无 ⋮ + 长按预览的接线锁定。
 *
 * 行为口径由 [ExploreShowLayout] 的纯函数承载并在此用期望值断言；源码结构断言
 * 只用于确保「三种网格真的换成了新卡片、⋮ 通道真的摘掉了」这两件用户可见的事。
 */
class ExploreGridCardWiringTest {

    private val card = SourceFileProbe.sourceText("ui/book/explore/ExploreShowGridCard.kt")
    private val gridScreen = SourceFileProbe.sourceText("ui/book/explore/ExploreShowGridScreen.kt")
    private val composeScreen = SourceFileProbe.sourceText("ui/book/explore/ExploreShowComposeScreen.kt")

    @Test
    fun cardIsVerticalColumnWithFullWidthCover() {
        // 上下结构：Column 主轴；封面占满列宽（不是行卡片的固定 coverWidth）
        assertTrue(card.contains("Column("))
        assertTrue(card.contains("Modifier.fillMaxWidth()"))
        assertFalse(card.contains("coverWidth"))
        assertTrue(card.contains("ExploreShowLayout.GRID_COVER_ASPECT_RATIO"))
        assertEquals(0.75f, ExploreShowLayout.GRID_COVER_ASPECT_RATIO, 0.0f)
    }

    @Test
    fun cardHasNoOverflowMoreButton() {
        // 用户要求：三种网格「去掉三个竖点」⇒ 卡片内不得出现 ⋮ 图标或 onMore 通道
        assertFalse(card.contains("MoreVert"))
        assertFalse(card.contains("onMore"))
        assertEquals(false, ExploreShowLayout.gridShowsMore(ExploreShowLayout.WATERFALL))
        assertEquals(false, ExploreShowLayout.gridShowsMore(ExploreShowLayout.DUAL))
        assertEquals(false, ExploreShowLayout.gridShowsMore(ExploreShowLayout.TRIPLE))
    }

    @Test
    fun cardWiresLongPressPreviewWithHaptic() {
        // 长按=预览：⋮ 移除后这是「先看后决定」的唯一入口，必须带触觉确认
        assertTrue(card.contains("combinedClickable"))
        assertTrue(card.contains("performHapticFeedback"))
        assertTrue(card.contains("onPreview(coverBounds.value)"))
        assertEquals(2, ExploreShowLayout.GRID_TITLE_MAX_LINES)
    }

    @Test
    fun gridScreenSwitchedToNewCardAndDroppedMoreChannel() {
        assertTrue(gridScreen.contains("ExploreShowGridCard("))
        assertFalse(gridScreen.contains("SearchBookListItem("))
        assertFalse(gridScreen.contains("onBookMore"))
        assertTrue(gridScreen.contains("ExploreShowLayout.gridIntroMaxLines("))
        assertEquals(Int.MAX_VALUE, ExploreShowLayout.gridIntroMaxLines(ExploreShowLayout.WATERFALL))
        assertEquals(0, ExploreShowLayout.gridIntroMaxLines(ExploreShowLayout.DUAL))
    }

    @Test
    fun waterfallIntroIsNotClampedToFixedLineCount() {
        // 用户实测反馈：瀑布必须完整展示简介才能形成错落（与订阅源同构），不得固定 2 行截断
        assertTrue(card.contains("maxLines = introMaxLines"))
        assertFalse(card.contains("maxLines = 2"))
    }

    @Test
    fun listBranchStillKeepsRowCardWithMoreEntry() {
        // 列表布局零回归：仍走行卡片且保留 ⋮（onMore 实参仍在）
        assertTrue(composeScreen.contains("SearchBookListItem("))
        assertTrue(composeScreen.contains("onMore = { onBookMore(book) }"))
        // 网格分支不再向网格屏传 ⋮ 通道
        assertFalse(composeScreen.contains("onBookMore = onBookMore,"))
    }
}
