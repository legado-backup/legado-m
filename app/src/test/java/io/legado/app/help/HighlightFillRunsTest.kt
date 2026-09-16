package io.legado.app.help

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * R1a 填充 run 合并判定单元测试（纯函数，无 Android 依赖）。
 *
 * 验证点：同色同形状可合并；颜色或形状任一不同即断 run；任一侧无填充或空样式亦断 run；
 * 其它通道（字色/加粗/下划线/阴影）差异**不影响**填充合并。
 */
class HighlightFillRunsTest {

    private val yellow = 0x66FFEB3B.toInt()

    @Test
    fun sameColorAndShape_merge() {
        assertTrue(
            "同色同形状应合并",
            HighlightFillRuns.sameFillRun(HighlightStyle(fill = yellow), HighlightStyle(fill = yellow))
        )
    }

    @Test
    fun differentColor_break() {
        assertFalse(
            "颜色不同应断 run",
            HighlightFillRuns.sameFillRun(
                HighlightStyle(fill = yellow),
                HighlightStyle(fill = 0x6600FF00.toInt())
            )
        )
    }

    @Test
    fun differentShape_break() {
        assertFalse(
            "形状不同应断 run",
            HighlightFillRuns.sameFillRun(
                HighlightStyle(fill = yellow, fillShape = HighlightStyle.FillShape.PILL),
                HighlightStyle(fill = yellow, fillShape = HighlightStyle.FillShape.MARKER)
            )
        )
    }

    @Test
    fun explicitRectangle_equalsUnset() {
        assertTrue(
            "显式矩形与未设置等价（均解析为 RECTANGLE）",
            HighlightFillRuns.sameFillRun(
                HighlightStyle(fill = yellow),
                HighlightStyle(fill = yellow, fillShape = HighlightStyle.FillShape.RECTANGLE)
            )
        )
    }

    @Test
    fun noFill_break() {
        val noFill = HighlightStyle()
        assertFalse("任一侧无填充应断 run", HighlightFillRuns.sameFillRun(noFill, HighlightStyle(fill = yellow)))
        assertFalse("任一侧无填充应断 run", HighlightFillRuns.sameFillRun(HighlightStyle(fill = yellow), noFill))
    }

    @Test
    fun nullStyle_break() {
        assertFalse("空样式应断 run", HighlightFillRuns.sameFillRun(null, HighlightStyle(fill = yellow)))
        assertFalse("空样式应断 run", HighlightFillRuns.sameFillRun(HighlightStyle(fill = yellow), null))
    }

    @Test
    fun otherChannelsIgnored() {
        val a = HighlightStyle(fill = yellow)
        val b = HighlightStyle(
            fill = yellow,
            textColor = 0xFF000000.toInt(),
            bold = true,
            underline = HighlightStyle.Underline(),
            shadow = HighlightStyle.Shadow(radius = 4f)
        )
        assertTrue("其它通道差异不影响填充合并", HighlightFillRuns.sameFillRun(a, b))
    }
}