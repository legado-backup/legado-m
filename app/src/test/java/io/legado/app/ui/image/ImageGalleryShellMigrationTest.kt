package io.legado.app.ui.image

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE 5.2 第 9 页（`activity_image_gallery`）**换装的 CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：本页原为「ConstraintLayout 壳 + 9 类节点」：
 *   根底黑 / `recycler_view`（垂直长画布，全屏 + 顶部 padding=顶栏高）/ `view_pager_fullscreen`（全屏横向层）
 *   / `webview_preheat`（1px 预热）/ `compose_top_bar` / `tv_page_index` / `progress_loading`
 *   / `layout_error`+`tv_error`+`btn_retry` / `layout_rotate_toolbar`+三按钮 / `tv_canvas_page_index`。
 * CE 5.2 把页面改为 `composeShell` + `attachComposeContent` 单源承载，**六个 View 内核以 `AndroidView`
 * 原样托管**（z-order 按原声明顺序入 Box）；另处置本轮真实缺陷三处（见 ⑦）。
 *
 * 本测试锁死七类事实，防回归（只写文档的约束一律失效）：
 *   ①单源装配（composeShell + attachComposeContent），且**不再走 viewBinding / 引用 R.layout**
 *   ②XML 已退役（`activity_image_gallery.xml` 不存在）
 *   ③六个 View 内核**以 AndroidView 原样托管**，类型与 id 复用与 XML 等价
 *   ④页面级显隐**改状态驱动**（顶栏/工具条/两个页码），全屏层显隐仍是 View 级命令式（与动画同段语义）
 *   ⑤顶栏高度**一次性测量**口径保留，且不再依赖 `composeTopBar.viewTreeObserver` 时序
 *   ⑥宿主业务逻辑**未消失**（逐项断言方法名）
 *   ⑦行为不变量 + 本轮缺陷修复：`super.onScrolled` 传参修正、页面级 4 个不可达节点不再重建、
 *     F179 刷新任务条 / 预热 WebView 配置与销毁 / 画布域黑白面色（已登记 allowlist）不变
 */
class ImageGalleryShellMigrationTest {

    private val page = "ui/image/ImageGalleryActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止自行设置 ViewCompositionStrategy", s.contains("ViewCompositionStrategy"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityImageGalleryBinding"))
        assertTrue(
            "宿主必须显式改绑 ViewBinding 泛型参数",
            s.contains("VMBaseActivity<ViewBinding, ImageCanvasViewModel>()")
        )
        // 词边界防止把 `import androidx.viewbinding.ViewBinding` 误判为「换装后仍用 binding」
        val bindingRefs = Regex("(?<![A-Za-z])binding\\.[A-Za-z]+").findAll(s).map { it.value }.toSet()
        assertEquals("换装后 binding 只允许 root（合成壳）：${bindingRefs}", setOf("binding.root"), bindingRefs)
    }

    @Test
    fun xmlIsRetired() {
        val f = File(SourceFileProbe.layoutDir(), "activity_image_gallery.xml")
        assertFalse("activity_image_gallery.xml 应已退役（CE 5.2）", f.exists())
    }

    @Test
    fun viewKernelsHostedViaAndroidView() {
        val s = src()
        listOf(
            "factory = { recyclerView }",
            "factory = { fullscreenPager }",
            "factory = { preheatWebView }",
            "factory = { pageIndexView }",
            "factory = { rotateToolbarView }",
            "factory = { canvasPageIndexView }",
        ).forEach { marker ->
            assertTrue("六个 View 内核必须以 AndroidView 托管：缺少 `$marker`", s.contains(marker))
        }
        assertTrue(
            "画布必须是程序化 RecyclerView（保 clipToPadding=false + overScrollMode=never）",
            s.contains("private fun createRecyclerView(): RecyclerView") &&
                s.contains("clipToPadding = false") && s.contains("overScrollMode = View.OVER_SCROLL_NEVER")
        )
        assertTrue(
            "全屏层必须是程序化 ViewPager2（黑底 + 初始 gone）",
            s.contains("private fun createFullscreenPager(): ViewPager2") && s.contains("setBackgroundColor(Color.BLACK)")
        )
        assertTrue(
            "预热必须是程序化 WebView（1px + invisible）",
            s.contains("private fun createPreheatWebView(): WebView") &&
                s.contains("ViewGroup.LayoutParams(1, 1)") && s.contains("visibility = View.INVISIBLE")
        )
        assertTrue(
            "旋转工具条必须复用既有 id 族（image_detail 同批迁移保留）",
            s.contains("R.id.layout_rotate_toolbar") &&
                s.contains("R.id.btn_rotate_left") && s.contains("R.id.btn_reset") &&
                s.contains("R.id.btn_rotate_right") && s.contains("R.id.tv_page_index")
        )
        assertTrue(
            "工具条按钮必须是 AppCompatImageButton + 无边界波纹底（XML 同构）",
            s.contains("private fun createRotateButton(") && s.contains("AppCompatImageButton(this)") &&
                s.contains("borderlessItemBackgroundRes()")
        )
    }

