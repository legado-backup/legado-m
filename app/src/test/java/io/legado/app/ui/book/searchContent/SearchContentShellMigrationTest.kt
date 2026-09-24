package io.legado.app.ui.book.searchContent

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE 5.2 第 4 页（`activity_search_content`）**换装的 CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：本页原为「XML 壳（ConstraintLayout）+ 5 个节点」：
 *   `compose_top_bar`（已是 ComposeView）/ `refresh_progress_bar`(自绘动画条) /
 *   `recycler_view`（FastScrollRecyclerView + View 版 adapter）/ `ll_search_base_info`（48dp 信息条）/
 *   `fb_stop`(mini FAB)。
 * CE 5.2 把页面改为 `composeShell` + `attachComposeContent` 单源承载，其中**无 Compose 等价物的四个
 * View 内核**（结果列表 / 自绘进度条 / 信息条 / mini FAB）一律以 `AndroidView` **原样托管**。
 *
 * 本测试锁死七类事实，防回归（只写文档的约束一律失效）：
 *   ①单源装配（composeShell + attachComposeContent），且**不再手写 ComposeView / viewBinding / 引用 R.layout**
 *   ②XML 已退役（`activity_search_content.xml` 不存在）
 *   ③四个 View 内核仍**以 AndroidView 原样托管**（不是被换成「看起来差不多」的 Compose 组件）
 *   ④三个 View 机制改由**状态**驱动（progressLoading / stopFabVisible / focusRequestSignal）
 *   ⑤进度条的**恒挂载**口径（本页原实现从不改它的可见性，只切动画态 ⇒ 不得改成条件组合）
 *   ⑥宿主业务逻辑**未消失**（逐项断言方法名）
 *   ⑦信息条几何/取色口径与 F76/F77 文案链路不变量
 */
class SearchContentShellMigrationTest {

