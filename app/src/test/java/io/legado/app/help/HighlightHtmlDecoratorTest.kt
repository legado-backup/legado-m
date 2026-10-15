package io.legado.app.help

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 模板模式高亮装饰（R7 接线）配对单测。
 *
 * 为什么必须单测这层：模板模式的高亮发生在**生成正文 HTML** 的时刻（不像 canvas 路径有逐列绘制的
 * 兜底），任何偏移/切分/样式映射的差错都会表现为"正文里多出奇怪的 span"或"高亮完全看不到"，
 * 且都在跨源沙箱内，真机上极难定位。此处逐条钉住：原样返回语义、切分正确性、排除集、
 * 色板三态解析、以及"整段命中落段元素"这一优化不得破坏文本内容。
 */
class HighlightHtmlDecoratorTest {

    private fun rule(
        id: String = "r1",
        pattern: String,
        isRegex: Boolean = false,
        style: HighlightStyle = HighlightStyle(fill = 0x80FFFF00.toInt()),
        targetScope: Int = HighlightRuleMatcher.SCOPE_ALL
    ) = HighlightRuleMatcher.Rule(
        id = id, pattern = pattern, isRegex = isRegex, style = style, targetScope = targetScope
    )

    @Test
    fun `无规则时原样返回且不匹配`() {
        val html = "<p>甲乙丙</p>"
        val result = HighlightHtmlDecorator.decorate(html, emptyList(), HighlightPalette.Tone.DAY)
        assertSame("无规则必须零成本原样返回（不发 jsoup）", html, result.html)
        assertEquals(0, result.matchedRules)
    }

    @Test
    fun `无命中时原样返回`() {
        val html = "<p>甲乙丙</p>"
        val result = HighlightHtmlDecorator.decorate(
            html, listOf(rule(pattern = "丁丁")), HighlightPalette.Tone.DAY
        )
        assertSame("无命中必须原样返回", html, result.html)
        assertEquals(0, result.matchedRules)
    }

    @Test
    fun `部分命中包成带内联样式的 span`() {
        val result = HighlightHtmlDecorator.decorate(
            "<p>前甲乙后</p>",
            listOf(rule(pattern = "甲乙", style = HighlightStyle(fill = 0x80FFFF00.toInt()))),
            HighlightPalette.Tone.DAY
        )
        assertEquals(1, result.matchedRules)
        assertTrue("命中段必须包成 span", result.html.contains("<span"))
        assertTrue("必须带内联样式（沙箱内不注入额外样式表）", result.html.contains("style=\""))
        assertTrue("填充色须为 CSS 8 位十六进制", result.html.contains("background-color:#FFFF0080"))
        assertTrue("未命中部分必须原样保留", result.html.contains("前"))
        assertTrue("未命中部分必须原样保留", result.html.contains("后"))
    }

    @Test
    fun `整段命中直接落段元素（背景覆盖整行宽）`() {
        val result = HighlightHtmlDecorator.decorate(
            "<p>甲乙丙丁</p>",
            listOf(rule(pattern = "甲乙丙丁", style = HighlightStyle(fill = 0x80FFFF00.toInt()))),
            HighlightPalette.Tone.DAY
        )
        assertEquals(1, result.matchedRules)
        assertFalse("整段命中不该再包 span（逐字符包裹会产生缝隙）", result.html.contains("<span"))
        assertTrue("样式须落在段元素上", result.html.contains("<p style=\""))
        assertFalse("段内文本不得丢字", result.html.contains("�"))
    }

    @Test
    fun `跨内联元素的命中只包裹命中片段且保留内联标记`() {
        val result = HighlightHtmlDecorator.decorate(
            "<p>前缀<em>命中</em>后缀</p>",
            listOf(rule(pattern = "命中", style = HighlightStyle(bold = true))),
            HighlightPalette.Tone.DAY
        )
        assertEquals(1, result.matchedRules)
        assertTrue("内联标记必须保留", result.html.contains("<em"))
        assertTrue("命中片段须在 span 内", Regex("<span[^>]*><em>命中</em></span>").containsMatchIn(result.html))
        assertTrue("加粗须映射为 font-weight", result.html.contains("font-weight:700"))
        assertTrue("前缀须保留且不在 span 内", result.html.startsWith("<p>前缀<span"))
    }

    @Test
    fun `排除集元素内文本不参与匹配也不被包裹`() {
        val html = "<p>正文</p><script>var 正文=1</script><style>.正文{}</style><p>正文</p>"
        val result = HighlightHtmlDecorator.decorate(
            html, listOf(rule(pattern = "正文", style = HighlightStyle(bold = true))),
            HighlightPalette.Tone.DAY
        )
        // 两个 p 都是命中 ⇒ 命中规则数 1；但 script/style 内的同名文本不得被包 span
        assertEquals(1, result.matchedRules)
        val scriptPart = result.html.substringAfter("<script>").substringBefore("</script>")
        assertFalse("script 内文本不得被高亮包裹", scriptPart.contains("<span"))
        assertTrue("script 内文本必须原样保留", scriptPart.contains("正文"))
    }

