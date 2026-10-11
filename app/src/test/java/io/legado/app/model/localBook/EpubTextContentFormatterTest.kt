package io.legado.app.model.localBook

import org.jsoup.Jsoup
import org.jsoup.select.Elements
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * EPUB 章节正文归一单测（epub-md-rich-rendering 阶段 1.3 配对）。
 *
 * 该实现由 `EpubFile.getContent()` 的**内联逻辑**抽取而来（原为零测试覆盖的纯函数）。
 * 断言口径直接落在**最终可见文本**上（`HtmlFormatter.formatKeepImg` 的产物），
 * 因为本类要防的正是"本该被剥掉的内容变成可见正文"这类问题。
 *
 * ⚠️ 关键用例：`<style>`/`<script>` 的**元素内容**必须一并消失——`formatKeepImg` 只按标签名过滤，
 * 不会吃掉元素内部的 CSS/JS 文本（这正是抽取前存在的真实泄漏路径）。
 */
class EpubTextContentFormatterTest {

    private fun format(html: String, removeRuby: Boolean = true): String {
        val elements = Elements()
        elements.add(Jsoup.parseBodyFragment(html).body())
        return EpubTextContentFormatter.format(elements, removeRuby)
    }

    @Test
    fun `style 与 script 的元素内容不得泄漏为可见正文`() {
        val out = format("<p>开头</p><style>p{color:red}</style><script>alert(1)</script><p>结尾</p>")
        assertTrue("正文必须保留", out.contains("开头") && out.contains("结尾"))
        assertFalse("CSS 源码不得作为可见文本出现", out.contains("color:red") || out.contains("p{"))
        assertFalse("JS 源码不得作为可见文本出现", out.contains("alert(1)"))
    }

    @Test
    fun `title link meta 元素及其内容被剔除`() {
        val out = format("<title>章节标题文本</title><link href=\"a.css\"/><meta name=\"k\" content=\"v\"/><p>正文</p>")
        assertFalse("title 的文本内容不得出现在正文", out.contains("章节标题文本"))
        assertTrue("正文必须保留", out.contains("正文"))
    }

    @Test
    fun `display none 两种书写与 hidden 元素被剔除`() {
        val out = format(
            "<p>可见</p>" +
                "<p style=\"display:none\">隐藏甲</p>" +
                "<p style=\"display: none\">隐藏乙</p>" +
                "<p hidden>隐藏丙</p>"
        )
        assertTrue("正文必须保留", out.contains("可见"))
        assertFalse("无空格写法必须剔除", out.contains("隐藏甲"))
        assertFalse("带空格写法必须剔除（旧实现只覆盖无空格写法）", out.contains("隐藏乙"))
        assertFalse("HTML5 hidden 属性必须剔除", out.contains("隐藏丙"))
    }

    @Test
    fun `封面占位图只保留第一张`() {
        val out = format("<img src=\"cover.jpeg\"/><p>正文</p><img src=\"cover.jpeg\"/>")
        assertEquals(
            "多资源拼接时同一封面会重复出现 ⇒ 只应保留一张",
            1,
            Regex("cover\\.jpeg").findAll(out).count()
        )
    }

    @Test
    fun `图片多属性仅保留 src 把尺寸交回阅读器样式`() {
        val out = format("<img src=\"a.png\" width=\"100\" height=\"200\" style=\"border:0\"/>")
        assertTrue("图片地址必须保留", out.contains("a.png"))
        assertFalse("width 必须被清除", out.contains("width"))
        assertFalse("height 必须被清除", out.contains("height"))
        assertFalse("style 必须被清除", out.contains("border"))
    }

    @Test
    fun `空 src 的破图被剔除而 data-src 懒加载图不误删`() {
        val broken = format("<p>前</p><img src=\"\"/><p>后</p>")
        assertFalse("src 存在但为空 ⇒ 必是破图，须剔除", broken.contains("src=\"\""))
        assertTrue("破图剔除不得连带删掉正文", broken.contains("前") && broken.contains("后"))

        val lazy = format("<img data-src=\"real.png\"/>")
        assertTrue("无 src 的懒加载图必须原样透传（交回退属性解析）", lazy.contains("real.png"))
    }

    @Test
    fun `注音剔除后文本并回相邻节点且不留多余空格`() {
        val out = format("<p>前<ruby>漢<rp>(</rp><rt>kan</rt><rp>)</rp></ruby>後</p>")
        assertTrue("本体汉字必须保留", out.contains("漢"))
        assertFalse("注音文本必须剔除", out.contains("kan"))
        assertFalse("注音括号必须剔除", out.contains("("))
        assertTrue("接合处不得留空格：期望连续「前漢後」", out.contains("前漢後"))
    }

    @Test
    fun `不剔除注音时 ruby 本体与注音文本都保留`() {
        val out = format("<p><ruby>漢<rt>kan</rt></ruby></p>", removeRuby = false)
        assertTrue("本体必须保留", out.contains("漢"))
        assertTrue("注音必须保留（跟随书籍设置）", out.contains("kan"))
    }

    @Test
    fun `产物只保留图片标签其余标签被剥离`() {
        val out = format("<div><span>文字</span><img src=\"a.png\"/></div>")
        assertTrue("正文文本必须保留", out.contains("文字"))
        assertFalse("div 标签必须被剥离", out.contains("<div"))
        assertFalse("span 标签必须被剥离", out.contains("<span"))
        assertTrue("图片标签必须保留", out.contains("<img"))
    }
}