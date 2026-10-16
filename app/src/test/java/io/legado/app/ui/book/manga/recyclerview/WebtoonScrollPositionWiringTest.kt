package io.legado.app.ui.book.manga.recyclerview

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test
import java.io.File

/**
 * 批 9 · D 档收口：`WebtoonRecyclerView.onScrolled` 的**硬 cast 崩溃面**退役护栏。
 *
 * 退役项：`layoutManager as LinearLayoutManager`（原 `:63`）—— 非 Linear 布局管理器下
 * `onScrolled` 每次滚动都抛 `ClassCastException`。
 * 活替代：`utils/RecyclerViewExtensions.findLastVisibleViewPosition()` /
 * `findFirstVisibleViewPosition()`（单源封装：非 Linear ⇒ `-1`，Linear ⇒ 取值与原实现逐字相同）。
 */
class WebtoonScrollPositionWiringTest {

    private fun src(): String =
        SourceFileProbe.sourceText("ui/book/manga/recyclerview/WebtoonRecyclerView.kt")

    @Test
    fun `硬 cast 已收口为单源封装`() {
        val s = src()
        assertEquals(
            "不得回潮硬 cast（非 Linear 布局管理器下必崩）",
            false,
            s.contains("layoutManager as LinearLayoutManager")
        )
        assertEquals(
            "末位可见项须走单源封装（非 Linear ⇒ -1，不崩）",
            true,
            s.contains("lastVisibleItemPosition = findLastVisibleViewPosition()")
        )
        assertEquals(
            "首位可见项须走单源封装",
            true,
            s.contains("firstVisibleItemPosition = findFirstVisibleViewPosition()")
        )
    }

    @Test
    fun `封装仍保留非 Linear 返回 -1 的契约`() {
        // 活替代者的契约本身也要锁：删掉 `is LinearLayoutManager` 分支会让「非 Linear 返回 -1」失效
        val util = SourceFileProbe.sourceText("utils/RecyclerViewExtensions.kt")
        assertEquals(
            "非 Linear 布局管理器必须返回 -1（-1 = 无可见项语义）",
            true,
            util.contains("if (layoutManager is LinearLayoutManager)")
        )
        assertEquals("封装不得改名为返回值语义以外的形态", true, util.contains("var pos = -1"))
    }

    @Test
    fun `WebtoonRecyclerView 仍自行装配布局管理器`() {
        // 与既有 ProgrammaticRecyclerViewLayoutManagerGuardTest 同源：程序化 RecyclerView 必须装配 LM
        val root: File = SourceFileProbe.mainJavaRoot()
        val f = File(root, "io/legado/app/ui/book/manga/recyclerview/WebtoonRecyclerView.kt")
        val creator = File(root, "io/legado/app/ui/book/manga/ReadMangaActivity.kt")
        assertEquals("WebtoonRecyclerView 文件必须存在", true, f.isFile)
        assertEquals("宿主须装配 layoutManager（见既有回归防线）", true, creator.isFile)
    }
}
