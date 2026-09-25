package io.legado.app.ui.widget.anima

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CE-b：`RotateLoading` 新增**程序化笔宽入口**的结构不变量（配对测试，JVM 可跑）。
 *
 * 背景：该类的笔宽基准 `thisWidth` 原先**只有 XML 一条入口**（`app:loading_width`，默认
 * `DEFAULT_WIDTH`=6dp）。透明壳页（`activity_translucence`）改为程序化构造后，XML 属性消失
 * ⇒ 笔宽会从 2dp 静默变成 6dp（视觉不等价）。因此新增 `setLoadingWidthDp(widthDp)`，
 * 并把「按当前笔宽重算两个绘制矩形」抽成 `refreshRects(w, h)` 单源。
 *
 * 本测试锁死四类事实：
 *  ①`setLoadingWidthDp` 是公开等价入口，且只改笔宽/重算矩形，不碰颜色与动画状态；
 *  ②矩形重算走 `refreshRects` 单源（`onSizeChanged` 与新增入口共用，不允许各写一份）；
 *  ③笔宽与 `Paint.strokeWidth` 保持同步（两处赋值都是 `thisWidth.toFloat()`）；
 *  ④既有 XML 属性通道与默认值未被破坏（`LoadMoreView` / `ExploreAdapter` 等仍走 XML）。
 */
class RotateLoadingWidthTest {

    private val rel = "ui/widget/anima/RotateLoading.kt"

    private fun src(): String = SourceFileProbe.sourceText(rel)

    @Test
    fun programmaticWidthEntryIsPublicAndGeometryOnly() {
        val s = src()
        assertTrue(
            "必须提供公开的程序化笔宽入口（透明壳页无 XML 属性通道）",
            s.contains("fun setLoadingWidthDp(widthDp: Int) {")
        )
        assertFalse("入口不得降级为 private", s.contains("private fun setLoadingWidthDp"))
        assertTrue("入口必须落到 thisWidth", s.contains("thisWidth = widthDp.dpToPx()"))
        assertTrue("入口必须同步 Paint 笔宽", s.contains("mPaint.strokeWidth = thisWidth.toFloat()"))
        assertTrue("入口必须重算绘制矩形", s.contains("refreshRects(width, height)"))
        assertTrue("入口必须触发重绘", s.contains("invalidate()"))
    }

    @Test
    fun rectsRecomputedThroughSingleSource() {
        val s = src()
        assertTrue(
            "矩形重算必须抽成单源函数",
            s.contains("private fun refreshRects(w: Int, h: Int)")
        )
        assertTrue("尺寸变化路径必须复用单源", s.contains("refreshRects(w, h)"))
        assertTrue("程序化笔宽路径必须复用单源", s.contains("refreshRects(width, height)"))
    }

    @Test
    fun widthAndStrokeStayInSync() {
        val s = src()
        assertEquals(
            "笔宽与 Paint 笔宽必须两处同步（构造函数 + 程序化入口）",
            2,
            Regex("""mPaint\.strokeWidth = thisWidth\.toFloat\(\)""").findAll(s).count()
        )
        // 入口内部顺序：先落 thisWidth → 再同步笔宽 → 最后重算矩形（错序会让矩形按旧笔宽算）
        val iWidth = s.indexOf("thisWidth = widthDp.dpToPx()")
        val iStroke = s.indexOf("mPaint.strokeWidth = thisWidth.toFloat()", iWidth)
        val iRects = s.indexOf("refreshRects(width, height)", iWidth)
        assertTrue("`setLoadingWidthDp` 内部顺序被破坏：$iWidth / $iStroke / $iRects", iWidth in 1 until iStroke && iStroke < iRects)
    }

    @Test
    fun xmlAttributeChannelAndDefaultPreserved() {
        val s = src()
        assertTrue(
            "既有 XML 属性通道不得被删（LoadMoreView / ExploreAdapter 仍走 XML）",
            s.contains("R.styleable.RotateLoading_loading_width")
        )
        assertTrue("类默认笔宽必须保持 6dp（未显式设定时口径不变）", s.contains("DEFAULT_WIDTH = 6"))
        assertTrue(
            "XML 未指定 loading_width 时必须回落默认值",
            Regex(
                """R\.styleable\.RotateLoading_loading_width,\s+DEFAULT_WIDTH\.dpToPx\(\)"""
            ).containsMatchIn(s)
        )
    }
}