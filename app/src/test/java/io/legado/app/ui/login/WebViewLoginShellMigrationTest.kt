package io.legado.app.ui.login

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：登录页 WebView Fragment（`fragment_web_view_login`）换装的 **CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：原 XML 为 `ConstraintLayout` 根（`compose_top_bar`(ComposeView) + `web_view_container` +
 * `progress_bar`）。CE-b 在 **Fragment 侧**退役该 XML：`BaseFragment(0)`（布局 id 传 0 = 无 XML）
 * + `onCreateView` 提供合成壳 + `attachComposeContent` 单源承载；两个 View 内核以 `AndroidView` 原样托管。
 *
 * 本测试锁死五类事实（只写文档的约束一律失效）：
 *   ①单源装配（`BaseFragment(0)` + `onCreateView` + `attachComposeContent`），不再引用已退役 binding
 *   ②XML 已退役（`fragment_web_view_login.xml` 不存在）
 *   ③两个 View 内核（WebView 容器 / `RefreshProgressBar`）以 `AndroidView` 原样托管且**先于组合挂载创建**
 *   ④进度机制改状态驱动（`webProgress`），不再调用 `gone()`
 *   ⑤宿主业务逻辑与登录链路未消失（cookie 持久化 / 页面回调 / 完成登录 / WebViewPool）
 */
class WebViewLoginShellMigrationTest {

    private val page = "ui/login/WebViewLoginFragment.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("布局 id 必须传 0（无 XML）", s.contains("BaseFragment(0)"))
        assertTrue("必须自行提供视图（onCreateView）", s.contains("override fun onCreateView("))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("shellRoot.attachComposeContent {"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("FragmentWebViewLoginBinding"))
        assertFalse("不得再依赖 R.layout 承载本页", s.contains("R.layout.fragment_web_view_login"))
    }

    @Test
    fun xmlIsRetired() {
        val f = File(SourceFileProbe.layoutDir(), "fragment_web_view_login.xml")
        assertFalse("fragment_web_view_login.xml 应已退役（CE-b）", f.exists())
    }

    @Test
    fun viewKernelsAreHostedViaAndroidView() {
        val s = src()
        listOf("webViewContainer", "progressBar").forEach { field ->
            assertTrue(
                "`$field` 必须在 onCreateView 建好（先于组合挂载）",
                Regex("""$field\s*=\s*(FrameLayout|RefreshProgressBar)\(ctx\)""").containsMatchIn(s)
            )
            assertTrue("`$field` 必须以 AndroidView 原样托管", s.contains("factory = { $field }"))
        }
        assertTrue("壳 root 必须是 onCreateView 返回的 FrameLayout", s.contains("return shellRoot"))
    }

    @Test
    fun progressIsStateDriven() {
        val s = src()
        assertTrue("进度必须改状态驱动", s.contains("private var webProgress by mutableIntStateOf"))
        assertTrue("进度 100 时进度条退出组合", s.contains("if (webProgress < 100)"))
        assertFalse("不得再调用旧的 gone() 扩展", s.contains(".gone("))
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onFragmentCreated(",
            "private fun initComposeContent(",
            "private fun checkHostCookie(",
            "private fun initWebView(",
            "private fun loadUrl(",
            "override fun onDestroy(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
        assertFalse("原 initComposeTopBar 已并入 initComposeContent", s.contains("private fun initComposeTopBar("))
        // 登录链路硬语义不得被换装带掉
        listOf(
            "CookieManager.getInstance().flush()",
            "CookieStore.setCookie(source.getKey(), cookie)",
            "override fun onPageStarted(",
            "override fun onPageFinished(",
            "override fun shouldOverrideUrlLoading(",
            "WebViewPool.acquire(requireContext())",
            "WebViewPool.release(it)",
            "shellRoot.snackbar(R.string.check_host_cookie)",
            "shellRoot.longSnackbar(R.string.jump_to_another_app, R.string.confirm)",
        ).forEach { marker ->
            assertTrue("登录链路不得缺失：`$marker`", s.contains(marker))
        }
    }
}