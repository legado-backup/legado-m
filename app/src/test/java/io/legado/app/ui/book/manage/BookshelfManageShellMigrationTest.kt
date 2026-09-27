package io.legado.app.ui.book.manage

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 书架管理页（`activity_arrange_book`）**两阶段换装**的结构不变量（配对测试，JVM 可跑）。
 *
 * - **CE-b（骨架）**：原 XML 为 `ConstraintLayout` 根（`compose_top_bar` + `recycler_view`
 *   (`FastScrollRecyclerView`，`0dp` 上下约束) + `select_action_bar`(`SelectActionBar`)）⇒ 骨架交 Compose，
 *   批量底栏以 `AndroidView` 原样托管。
 * - **CF 6.2（列表）**：`item_arrange_book` 退役 ⇒ 列表由程序化 `FastScrollRecyclerView` + `BookAdapter`
 *   改为 Compose `LazyColumn`（`ui/book/manage/compose/ArrangeBookComposeList.kt`）；拖拽换序/滑选/落库
 *   三条链搬到 Compose（`reorderable` + 容器 `pointerInput` + `onOrderCommitted`），**选择态提到宿主**。
 *
 * 本测试锁死五类事实（只写文档的约束一律失效）：
 *   ①单源装配（composeShell + attachComposeContent），不再手写 ComposeView / viewBinding / 引用 R.layout
 *   ②XML 已退役（`activity_arrange_book.xml` 不存在）
 *   ③批量底栏仍以 `AndroidView` 托管；列表已换 Compose（**不得回退**为 View 列表）
 *   ④原「滚动位置」语义不得丢（View 侧 `RecyclerView` 自带布局态保存 ⇒ 换 Compose 后须宿主显式保存/恢复）
 *   ⑤宿主业务逻辑与批量操作链未消失（拖拽排序 / 批量菜单 / 备份导出）
 */
class BookshelfManageShellMigrationTest {

    private val page = "ui/book/manage/BookshelfManageActivity.kt"
    private val listPage = "ui/book/manage/compose/ArrangeBookComposeList.kt"

    private fun src(): String = code(page)

    private fun listSrc(): String = code(listPage)

    /**
     * 剥块注释 + 行注释后再断言：`SourceFileProbe.sourceText` 只剥「以 `//` 或 `*` 开头」的行，
     * 单行 KDoc 与行首非 `*` 的块注释会漏 ⇒ 注释里的「换装前」类名（`FastScrollRecyclerView` 等）
     * 会造成**假阳性**（本项目已多次踩坑，见交接文档 §8）。
     */
    private fun code(rel: String): String = SourceFileProbe.rawText(rel)
        .replace(Regex("/\\*[\\s\\S]*?\\*/"), "")
        .lines()
        .filterNot { it.trimStart().startsWith("//") }
        .joinToString("\n")

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
    fun listIsComposeAndActionBarStaysView() {
        val s = src()
        // 批量底栏仍是 View 内核（`SelectActionBar`，非 item ⇒ 不在 CF 范围）
        assertTrue("批量底栏须仍托管在 AndroidView 上", s.contains("factory = { selectActionBar }"))
        // 列表已换 Compose（CF 6.2）：不得回退为 View 列表
        assertFalse("不得再手挂 FastScrollRecyclerView", s.contains("FastScrollRecyclerView"))
        assertFalse("不得再挂 ItemTouchHelper / 滑选助手", s.contains("ItemTouchHelper(") || s.contains("DragSelectTouchHelper"))
        assertTrue("列表须走 Compose 单源", s.contains("ArrangeBookList("))
        assertTrue("列表状态须由宿主持有（旋转恢复）", s.contains("private val listState = LazyListState()"))
        val l = listSrc()
        assertTrue("Compose 列表须用 LazyColumn", l.contains("LazyColumn("))
        assertTrue("换序须接入 reorderable", l.contains("rememberReorderableLazyListState("))
        assertTrue("滑选须保留长按拖动", l.contains("detectDragGesturesAfterLongPress"))
    }

    @Test
    fun scrollPositionSemanticsPreserved() {
        // 交接文档 §8-64：View 侧 RecyclerView 带 id 时自带布局态保存 ⇒ 换 Compose 后必须显式补，否则旋转丢位置
        val s = src()
        assertTrue("须重写 onSaveInstanceState", s.contains("override fun onSaveInstanceState("))
        assertTrue("须保存首项下标", s.contains("KEY_SCROLL_INDEX"))
        assertTrue("恢复须等数据到达", s.contains("listState.scrollToItem(index, pendingScrollOffset)"))
    }

    @Test
    fun hostLogicPreserved() {
        val s = src()
        listOf(
            "override fun onActivityCreated(",
            // CF 6.2：原 initRecyclerView（View 列表装配）已收敛为 dragMode 状态初始化
            "private fun initDragMode(",
            "private fun initOtherView(",
            "private fun initGroupData(",
            "private fun buildMenuActions(",
            "private fun upTitle(",
            "override fun manageBackgroundAlphaEnabled(",
        ).forEach { marker ->
            assertTrue("换装不得删改宿主逻辑：缺少 `$marker`", s.contains(marker))
        }
        // 批量操作链不得被换装带掉（菜单 id / 主操作文案 / 端到端批量入口）
        listOf(
            "R.string.move_to_group",
            "R.menu.bookshelf_menage_sel",
            "viewModel.upCanUpdate(selection, true)",
            "viewModel.upCanUpdate(selection, false)",
            "viewModel.clearCache(selection)",
            "viewModel.changeSource(selection, source)",
        ).forEach { marker ->
            assertTrue("批量链不得缺失：`$marker`", s.contains(marker))
        }
    }
}