    private val page = "ui/book/searchContent/SearchContentActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertFalse("禁止自行设置 ViewCompositionStrategy", s.contains("ViewCompositionStrategy"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivitySearchContentBinding"))
        assertFalse("原 applyNavigationBarMargin 手工 inset 链路应已由 Compose 承担", s.contains("applyNavigationBarMargin"))
    }

    @Test
    fun xmlIsRetired() {
        val f = File(SourceFileProbe.layoutDir(), "activity_search_content.xml")
        assertFalse("activity_search_content.xml 应已退役（CE 5.2）", f.exists())
    }

    @Test
    fun viewKernelsAreHostedViaAndroidView() {
        val s = src()
        assertTrue(
            "RefreshProgressBar（自绘动画条、无 Compose 等价物）必须以 AndroidView 原样托管",
            s.contains("AndroidView(") && s.contains("RefreshProgressBar(ctx)")
        )
        assertTrue(
            "结果列表（FastScrollRecyclerView + View 版 adapter）必须以 AndroidView 原样托管",
            s.contains("createResultList(") && s.contains("FastScrollRecyclerView(context)")
        )
        assertTrue(
            "程序化构造的列表必须显式赋 id（FastScroller.setLayoutParams 以 view id 定位宿主，缺 id 即崩）",
            s.contains("id = R.id.recycler_view")
        )
        assertTrue(
            "底部 48dp 信息条必须以 AndroidView 程序化构造（保住 middle 省略/长按提示/波纹底几何）",
            s.contains("createSearchInfoBar(") && s.contains("LinearLayout(context)")
        )
        assertTrue(
            "停止 FAB 必须以 AndroidView 托管 FloatingActionButton（mini 态无像素等价 Compose 组件）",
            s.contains("createStopFab(") && s.contains("FloatingActionButton(context)") &&
                s.contains("FloatingActionButton.SIZE_MINI")
        )
        assertTrue(
            "信息条必须保留导航栏边距（对齐原 applyNavigationBarMargin()）",
            s.contains("navigationBarsPadding()")
        )
        assertTrue(
            "FAB 底边距对齐原 constraintBottom_toTopOf=ll_search_base_info（位于信息条之上）",
            s.contains("Alignment.BottomEnd") && s.contains("padding(16.dp)")
        )
    }

    @Test
    fun viewMechanismsAreStateDriven() {
        val s = src()
        listOf("progressLoading", "stopFabVisible").forEach { state ->
            assertTrue("原 View 机制必须改由状态驱动：缺少 `$state`", s.contains("private var $state by mutableStateOf"))
        }
        assertTrue(
            "点信息条 → 聚焦搜索框须走信号量（原 showSoftInput 目标已随 ComposeView 退役）",
            s.contains("private var focusRequestSignal by mutableIntStateOf") &&
                s.contains("searchFocusRequester.requestFocus()")
        )
        assertFalse(
            "不得再调用旧的 visible()/gone()/invisible() 扩展",
            s.contains(".invisible()") || s.contains(".gone()") || s.contains(".visible()")
        )
    }

    @Test
    fun progressBarStaysMounted() {
        val s = src()
        assertTrue(
            "进度条动画态必须由 progressLoading 驱动",
            s.contains("it.isAutoLoading = progressLoading")
        )
        assertFalse(
            "本页原实现从不改进度条可见性 ⇒ 不得改成条件组合（否则空闲态会少 2dp 高度）",
            s.contains("if (progressLoading)")
        )
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "private fun initComposeContent(",
            "private fun createResultList(",
            "private fun createStopFab(",
            "private fun createSearchInfoBar(",
            "private fun createNavArrow(",
            "private fun borderlessItemBackgroundRes(",
            "private fun setInfoText(",
            "private fun scrollToChapter(",
            "private fun buildMenuActions(",
            "private fun handleMenuAction(",
            "private fun initSearchResultList(",
            "private fun initBook(",
            "private fun initCacheFileNames(",
            "override fun observeLiveBus(",
            "fun startContentSearch(",
            "private fun renderProgress(",
            "private fun renderCoverage(",
            "private fun updateDistribution(",
            "override fun openSearchResult(",
            "override fun durChapterIndex(",
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
        // F76：覆盖率三态文案（进度 / 已搜覆盖 / 带回既有结果）必须保留
        listOf(
            "R.string.search_content_progress",
            "R.string.search_content_coverage_scanned",
            "R.string.search_content_coverage_uncached",
            "R.string.search_content_coverage,",
        ).forEach { marker ->
            assertTrue("F76 覆盖率链路不得缺失：缺少 `$marker`", s.contains(marker))
        }
        assertTrue("有跳过才提「未缓存边界」的口径必须保留", s.contains("if (skipped > 0)"))
        // F77：命中分布 ≥2 章才给「按章直达」入口 + 按章首条定位
        assertTrue("命中分布入口阈值口径必须保留", s.contains("hitDistribution.size >= 2"))
        assertTrue("按章直达必须定位到该章首条命中", s.contains("scrollToPositionWithOffset"))
        // 搜索可中断
        assertTrue("停止 FAB 必须能取消搜索任务", s.contains("searchJob?.cancel()"))
        // 线程口径：原借 View.post 回主线程改由 runOnUiThread 承担（列表/文案均须主线程）
        assertTrue("结果/文案更新必须回主线程", s.contains("runOnUiThread {"))
        // 信息条几何与文本省略口径（48dp 条 / 36dp 箭头 / middle 省略）
        assertTrue("信息条高度口径必须保留", s.contains("48.dpToPx()"))
        assertTrue("箭头宽度口径必须保留", s.contains("36.dpToPx()"))
        assertTrue("信息条文本必须保留 middle 省略", s.contains("TextUtils.TruncateAt.MIDDLE"))
        // 组合挂载晚于 initData ⇒ 定位请求必须可回放
        assertTrue("列表未挂载时的定位请求必须有回放点", s.contains("pendingScrollPosition"))
    }
}