package io.legado.app.ui.rss.favorites.compose

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CF 6.2 配对测试：订阅收藏列表的 **Compose 侧契约**（`item_rss_article` 的第二个宿主）。
 *
 * 收藏页与文章列表**共用** `item_rss_article`（样式 0 行）⇒ 本页换装的等价性风险集中在三点：
 * ①行实现必须复用 `RssArticleListRow` 单源（不得另写一份「100dp 定高 + 110×68 缩略图」行）；
 * ②封面取数必须走收藏表 `rssStarDao`（文章列表走 `rssArticleDao`，两表分离）；
 * ③原 `setOnLongClickListener` 的**长按删除**语义不得丢。
 */
class RssFavoritesComposeListTest {

    private fun src(): String =
        SourceFileProbe.sourceText("ui/rss/favorites/compose/RssFavoritesComposeList.kt")

    @Test
    fun reusesArticleRowSingleSource() {
        val s = src()
        assertTrue("必须复用文章列表样式 0 行单源", s.contains("RssArticleListRow("))
        assertTrue("必须取数通道单源（类型别名）", s.contains("RssArticleImageQuery"))
    }

    @Test
    fun starCoverUsesStarDao() {
        assertTrue(
            "收藏封面必须走收藏表单行查（与文章表的 base64 大图口径同源）",
            src().contains("appDb.rssStarDao.getImage(origin, link)")
        )
    }

    @Test
    fun longPressDeletesStarAndClickReads() {
        val s = src()
        assertTrue("长按必须回调删除", s.contains("onLongClick = { onItemLongClick(star) }"))
        assertTrue("单击必须回调打开", s.contains("onClick = { onItemClick(star) }"))
        assertTrue("收藏行无已读态（原 Adapter 也未做已读着色）", s.contains("read = false"))
    }

    @Test
    fun listIsComposeAndAdapterRetired() {
        val s = src()
        assertTrue("必须是 LazyColumn 容器", s.contains("LazyColumn("))
        assertTrue("行间分隔线由 HorizontalDivider 承担", s.contains("HorizontalDivider("))
        assertTrue("底色必须走资源单源", s.contains("colorResource(R.color.bg_divider_line)"))
        assertFalse("不得残留 View 列表", Regex("(?<![A-Za-z0-9_])RecyclerView").containsMatchIn(s))
        assertFalse("不得残留 DividerItemDecoration 路径", s.contains("VerticalDivider"))
        assertFalse(
            "原 RssFavoritesAdapter 应已退役",
            File(
                SourceFileProbe.mainJavaRoot(),
                "io/legado/app/ui/rss/favorites/RssFavoritesAdapter.kt"
            ).isFile
        )
    }
}