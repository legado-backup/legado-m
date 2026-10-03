package io.legado.app.ui.rss.article

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 订阅列表翻页「是否还有下一页」纯函数的回归测试（2026-10-01 缺陷①）。
 *
 * 背景：`RssArticlesViewModel.loadMoreSuccess()` 的「追加成功」出口此前**不发完成信号** ⇒ 宿主在途闸
 * `isLoadingState` 永为 `true` ⇒ 后续翻页全被拦 + 页脚永久转圈（用户报障「最多只能翻两页」）。
 * 本测试把三态判定钉死为纯函数口径，锁住「追加成功必须判为仍有下一页」这一关键分支。
 */
class RssLoadMoreOutcomeTest {

    @Test
    fun emptyPageMeansNoMore() {
        // 空结果（源已到底 / 该页无数据）⇒ 判定到底（与「我是有底线的」语义一致）
        assertFalse(RssLoadMoreOutcome.hasMore(articlesEmpty = true, firstItemInDb = false, lastItemInDb = false))
    }

    @Test
    fun duplicatedPageMeansNoMore() {
        // 首末条均已入库 ⇒ 重复页（源忽略分页参数）⇒ 判定到底，避免对同一 URL 无限重复请求
        assertFalse(RssLoadMoreOutcome.hasMore(articlesEmpty = false, firstItemInDb = true, lastItemInDb = true))
    }

    @Test
    fun brandNewPageMeansHasMore() {
        // 🔴 缺陷①核心分支：真实新页（首末条均未入库）⇒ 必须判为仍有下一页
        // （若此处返回 false，宿主会立刻显示底线文案并停止翻页 = 用户报障「翻两页就停」）
        assertTrue(RssLoadMoreOutcome.hasMore(articlesEmpty = false, firstItemInDb = false, lastItemInDb = false))
    }

    @Test
    fun partiallyKnownPageStillHasMore() {
        // 只有一端在库（例如首条与上一页末条重叠）⇒ 仍有新增条目 ⇒ 必须继续翻页
        assertTrue(RssLoadMoreOutcome.hasMore(articlesEmpty = false, firstItemInDb = true, lastItemInDb = false))
        assertTrue(RssLoadMoreOutcome.hasMore(articlesEmpty = false, firstItemInDb = false, lastItemInDb = true))
    }

    @Test
    fun emptyPageWinsOverDbFlags() {
        // 空结果优先：即便查库标记为 false 且无任何条目，也必须是「到底」（不得因无条目而误判有下一页）
        assertFalse(RssLoadMoreOutcome.hasMore(articlesEmpty = true, firstItemInDb = true, lastItemInDb = true))
    }
}