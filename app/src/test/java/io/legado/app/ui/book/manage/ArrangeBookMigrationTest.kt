package io.legado.app.ui.book.manage

import io.legado.app.testkit.SourceFileProbe
import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CF 6.2 配对测试：`item_arrange_book` 退役（书籍整理/书架管理列表 View → Compose）。
 *
 * 换装前：`BookshelfManageActivity` 用 `FastScrollRecyclerView`（`AndroidView` 托管）+ `BookAdapter`
 * （inflate `item_arrange_book.xml`）+ `ItemTouchHelper`（拖拽换序）+ `DragSelectTouchHelper`（滑选）。
 * 换装后：Compose `LazyColumn`（`ui/book/manage/compose/ArrangeBookComposeList.kt`）+ `sh.calvin.reorderable`
 * （换序）+ 容器 `pointerInput` 滑选；**选择态提到宿主**（`selectedUrls`）供底栏计数与批量操作读取。
 */
class ArrangeBookMigrationTest {

    private val page = "ui/book/manage/BookshelfManageActivity.kt"

    /**
     * 宿主源码的**代码面**（剥块注释 + 行注释）。
     *
     * 为什么不用 `SourceFileProbe.sourceText`：它只剥「以 `//` 或 `*` 开头」的行，**单行 KDoc（以斜杠加星号起头）
     * 与行首非 `*` 的块注释不被剥除** ⇒ 注释里记录的历史类名（本页 KDoc 大量提到 `BookAdapter` /
     * `FastScrollRecyclerView` 作为「换装前」对照）会造成**假阳性**（本项目已多次踩坑，见交接文档 §8）。
     */
    private fun src(): String = SourceFileProbe.rawText(page)
        .replace(Regex("/\\*[\\s\\S]*?\\*/"), "")
        .lines()
        .filterNot { it.trimStart().startsWith("//") }
        .joinToString("\n")

    @Test
    fun deadArtifactsAreGone() {
        assertFalse(
            "死布局应已退役：item_arrange_book.xml",
            File(SourceFileProbe.layoutDir(), "item_arrange_book.xml").isFile
        )
        assertFalse(
            "死 Adapter 应已退役：BookAdapter.kt",
            File(SourceFileProbe.mainJavaRoot(), "io/legado/app/ui/book/manage/BookAdapter.kt").isFile
        )
    }

    @Test
    fun hostNoLongerHostsViewList() {
        val s = src()
        assertFalse("不得再引用死 Adapter", s.contains("BookAdapter"))
        assertFalse("不得再手挂 FastScrollRecyclerView", s.contains("FastScrollRecyclerView"))
        assertFalse("不得再挂 ItemTouchHelper/滑选助手（已由 Compose 列表承担）", s.contains("ItemTouchHelper("))
        assertFalse("不得再挂 DragSelectTouchHelper", s.contains("DragSelectTouchHelper"))
        assertTrue("须改挂 Compose 列表单源", s.contains("ArrangeBookList("))
        assertTrue("列表状态须由宿主持有（旋转恢复）", s.contains("private val listState = LazyListState()"))
    }

    @Test
    fun selectionIsHostSingleSource() {
        // 原选择态在 Adapter 内（selectedBooks），而底栏计数与批量操作都在宿主读取 ⇒ 换装后必须提为宿主单源
        val s = src()
        assertTrue("选择态须为宿主状态", s.contains("private var selectedUrls by mutableStateOf<Set<String>>"))
        assertTrue("选中项派生须走 selection", s.contains("private val selection: List<Book>"))
        listOf(
            "viewModel.upCanUpdate(selection, true)",
            "viewModel.clearCache(selection)",
            "viewModel.deleteBook(selection, checkBox.isChecked)",
            "viewModel.changeSource(selection, source)"
        ).forEach { marker ->
            assertTrue("批量操作须读宿主选择态：缺少 `$marker`", s.contains(marker))
        }
        assertTrue("底栏计数须用展示列表总数", s.contains("selectActionBar.upCountView(selection.size, visibleBooks.size)"))
    }

    @Test
    fun scrollPositionIsSavedAndRestored() {
        // 交接文档 §8-64：View 侧 RecyclerView 自带布局态保存 ⇒ 换 Compose 后必须由宿主显式补
        val s = src()
        assertTrue("须保存首项下标", s.contains("KEY_SCROLL_INDEX"))
        assertTrue("须保存首项偏移", s.contains("KEY_SCROLL_OFFSET"))
        assertTrue("须重写 onSaveInstanceState", s.contains("override fun onSaveInstanceState("))
        assertTrue("恢复须等数据到达（否则被钳到 0）", s.contains("listState.scrollToItem(index, pendingScrollOffset)"))
    }

    @Test
    fun dragModeStateDrivesHandleVisibility() {
        val s = src()
        assertTrue("排序模式须由 bookshelfSort==3 驱动", s.contains("dragModeState = bookSort == 3"))
        assertTrue("初值同样驱动", s.contains("dragModeState = AppConfig.bookshelfSort == 3"))
    }
}