    @Test
    fun `text-ignore 元素内文本不参与匹配`() {
        val html = "<div data-reader-text-ignore>题签正文</div><p>正文</p>"
        val result = HighlightHtmlDecorator.decorate(
            html, listOf(rule(pattern = "正文", style = HighlightStyle(bold = true))),
            HighlightPalette.Tone.DAY
        )
        assertEquals(1, result.matchedRules)
        val ignorePart = result.html.substringAfter(">").substringBefore("</div>")
        assertFalse("装饰题签内文本不得被高亮", ignorePart.contains("font-weight"))
        // 正文段是**整段命中** ⇒ 走"样式落段元素"分支（不再包 span），故按装饰事实断言
        assertTrue("正文段须被装饰", result.html.contains("font-weight:700"))
        assertTrue("题签文本必须原样保留（不得被剔除）", ignorePart.contains("题签正文"))
    }

    @Test
    fun `色板派生样式按阅读器三态解析`() {
        val style = HighlightStyle(textColor = 0xFF000000.toInt(), paletteSlot = HighlightPalette.Slot.EMPHASIS)
        val day = HighlightHtmlDecorator.decorate(
            "<p>重点</p>", listOf(rule(pattern = "重点", style = style)), HighlightPalette.Tone.DAY
        )
        val eink = HighlightHtmlDecorator.decorate(
            "<p>重点</p>", listOf(rule(pattern = "重点", style = style)), HighlightPalette.Tone.EINK
        )
        assertTrue("日间须解析为槽位浅底色", day.html.contains("color:${colorCss(HighlightPalette.color(HighlightPalette.Slot.EMPHASIS, HighlightPalette.Tone.DAY))}"))
        assertTrue("水墨屏须解析为纯黑（不依赖色相）", eink.html.contains("color:#000000FF"))
        assertFalse("两态颜色必须不同", day.html.contains("color:#000000FF"))
    }

    @Test
    fun `填充形状与下划线线型映射到 CSS`() {
        val rounded = HighlightHtmlDecorator.decorate(
            "<p>甲乙</p>",
            listOf(rule(pattern = "甲乙", style = HighlightStyle(fill = 0x80FF0000.toInt(), fillShape = HighlightStyle.FillShape.ROUNDED))),
            HighlightPalette.Tone.DAY
        )
        assertTrue("圆角填充须映射 border-radius", rounded.html.contains("border-radius"))

        val marker = HighlightHtmlDecorator.decorate(
            "<p>甲乙</p>",
            listOf(rule(pattern = "甲乙", style = HighlightStyle(fill = 0x80FF0000.toInt(), fillShape = HighlightStyle.FillShape.MARKER))),
            HighlightPalette.Tone.DAY
        )
        assertTrue("底色条须用渐变只画下缘", marker.html.contains("linear-gradient"))

        val wavy = HighlightHtmlDecorator.decorate(
            "<p>甲乙</p>",
            listOf(rule(pattern = "甲乙", style = HighlightStyle(underline = HighlightStyle.Underline(kind = HighlightStyle.Kind.WAVY)))),
            HighlightPalette.Tone.DAY
        )
        assertTrue("波浪下划线须映射 text-decoration-style", wavy.html.contains("text-decoration-style:wavy"))
        assertTrue("线型须映射到下划线通道", wavy.html.contains("text-decoration-line:underline"))
    }

    @Test
    fun `标题作用域只命中的标题而非正文`() {
        val titleOnly = rule(pattern = "甲", targetScope = HighlightRuleMatcher.SCOPE_TITLE)
        val result = HighlightHtmlDecorator.decorate(
            "<h2>甲章</h2><p>甲段</p>", listOf(titleOnly), HighlightPalette.Tone.DAY
        )
        assertEquals(1, result.matchedRules)
        val h2 = result.html.substringAfter("<h2").substringBefore("</h2>")
        val p = result.html.substringAfter("<p").substringBefore("</p>")
        assertTrue("标题须被高亮", h2.contains("<span"))
        assertFalse("正文不得被标题作用域规则高亮", p.contains("<span"))
    }

    @Test
    fun `正则命中与 DOTALL 生效`() {
        val result = HighlightHtmlDecorator.decorate(
            "<p>数值 123 与 456</p>",
            listOf(rule(pattern = "\\d+", isRegex = true, style = HighlightStyle(bold = true))),
            HighlightPalette.Tone.DAY
        )
        assertEquals(1, result.matchedRules)
        assertEquals("两处数字都须被包裹", 2, Regex("<span").findAll(result.html).count())
    }

    // === HL-3：手动划线进模板正文（按文本定位，不用 canvas 偏移硬套） ===