    @Test
    fun visibilityMechanismsAreStateDriven() {
        val s = src()
        listOf(
            "topBarVisible", "rotateToolbarVisible",
            "pageIndexVisible", "pageIndexText",
            "canvasPageIndexVisible", "canvasPageIndexText",
        ).forEach { name ->
            assertTrue("原 View 机制必须改由状态驱动：缺少 `private var $name by mutableStateOf`",
                s.contains("private var $name by mutableStateOf"))
        }
        assertFalse("不得再直接操作已退役页码节点", s.contains("binding.tvPageIndex"))
        assertFalse("不得再直接操作已退役工具条节点", s.contains("binding.layoutRotateToolbar"))
        assertTrue(
            "全屏层显隐**保持 View 级命令式**（与 alpha 动画的 withEndAction 同段语义，注册为口径例外）",
            s.contains("fullscreenPager.visibility = View.VISIBLE") &&
                s.contains("fullscreenPager.visibility = View.GONE")
        )
    }

    @Test
    fun topBarHeightMeasurementKeepsOnceOnlySemantics() {
        val s = src()
        assertTrue(
            "顶栏高度必须由组合测量上报（替代原 viewTreeObserver 时序依赖）",
            s.contains("onGloballyPositioned { topBarHeightPx = it.size.height }")
        )
        assertTrue(
            "顶栏高度必须一次性落地为画布 paddingTop（原 BUG1 fix V2 口径）",
            s.contains("private var topBarPaddingApplied") &&
                s.contains("LaunchedEffect(topBarHeightPx)") &&
                s.contains("recyclerView.setPadding(")
        )
        assertFalse(
            "不得再依赖 composeTopBar.viewTreeObserver（换装后顶栏已非 View）",
            s.contains("composeTopBar.viewTreeObserver")
        )
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "private fun initComposeContent(",
            "private fun initImmersion(",
            "private fun createRecyclerView(",
            "private fun createFullscreenPager(",
            "private fun createPreheatWebView(",
            "private fun createPageIndexView(",
            "private fun createCanvasPageIndexView(",
            "private fun createRotateToolbar(",
            "private fun createRotateButton(",
            "private fun borderlessItemBackgroundRes(",
            "private fun buildMenuActions(",
            "private fun starCurrentArticle(",
            "private fun refreshImages(",
            "private fun finishRefresh(",
            "private fun initRecyclerView(",
            "private fun onCanvasItemClick(",
            "private fun initFullscreenViewPager(",
            "private fun initRotateToolbar(",
            "private fun enterHorizontalMode(",
            "private fun exitHorizontalMode(",
            "private fun setupFullscreenViewPager(",
            "private fun updatePageIndex(",
            "private fun toggleImmersive(",
            "private fun updateCanvasPageIndex(",
            "private fun initPreheatWebView(",
            "private fun triggerFallbackReload(",
            "private fun saveImage(",
            "private fun shareImage(",
            "override fun onDestroy(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
    }

    @Test
    fun behaviorInvariantsAndBugFixes() {
        val s = src()
        // ① 缺陷修复：onScrolled 基类传参由 (dy, dy) 修正为 (dx, dy)
        assertTrue("onScrolled 必须正确透传 dx", s.contains("super.onScrolled(recyclerView, dx, dy)"))
        assertFalse("不得回退成 dx 位置传 dy 的旧写法", s.contains("super.onScrolled(recyclerView, dy, dy)"))
        // ② 页面级 4 个不可达节点（零代码引用）随壳退役，不重建
        listOf("layout_error", "btn_retry", "tv_error", "progress_loading").forEach { dead ->
            assertFalse("页面级死节点不得重建：`$dead`", s.contains(dead))
        }
        // ③ 画布域固定黑白面色（同域同口径已登记 allowlist，禁止换成 M3 派生键）
        assertTrue("画布域黑底必须保留字面语义", s.contains("Color.BLACK"))
        assertTrue("画布域白字/白 tint 必须保留字面语义", s.contains("Color.WHITE"))
        // ④ 横向浏览链路口径
        assertTrue("进入横向模式必须仍建 adapter", s.contains("fullscreenPager.adapter = adapter"))
        assertTrue("退出横向模式必须仍回同步列表位置", s.contains("recyclerView.smoothScrollToPosition(listPos)"))
        assertTrue("画布分页阈值判定必须保留", s.contains("ImageCanvasAdapter.PAGINATION_THRESHOLD"))
        assertTrue("滚动速度预加载必须保留", s.contains("scrollSpeedThreshold") && s.contains("preloadAround("))
        // ⑤ F179 刷新回执 + 预热 WebView 生命周期
        assertTrue("F179 任务条必须仍挂顶栏 secondRow", s.contains("secondRow = {"))
        assertTrue("F179 任务条自动消退必须仍用宿主 View 的 handler", s.contains("binding.root.postDelayed(it, 2500)"))
        assertTrue("预热 WebView 必须仍开 JS/DOM/DB", s.contains("settings.javaScriptEnabled = true"))
        assertTrue("预热 WebView 必须在销毁时释放", s.contains("stopLoading()") && s.contains("destroy()"))
        assertTrue("降级重载链路必须保留", s.contains("private fun triggerFallbackReload("))
    }
}