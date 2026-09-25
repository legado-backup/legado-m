package io.legado.app.ui.book.explore

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：发现分类页（`activity_explore_show`）换装的 **CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：原 XML 为 `ConstraintLayout` 根（`compose_top_bar`(ComposeView) + `DynamicFrameLayout@content_view`
 * 内嵌 `compose_list`(ComposeView)）。CE-b 把骨架交给 Compose，单个合成壳单源承载：
 * `Column { 顶栏 ; Box(weight 1f){ 列表 Composition } }`。
 *
 * **实测事实（须由测试锁定）**：本页**从不调用 `DynamicFrameLayout` 的 ViewSwitcher API**
 * （全类零引用 `contentView`）⇒ 该容器退化为普通 `Box`，同 `activity_rss_search` 的 `content_view` 先例。
 *
 * 本测试锁死五类事实（只写文档的约束一律失效）：
 *   ①单源装配（composeShell + attachComposeContent），不再手写 ComposeView / viewBinding / 引用 R.layout
 *   ②XML 已退役（`activity_explore_show.xml` 不存在）
 *   ③`DynamicFrameLayout` 退化判定有据（既无 XML 依赖也无 `contentView` 引用）
 *   ④`ViewCompositionStrategy` 自设已删除（CB-1 ⑤）
 *   ⑤宿主业务逻辑与数据流未消失（分页/上滑加载/书架态/更多菜单/预览提示/WebViewPool 作用域）
 */
class ExploreShowShellMigrationTest {

    private val page = "ui/book/explore/ExploreShowActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertFalse("禁止自行设置 ViewCompositionStrategy", s.contains("ViewCompositionStrategy"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityExploreShowBinding"))
        assertTrue("顶栏与列表必须收敛为单一 initComposeContent", s.contains("private fun initComposeContent("))
        assertFalse("原 initTopBar / initComposeList 必须已合并", s.contains("initTopBar(") || s.contains("initComposeList("))
    }

    @Test
    fun xmlIsRetired() {
        val f = File(SourceFileProbe.layoutDir(), "activity_explore_show.xml")
        assertFalse("activity_explore_show.xml 应已退役（CE-b）", f.exists())
    }

    @Test
    fun dynamicFrameLayoutDegradedWithEvidence() {
        val s = src()
        assertFalse("不得再引用 XML 时代的 content_view / compose_list 节点", s.contains("binding.contentView") || s.contains("binding.composeList"))
        assertFalse("不得再引用 XML 时代的顶栏节点", s.contains("binding.composeTopBar"))
        assertTrue("列表区必须以 Box(weight 1f) 承载（等价原 0dp + 上下约束）", s.contains(".weight(1f)"))
        assertTrue("列表 Composition 必须仍在页内渲染", s.contains("ExploreShowComposeScreen("))
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "private fun showPagePicker(",
            "private fun buildBookActions(",
            "private fun addToBookshelf(",
            "private fun dismissPreviewHint(",
            "private fun scrollToBottom(",
            "private fun scrollToTop(",
            "private fun upData(",
            "private fun upDataTop(",
            "private fun replaceComposeBooks(",
            "private fun isInBookshelf(",
            "private fun showBookInfo(",
            "override fun onPause(",
            "override fun onDestroy(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
        listOf(
            "viewModel.booksData.observe(this)",
            "viewModel.addBooksData.observe(this)",
            "viewModel.errorLiveData.observe(this)",
            "viewModel.errorTopLiveData.observe(this)",
            "viewModel.upAdapterLiveData.observe(this)",
            "WebViewPool.scheduleDestroyScope(WebViewPool.Scope.DISCOVERY)",
            "WebViewPool.destroyScope(WebViewPool.Scope.DISCOVERY)",
            "VideoPlaylistHolder.set(videoList, idx)",
        ).forEach { marker ->
            assertTrue("数据流/作用域链不得缺失：`$marker`", s.contains(marker))
        }
    }
}