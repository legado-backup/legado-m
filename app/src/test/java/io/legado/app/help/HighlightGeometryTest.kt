package io.legado.app.help

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R1a 形状填充几何单元测试（纯几何，无 Android 依赖）。
 *
 * 验证点：
 * - 矩形/圆角/胶囊铺满整行高（与改造前逐列矩形逐像素等价）
 * - 其余形状的填充带落在行内且非空
 * - 胶囊端部半径 = 填充带高的一半（降级口径）
 */
class HighlightGeometryTest {

    private val height = 60f
    private val baseline = 48f
    private val textSize = 36f

    @Test
    fun fillBand_rectLikeShapes_coverFullLine() {
        // 零回归：矩形/圆角/胶囊均铺满整行（top=0 / bottom=height）
        listOf(
            HighlightStyle.FillShape.RECTANGLE,
            HighlightStyle.FillShape.ROUNDED,
            HighlightStyle.FillShape.PILL
        ).forEach { shape ->
            val band = HighlightGeometry.fillBand(baseline, textSize, height, shape)
            assertEquals("$shape top", 0f, band.top, 0.001f)
            assertEquals("$shape bottom", height, band.bottom, 0.001f)
        }
    }

    @Test
    fun fillBand_otherShapes_withinLineAndNonEmpty() {
        listOf(
            HighlightStyle.FillShape.MARKER,
            HighlightStyle.FillShape.HALF,
            HighlightStyle.FillShape.BASELINE
        ).forEach { shape ->
            val band = HighlightGeometry.fillBand(baseline, textSize, height, shape)
            assertTrue("$shape top 不越上界", band.top >= 0f)
            assertTrue("$shape bottom 不越下界", band.bottom <= height)
            assertTrue("$shape 填充带非空", band.bottom > band.top)
        }
    }

    @Test
    fun fillBand_marker_isShorterThanLine() {
        val band = HighlightGeometry.fillBand(baseline, textSize, height, HighlightStyle.FillShape.MARKER)
        assertTrue("荧光笔高度小于行高", band.bottom - band.top < height)
    }

    @Test
    fun pillRadiusX_isHalfOfBandHeight() {
        val band = HighlightGeometry.fillBand(baseline, textSize, height, HighlightStyle.FillShape.PILL)
        assertEquals("胶囊端半径 = 带宽一半", (band.bottom - band.top) / 2f,
            HighlightGeometry.pillRadiusX(band), 0.001f)
    }

    @Test
    fun resolvedFillShape_defaultsToRectangle() {
        // 未设置形状 → 矩形（零回归）
        val style = HighlightStyle(fill = 0x80FFF176.toInt())
        assertEquals(HighlightStyle.FillShape.RECTANGLE, style.resolvedFillShape)
        assertTrue("矩形不算非矩形形状", !style.hasNonRectFillShape)
        assertTrue("显式设形状即非矩形",
            HighlightStyle(fill = 1, fillShape = HighlightStyle.FillShape.PILL).hasNonRectFillShape)
    }
}