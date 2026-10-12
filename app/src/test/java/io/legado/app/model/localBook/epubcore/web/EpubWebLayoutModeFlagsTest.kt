package io.legado.app.model.localBook.epubcore.web

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 五态分流在 WebView 布局层的落实：开关推导 + 阅读器 CSS 构造（AD-06）。
 *
 * 关键断言：①默认（REFLOWABLE）行为与本版前一致（分栏 + 阅读器字体/颜色注入）；
 * ②保真模式不注入阅读器字体/颜色/行高，也不做正文容器去边距归一化；
 * ③单页模式不分栏且内容不溢出。
 */
class EpubWebLayoutModeFlagsTest {

    private fun request(
        preserve: Boolean = false,
        singlePage: Boolean = false,
        readerFontFamily: String? = null,
        readerFontUrl: String? = readerFontFamily?.let { "file:///fonts/a.ttf" },
        textFullJustify: Boolean = false
    ) = EpubWebLayoutRequest(
        chapterIndex = 0,
        chapterHref = "OEBPS/chapter1.xhtml",
        title = "第一章",
        html = "<html><body><p>hello</p></body></html>",
        viewportWidthPx = 1080,
        viewportHeightPx = 1920,
        fontSizePx = 18f,
        textColor = 0xFF102030.toInt(),
        lineHeightPx = 32f,
        readerFontFamily = readerFontFamily,
        readerFontUrl = readerFontUrl,
        textFullJustify = textFullJustify,
        preservePublisherLayout = preserve,
        singlePage = singlePage
    )

    @Test
    fun reflowableFlagsKeepReaderChrome() {
        val flags = EpubWebLayoutModeFlagsFactory.from(request(readerFontFamily = "ReaderFont", textFullJustify = true))
        assertFalse(flags.preservePublisherLayout)
        assertFalse(flags.singlePage)
        assertTrue(flags.applyReaderFont)
        assertTrue(flags.applyReaderTypography)
        assertTrue(flags.allowJustifyStretch)
    }

    @Test
    fun preserveModeDisablesAllReaderOverrides() {
        val flags = EpubWebLayoutModeFlagsFactory.from(request(preserve = true, readerFontFamily = "ReaderFont", textFullJustify = true))
        assertTrue(flags.preservePublisherLayout)
        assertFalse(flags.applyReaderFont)
        assertFalse(flags.applyReaderTypography)
        assertFalse(flags.allowJustifyStretch)
    }

    @Test
    fun singlePageDisablesReaderTypography() {
        val flags = EpubWebLayoutModeFlagsFactory.from(request(singlePage = true, readerFontFamily = "ReaderFont"))
        assertTrue(flags.singlePage)
        assertFalse(flags.applyReaderTypography)
    }

    @Test
    fun reflowableCssInjectsReaderFontColorAndColumns() {
        val css = EpubWebLayoutCssBuilder.build(request(readerFontFamily = "ReaderFont"))
        assertTrue("@font-face" in css)
        assertTrue("column-width: 1080px" in css)
        assertTrue("#102030" in css)
        assertTrue("body > article" in css)
    }

    @Test
    fun systemFontFamilyWithoutFontUrl仍注入阅读器排版且不抛异常() {
        // 铁证 2026-10-13：用户**未选自定义字体**时字体是系统族（sans-serif/serif/monospace），
        // 此时 `readerFontUrl` 为 null ⇒ 旧实现对 URL 用 `!!` 抛 NPE，被 wrapHtml 的 runCatching 吞掉
        // ⇒ 整个 Web 布局失败并降级纯文本（出版方样式与阅读器字号全丢）。本用例锁死该回归。
        val req = request(readerFontFamily = "sans-serif", readerFontUrl = null)
        val flags = EpubWebLayoutModeFlagsFactory.from(req)
        assertTrue("系统字体族仍应下发字体族", flags.applyReaderFont)
        val css = EpubWebLayoutCssBuilder.build(req)
        assertFalse("@font-face" in css)
        assertTrue("字号/行高仍须注入", "font-size: 18.0px" in css)
        assertTrue("正文颜色仍须注入", "#102030" in css)
        assertTrue("仍须分栏容器", "column-width: 1080px" in css)
    }

    @Test
    fun preserveCssKeepsPublisherBoxModel() {
        val css = EpubWebLayoutCssBuilder.build(
            request(preserve = true, readerFontFamily = "ReaderFont", textFullJustify = true)
        )
        assertFalse("@font-face" in css)
        assertFalse("#102030" in css)
        assertFalse("body > article" in css)
        assertFalse("letter-spacing" in css)
        // 保真但仍需分栏容器（多页滚动）。
        assertTrue("column-width: 1080px" in css)
    }

    @Test
    fun singlePageCssDisablesColumnSplitting() {
        val css = EpubWebLayoutCssBuilder.build(request(preserve = true, singlePage = true))
        assertTrue("column-width: auto" in css)
        assertTrue("overflow: hidden !important" in css)
        assertFalse("column-width: 1080px" in css)
    }

    @Test
    fun modeFlagsArePartOfRequestEquality() {
        assertEquals(request(preserve = true), request(preserve = true))
        assertTrue(request(preserve = true) != request(preserve = false))
    }
}