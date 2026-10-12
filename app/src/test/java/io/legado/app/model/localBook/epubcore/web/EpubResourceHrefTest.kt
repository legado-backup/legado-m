package io.legado.app.model.localBook.epubcore.web

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 资源引用解析单源（[EpubResourceHref]）配对单测。
 *
 * 覆盖：①`data:` 内联原样返回；②相对引用按章节路径解析；③`#fragment`/`?query` 剥离；
 * ④站点根绝对路径；⑤外部 scheme 原样返回；⑥空引用回落章节路径；
 * ⑦**单源锁**：WebView 适配器必须委托本单源（不得再自带一份实现 —— 口径分裂时
 * 「保真级能显示、分页级恒裂图」且任何用例都不会变红）。
 *
 * 注：JVM 单测下 `android.net.Uri` 为 stub ⇒ 覆盖的是不依赖 `Uri` 的分支
 * （`epub.local` 回源地址分支由既有 WebView 真机路径覆盖）。
 */
class EpubResourceHrefTest {

    private val chapter = "OEBPS/text/ch1.xhtml"

    @Test
    fun `data url 原样返回不经归档`() {
        val src = "data:image/png;base64,AAAA"
        assertEquals(src, EpubResourceHref.resolve(chapter, src))
    }

    @Test
    fun `相对引用以章节路径为基准解析`() {
        assertEquals("OEBPS/images/a.png", EpubResourceHref.resolve(chapter, "../images/a.png"))
        assertEquals("OEBPS/text/fig1.png", EpubResourceHref.resolve(chapter, "fig1.png"))
    }

    @Test
    fun `剥离 fragment 与 query 装饰`() {
        assertEquals("OEBPS/text/fig1.png", EpubResourceHref.resolve(chapter, "fig1.png#frag?x=1"))
        assertEquals("OEBPS/text/fig1.png", EpubResourceHref.resolve(chapter, "fig1.png?x=1#frag"))
    }

    @Test
    fun `站点根绝对路径归一化为归档路径`() {
        assertEquals("OEBPS/images/a.png", EpubResourceHref.resolve(chapter, "/OEBPS/images/a.png"))
    }

    @Test
    fun `外部 scheme 原样返回不当作归档资源`() {
        assertEquals(
            "https://example.com/a.png",
            EpubResourceHref.resolve(chapter, "https://example.com/a.png")
        )
        assertEquals("urn:isbn:123", EpubResourceHref.resolve(chapter, "urn:isbn:123"))
    }

    @Test
    fun `空引用回落到章节自身路径`() {
        assertEquals(chapter, EpubResourceHref.resolve(chapter, "   "))
    }

    @Test
    fun `WebView 适配器必须委托单源且不再自带一份实现`() {
        val adapter = SourceFileProbe.sourceText("model/localBook/epubcore/web/EpubWebLayoutAdapter.kt")
        assertTrue(
            "适配器必须调用 EpubResourceHref.resolve（否则与本单源口径分裂）",
            adapter.contains("EpubResourceHref.resolve(")
        )
        assertFalse(
            "适配器不得再自带解析实现（`epub.local` 回源判定只允许出现在单源里）",
            adapter.contains("epub.local")
        )
        val single = SourceFileProbe.sourceText("model/localBook/epubcore/web/EpubResourceHref.kt")
        assertTrue("单源必须处理 epub.local 回源地址", single.contains("epub.local"))
    }
}
