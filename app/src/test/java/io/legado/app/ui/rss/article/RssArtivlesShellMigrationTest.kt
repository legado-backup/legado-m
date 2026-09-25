package io.legado.app.ui.rss.article

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：RSS 分类页（`activity_rss_artivles`）换装的 **CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：原 XML 为 `LinearLayout { compose_top_bar ; tabs_container(8dp) ; view_pager }`。CE-b 把骨架交给 Compose，
 * `tabs_container`（宿主以 View 语义反复 addView/removeView）与 `view_pager` 以 `AndroidView` 原样托管。
 */
class RssArtivlesShellMigrationTest {

    private val page = "ui/rss/article/RssSortActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止自行设置 ViewCompositionStrategy", s.contains("ViewCompositionStrategy"))
        assertTrue("骨架必须收敛为单个 initComposeContent", s.contains("private fun initComposeContent("))
        assertFalse("换装后不得再引用已退役布局/委托", s.contains("ActivityRssArtivlesBinding") || s.contains("viewBinding("))
    }

    @Test
    fun xmlIsRetired() {
        assertFalse(
            "activity_rss_artivles.xml 应已退役（CE-b）",
            File(SourceFileProbe.layoutDir(), "activity_rss_artivles.xml").exists()
        )
    }

    @Test
    fun viewKernelsAreHostedViaAndroidView() {
        val s = src()
        assertTrue("分类标签行必须以 AndroidView 托管", s.contains("factory = { tabsContainer }"))
        assertTrue("分页容器必须以 AndroidView 托管", s.contains("factory = { viewPager }"))
        assertTrue(
            "两者必须是 Activity 字段（by lazy）——onActivityCreated 就要装配",
            Regex("""private val tabsContainer\s*:\s*LinearLayout\s+by lazy""").containsMatchIn(s) &&
                Regex("""private val viewPager\s*:\s*ViewPager\s+by lazy""").containsMatchIn(s)
        )
        assertFalse("不得再引用 XML 时代节点", s.contains("binding.tabsContainer") || s.contains("binding.viewPager"))
        // 程序化 ViewPager 必须显式赋 id：FragmentStatePagerAdapter.startUpdate 要求 container 有 view id
        assertTrue("ViewPager 必须显式赋 R.id.view_pager", s.contains("id = R.id.view_pager"))
    }

    @Test
    fun sharedArticleListShellIsSingleSource() {
        // CE-b：fragment_rss_articles 由两个 Fragment 共用 ⇒ 装配下沉共享基类单源
        val base = SourceFileProbe.sourceText("ui/rss/article/RssArticlesShellFragment.kt")
        val frag = SourceFileProbe.sourceText("ui/rss/article/RssArticlesFragment.kt")
        assertTrue("基类必须是 VMBaseFragment<VM>(0)（无 XML）", base.contains("VMBaseFragment<VM>(0)"))
        assertTrue("基类必须 override onCreateView 提供合成壳", base.contains("override fun onCreateView("))
        assertTrue("基类必须走 attachComposeContent 单源挂载", base.contains("root.attachComposeContent {"))
        assertTrue("SwipeRefreshLayout 必须以 AndroidView 托管", base.contains("factory = { refreshLayout }"))
        assertTrue("两个 View 必须显式赋 id", base.contains("id = R.id.refresh_layout") && base.contains("id = R.id.recycler_view"))
        assertTrue("recycler 必须复刻 clipToPadding=false", base.contains("clipToPadding = false"))
        assertTrue("宿主必须继承共享基类", frag.contains(": RssArticlesShellFragment<RssArticlesViewModel>()"))
        assertFalse("宿主不得再走 viewBinding 委托", frag.contains("viewBinding("))
        assertFalse("宿主不得再引用已退役布局", frag.contains("FragmentRssArticlesBinding"))
        assertFalse(
            "fragment_rss_articles.xml 应已退役（CE-b）",
            File(SourceFileProbe.layoutDir(), "fragment_rss_articles.xml").exists()
        )
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "private fun setupMultiLineTabs(",
            "override fun onActivityCreated(",
            "override fun onSaveInstanceState(",
            "private fun initComposeContent(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
        // F143 徽标 / F201 页码 chip / F210 收起展开 三条优化语义不得被换装带掉
        listOf(
            "appliedBadgeCounts",
            "pageMenuTitle",
            "tabsExpanded",
            "updateTabSelection(",
        ).forEach { marker ->
            assertTrue("标签语义不得缺失：`$marker`", s.contains(marker))
        }
    }
}