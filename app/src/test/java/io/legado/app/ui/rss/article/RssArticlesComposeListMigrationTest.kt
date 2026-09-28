package io.legado.app.ui.rss.article

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CF 6.2 配对测试：**RSS 文章五样式族**（`item_rss_article` ~ `item_rss_article_4` + `layout-land` 变体）
 * 换装 Compose。
 *
 * 换装前：宿主 `RssArticlesFragment` 挂 `RecyclerViewAtPager2`，按 `articleStyle` 选 6 个 Adapter
 * （`RssArticlesAdapter` + `_1`~`_5`），各自 inflate 一个 `item_*` 布局。
 * 换装后：样式 **0~4 → Compose 列表**（`RssArticlesComposeList`），样式 **5（自由布局冻结区）→ 原 View 路径**。
 *
 * 本测试锁三件事：①退役件确实消失（防回退）②**禁止半迁移双源**（每样式一条路径）
 * ③宿主既有行为（触底翻页 / 位置记忆 / 页码跳转 / 顶部占位 / 下拉刷新判据）不被换装带掉。
 */
class RssArticlesComposeListMigrationTest {

    private fun fragment(): String = SourceFileProbe.sourceText("ui/rss/article/RssArticlesFragment.kt")

    private fun layout(name: String): File = File(SourceFileProbe.layoutDir(), name)

    private fun landLayout(name: String): File =
        File(SourceFileProbe.layoutDir().parentFile, "layout-land/$name")

    @Test
    fun retiredArtifactsAreGone() {
        listOf(
            "item_rss_article.xml",
            "item_rss_article_1.xml",
            "item_rss_article_2.xml",
            "item_rss_article_3.xml",
            "item_rss_article_4.xml",
        ).forEach { xml ->
            assertFalse("$xml 应已随宿主 Adapter 退役（CF 6.2）", layout(xml).isFile)
        }
        assertFalse(
            "layout-land/item_rss_article_3.xml 应已退役（横屏变体随样式 3 折叠进同一实现）",
            landLayout("item_rss_article_3.xml").isFile
        )
        listOf(
            "ui/rss/article/RssArticlesAdapter.kt",
            "ui/rss/article/RssArticlesAdapter1.kt",
            "ui/rss/article/RssArticlesAdapter2.kt",
            "ui/rss/article/RssArticlesAdapter3.kt",
            "ui/rss/article/RssArticlesAdapter4.kt",
        ).forEach { rel ->
            assertFalse(
                "$rel 应已删除（宿主换装 Compose 后无实例化点）",
                File(SourceFileProbe.mainJavaRoot(), "io/legado/app/$rel").isFile
            )
        }
    }

    @Test
    fun style5FreeLayoutStaysOnViewPath() {
        // 自由布局（articleStyle=5）是尺寸算法冻结区 ⇒ 必须保留原 View 路径与其全部分支
        assertTrue(
            "样式 5 必须保留原 View 路径（冻结区不可迁移）",
            layout("item_rss_article_free.xml").isFile
        )
        val s = fragment()
        listOf(
            "RssFreeGridLayoutManager(",
            "RssArticlesAdapter5(",
            "FreeGridSizeCalculator.DEFAULT_RATIO",
            "RssImageRatioStore.peek(",
            "adapter.addFooterView {",
        ).forEach { marker ->
            assertTrue("样式 5 链路不得缺失：`$marker`", s.contains(marker))
        }
    }

    @Test
    fun styles0to4UseComposeSinglePath() {
        val s = fragment()
        assertTrue(
            "样式 0~4 必须整段走 Compose 列表（非逐样式半迁移）",
            s.contains("private val useComposeList") && s.contains("articleStyle != 5")
        )
        assertTrue("必须经共享装配入口挂进 refreshLayout", s.contains("installComposeList {"))
        assertTrue("必须渲染 Compose 列表", s.contains("RssArticlesComposeList("))
        assertTrue(
            "列表滚动状态必须由宿主持有（位置记忆/页码跳转要命令式驱动）",
            s.contains("RssArticleListStateHolder(articleStyle)")
        )
        // 换装后不得再出现已退役 Adapter 的任何引用
        listOf(
            "RssArticlesAdapter(",
            "RssArticlesAdapter1(",
            "RssArticlesAdapter2(",
            "RssArticlesAdapter3(",
            "RssArticlesAdapter4(",
            "ItemRssArticle",
            "VerticalDivider(",
        ).forEach { gone ->
            assertFalse("换装后不得残留旧列表实现：`$gone`", s.contains(gone))
        }
        // 注意：`RssFreeGridLayoutManager(` 以 `GridLayoutManager(` 结尾 ⇒ 必须用词边界匹配，
        // 否则「样式 5 保留」与「旧网格管理器已移除」两条断言会互相打架
        assertFalse(
            "换装后不得再手建 GridLayoutManager（样式 2/4 已走 LazyVerticalGrid）",
            Regex("(?<![A-Za-z0-9_])GridLayoutManager\\(").containsMatchIn(s)
        )
        assertFalse(
            "换装后不得再手建 StaggeredGridLayoutManager（样式 3 已走 LazyVerticalStaggeredGrid）",
            Regex("(?<![A-Za-z0-9_])StaggeredGridLayoutManager\\(").containsMatchIn(s)
        )
    }

