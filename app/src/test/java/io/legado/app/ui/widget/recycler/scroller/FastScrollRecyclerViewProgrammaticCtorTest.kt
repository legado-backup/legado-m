package io.legado.app.ui.widget.recycler.scroller

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * `FastScrollRecyclerView(context)`**程序化构造**路径的结构不变量（JVM 可跑）。
 *
 * 背景（CE 5.2 全文搜索页实测崩溃，根因链条逐字可复现）：
 *   `FastScrollRecyclerView(context)` → `layout(context, null)` → `FastScroller(context, null)`
 *   → FastScroller 的 `(context, attrs, defStyleAttr)` 构造执行
 *   `layoutParams = generateLayoutParams(null)` → `LinearLayout.generateLayoutParams(null)`
 *   → `UnsupportedOperationException: You must supply a layout_width attribute.`
 *
 * 本仓此前**所有** `FastScrollRecyclerView` 都由 XML 膨胀（attrs 非空）⇒ 该路径从未被走到；
 * 直到 CE 5.2 把 `activity_search_content.xml` 退役、改为程序化装配才暴露。
 * 处置 = 让 `layout()` 在 `attrs == null` 时改走**无属性构造** `FastScroller(context)`
 * （该构造本就为程序化用途准备：自带 `layoutParams`，且 `layout(context, null)` 全程空安全）。
 *
 * 本测试锁死三件事，防回归（只写文档的约束一律失效）：
 *   ①null attrs 不得再交给 3 参构造（否则重复崩溃）
 *   ②attrs 非空（XML 路径）行为一字不变
 *   ③程序化构造的自身 `layoutParams` 口径不变
 */
class FastScrollRecyclerViewProgrammaticCtorTest {

    private val page = "ui/widget/recycler/scroller/FastScrollRecyclerView.kt"

    private fun src(): String = SourceFileProbe.sourceText(page)

    @Test
    fun nullAttrsGoThroughNoAttrConstructor() {
        val s = src()
        assertTrue(
            "attrs==null 必须改走无属性构造 FastScroller(context)（否则 generateLayoutParams(null) 崩）",
            s.contains("if (attrs == null) FastScroller(context) else FastScroller(context, attrs)")
        )
        assertFalse(
            "不得恢复成无条件 FastScroller(context, attrs)（程序化装配会再次抛 UnsupportedOperationException）",
            s.contains("mFastScroller = FastScroller(context, attrs)")
        )
    }

    @Test
    fun xmlPathUnchanged() {
        val s = src()
        // XML 膨胀（attrs 非空）仍走 3 参构造 ⇒ 布局属性解析口径不变
        assertTrue(
            "attrs 非空时仍须走 FastScroller(context, attrs)",
            s.contains("else FastScroller(context, attrs)")
        )
        assertTrue(
            "程序化构造的 1 参构造仍须自带 layoutParams（WRAP_CONTENT × MATCH_PARENT）",
            s.contains("layoutParams =\n            LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT)") ||
                s.contains("LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT)")
        )
    }

    @Test
    fun sectionIndexerWiringPreserved() {
        val s = src()
        // 换装不得顺手删能力：adapter 为 SectionIndexer 时必须继续挂到 fast scroller
        assertTrue("SectionIndexer 挂载链路不得丢失", s.contains("setSectionIndexer(adapter as FastScroller.SectionIndexer?)"))
        assertTrue("快速滚动条必须在 onAttachedToWindow 挂到父容器", s.contains("mFastScroller.setLayoutParams(parent)"))
        assertTrue("滚动条 id 单源不得改动", s.contains("R.id.fast_scroller"))
    }
}