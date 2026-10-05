package io.legado.app.ui.rss.article.compose

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * add-rss-article-refresh-to-top 配对测试（Compose 列表侧）。
 *
 * 锁「宿主强制回顶」在本组件的消费契约：
 * ①以参数 `scrollTopRequest` 接收宿主请求（**不改**条目 key 与 `LazyListState` 持有方式）；
 * ②经 `LaunchedEffect` 在**本次组合（已含新数据）应用后**执行 `scrollToItem(0)` ——
 *   若在数据写入同帧直接滚动，LazyList 会先以**旧数据**消费该滚动并记录旧首条 key，
 *   新数据到达时按 key 把旧首条锚回视口顶 ⇒ 回顶被静默吞掉
 *   （2026-10-05 模拟器 L2 实证：修复前「开关开启但刷新后首条仍是旧条目」）。
 */
class RssArticlesComposeListScrollTopRequestTest {

    private fun list(): String =
        SourceFileProbe.sourceText("ui/rss/article/compose/RssArticlesComposeList.kt")

    @Test
    fun declaresScrollTopRequestParam() {
        assertTrue(
            "必须声明 scrollTopRequest 入参（宿主递增强制回顶请求）",
            list().contains("scrollTopRequest: Int,")
        )
    }

    @Test
    fun consumesRequestInEffectAfterComposition() {
        val s = list()
        assertTrue(
            "必须经 LaunchedEffect 消费请求（晚于本次组合应用，避免被旧数据先消费）",
            s.contains("LaunchedEffect(scrollTopRequest)")
        )
        assertTrue(
            "消费体必须命令式滚到下标 0",
            s.contains("stateHolder.scrollToItem(0)")
        )
    }

    @Test
    fun keyAndStateOwnershipUnchanged() {
        val s = list()
        assertTrue("条目稳定 key 必须保持单源（回顶不得靠换 key 实现）", s.contains("RssArticleKey::of"))
        assertTrue(
            "列表滚动状态仍由宿主注入持有",
            s.contains("stateHolder: RssArticleListStateHolder")
        )
        assertFalse(
            "不得用序号当 key（会整条重建并重取封面）",
            s.contains("key = { index, _ -> index.toString() }")
        )
    }
}
