package io.legado.app.ui.rss.favorites

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：订阅收藏页（`activity_rss_favorites`）换装的 **CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：原 XML 为 `LinearLayout { compose_top_bar ; tab_layout ; FrameLayout(weight 1){ view_pager ; empty_overlay } }`。
 * CE-b 把骨架交给 Compose：`TabLayout`/`ViewPager` 以 `AndroidView` 原样托管；
 * **原 `empty_overlay` 这个宿主 `setContent` 的 ComposeView 槽改为「状态驱动页内渲染」** ⇒ 不再需要 composeSlot 例外。
 */
class RssFavoritesShellMigrationTest {

    private val page = "ui/rss/favorites/RssFavoritesActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertTrue("骨架必须收敛为单个 initComposeContent", s.contains("private fun initComposeContent("))
        assertFalse("换装后不得再引用已退役布局/委托", s.contains("ActivityRssFavoritesBinding") || s.contains("viewBinding("))
    }

    @Test
    fun xmlIsRetired() {
        assertFalse(
            "activity_rss_favorites.xml 应已退役（CE-b）",
            File(SourceFileProbe.layoutDir(), "activity_rss_favorites.xml").exists()
        )
    }

    @Test
    fun viewKernelsAndEmptyStateAreHostedInPage() {
        val s = src()
        assertTrue("TabLayout 必须以 AndroidView 托管", s.contains("factory = { tabLayout }"))
        assertTrue("ViewPager 必须以 AndroidView 托管", s.contains("factory = { viewPager }"))
        assertTrue(
            "两者必须是 Activity 字段（by lazy）——onActivityCreated 就要 setupWithViewPager",
            Regex("""private val tabLayout\s*:\s*TabLayout\s+by lazy""").containsMatchIn(s) &&
                Regex("""private val viewPager\s*:\s*ViewPager\s+by lazy""").containsMatchIn(s)
        )
        // 空态槽改状态驱动页内渲染（不再有 binding.emptyOverlay / initEmptyState）
        assertTrue("空态必须状态驱动页内渲染", s.contains("if (composeGroups.isEmpty())"))
        assertTrue("空态占位必须仍在", s.contains("EmptyStatePlaceholder("))
        assertTrue(
            "Column 内 lambda 的 this 被 ColumnScope 遮蔽 ⇒ 必须显式限定 Activity",
            s.contains("MainActivity.openRss(this@RssFavoritesActivity)")
        )
        assertFalse(
            "不得再引用 XML 时代节点",
            s.contains("binding.emptyOverlay") || s.contains("binding.tabLayout") || s.contains("binding.viewPager")
        )
        assertFalse("原 initEmptyState 必须已并入页内渲染", s.contains("private fun initEmptyState("))
        // 程序化 ViewPager 必须显式赋 id：FragmentStatePagerAdapter.startUpdate 要求 container 有 view id
        assertTrue("ViewPager 必须显式赋 R.id.view_pager", s.contains("id = R.id.view_pager"))
    }

    @Test
    fun sharedArticleListShellIsSingleSource() {
        // CE-b：fragment_rss_articles 由两个 Fragment 共用（本页列表 Fragment + 文章列表 Fragment）
        // ⇒ 装配下沉到共享基类单源，本页只继承，不再持有任何 ViewBinding
        val frag = SourceFileProbe.sourceText("ui/rss/favorites/RssFavoritesFragment.kt")
        assertTrue(
            "收藏列表 Fragment 必须继承共享基类",
            frag.contains(": RssArticlesShellFragment<RssFavoritesViewModel>()")
        )
        assertFalse("不得再走 viewBinding 委托", frag.contains("viewBinding("))
        assertFalse("不得再引用已退役布局", frag.contains("FragmentRssArticlesBinding"))
        assertFalse("不得再直接引用 XML 时代节点", frag.contains("binding.recyclerView") || frag.contains("binding.refreshLayout"))
        assertTrue("必须继续装配 recycler（layoutManager/adapter）与 refreshLayout", frag.contains("recyclerView.adapter = adapter"))
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "override fun onResume(",
            "private fun initView(",
            "private fun upFragments(",
            "private fun buildGroupMenuActions(",
            "private fun buildMenuActions(",
            "private sealed interface PendingDelete",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
        // F145 单分组标题承载 / 单分组时 TabLayout 以 View 语义 gone-visible
        listOf(
            "composeGroups.size == 1",
            "tabLayout.setupWithViewPager(viewPager)",
            "tabLayout.gone()",
            "tabLayout.visible()",
        ).forEach { marker ->
            assertTrue("分组上下文语义不得缺失：`$marker`", s.contains(marker))
        }
    }
}