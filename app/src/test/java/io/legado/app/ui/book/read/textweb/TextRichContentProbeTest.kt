package io.legado.app.ui.book.read.textweb

import io.legado.app.help.md.MdDocumentBuilder
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 富渲染内容探测契约测试（阶段 3.1/3.2 接线配对）。
 *
 * 守护两类真实风险：①口径与 `TextChapterLayout` 不一致导致"能渲染的书被判成不可渲染"；
 * ②宽判定导致"正文提到 mermaid 一词就注入 2.4MB 运行时"。
 */
class TextRichContentProbeTest {

    @Test
    fun `抽取 usehtml 内层且口径与 canvas 一致`() {
        val inner = "<p class=\"reader-paragraph\">正文</p>"
        assertEquals(inner, TextRichContentProbe.extractUseHtmlInner("<usehtml>$inner</usehtml>"))
        // canvas 判定是 startsWith("<usehtml") + 首个 '>' 到最后一个 '<'
        assertEquals(inner, TextRichContentProbe.extractUseHtmlInner("<usehtml  >$inner</usehtml >"))
    }

    @Test
    fun `非 usehtml 内容返回空以回落 canvas`() {
        assertNull(TextRichContentProbe.extractUseHtmlInner(null))
        assertNull(TextRichContentProbe.extractUseHtmlInner(""))
        assertNull(TextRichContentProbe.extractUseHtmlInner("普通纯文本正文"))
        assertNull("标签不完整时不得硬切", TextRichContentProbe.extractUseHtmlInner("<usehtml>只有开头"))
        assertNull("内层为空时视为不可用", TextRichContentProbe.extractUseHtmlInner("<usehtml></usehtml>"))
    }

    @Test
    fun `prepare 同时给出正文与富渲染标注`() {
        val prepared = TextRichContentProbe.prepare(
            "<usehtml><pre class=\"mermaid\">graph TD;A-->B</pre><p>公式 \$x^2\$</p></usehtml>"
        )
        requireNotNull(prepared)
        assertTrue(prepared.hasMermaid)
        assertTrue(prepared.hasMath)
        assertTrue(prepared.html.contains("graph TD"))
    }

    @Test
    fun `mermaid 需为类名而非任意出现该词`() {
        assertTrue(TextRichContentProbe.detectMermaid("<pre class=\"mermaid\">x</pre>"))
        assertTrue(TextRichContentProbe.detectMermaid("<div class='foo mermaid bar'>x</div>"))
        assertFalse(
            "正文提到 mermaid 一词不得触发 2.4MB 运行时注入",
            TextRichContentProbe.detectMermaid("<p>本章介绍 mermaid 语法</p>")
        )
        assertFalse(TextRichContentProbe.detectMermaid("<p class=\"mermaidx\">x</p>"))
    }

    @Test
    fun `公式需成对定界符`() {
        assertTrue(TextRichContentProbe.detectMath("<p>\$x^2 + y^2\$</p>"))
        assertTrue(TextRichContentProbe.detectMath("<p>\$\$\\int_0^1 x dx\$\$</p>"))
        assertFalse("孤立美元符（货币）不得判定为公式", TextRichContentProbe.detectMath("<p>价格 5\$ 与 8\$</p>"))
        assertFalse("定界符内侧为空白不判为公式", TextRichContentProbe.detectMath("<p>\$ 5 and 8 \$</p>"))
        assertFalse("空公式不判定", TextRichContentProbe.detectMath("<p>\$\$</p>"))
    }

    @Test
    fun `代码块内的美元符不算公式`() {
        assertFalse(
            TextRichContentProbe.detectMath("<pre><code>echo \$HOME \$PATH</code></pre>")
        )
        // 正文公式仍在代码块之外时正常判定
        assertTrue(
            TextRichContentProbe.detectMath("<pre><code>echo \$HOME</code></pre><p>\$a+b\$</p>")
        )
    }

    @Test
    fun `无富渲染元素时两项标注均为假`() {
        val prepared = TextRichContentProbe.prepare("<usehtml><p>纯文字段落</p></usehtml>")
        requireNotNull(prepared)
        assertFalse(prepared.hasMermaid)
        assertFalse(prepared.hasMath)
    }

    // === 非 <usehtml> 文本类内容（在线正文 / 本地 txt）：allowPlainText ===
    // 用户反馈「开启模板后看不到任何变化」的根因之一：txt/在线正文不带 <usehtml> ⇒ 一律回落 canvas。

    @Test
    fun `非 usehtml 内容默认不可用但放开后可归一化`() {
        assertNull("默认（仅 md 形态）保持既有语义 ⇒ 回落 canvas", TextRichContentProbe.prepare("普通纯文本正文"))

        val plain = TextRichContentProbe.prepare("第一段\n\n第二段\n同一段内换行", allowPlainText = true)
        requireNotNull(plain)
        // **一行一段**（与 archive / TextReaderDocument 的 lineSequence 同口径）：空行丢弃，
        // 段内换行不再折叠成空格（旧口径会把整章塌成一个 <p>，段落语义装饰随之全失效）
        assertEquals(
            "<p class=\"reader-paragraph\">第一段</p>\n" +
                "<p class=\"reader-paragraph\">第二段</p>\n" +
                "<p class=\"reader-paragraph\">同一段内换行</p>",
            plain.html
        )
        assertFalse(plain.hasMermaid)
        assertFalse(plain.hasMath)
    }

