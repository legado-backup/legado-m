package io.legado.app.ui.book.search

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE 5.2 第 2 页（`activity_book_search`）**换装的 CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：本页原为「XML 壳（ConstraintLayout）+ 5 类 View 机制」：
 *   `search_view`（原生 `io.legado.app.ui.widget.SearchView`）+ `btn_menu`（`ModernActionPopup`）·
 *   `refresh_progress_bar`（自绘动画条）· `content_view`(DynamicFrameLayout) + `compose_results` ·
 *   `hsv_source_group_bar` + `ll_source_group_tags`（程序化 TextView chips）· `ll_input_help`（挡点击覆盖层）·
 *   `fb_start_stop`（mini FAB，图标随搜索状态在「停止/继续」间切换）。
 *
 * CE 5.2 把页面改为 `composeShell` + `attachComposeContent` 单源承载：顶栏/搜索框/chips/覆盖层为 Compose，
 * **两个无 Compose 等价物的 View**（`RefreshProgressBar` 自绘动画、mini `FloatingActionButton`）以
 * `AndroidView` **原样托管**；其余 View 机制一律改由状态驱动。
 *
 * 本测试锁死七类事实，防回归（只写文档的约束一律失效）：
 *   ①单源装配（composeShell + attachComposeContent），且不再手写 ComposeView / viewBinding / 引用 R.layout
 *   ②XML 退役（`activity_book_search.xml` + 其独占的 `menu/book_search.xml` 均不存在）
 *   ③两个无等价物的 View 仍以 AndroidView 原样托管（不是被换成「看起来差不多」的 Compose 组件）
 *   ④原 View 机制改由状态驱动（8 个状态字段），且旧的 visible()/gone()/invisible() 调用清零
 *   ⑤宿主业务逻辑未消失（逐项断言方法名）
 *   ⑥顶栏仍走页内直接渲染 `GlassTopAppBar`（不经 `installGlassTopBar`），搜索框走共享 `SettingsSearchBar`
 *   ⑦行为不变量（改词副作用 / 自动聚焦 / 失效分组兜底 / 分组 chips 单源 / 覆盖层挡点击）
 */
class SearchShellMigrationTest {

