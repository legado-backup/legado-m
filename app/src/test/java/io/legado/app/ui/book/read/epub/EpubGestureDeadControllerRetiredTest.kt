package io.legado.app.ui.book.read.epub

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 批 8：EPUB 手势控制器「被取代整类」退役守护。
 *
 * 退役项：`EpubGestureController`（触摸解析器本体，**全仓零实例化**）+ 其 `Listener.onSwipe`
 * （零覆写、控制器从不调用）。
 * 同语义活替代：`EpubReadView.onTouchEvent` 自身承担触摸解析（拖动/点击分支）；滑动增量回调名义
 * 由控制器的 `onDrag` 承担 ⇒ `onSwipe` 无接收方。
 *
 * 保留项：仅回调契约仍在服役（`EpubReadView.Listener` 继承 / `ReadBookActivity` 覆写）⇒
 * 平移为顶层 `EpubGestureListener`，成员语义不变（见下方行为断言）。
 */
class EpubGestureDeadControllerRetiredTest {

    @Test
    fun `平移后的九宫格动作分发语义不变`() {
        val calls = mutableListOf<String>()
        val listener = object : EpubGestureListener {
            override fun onCenterTap(x: Float, y: Float) {
                calls += "center"
            }

            override fun onPreviousPage() {
                calls += "prev"
            }

            override fun onNextPage() {
                calls += "next"
            }
        }
        listener.onTapAction(0, 1f, 2f)
        listener.onTapAction(1, 1f, 2f)
        listener.onTapAction(2, 1f, 2f)
        listener.onTapAction(-1, 1f, 2f)
        listener.onTapAction(9, 1f, 2f)
        assertEquals(
            "0=中央 / 1=下一页 / 2=上一页 / -1=忽略 / 其余回落中央",
            listOf("center", "next", "prev", "center"),
            calls
        )
    }

    @Test
    fun `零实例化触摸控制器已退役且回调契约仍被继承`() {
        val viewSrc = SourceFileProbe.sourceText("ui/book/read/epub/EpubReadView.kt")
        assertEquals("退役项不得回潮（类引用）", false, viewSrc.contains("EpubGestureController"))
        assertTrue(
            "回调契约须以顶层接口被继承",
            viewSrc.contains("interface Listener : EpubGestureListener")
        )
        assertTrue(
            "九宫格动作入口必须保留（EpubReadView 调用 listener.onTapAction）",
            viewSrc.contains("listener.onTapAction(")
        )
    }

    @Test
    fun `平移后的回调契约不含死成员onSwipe`() {
        val listenerSrc = SourceFileProbe.sourceText("ui/book/read/epub/EpubGestureListener.kt")
        assertEquals("零覆写零调用的 onSwipe 不得回潮", false, listenerSrc.contains("onSwipe"))
        assertTrue("单击回调必须保留", listenerSrc.contains("fun onPageClick("))
        assertTrue("九宫格动作入口必须保留", listenerSrc.contains("fun onTapAction("))
        assertTrue("翻页回调必须保留", listenerSrc.contains("fun onNextPage()"))
        assertTrue("翻页回调必须保留", listenerSrc.contains("fun onPreviousPage()"))
        assertTrue("中央点击回调必须保留", listenerSrc.contains("fun onCenterTap("))
    }
}
