package io.legado.app.ui.book.read.page

import io.legado.app.help.HighlightStyle
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B5 · R25·5.3.4 「缩进渲染纯函数」配对测试。
 *
 * 被测：[HighlightDraw.shouldRenderOnIndentColumn]（段首缩进列是否允许渲染该高亮样式）。
 * 为什么必须守：段首缩进列是**空白列**，装饰类高亮若覆盖它会露馅
 * （方框把段首空白一起框住、下划线从缩进处起画）；而纯色背景填充若跳过缩进列，
 * 整段底色会出现明显缺口。两类语义相反，靠一个布尔判定分流 ⇒ 判定反转即为可视缺陷。
 */
class HighlightDrawIndentColumnTest {

    @Test
    fun nullStyle_notRendered() {
        assertFalse("无样式不得渲染", HighlightDraw.shouldRenderOnIndentColumn(null))
    }

    @Test
    fun underline_skipsIndentColumn() {
        assertFalse(
            "下划线属装饰类，不得覆盖缩进列",
            HighlightDraw.shouldRenderOnIndentColumn(
                HighlightStyle(underline = HighlightStyle.Underline())
            )
        )
    }

    @Test
    fun strike_skipsIndentColumn() {
        assertFalse(
            "删除线属装饰类，不得覆盖缩进列",
            HighlightDraw.shouldRenderOnIndentColumn(
                HighlightStyle(strike = HighlightStyle.Deco(color = 0xFF000000.toInt()))
            )
        )
    }

    @Test
    fun box_skipsIndentColumn() {
        assertFalse(
            "方框属装饰类，不得覆盖缩进列",
            HighlightDraw.shouldRenderOnIndentColumn(
                HighlightStyle(box = HighlightStyle.Deco(color = 0xFF000000.toInt()))
            )
        )
    }

    @Test
    fun emphasis_skipsIndentColumn() {
        assertFalse(
            "着重号属装饰类，不得覆盖缩进列",
            HighlightDraw.shouldRenderOnIndentColumn(
                HighlightStyle(emphasis = HighlightStyle.Deco(color = 0xFF000000.toInt()))
            )
        )
    }

    @Test
    fun plainFill_rendersOnIndentColumn() {
        assertTrue(
            "纯色矩形填充必须铺满缩进列（否则整段底色缺口）",
            HighlightDraw.shouldRenderOnIndentColumn(HighlightStyle(fill = 0x66FFEB3B))
        )
    }

    @Test
    fun explicitRectangleFill_rendersOnIndentColumn() {
        assertTrue(
            "显式 RECTANGLE 与未设置等价，必须铺满缩进列",
            HighlightDraw.shouldRenderOnIndentColumn(
                HighlightStyle(
                    fill = 0x66FFEB3B,
                    fillShape = HighlightStyle.FillShape.RECTANGLE
                )
            )
        )
    }

    @Test
    fun nonRectFill_skipsIndentColumn() {
        // R1a：非矩形填充（胶囊/马克笔/半高/基线）形状边界语义不含段首空白，
        // 覆盖缩进列会出现「形状悬空在缩进处」的错位
        HighlightStyle.FillShape.entries
            .filter { it != HighlightStyle.FillShape.RECTANGLE }
            .forEach { shape ->
                assertFalse(
                    "非矩形填充形状 $shape 不得覆盖缩进列",
                    HighlightDraw.shouldRenderOnIndentColumn(
                        HighlightStyle(fill = 0x66FFEB3B, fillShape = shape)
                    )
                )
            }
    }

    @Test
    fun decorationPlusNonRectFill_stillSkipsIndentColumn() {
        assertFalse(
            "装饰 + 非矩形填充叠加时仍不得覆盖缩进列",
            HighlightDraw.shouldRenderOnIndentColumn(
                HighlightStyle(
                    fill = 0x66FFEB3B,
                    fillShape = HighlightStyle.FillShape.PILL,
                    underline = HighlightStyle.Underline()
                )
            )
        )
    }

    @Test
    fun textColorOnly_stillRendersOnIndentColumn() {
        // 字色不属装饰类、也无填充形状 ⇒ 判定为「可渲染」（缩进列本身是空白，字色实际不产生像素，
        // 但语义上不得与装饰类同流合污：判定只认「装饰」与「非矩形填充」两个减项）
        assertTrue(
            "仅字色不属装饰类，判定应为可渲染",
            HighlightDraw.shouldRenderOnIndentColumn(
                HighlightStyle(textColor = 0xFFD32F2F.toInt())
            )
        )
    }
}