    private val page = "ui/book/search/SearchActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertFalse("禁止自行设置 ViewCompositionStrategy", s.contains("ViewCompositionStrategy"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityBookSearchBinding"))
    }

    @Test
    fun xmlAndItsExclusiveMenuAreRetired() {
        val layout = File(SourceFileProbe.layoutDir(), "activity_book_search.xml")
        assertFalse("activity_book_search.xml 应已退役（CE 5.2）", layout.exists())
        val menu = File(SourceFileProbe.layoutDir().parentFile, "menu/book_search.xml")
        assertFalse(
            "menu/book_search.xml 是本页独占资源，随页退役（动作改 AppDropdownMenu 数据驱动）",
            menu.exists()
        )
    }

    @Test
    fun viewKernelsAreHostedViaAndroidView() {
        val s = src()
        assertTrue(
            "RefreshProgressBar（自绘动画条、无 Compose 等价物）必须以 AndroidView 原样托管",
            s.contains("AndroidView(") && s.contains("RefreshProgressBar(ctx)")
        )
        assertTrue(
            "停止/继续 FAB 必须以 AndroidView 托管 FloatingActionButton（mini 态无像素等价 Compose 组件）",
            s.contains("createStopFab(") && s.contains("FloatingActionButton(context)") &&
                s.contains("FloatingActionButton.SIZE_MINI")
        )
        assertTrue(
            "FAB 底边距必须含导航栏 inset（对齐原 applyNavigationBarMargin(true)）",
            s.contains("navigationBarsPadding()")
        )
        assertTrue(
            "FAB 图标为动态资源（搜索中「停止」/可继续「继续」）⇒ 必须由状态驱动 setImageResource",
            s.contains("stopFabIconRes") && s.contains("fab.setImageResource(fabIconRes)")
        )
    }

    @Test
    fun viewMechanismsAreStateDriven() {
        val s = src()
        listOf(
            "composeSearchQuery", "menuExpanded", "sourceGroups", "selectedGroupNames",
            "progressLoading", "stopFabVisible", "stopFabIconRes", "inputHelpVisible",
        ).forEach { state ->
            val marker = "private var $state by mutable"
            assertTrue("原 View 机制必须改由状态驱动：缺少 `$state`", s.contains(marker))
        }
        assertFalse(
            "不得再调用旧的 visible()/gone()/invisible() 扩展",
            s.contains(".invisible()") || s.contains(".gone()") || s.contains(".visible()")
        )
    }

    @Test
    fun legacyViewMechanismsAreGone() {
        val s = src()
        listOf(
            "searchEditText", "createSourceGroupChip", "updateKeyboardGroupBarVisible",
            "updateInputHelpBottomMargin", "setOnApplyWindowInsetsListenerCompat",
            "showSearchMenu", "prepareSearchMenu", "onCompatOptionsItemSelected",
        ).forEach { gone ->
            assertFalse("原 View 机制必须随换装删除：仍残留 `$gone`", s.contains(gone))
        }
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "override fun onNewIntent(",
            "private fun initComposeContent(",
            "private fun createStopFab(",
            "private fun handleMenuAction(",
            "private fun buildMenuActions(",
            "private fun handleGroupSelect(",
            "private fun healStaleSearchScope(",
            "private fun applyQuery(",
            "private fun submitSearch(",
            "private fun initData(",
            "private fun receiptIntent(",
            "private fun scrollToBottom(",
            "private fun visibleInputHelp(",
            "private fun updateSourceGroupTags(",
            "private fun upHistory(",
            "private fun startSearch(",
            "private fun searchFinally(",
            "override fun observeLiveBus(",
            "private fun togglePrecisionSearch(",
            "private fun toggleCompactSearchResult(",
            "private fun showBookInfo(",
            "private fun isInBookshelf(",
            "private fun searchHistory(",
            "private fun deleteHistory(",
            "override fun onSearchScopeOk(",
            "private fun alertSearchScope(",
            "private fun alertClearHistory(",
            "SearchResultScreen(",
            "SearchInputHelpScreen(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
    }

    @Test
    fun topBarAndSearchBarUseSharedComponentsInPage() {
        val s = src()
        assertTrue("顶栏必须页内直接渲染 GlassTopAppBar", s.contains("GlassTopAppBar("))
        assertTrue("搜索输入必须走共享 SettingsSearchBar（全站搜索页单源）", s.contains("SettingsSearchBar("))
        assertTrue("更多菜单必须走共享 AppDropdownMenu", s.contains("AppDropdownMenu("))
        // 本页历史上从不经 installGlassTopBar（无 title_bar 锚点）⇒ 如实锁定该事实，防未来被误改
        assertFalse("本页不应引入 installGlassTopBar（无顶栏锚点）", s.contains("installGlassTopBar("))
    }

    @Test
    fun behaviorInvariantsKept() {
        val s = src()
        // 改词副作用（原 onQueryTextChange）：停搜索 + 收状态条 + 隐藏 FAB + 刷历史
        assertTrue("改词必须停止当前搜索", s.contains("viewModel.stop()"))
        assertTrue("改词必须收起结果状态条", s.contains("resultSummaryVisible = false"))
        // 提交（原 onQueryTextSubmit）：落历史 + 起搜索 + 收输入帮助
        assertTrue("提交必须保存搜索键", s.contains("viewModel.saveSearchKey(searchKey)"))
        assertTrue("提交必须收起输入帮助", s.contains("visibleInputHelp(false)"))
        // 自动聚焦（原 searchEditText.requestFocus）
        assertTrue("必须保留进入页面自动聚焦搜索框", s.contains("autoFocusSignal"))
        assertTrue("自动聚焦必须经 FocusRequester 承载", s.contains("searchFocusRequester.requestFocus()"))
        // 失效分组兜底（原 prepareSearchMenu 的 hasChecked 分支）
        assertTrue("必须保留失效分组兜底", s.contains("healStaleSearchScope()"))
        // 分组 chips 必须走共享 AppFilterChip（同语义不留第二套视觉）
        assertTrue("分组 chips 必须用共享 AppFilterChip", s.contains("AppFilterChip("))
        // 覆盖层挡点击语义（原 ll_input_help 的 clickable）
        assertTrue("覆盖层须保留挡点击语义", s.contains("indication = null"))
        // 返回键语义（原 finish() 的 hasFocus 分支）
        assertTrue("输入法展开时返回须先收键盘而非退出", s.contains("BackHandler("))
    }
}