    @Test
    fun hostBehaviorsPreserved() {
        val s = fragment()
        listOf(
            // 下拉刷新判据（Compose 列表不滚动 ⇒ 必须显式喂回 canScrollBackward）
            "setOnChildScrollUpCallback { _, _ -> composeCanScrollBackward }",
            // 触底翻页三态 + 页脚重试
            "private fun scrollToBottom(",
            "loadMoreView.error(",
            "loadMoreView.noMore()",
            // AD-02：页脚在途闸单源 —— 任何出口都先无条件收敛转圈（修复「一直下一页转圈」）
            "loadMoreView.stopLoad()",
            // 位置记忆（播放器/图片页返回）
            "VideoPlay.lastPlayedArticleLink",
            "ImagePlay.lastPlayedArticleLink",
            "listStateHolder.scrollToItem(position)",
            // 页码跳转后回顶
            "private fun scrollToTop()",
            // 旋转/进程重建后的位置恢复（宿主持有 LazyListState ⇒ 必须自行保存；View 侧 RecyclerView 是自动的）
            "override fun onSaveInstanceState(",
            "STATE_SCROLL_INDEX",
            "private fun consumePendingScroll()",
            // modern-rss 顶部覆盖占位 + 主壳底栏留白
            "topOverlaySpaceState.intValue = topOverlaySpace",
            "mainBottomBarContentPadding()",
            // 分页上下文传给播放器
            "nextPageUrl = viewModel.nextPageUrl",
        ).forEach { marker ->
            assertTrue("换装不得带掉既有行为：缺少 `$marker`", s.contains(marker))
        }
    }

    @Test
    fun favoritesHostSharesSameRowSingleSource() {
        val favorites = SourceFileProbe.sourceText("ui/rss/favorites/RssFavoritesFragment.kt")
        assertTrue("收藏页也必须走 Compose 列表装配", favorites.contains("installComposeList {"))
        assertTrue("收藏页必须复用同一装配入口", favorites.contains("RssStarComposeList("))
        assertFalse(
            "收藏页不得再引用已退役 Adapter",
            favorites.contains("RssFavoritesAdapter")
        )
    }

    /**
     * AD-02 回归（2026-09-28 用户报障「一直下一页在转圈」）：在途闸必须**单源**。
     *
     * 修复前：页脚转圈由 `loadMoreView.hasMore()` 置位，却只在 `!hasMore` 时被 `noMore()` 收敛
     * ⇒ 翻页成功但仍有下一页时页脚永远转圈；且在途判定存在双源（`viewModel.isLoading` 与 `isLoadingState`），
     * 两者可能漂移。修复后唯一判据 = `isLoadingState`，且每个出口都无条件 `stopLoad()`。
     */
    @Test
    fun inFlightGateIsSingleSourced() {
        val code = codeOnly(fragment())
        assertFalse(
            "UI 层不得再读 viewModel.isLoading（在途闸单源 = isLoadingState）",
            code.contains("viewModel.isLoading")
        )
        assertTrue("触底守卫必须读 isLoadingState", code.contains("if (isLoadingState.value) return"))
        assertTrue("页脚必须在任何出口无条件收敛转圈", code.contains("loadMoreView.stopLoad()"))
    }

    /**
     * 取「非注释」代码文本：断言「旧写法已删」时必须先剔除注释行，否则注释里的示例会误报命中
     * （本仓既有教训：断言"旧写法已删"要先剔除注释行）。
     */
    private fun codeOnly(text: String): String =
        text.lineSequence()
            .filterNot {
                val t = it.trimStart()
                t.startsWith("//") || t.startsWith("*") || t.startsWith("/*")
            }
            .joinToString("\n")
}