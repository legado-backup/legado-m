package io.legado.app.ui.browser

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE 5.2 第 3 页（`activity_web_view`）**换装的 CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：本页原为 FrameLayout（根）+ ConstraintLayout（`ll_view`）+ 6 个节点：
 *   `compose_top_bar`(ComposeView) · `notice_bar`（**F215 明文保持纯 View**）· `web_view_container`（承载
 *   池化 WebView）· `progress_bar`(1dp，悬浮) · `custom_web_view`（网页自定义全屏 overlay）。
 *
 * CE 5.2 改为 `composeShell` + `attachComposeContent` 单源承载页面骨架，
 * **四个 View 内核一律 `AndroidView` 原样托管**（WebView 容器 / 通知条 / 进度条 / 全屏容器），
 * 并把两个 View 机制改为状态驱动（`webProgress` / `customFullscreen`）。
 *
 * 本测试锁死六类事实：
 *   ①单源装配，且不再手写 ComposeView / viewBinding / 引用 `R.layout`
 *   ②XML 已退役
 *   ③四个 View 内核仍以 AndroidView 原样托管（未被替换成「看起来差不多」的 Compose 组件）
 *   ④View 机制改状态驱动；旧 `binding.<子视图>` 用法清零
 *   ⑤宿主业务逻辑（WebView 客户端/Chrome 客户端/JS 接口/返回键/二次确认）未消失
 *   ⑥**F215 结论保留**：通知条文案与可见性仍走 View API（不得改成 Compose 条件组合）
 */
class WebViewShellMigrationTest {

    private val page = "ui/browser/WebViewActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertFalse("禁止自行设置 ViewCompositionStrategy", s.contains("ViewCompositionStrategy"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局绑定", s.contains("ActivityWebViewBinding"))
    }

    @Test
    fun xmlIsRetired() {
        val f = File(SourceFileProbe.layoutDir(), "activity_web_view.xml")
        assertFalse("activity_web_view.xml 应已退役（CE 5.2）", f.exists())
    }

    @Test
    fun fourViewKernelsAreHostedViaAndroidView() {
        val s = src()
        assertTrue("WebView 容器必须 AndroidView 托管并挂载池化 WebView", s.contains("addView(currentWebView)"))
        assertTrue("通知条（F215 纯 View）必须 AndroidView 托管程序化 View", s.contains("createNoticeBar(ctx)"))
        assertTrue(
            "进度条（自绘动画条、无 Compose 等价物）必须 AndroidView 托管",
            s.contains("RefreshProgressBar(ctx)") && s.contains("AndroidView(")
        )
        assertTrue("自定义全屏容器必须 AndroidView 托管并留引用", s.contains("customWebViewContainer = it"))
        assertTrue("进度必须由状态落到 setDurProgress", s.contains("it.setDurProgress(webProgress)"))
    }

    @Test
    fun viewMechanismsAreStateDrivenAndLegacyChildrenGone() {
        val s = src()
        assertTrue("进度条显隐必须由状态驱动", s.contains("private var webProgress by mutableIntStateOf"))
        assertTrue("自定义全屏必须由状态驱动", s.contains("private var customFullscreen by mutableStateOf"))
        listOf(
            "binding.noticeBar", "binding.noticeText", "binding.noticeClose",
            "binding.progressBar", "binding.llView", "binding.customWebView",
            "binding.composeTopBar", "initComposeTopBar",
        ).forEach { gone ->
            assertFalse("原 XML 子视图/初始化函数必须随换装删除：仍残留 `$gone`", s.contains(gone))
        }
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "private fun initVerificationGuide(",
            "private fun initComposeContent(",
            "private fun createNoticeBar(",
            "private fun applyNoticeBar(",
            "private fun onNoticeClose(",
            "override fun onSaveInstanceState(",
            "private fun onClickOk(",
            "private fun buildMenuActions(",
            "private fun toggleFullScreen(",
            "private fun initWebView(",
            "private fun saveImage(",
            "private fun selectSaveFolder(",
            "override fun finish(",
            "private fun close(",
            "override fun onPause(",
            "override fun onResume(",
            "override fun onDestroy(",
            "inner class CustomWebChromeClient",
            "inner class CustomWebViewClient",
            "private class JSInterface(",
            "WebViewPool.release(pooledWebView)",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
    }

    @Test
    fun f215NoticeBarStaysPureView() {
        val s = src()
        // F215：文案与可见性必须落 View API（不得改为 Compose 条件组合/Compose Text）
        assertTrue("通知条文案必须写 View（TextView.text）", s.contains("label.text = text"))
        assertTrue("通知条可见性必须切 View", s.contains("bar.visibility = View.VISIBLE"))
        assertTrue("挑战期条不可关闭的语义必须保留", s.contains("close.visibility = if (closable) View.VISIBLE else View.GONE"))
        assertFalse("通知条不得改为 Compose 条件组合（F215 明确否决）", s.contains("if (challengeChecking) Text("))
    }
}