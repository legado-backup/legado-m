package io.legado.app.ui.book.manage

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：书架管理页（`activity_arrange_book`）换装的 **CB-1 结构不变量**（配对测试，JVM 可跑）。
 *
 * 背景：原 XML 为 `ConstraintLayout` 根（`compose_top_bar` + `recycler_view`(`FastScrollRecyclerView`，`0dp` 上下约束)
 * + `select_action_bar`(`SelectActionBar`)）。CE-b 把骨架交给 Compose：顶栏内容搬入页内，列表与批量底栏
 * **以 `AndroidView` 原样托管**（两者在 `onActivityCreated` 就要设 layoutManager/adapter/拖拽助手/回调 ⇒ 必须是字段）。
 *
 * 本测试锁死五类事实（只写文档的约束一律失效）：
 *   ①单源装配（composeShell + attachComposeContent），不再手写 ComposeView / viewBinding / 引用 R.layout
 *   ②XML 已退役（`activity_arrange_book.xml` 不存在）
 *   ③两个 View 内核以 `AndroidView` 托管，且**列表必须显式赋 `R.id.recycler_view`**
 *   ④原 `android:scrollbars="none"` 语义不得丢
 *   ⑤宿主业务逻辑与批量操作链未消失（拖拽排序 / 批量菜单 / 备份导出）
 */
class BookshelfManageShellMigrationTest {

    private val page = "ui/book/manage/BookshelfManageActivity.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun singleSourceAssemblyAndNoLegacyBinding() {
        val s = src()
        assertTrue("必须经 composeShell 创建合成壳", s.contains("composeShell(this)"))
        assertTrue("必须走 attachComposeContent 单源挂载", s.contains("binding.root.attachComposeContent {"))
        assertFalse("禁止手写 ComposeView 装配", s.contains("ComposeView("))
        assertTrue("骨架必须收敛为单一 initComposeContent", s.contains("private fun initComposeContent("))
        assertFalse("换装后不得再走 viewBinding 委托", s.contains("viewBinding("))
        assertFalse("换装后不得再引用已退役布局", s.contains("ActivityArrangeBookBinding"))
        assertFalse("原 initComposeTopBar 必须已合并", s.contains("initComposeTopBar("))
    }

    @Test
    fun xmlIsRetired() {
        val f = File(SourceFileProbe.layoutDir(), "activity_arrange_book.xml")
        assertFalse("activity_arrange_book.xml 应已退役（CE-b）", f.exists())
    }

    @Test
    fun viewKernelsAreHostedViaAndroidView() {
        val s = src()
        listOf("recyclerView", "selectActionBar").forEach { field ->
            assertTrue("`$field` 必须托管在 AndroidView 上", s.contains("factory = { $field }"))
        }
        assertTrue(
            "列表必须是 Activity 字段（by lazy）——onActivityCreated 就要装配它",
            Regex("""private val recyclerView\s*:\s*FastScrollRecyclerView\s+by lazy""").containsMatchIn(s)
        )
        // 程序化构造必须显式赋 id（FastScroller 以 view id 定位宿主）+ 复刻 scrollbars=none
        assertTrue("必须显式赋 R.id.recycler_view", s.contains("id = R.id.recycler_view"))
        assertTrue("必须复刻 XML 的 scrollbars=none", s.contains("isVerticalScrollBarEnabled = false"))
        assertFalse("不得再引用 XML 时代的 binding 节点", s.contains("binding.recyclerView") || s.contains("binding.selectActionBar"))
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            "private fun initRecyclerView(",
            "private fun initOtherView(",
            "private fun initGroupData(",
            "private fun buildMenuActions(",
            "private fun upTitle(",
            "override fun manageBackgroundAlphaEnabled(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
        // 批量操作链与拖拽排序不得被换装带掉
        listOf(
            "R.string.move_to_group",
            "R.menu.bookshelf_menage_sel",
            "DragSelectTouchHelper",
            "ItemTouchHelper(itemTouchCallback)",
            "dragSelectTouchHelper.activeSlideSelect()",
            "setEdgeEffectColor(primaryColor)",
        ).forEach { marker ->
            assertTrue("批量/拖拽链不得缺失：`$marker`", s.contains(marker))
        }
    }
}