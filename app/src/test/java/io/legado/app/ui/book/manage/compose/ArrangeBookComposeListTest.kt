package io.legado.app.ui.book.manage.compose

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * `ArrangeBookList`（CF 6.2 `item_arrange_book` 换装）结构不变量：交互等价项逐条钉死。
 *
 * 为什么必须钉：本页换装把 View 侧三条能力链（`ItemTouchHelper` 拖拽换序 / `DragSelectTouchHelper` 滑选 /
 * `ItemTouchCallback` 落库）整体搬到 Compose ⇒ **任一环漏搬都是「功能静默消失」**（用户可感且难发现）。
 */
class ArrangeBookComposeListTest {

    private val rel = "ui/book/manage/compose/ArrangeBookComposeList.kt"

    private fun code(): String = SourceFileProbe.rawText(rel)
        .replace(Regex("/\\*[\\s\\S]*?\\*/"), "")
        .lines()
        .filterNot { it.trimStart().startsWith("//") }
        .joinToString("\n")

    @Test
    fun listUsesComposeContainers() {
        val c = code()
        assertTrue("须用 LazyColumn", c.contains("LazyColumn("))
        assertTrue("条目须带稳定 key（换序/复用不串行）", c.contains("key = { _, book -> book.bookUrl }"))
    }

    @Test
    fun dragReorderKeepsOriginalOrderRule() {
        // 原 `BookAdapter.swap`：两侧 order 相同 ⇒ 整体重排 1..n；否则只互换这两本的 order（**逐字保留**）
        val c = code()
        assertTrue("须接入 reorderable", c.contains("rememberReorderableLazyListState("))
        assertTrue("须有拖拽手柄槽", c.contains("draggableHandle("))
        assertTrue("两侧 order 相同的整体重排分支须保留", c.contains("if (src.order == target.order)"))
        assertTrue("须整体重排 1..n", c.contains("book.order = index + 1"))
        assertTrue("须互换这两本的 order", c.contains("src.order = target.order"))
        assertTrue("拖拽结束须回传结果供宿主落库", c.contains("onOrderCommitted(localBooks)"))
        // 对齐原 `BookAdapter.onClearView` 的 `isMoved` 守卫：未真正移动不写库
        assertTrue("未移动不得落库（isMoved 守卫）", c.contains("if (dragging) {"))
    }

    @Test
    fun slideSelectIsPreserved() {
        val c = code()
        assertTrue("须保留长按拖动滑选", c.contains("detectDragGesturesAfterLongPress"))
        assertTrue("滑选须逐项切换", c.contains("onToggleSelect"))
    }

    @Test
    fun rowKeepsOriginalAffordances() {
        val c = code()
        listOf(
            "Checkbox(",
            "colorResource(R.color.primaryText)",
            "colorResource(R.color.tv_text_summary)",
            "stringResource(R.string.local_book)",
            "stringResource(R.string.group)",
            "stringResource(R.string.delete)",
            "stringResource(R.string.drag_handle)"
        ).forEach { marker ->
            assertTrue("行内元素缺失（用户可感）：$marker", c.contains(marker))
        }
        assertTrue("点标题开详情须受开关控制", c.contains("enabled = openBookInfoByClickTitle"))
        assertFalse("不得出现硬编码色", Regex("Color\\(0x").containsMatchIn(c))
    }
}