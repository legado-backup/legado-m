package io.legado.app.help

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * F-P1-2 高亮规则系统单元测试
 * 验证 HighlightStyle 的 merge 语义 + isEmpty + needsPerColumnDraw
 *
 * 验证点：
 * - merge 按通道 last-wins 叠加
 * - merge 布尔通道取或
 * - merge null base 返回 other
 * - isEmpty 全通道关闭时为 true
 * - needsPerColumnDraw 除纯背景填充外任何通道开启时为 true
 */
class HighlightStyleTest {

    @Test
    fun merge_lastWinsByChannel() {
        // 正常用例：merge 按通道 last-wins 叠加
        val base = HighlightStyle(fill = 0x80FFF176.toInt(), textColor = 0xFFFF0000.toInt())
        val other = HighlightStyle(textColor = 0xFF0000FF.toInt(), bold = true)
        val merged = HighlightStyle.merge(base, other)
        assertEquals("fill 保持 base", 0x80FFF176.toInt(), merged.fill)
        assertEquals("textColor 被 other 覆盖", 0xFF0000FF.toInt(), merged.textColor)
        assertTrue("bold 取或", merged.bold)
    }

    @Test
    fun merge_nullBaseReturnsOther() {
        // 边界用例：merge null base 返回 other
        val other = HighlightStyle(fill = 0x80FFF176.toInt(), bold = true)
        val merged = HighlightStyle.merge(null, other)
        assertEquals("fill 来自 other", other.fill, merged.fill)
        assertTrue("bold 来自 other", merged.bold)
    }

    @Test
    fun merge_booleanChannelsTakeOr() {
        // 正常用例：merge 布尔通道取或
        val base = HighlightStyle(bold = true, italic = false)
        val other = HighlightStyle(bold = false, italic = true)
        val merged = HighlightStyle.merge(base, other)
        assertTrue("bold 取或：true || false = true", merged.bold)
        assertTrue("italic 取或：false || true = true", merged.italic)
    }

    @Test
    fun isEmpty_allChannelsOff() {
        // 边界用例：全通道关闭时 isEmpty = true
        val empty = HighlightStyle()
        assertTrue("默认样式 isEmpty", empty.isEmpty)

        val nonEmpty = HighlightStyle(fill = 0x80FFF176.toInt())
        assertFalse("有 fill 不 isEmpty", nonEmpty.isEmpty)
    }

    @Test
    fun needsPerColumnDraw_anyNonFillChannel() {
        // 正常用例：除纯背景填充外任何通道开启时 needsPerColumnDraw = true
        val pureFill = HighlightStyle(fill = 0x80FFF176.toInt())
        assertFalse("仅 fill 不需要逐列绘制", pureFill.needsPerColumnDraw)

        val withText = HighlightStyle(fill = 0x80FFF176.toInt(), textColor = 0xFFFF0000.toInt())
        assertTrue("fill + textColor 需要逐列绘制", withText.needsPerColumnDraw)

        val withUnderline = HighlightStyle(underline = HighlightStyle.Underline())
        assertTrue("仅 underline 需要逐列绘制", withUnderline.needsPerColumnDraw)

        val withBold = HighlightStyle(bold = true)
        assertTrue("仅 bold 需要逐列绘制", withBold.needsPerColumnDraw)
    }
}
