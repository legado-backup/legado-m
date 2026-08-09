package io.legado.app.utils

import io.legado.app.help.HighlightStyle
import io.legado.app.utils.CssStyleParser.toHighlightStyle
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * B15 高亮捕获组样式单元测试
 * 验证 CssStyleParser 的 CSS 解析 / HTML 标签解析 / 颜色解析 / 捕获组样式提取
 *
 * 验证点：
 * - parseColor：#RGB/#RRGGBB/#AARRGGBB/颜色名/非法值
 * - parseStyle：CSS 属性解析（bold/italic/underline/color/font-size/font-family）
 * - parseHtmlStyle：HTML 标签解析（b/i/u/font/span）
 * - extractGroupStyles：模板中 $N 组样式映射（含默认样式）
 * - toHighlightStyle：CSS → 项目 HighlightStyle 通道映射
 */
class CssStyleParserTest {

    @Test
    fun parseColor_hexShort_alpha255() {
        assertEquals("短六进制 #F00 → 0xFFFF0000", 0xFFFF0000.toInt(), CssStyleParser.parseColor("#F00"))
    }

    @Test
    fun parseColor_hex6_alpha255() {
        assertEquals("#FF0000 → 0xFFFF0000", 0xFFFF0000.toInt(), CssStyleParser.parseColor("#FF0000"))
    }

    @Test
    fun parseColor_hex8_keepsAlpha() {
        assertEquals("#80FF0000 → 0x80FF0000", 0x80FF0000.toInt(), CssStyleParser.parseColor("#80FF0000"))
    }

    @Test
    fun parseColor_namedColors() {
        assertEquals("red", 0xFFFF0000.toInt(), CssStyleParser.parseColor("red"))
        assertEquals("blue", 0xFF0000FF.toInt(), CssStyleParser.parseColor("blue"))
        assertEquals("green", 0xFF008000.toInt(), CssStyleParser.parseColor("green"))
        assertEquals("gold", 0xFFFFD700.toInt(), CssStyleParser.parseColor("gold"))
    }

    @Test
    fun parseColor_invalid_returnsNull() {
        assertNull("非法颜色返回 null", CssStyleParser.parseColor("not-a-color"))
        assertNull("未知颜色返回 null", CssStyleParser.parseColor("verydarkred"))
        assertNull("空串返回 null", CssStyleParser.parseColor(""))
    }

    @Test
    fun parseStyle_boldAndColor() {
        val style = CssStyleParser.parseStyle("font-weight:bold; color:red;")
        assertTrue("bold 生效", style.isBold)
        assertEquals("color=red", 0xFFFF0000.toInt(), style.color)
    }

    @Test
    fun parseStyle_fontWeightNumber() {
        assertTrue("font-weight:700 视为 bold", CssStyleParser.parseStyle("font-weight:700").isBold)
        assertFalse("font-weight:400 非 bold", CssStyleParser.parseStyle("font-weight:400").isBold)
    }

    @Test
    fun parseStyle_italicUnderlineFontSize() {
        val style = CssStyleParser.parseStyle("font-style:italic; text-decoration:underline; font-size:16sp;")
        assertTrue(style.isItalic)
        assertTrue(style.isUnderline)
        assertEquals("font-size:16sp → 16f", 16f, style.fontSizeSp ?: 0f, 0f)
    }

    @Test
    fun parseStyle_empty_returnsEmptyStyle() {
        val style = CssStyleParser.parseStyle("")
        assertFalse("空样式 hasStyle=false", style.hasStyle())
    }

    @Test
    fun parseHtmlStyle_tags() {
        val style = CssStyleParser.parseHtmlStyle("<b><font color=\"red\">")
        assertTrue("b 标签 → bold", style.isBold)
        assertEquals("font color=red", 0xFFFF0000.toInt(), style.color)
    }

    @Test
    fun parseHtmlStyle_spanStyle() {
        val style = CssStyleParser.parseHtmlStyle("""<span style="font-size:12sp; font-weight:bold">""")
        assertTrue("span 内 bold", style.isBold)
        assertEquals("span 内 font-size", 12f, style.fontSizeSp ?: 0f, 0f)
    }

    @Test
    fun parseHtmlStyle_italicUnderline() {
        val style = CssStyleParser.parseHtmlStyle("<i><u>")
        assertTrue(style.isItalic)
        assertTrue(style.isUnderline)
    }

    @Test
    fun extractGroupStyles_withTags() {
        val map = CssStyleParser.extractGroupStyles("<b><font color=\"red\">$1</font></b><i>$2</i>")
        assertEquals("应提取 2 组", 2, map.size)
        val g1 = map[1]
        assertNotNull("组1存在", g1)
        assertTrue("组1 bold", g1!!.isBold)
        assertEquals("组1 color=red", 0xFFFF0000.toInt(), g1.color)
        val g2 = map[2]
        assertNotNull("组2存在", g2)
        assertTrue("组2 italic", g2!!.isItalic)
    }

    @Test
    fun extractGroupStyles_plainGroup_defaultStyle() {
        val map = CssStyleParser.extractGroupStyles("\$1-\$2")
        assertEquals("裸 \$N 组提取", 2, map.size)
        assertFalse("裸组默认样式 hasStyle=false", map[1]!!.hasStyle())
        assertFalse(map[2]!!.hasStyle())
    }

    @Test
    fun extractGroupStyles_lruCacheReturnsSame() {
        val template = "<b>$1</b>"
        val first = CssStyleParser.extractGroupStyles(template)
        val second = CssStyleParser.extractGroupStyles(template)
        assertTrue("LRU 缓存命中应返回同一实例", first === second)
    }

    @Test
    fun toHighlightStyle_mapsChannels() {
        val css = CssStyleParser.CssStyle(isBold = true, color = 0xFFFF0000.toInt())
        val hs = css.toHighlightStyle()
        assertTrue("bold → bold", hs.bold)
        assertEquals("color → textColor", 0xFFFF0000.toInt(), hs.textColor)
        assertEquals("underline 未设置 → null", null, hs.underline)
        assertTrue("非空样式", !hs.isEmpty)
    }

    @Test
    fun toHighlightStyle_underlineMapsKind() {
        val css = CssStyleParser.CssStyle(isUnderline = true)
        val hs = css.toHighlightStyle()
        assertEquals("underline → SOLID", HighlightStyle.Kind.SOLID, hs.underline?.kind)
    }
}
