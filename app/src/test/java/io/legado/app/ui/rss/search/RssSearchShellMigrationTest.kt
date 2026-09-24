package io.legado.app.ui.rss.search

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE 5.2 首个页面（`activity_rss_search`）**换装的 CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：本页原为「XML 壳（ConstraintLayout）+ 5 个 View 机制」：
 *   `compose_top_bar` / `refresh_progress_bar`(自绘动画条) / `content_view`(DynamicFrameLayout) + `compose_results`
 *   / `ll_input_help`(挡点击覆盖层) + `compose_input_help` / `fb_start_stop`(mini FAB)。
 * CE 5.2 把页面改为 `composeShell` + `attachComposeContent` 单源承载，其中**无 Compose 等价物的两个 View**
 * （`RefreshProgressBar` 自绘动画、`FloatingActionButton` mini 态）以 `AndroidView` **原样托管**。
 *
 * 本测试锁死五类事实，防回归（只写文档的约束一律失效）：
 *   ①单源装配（composeShell + attachComposeContent），且**不再手写 ComposeView / viewBinding / 引用 R.layout**
 *   ②XML 已退役（`activity_rss_search.xml` 不存在）
 *   ③两个无等价物的 View 仍**以 AndroidView 原样托管**（不是被换成「看起来差不多」的 Compose 组件）
 *   ④三个 View 机制改由**状态**驱动（progressLoading / stopFabVisible / inputHelpVisible）
 *   ⑤宿主业务逻辑**未消失**（逐项断言方法名）
 *   ⑥顶栏仍走**页内直接渲染** `GlassTopAppBar`（本页历史上就不经 `installGlassTopBar`，如实锁定）
 */
class RssSearchShellMigrationTest {

    private val page = "ui/rss/search/RssSearchActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertFalse("禁止自行设置 ViewCompositionStrategy", s.contains("ViewCompositionStrategy"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityRssSearchBinding"))
    }

    @Test
    fun xmlIsRetired() {
        val f = File(SourceFileProbe.layoutDir(), "activity_rss_search.xml")
        assertFalse("activity_rss_search.xml 应已退役（CE 5.2）", f.exists())
    }

    @Test
    fun viewKernelsAreHostedViaAndroidView() {
        val s = src()
        assertTrue(
            "RefreshProgressBar（自绘动画条、无 Compose 等价物）必须以 AndroidView 原样托管",
            s.contains("AndroidView(") && s.contains("RefreshProgressBar(ctx)")
        )
        assertTrue(
            "停止 FAB 必须以 AndroidView 托管 FloatingActionButton（mini 态无像素等价 Compose 组件）",
            s.contains("createStopFab(") && s.contains("FloatingActionButton(context)") &&
                s.contains("FloatingActionButton.SIZE_MINI")
        )
        assertTrue(
            "FAB 底边距必须含导航栏 inset（对齐原 applyNavigationBarMargin(true)）",
            s.contains("navigationBarsPadding()")
        )
    }

    @Test
    fun viewMechanismsAreStateDriven() {
        val s = src()
        listOf("progressLoading", "stopFabVisible", "inputHelpVisible").forEach { state ->
            assertTrue("原 View 机制必须改由状态驱动：缺少 `$state`", s.contains("private var $state by mutableStateOf"))
        }
        assertFalse("不得再调用旧的 visible()/gone()/invisible() 扩展", s.contains(".invisible()") || s.contains(".gone()"))
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "private fun buildMenuActions(",
            "private fun handleMenuAction(",
            "private fun updateSearchType(",
            "private fun handleGroupSelect(",
            "private fun reSearchIfNeeded(",
            "private fun submitSearch(",
            "private fun stopSearch(",
            "private fun initData(",
            "private fun receiptIntent(",
            "private fun visibleInputHelp(",
            "private fun upHistory(",
            "private fun startSearch(",
            "private fun searchFinally(",
            "override fun observeLiveBus(",
            "private fun showArticleInfo(",
            "private fun searchHistory(",
            "private fun deleteHistory(",
            "private fun alertClearHistory(",
            "RssSearchTypeChipsRow(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
    }

    @Test
    fun topBarRendersInPageNotViaAnchorInstaller() {
        val s = src()
        assertTrue("顶栏必须页内直接渲染 GlassTopAppBar", s.contains("GlassTopAppBar("))
        // 本页历史上从不经 installGlassTopBar（无 title_bar 锚点）⇒ 如实锁定该事实，防未来被误改
        assertFalse("本页不应引入 installGlassTopBar（无顶栏锚点）", s.contains("installGlassTopBar("))
    }

    @Test
    fun behaviorInvariantsKept() {
        val s = src()
        // B1 相邻修复口径：输入变化必须停搜索 + 隐藏 FAB + 清空态标记（原注释逐字语义）
        assertTrue("输入变化必须停止当前搜索", s.contains("viewModel.stop()"))
        assertTrue("输入变化必须清空已搜索标记", s.contains("hasSearched = false"))
        // 结果标题/摘要按关键词高亮（修复 4）
        assertTrue("结果高亮口径必须保留", s.contains("highlightQuery = composeSearchQuery.trim()"))
        // 输入帮助覆盖层必须保留「挡点击」语义（原 ll_input_help 的 clickable）
        assertTrue("覆盖层须保留挡点击语义", s.contains("indication = null"))
    }
}