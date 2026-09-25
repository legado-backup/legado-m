package io.legado.app.ui.book.source.manage

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：书源管理页（`activity_book_source`）换装的 **CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：原 XML = `LinearLayout`（`TitleBar@title_bar` 带 `contentLayout=view_search` + `FrameLayout` 内
 * `FastScrollRecyclerView`）。实测宿主 `initComposeContent()` 早已把前两者作废（titleBar 置 GONE、recyclerView
 * 摘出后原位插入手拼 `ComposeView`）⇒ XML 是**死壳**，换装只需把「运行时装配」收敛为合成壳单源。
 *
 * 注意：本文件内另有**顶层** `SourceGroupFilterDialog`（Compose 弹框，独立窗口）仍会自建 `ComposeView`
 * ⇒ 断言只锁「宿主自身的装配」，不以整文件是否出现 `ComposeView(` 判定；该例外已登记到
 * `ComposeShellSingleSourceTest.sameFileComposeDialogExceptions`（含反向自检）。
 */
class BookSourceShellMigrationTest {

    private val page = "ui/book/source/manage/BookSourceActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("原先的「摘 recyclerView 再手拼 ComposeView」必须消失", s.contains("val cv = ComposeView(this)"))
        assertFalse("不再需要摘取父容器/占位索引", s.contains("container.addView(cv, index)"))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityBookSourceBinding"))
        assertFalse("不得再引用已退役的 titleBar 节点", s.contains("binding.titleBar"))
        assertFalse("不得再引用已退役的 recyclerView 节点", s.contains("binding.recyclerView"))
    }

    @Test
    fun xmlIsRetired() {
        assertFalse(
            "activity_book_source.xml 应已退役（CE-b）",
            File(SourceFileProbe.layoutDir(), "activity_book_source.xml").exists()
        )
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "override fun manageBackgroundAlphaEnabled(",
            "private fun showSortMenu(",
            "private fun showFilterMenu(",
            "private fun pageMenuActions(",
            "private fun upBookSource(",
            "private fun initLiveDataGroup(",
            "private fun initBookCounts(",
            "private fun resumeCheckSource(",
            "private fun refreshDebugMessages(",
            "private fun sourceMenuActions(",
            "private fun updateSearchQuery(",
            "private fun sameBookSourcePartContent(",
            "internal var sourceDataVersion",
            "override fun finish(",
            "override fun onDestroy(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
        // 缓存键依赖的版本号递增单源（换装不得带掉）
        assertTrue("本地改动必须仍走 mutateSourcesLocally 递增版本号", s.contains("private fun mutateSourcesLocally("))
    }
}