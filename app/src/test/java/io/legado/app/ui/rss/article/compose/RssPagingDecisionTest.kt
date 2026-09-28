package io.legado.app.ui.rss.article.compose

import io.legado.app.data.entities.RssArticle
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 订阅列表「翻页时机」单源纯函数的回归测试。
 *
 * 背景（2026-09-28 用户报障）：订阅源文章列表在**非自由布局**的四个样式下快速下滑明显卡顿、
 * 页脚「一直下一页转圈」。根因之一是 Compose 列表的翻页提前量恒为 `0`
 * （`threshold = if (style == 3 && isPreload) 5 else 0`）⇒ 必须滑到**真正的最后一条**才发请求，
 * 触底后必然出现「网络 RTT + 落库 + Flow 回流 + 重组」的空窗。
 *
 * 本测试把「翻页时机」钉死为纯函数口径，锁三件事：
 * ① 提前量**永不为 0**（任何样式 × 预加载组合）；② 判定六要素的全部边界（空表 / `hasMore=false` /
 * 在途 / 无可见项 / 越界样式 / 末项前一条）；③ 稳定 key 必须等价于实体主键（`origin+link+sort`）。
 */
class RssPagingDecisionTest {

    @Test
    fun thresholdNeverZero() {
        // 覆盖在用五样式 + 越界取值 × 预加载两种取值：任何组合都不得返回 0
        (-1..6).forEach { style ->
            listOf(false, true).forEach { preload ->
                val threshold = RssPagingThresholdResolver.resolve(style, preload)
                assertTrue(
                    "style=$style preload=$preload 的提前量不得为 0（0 ⇒ 必须滑到底才请求）",
                    threshold >= 1
                )
            }
        }
    }

    @Test
    fun waterfallPreloadUsesFiveOthersUseOne() {
        // 与原实现唯二的差异点：瀑布流(3) + 预加载源 ⇒ 提前 5 条（沿用旧口径）
        assertEquals(5, RssPagingThresholdResolver.resolve(3, true))
        // 其余一律提前 1 条（对齐自由布局 `itemCount - 2` 的跟手度）
        assertEquals(1, RssPagingThresholdResolver.resolve(3, false))
        listOf(0, 1, 2, 4).forEach { style ->
            assertEquals(1, RssPagingThresholdResolver.resolve(style, true))
            assertEquals(1, RssPagingThresholdResolver.resolve(style, false))
        }
        // 越界样式（导入的来源 JSON 可携带任意 articleStyle）同样落默认阈值，不得崩溃
        listOf(-1, 5, 6, 99).forEach { style ->
            assertEquals(1, RssPagingThresholdResolver.resolve(style, true))
        }
    }

    @Test
    fun emptyListNeverLoadsMore() {
        assertFalse(decision(itemCount = 0, lastVisibleIndex = 0))
        assertFalse(decision(itemCount = 0, lastVisibleIndex = -1))
    }

    @Test
    fun noMoreStopsPaging() {
        assertFalse(decision(itemCount = 20, lastVisibleIndex = 19, hasMore = false))
    }

    @Test
    fun inFlightStopsPaging() {
        // 在途闸：有加载在飞时不得重复触发同一页
        assertFalse(decision(itemCount = 20, lastVisibleIndex = 19, isLoading = true))
    }

    @Test
    fun noVisibleItemNeverLoadsMore() {
        assertFalse(decision(itemCount = 20, lastVisibleIndex = -1))
    }

    @Test
    fun thresholdOneTriggersBeforeLastItemVisible() {
        // 核心修复点：20 条、阈值 1 ⇒ 末项**前一条**可见即应触发
        assertTrue(decision(itemCount = 20, lastVisibleIndex = 18, threshold = 1))
        assertFalse(decision(itemCount = 20, lastVisibleIndex = 17, threshold = 1))
    }

    @Test
    fun zeroThresholdRegressionWouldRequireLastItemVisible() {
        // 反向锁定被替换掉的旧口径：阈值 0 时「倒数第二条可见」不触发 ⇒ 必须滑到最后一条
        assertFalse(decision(itemCount = 20, lastVisibleIndex = 18, threshold = 0))
        assertTrue(decision(itemCount = 20, lastVisibleIndex = 19, threshold = 0))
    }

    @Test
    fun waterfallPreloadThresholdFive() {
        assertTrue(decision(itemCount = 20, lastVisibleIndex = 14, threshold = 5))
        assertFalse(decision(itemCount = 20, lastVisibleIndex = 13, threshold = 5))
    }

    @Test
    fun singleItemListTriggersAtThresholdOne() {
        // 首页条目少于半屏（原 View 路径的死角）：只有 1 条时也必须能触发翻页
        assertTrue(decision(itemCount = 1, lastVisibleIndex = 0, threshold = 1))
    }

    @Test
    fun articleKeyMatchesEntityPrimaryKey() {
        val a = RssArticle(origin = "o", link = "l", sort = "s")
        assertEquals("o|l|s", RssArticleKey.of(a))
        // 主键相同 ⇒ key 必须相同（同一条目的 title/read 变化不得换 key，否则列表项被整条重建）
        val sameKey = RssArticle(origin = "o", link = "l", sort = "s", title = "changed", read = true)
        assertEquals(RssArticleKey.of(a), RssArticleKey.of(sameKey))
        // 主键任一维变化 ⇒ key 必须不同
        assertNotEquals(RssArticleKey.of(a), RssArticleKey.of(a.copy(sort = "s2")))
        assertNotEquals(RssArticleKey.of(a), RssArticleKey.of(a.copy(origin = "o2")))
        assertNotEquals(RssArticleKey.of(a), RssArticleKey.of(a.copy(link = "l2")))
    }

    private fun decision(
        itemCount: Int,
        lastVisibleIndex: Int,
        hasMore: Boolean = true,
        isLoading: Boolean = false,
        threshold: Int = 1
    ): Boolean = RssPagingDecision.shouldLoadMore(
        itemCount = itemCount,
        hasMore = hasMore,
        isLoading = isLoading,
        lastVisibleIndex = lastVisibleIndex,
        threshold = threshold
    )
}