    @Test
    fun `手动划线按文本定位并包成 span`() {
        val result = HighlightHtmlDecorator.decorate(
            "<p>第一句。</p><p>第二句带重点。</p>",
            emptyList(),
            HighlightPalette.Tone.DAY,
            manual = listOf(
                HighlightHtmlDecorator.ManualHighlight(
                    text = "带重点", start = 0, end = 3, style = HighlightStyle(fill = 0x66FFEB3B.toInt())
                )
            )
        )
        assertEquals("手动划线不应计入规则命中数", 0, result.matchedRules)
        assertEquals("须记录 1 条手动划线已装饰", 1, result.matchedManual)
        assertTrue("划线文字须被 span 包住", result.html.contains("<span"))
        assertTrue("须带上填充色", result.html.contains(colorCss(0x66FFEB3B.toInt())))
        assertFalse("未划线的句子不得被包", result.html.substringBefore("第二句").contains("<span"))
    }

    @Test
    fun `手动划线文本在章内找不到时跳过不误锚`() {
        val result = HighlightHtmlDecorator.decorate(
            "<p>甲乙丙</p>",
            emptyList(),
            HighlightPalette.Tone.DAY,
            manual = listOf(
                HighlightHtmlDecorator.ManualHighlight(
                    text = "完全不在正文里的句子", start = 0, end = 9,
                    style = HighlightStyle(fill = 0x66FFEB3B.toInt())
                )
            )
        )
        assertEquals("零命中必须原样返回（宁可不高亮也不画错位置）", 0, result.matchedManual)
        assertFalse(result.html.contains("<span"))
    }

    @Test
    fun `手动划线空文本或空样式一律跳过`() {
        val blankText = HighlightHtmlDecorator.decorate(
            "<p>甲乙丙</p>", emptyList(), HighlightPalette.Tone.DAY,
            manual = listOf(
                HighlightHtmlDecorator.ManualHighlight("", 0, 0, HighlightStyle(fill = 1))
            )
        )
        assertEquals(0, blankText.matchedManual)
        val emptyStyle = HighlightHtmlDecorator.decorate(
            "<p>甲乙丙</p>", emptyList(), HighlightPalette.Tone.DAY,
            manual = listOf(HighlightHtmlDecorator.ManualHighlight("甲乙", 0, 2, HighlightStyle()))
        )
        assertEquals("空样式等于无高亮，不必多包一层 span", 0, emptyStyle.matchedManual)
    }

    @Test
    fun `手动划线跨块时两段各自上色`() {
        // 跨块的划线被块边界切开：本用例两段都被整段覆盖 ⇒ 走"整段命中落段元素"优化
        // （样式挂在各段元素上而非包 span，背景因此铺满整行、也没有逐字符包裹的缝隙）
        val result = HighlightHtmlDecorator.decorate(
            "<p>前半句</p><p>后半句</p>",
            emptyList(),
            HighlightPalette.Tone.DAY,
            manual = listOf(
                HighlightHtmlDecorator.ManualHighlight(
                    text = "前半句后半句", start = 0, end = 6,
                    style = HighlightStyle(fill = 0x66FFEB3B.toInt())
                )
            )
        )
        assertEquals("划线命中数按划线条数计，不按被切开的段数计", 1, result.matchedManual)
        assertEquals(
            "两段都必须带上填充色",
            2,
            Regex(Regex.escape(colorCss(0x66FFEB3B.toInt()))).findAll(result.html).count()
        )
    }

    // === locateByText：空白无关定位（模板面与 canvas 文本口径不同，靠它对齐） ===

    @Test
    fun `locateByText 忽略空白差异并返回原文本区间`() {
        val chapter = "第一段\n\n　第二段正文"
        val range = HighlightHtmlDecorator.locateByText(chapter, "第二段 正文", 0)
        assertEquals("须定位到原文本坐标", chapter.indexOf("第二段"), range?.first)
        assertEquals("末字须落在原文本上", chapter.indexOf("正文") + 2, (range?.last ?: -1) + 1)
    }

    @Test
    fun `locateByText 重复文本择离提示最近的一处`() {
        val chapter = "甲方说着。乙方点头。甲方说着。"
        val first = HighlightHtmlDecorator.locateByText(chapter, "甲方说着", 0)
        val second = HighlightHtmlDecorator.locateByText(chapter, "甲方说着", chapter.lastIndexOf("甲方说着"))
        assertEquals("hint=0 取第一处", chapter.indexOf("甲方说着"), first?.first)
        assertEquals("hint 指第二处即取第二处", chapter.lastIndexOf("甲方说着"), second?.first)
    }

    @Test
    fun `locateByText 找不到或入参非法返回 null`() {
        assertNull(HighlightHtmlDecorator.locateByText("甲乙丙", "丁", 0))
        assertNull(HighlightHtmlDecorator.locateByText("", "甲", 0))
        assertNull(HighlightHtmlDecorator.locateByText("甲乙丙", "   ", 0))
        assertNull("needle 比全文还长时必须安全返回 null", HighlightHtmlDecorator.locateByText("甲", "甲乙丙丁", 0))
    }

    private fun colorCss(argb: Int): String = String.format(
        java.util.Locale.US, "#%02X%02X%02X%02X",
        (argb ushr 16) and 0xFF, (argb ushr 8) and 0xFF, argb and 0xFF, (argb ushr 24) and 0xFF
    )
}
