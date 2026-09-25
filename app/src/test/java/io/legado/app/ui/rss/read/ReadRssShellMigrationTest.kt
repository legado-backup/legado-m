package io.legado.app.ui.rss.read

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：RSS 阅读页（`activity_rss_read`）换装的 **CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：原 XML 为 `FrameLayout` 根 > `ll_view`(ConstraintLayout：`compose_top_bar` + `web_view_container` +
 * `progress_bar`) + 兄弟 `custom_web_view`（网页自定义全屏 overlay，绘于最上层）。CE-b 把骨架交给 Compose，
 * 其中**三个 View 内核一律 `AndroidView` 原样托管**（WebView 容器 / `RefreshProgressBar` / 全屏容器）。
 *
 * 本测试锁死六类事实（只写文档的约束一律失效）：
 *   ①单源装配（composeShell + attachComposeContent），不再手写 ComposeView / viewBinding / 引用 R.layout
 *   ②XML 已退役（`activity_rss_read.xml` 不存在）
 *   ③三个 View 内核仍以 `AndroidView` 原样托管，且**必须是 Activity 字段**（宿主 `onActivityCreated` 就要配置它们）
 *   ④四个 View 机制改状态驱动（`webProgress`/`topBarVisible`/`topBarOffsetY`/`pageContentVisible`）
 *   ⑤宿主业务逻辑与 F146 沉浸链路口径未消失（含 `Modifier.offset{}` 与 `onGloballyPositioned`）
 *   ⑥insets 锚点仍在合成壳 `root`（CB-1 ⑤）
 */
class ReadRssShellMigrationTest {

    private val page = "ui/rss/read/ReadRssActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertFalse("禁止自行设置 ViewCompositionStrategy", s.contains("ViewCompositionStrategy"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityRssReadBinding"))
    }

    @Test
    fun xmlIsRetired() {
        val f = File(SourceFileProbe.layoutDir(), "activity_rss_read.xml")
        assertFalse("activity_rss_read.xml 应已退役（CE-b）", f.exists())
    }

    @Test
    fun viewKernelsAreHostedViaAndroidView() {
        val s = src()
        listOf(
            "webViewContainer", // 原 web_view_container（宿主已在 onActivityCreated 挂好 currentWebView）
            "progressBar", // 原 progress_bar（自绘动画条，无 Compose 等价物）
            "customWebView", // 原 custom_web_view（网页自定义全屏 overlay）
        ).forEach { field ->
            assertTrue(
                "`$field` 必须是 Activity 字段（by lazy）——工厂内创建会让 onActivityCreated 的配置扑空",
                Regex("""private val $field\s*:[^=]*by lazy""").containsMatchIn(s)
            )
            assertTrue("`$field` 必须以 AndroidView 原样托管", s.contains("factory = { $field }"))
        }
        // 网页区容器绝不条件移除（否则 WebView 被 detach）——用 alpha 表达原 ll_view 的 invisible
        assertTrue("页面骨架收起必须用 alpha 表达而非条件移除", s.contains(".alpha(if (pageContentVisible) 1f else 0f)"))
    }

    @Test
    fun viewMechanismsAreStateDriven() {
        val s = src()
        listOf(
            "private var webProgress by mutableIntStateOf",
            "private var topBarVisible by mutableStateOf",
            "private var topBarOffsetY by mutableFloatStateOf",
            "private var pageContentVisible by mutableStateOf",
        ).forEach { marker ->
            assertTrue("原 View 机制必须改状态驱动：缺少 `$marker`", s.contains(marker))
        }
        assertFalse(
            "不得再调用旧的 visible()/gone()/invisible() 扩展",
            s.contains(".invisible()") || s.contains(".gone()") || s.contains("binding.llView")
        )
        assertFalse("不得再直接操作 XML 时代的顶栏 View", s.contains("binding.composeTopBar"))
        assertFalse("不得再直接操作 XML 时代的进度条", s.contains("binding.progressBar"))
    }

    @Test
    fun immersiveChainAndInsetsAnchorPreserved() {
        val s = src()
        // F146：位移改放置阶段求值（不逐帧重组），高度由组合上报
        assertTrue("顶栏位移必须走 Modifier.offset 放置阶段", s.contains(".offset { IntOffset(0, topBarOffsetY.roundToInt()) }"))
        assertTrue("顶栏高度必须由 onGloballyPositioned 上报", s.contains(".onGloballyPositioned { topBarFullHeight = it.size.height }"))
        assertTrue("沉浸滚动观察链必须保留", s.contains("private fun initImmersiveScroll("))
        assertTrue("收起/展开状态机必须保留", s.contains("private fun setTopBarCollapsed("))
        assertTrue("沉浸诊断日志必须保留", s.contains("TAG_RSS_IMMERSIVE"))
        // CB-1 ⑤：insets 锚点在合成壳 root（原 XML 根 FrameLayout 的同位）
        assertTrue("insets 锚点必须在合成壳 root", s.contains("binding.root.setOnApplyWindowInsetsListenerCompat"))
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "override fun onNewIntent(",
            "override fun onConfigurationChanged(",
            "private fun initComposeContent(",
            "override fun updateFavorite(",
            "override fun deleteFavorite(",
            "private fun initView(",
            "private fun initWebView(",
            "private fun initLiveData(",
            "private fun upWebviewSettings(",
            "private fun initJavascriptInterface(",
            "private fun upStarMenu(",
            "private fun upTtsMenu(",
            "private fun readAloud(",
            "override fun onPause(",
            "override fun onResume(",
            "override fun onDestroy(",
            "private fun buildMenuActions(",
            "private fun refresh(",
            "fun start(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
        assertFalse("原 initComposeTopBar 已并入 initComposeContent", s.contains("private fun initComposeTopBar("))
        // 网页能力链不得被换装带掉（源站页面强依赖）
        listOf(
            "currentWebView.webChromeClient = CustomWebChromeClient()",
            "currentWebView.webViewClient = CustomWebViewClient()",
            "override fun shouldInterceptRequest(",
            "override fun onShowCustomView(",
            "override fun onHideCustomView(",
            "WebViewPool.acquire(this)",
            "WebViewPool.release(pooledWebView)",
        ).forEach { marker ->
            assertTrue("WebView 能力链不得缺失：`$marker`", s.contains(marker))
        }
    }
}