    /**
     * 真机形态回归守卫（2026-10-20 铁证）。
     *
     * 真机抽检 47 个章节缓存**全部**是「每行一段、行间无空行、无任何标签」的纯文本形态。
     * 旧实现按"空行"切段 ⇒ 这类正文**整章塌成一个 `<p>`** ⇒ archive 的 `as-*` 与自研的 `dh-*`
     * 段落语义装饰（都只点 `.reader-paragraph`）只剩首段可命中 ⇒ 用户报「段落效果全没了」，
     * 且**同时**打在 archive 主题与自研主题两套上。本用例把该形态钉死。
     */
    @Test
    fun `真机纯文本形态必须逐行成段不得塌成一个段落`() {
        val chapter = "第一段正文\n第二段正文\n第三段正文"
        val prepared = TextRichContentProbe.prepare(chapter, allowPlainText = true)
        requireNotNull(prepared)
        assertEquals(
            "非空行数 = 段数（3 行 ⇒ 3 段），不得塌成一个 <p>",
            3,
            Regex("<p ").findAll(prepared.html).count()
        )
        assertTrue("每段必须带 archive 段落契约类", prepared.html.contains("<p class=\"reader-paragraph\">"))
        assertFalse("整章不得只产出一个段落", prepared.html.trim().startsWith("<p class=\"reader-paragraph\">第一段正文 第二段正文"))
    }

    @Test
    fun `段首全角空格缩进被 trim 不与 CSS 首行缩进叠加`() {
        val prepared = TextRichContentProbe.prepare("\u3000\u3000正文一\n\u3000正文二", allowPlainText = true)
        requireNotNull(prepared)
        assertEquals(
            "<p class=\"reader-paragraph\">正文一</p>\n<p class=\"reader-paragraph\">正文二</p>",
            prepared.html
        )
    }

    @Test
    fun `纯文本段落化必须转义且空输入不可用`() {
        val escaped = TextRichContentProbe.prepare("a < b & c > d", allowPlainText = true)
        requireNotNull(escaped)
        assertEquals(
            "纯文本必须转义（与 md 路线安全模式同口径）",
            "<p class=\"reader-paragraph\">a &lt; b &amp; c &gt; d</p>",
            escaped.html
        )

        assertNull("空白内容不可用 ⇒ 回落 canvas", TextRichContentProbe.prepare("   \n  ", allowPlainText = true))
        assertNull(TextRichContentProbe.prepare(null, allowPlainText = true))
    }

    @Test
    fun `在线正文 HTML 片段原样使用不二次转义`() {
        val html = "<p>段落</p><img src=\"data:image/png;base64,AA\">"
        val prepared = TextRichContentProbe.prepare(html, allowPlainText = true)
        requireNotNull(prepared)
        assertEquals("已是 HTML 片段 ⇒ 原样使用（不得转义）", html, prepared.html)
    }

    @Test
    fun `归一化后仍走同一套富渲染元素判定`() {
        val prepared = TextRichContentProbe.prepare("公式 \$a^2+b^2=c^2\$ 在此", allowPlainText = true)
        requireNotNull(prepared)
        assertTrue("放开路径必须复用同一套公式判定（不得另起口径）", prepared.hasMath)
    }

    // === 有界文档（AD-15/§1.3「单章 2Mi / 20k blocks」，与 md 侧同源复用常量）===
    // 超限一律返回 null ⇒ 调用方回落 canvas 基础排版（软切），不得把超大 DOM 交给 WebView。

    @Test
    fun `字符数超限的文本内容直接不可用`() {
        val huge = "字".repeat(MdDocumentBuilder.MaxChapterChars + 1)
        assertNull(
            "超字符上界须拒（回落 canvas），不得把超大文档交给 WebView 承载面",
            TextRichContentProbe.prepare(huge, allowPlainText = true)
        )
    }

    @Test
    fun `块数超限的 HTML 内容直接不可用`() {
        val many = "<p>x</p>".repeat(MdDocumentBuilder.MaxChapterBlocks + 1)
        assertTrue(
            "前提：字符数未超字符上界（本用例只考验块数上界）",
            many.length <= MdDocumentBuilder.MaxChapterChars
        )
        assertNull(
            "字符达标但节点数爆炸同样须拒",
            TextRichContentProbe.prepare(many, allowPlainText = true)
        )
    }

    @Test
    fun `纯文本海量段落超限亦不可用`() {
        val many = "a\n\n".repeat(MdDocumentBuilder.MaxChapterBlocks + 1)
        assertTrue("前提：字符数未超字符上界", many.length <= MdDocumentBuilder.MaxChapterChars)
        assertNull(TextRichContentProbe.prepare(many, allowPlainText = true))
    }

    @Test
    fun `usehtml 路径同样受有界文档约束`() {
        val inner = "<p>x</p>".repeat(MdDocumentBuilder.MaxChapterBlocks + 1)
        assertNull(TextRichContentProbe.prepare("<usehtml>$inner</usehtml>"))
    }

    @Test
    fun `块数未超上界的章节照常可用`() {
        val ok = "<p>x</p>".repeat(MdDocumentBuilder.MaxChapterBlocks - 1)
        assertNotNull(
            "未超上界不得误伤（判据为严格大于）",
            TextRichContentProbe.prepare(ok, allowPlainText = true)
        )
    }
}