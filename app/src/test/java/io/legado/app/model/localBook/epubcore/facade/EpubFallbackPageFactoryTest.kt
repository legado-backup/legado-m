package io.legado.app.model.localBook.epubcore.facade

import android.graphics.RectF
import android.text.TextPaint
import io.legado.app.constant.ReaderDocumentLimits
import io.legado.app.model.localBook.epubcore.layout.EpubCoreLayoutConfig
import io.legado.app.model.localBook.epubcore.layout.EpubImageFragment
import io.legado.app.model.localBook.epubcore.layout.EpubMeasuredTextFragment
import io.legado.app.model.localBook.epubcore.layout.EpubMeasuredTextKind
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 降级页工厂单测（epub-md-rich-rendering 阶段 1.6 配对）。
 *
 * 覆盖：①TEXT 级产出单页正文；②空内容自动升格为 RAW 说明页；
 * ③RAW 级恒非空（终态兜底不崩溃）；④空白原因回退到通用文案；
 * ⑤**CANVAS 级分页**（长正文切多页、超宽折行、空/超限不抛、逐行片段带行高）；
 * ⑥CANVAS 级**接线锁**（`EpubCoreFacade` 的 `Stage.CANVAS_PAGE` 分支必须调 `canvasPages`）。
 *
 * 注：JVM 单测下 android.jar 为 stub（`returnDefaultValues = true`），故只断言结构与文本，
 * 不断言 [RectF] 的数值。
 */
class EpubFallbackPageFactoryTest {

    private fun config(width: Int = 600, height: Int = 800) = EpubCoreLayoutConfig(
        pageWidthPx = width,
        pageHeightPx = height,
        textPaint = TextPaint()
    )

    /** CANVAS 级用例配置：显式给页高/行高/段距，使分页结果可确定断言。 */
    private fun canvasConfig(height: Int = 100, lineHeight: Float = 20f) = EpubCoreLayoutConfig(
        pageWidthPx = 600,
        pageHeightPx = height,
        paragraphSpacingPx = 0,
        textPaint = TextPaint(),
        lineHeightPx = lineHeight
    )

    /** 假换行：一段一行（隔离分页逻辑与字体测量）。 */
    private val oneLinePerParagraph = EpubFallbackPageFactory.CanvasLineBreaker { text, _ -> listOf(text) }

    @Test
    fun `textPages 产出单页正文且带可绘制文本片段`() {
        val pages = EpubFallbackPageFactory.textPages(
            chapterIndex = 3,
            chapterHref = "OEBPS/text/ch3.xhtml",
            text = "  第一段正文  ",
            config = config()
        )
        assertEquals(1, pages.size)
        val page = pages.single()
        assertEquals(3, page.chapterIndex)
        assertEquals("OEBPS/text/ch3.xhtml", page.chapterHref)
        assertEquals(1, page.totalPagesInChapter)
        assertEquals("第一段正文", page.text.toString())
        assertNull("降级页无源锚点，不得臆造", page.start)
        val fragment = page.fragments.single()
        assertTrue(fragment is EpubMeasuredTextFragment)
        assertEquals("第一段正文", (fragment as EpubMeasuredTextFragment).text.toString())
    }

    @Test
    fun `空正文自动升格为 RAW 说明页`() {
        val pages = EpubFallbackPageFactory.textPages(
            chapterIndex = 0,
            chapterHref = "ch.xhtml",
            text = "   \n  ",
            config = config()
        )
        assertEquals(1, pages.size)
        assertTrue("空内容必须有兜底文案", pages.single().text.isNotBlank())
    }

    @Test
    fun `rawPages 恒非空且保留原因`() {
        val pages = EpubFallbackPageFactory.rawPages(
            chapterIndex = 7,
            chapterHref = "OEBPS/ch7.xhtml",
            reason = "本章渲染失败（EMPTY_RESULT）",
            config = config()
        )
        assertEquals(1, pages.size)
        assertTrue(pages.single().text.contains("EMPTY_RESULT"))
        assertEquals(1, pages.single().fragments.size)
    }

    @Test
    fun `rawPages 对空白原因回退到通用文案`() {
        val pages = EpubFallbackPageFactory.rawPages(
            chapterIndex = 0,
            chapterHref = "ch.xhtml",
            reason = "  ",
            config = config()
        )
        assertTrue("不得产出空页", pages.single().text.isNotBlank())
    }

    @Test
    fun `canvasPages 长正文按页高切成多页且不丢行不丢序`() {
        val html = (1..12).joinToString("") { "<p>第${it}段</p>" }
        val pages = EpubFallbackPageFactory.canvasPages(
            chapterIndex = 5,
            chapterHref = "OEBPS/text/ch5.xhtml",
            title = "第五章",
            html = html,
            config = canvasConfig(height = 100, lineHeight = 20f),
            breaker = oneLinePerParagraph
        )
        // 标题 + 12 段 = 13 行；每页 5 行（100 / 20）⇒ 5 + 5 + 3
        assertEquals(3, pages.size)
        assertEquals(listOf(5, 5, 3), pages.map { it.fragments.size })
        assertEquals(listOf(0, 1, 2), pages.map { it.pageIndex })
        pages.forEach { assertEquals("每页都必须回填总页数", 3, it.totalPagesInChapter) }
        val lines = pages.flatMap { page ->
            page.fragments.map { (it as EpubMeasuredTextFragment).text.toString() }
        }
        assertEquals(listOf("第五章") + (1..12).map { "第${it}段" }, lines)
        assertEquals("分页后每页文本应与片段拼接一致", lines, pages.flatMap { it.text.split("\n") })
    }

    @Test
    fun `canvasPages 超宽段落按注入的换行测量折行`() {
        val pages = EpubFallbackPageFactory.canvasPages(
            chapterIndex = 0,
            chapterHref = "ch.xhtml",
            title = "",
            html = "<p>甲乙丙丁戊己</p>",
            config = canvasConfig(height = 100, lineHeight = 20f),
            breaker = EpubFallbackPageFactory.CanvasLineBreaker { text, _ -> text.chunked(2) }
        )
        val page = pages.single()
        assertEquals("12\\n34\\n56 式折行后应在一页内", 1, pages.size)
        assertEquals("甲乙\n丙丁\n戊己", page.text.toString())
        assertEquals(listOf("甲乙", "丙丁", "戊己"), page.fragments.map { (it as EpubMeasuredTextFragment).text.toString() })
    }

    @Test
    fun `canvasPages 空正文返回空列表交由下游 TEXT 处理`() {
        val pages = EpubFallbackPageFactory.canvasPages(
            chapterIndex = 0,
            chapterHref = "ch.xhtml",
            title = "",
            html = "   \n  ",
            config = canvasConfig(),
            breaker = oneLinePerParagraph
        )
        assertTrue("空正文不得在本级产页（否则会截住降级链）", pages.isEmpty())
    }

    @Test
    fun `canvasPages 正文超限不抛异常而是返回空列表`() {
        val huge = "字".repeat(ReaderDocumentLimits.MaxSourceChars + 1)
        val pages = EpubFallbackPageFactory.canvasPages(
            chapterIndex = 0,
            chapterHref = "ch.xhtml",
            title = "",
            html = "<p>$huge</p>",
            config = canvasConfig(),
            breaker = oneLinePerParagraph
        )
        assertTrue("超限必须软回落（不抛），由调用方继续下探", pages.isEmpty())
    }

    @Test
    fun `canvasPages 每页片段带行高与文本类型供渲染器逐行绘制`() {
        val pages = EpubFallbackPageFactory.canvasPages(
            chapterIndex = 0,
            chapterHref = "ch.xhtml",
            title = "",
            html = "<p>甲乙</p>",
            config = canvasConfig(height = 100, lineHeight = 20f),
            breaker = EpubFallbackPageFactory.CanvasLineBreaker { text, _ -> text.chunked(1) }
        )
        val fragments = pages.single().fragments.map { it as EpubMeasuredTextFragment }
        assertEquals(listOf("甲", "乙"), fragments.map { it.text.toString() })
        fragments.forEach {
            assertEquals(20f, it.lineHeightPx ?: 0f)
            assertEquals(EpubMeasuredTextKind.Text, it.kind)
            assertNull("降级页不得臆造源锚点", it.source)
        }
    }

    @Test
    fun `降级链 CANVAS 级必须接线到 canvasPages 且不再恒返回空`() {
        val code = SourceFileProbe.sourceText("model/localBook/epubcore/facade/EpubCoreFacade.kt")
        val branch = code.lines().firstOrNull { it.contains("Stage.CANVAS_PAGE") }
        assertTrue("EpubCoreFacade 必须存在 CANVAS_PAGE 分支", branch != null)
        assertTrue(
            "CANVAS_PAGE 必须调用 canvasPages（否则该级恒空 ⇒ 直接掉到单页 TEXT，整章挤一页）",
            branch!!.contains("canvasPages(")
        )
        assertFalse(
            "CANVAS_PAGE 不得再恒返回 emptyList",
            code.contains("Stage.CANVAS_PAGE -> emptyList()")
        )
    }

    @Test
    fun `canvasPages 图片块产出图片片段且引用经单源解析`() {
        val html = """<p>前文</p><img src="../images/a.png" width="300px" height="150px"><p>后文</p>"""
        val pages = EpubFallbackPageFactory.canvasPages(
            chapterIndex = 1,
            chapterHref = "OEBPS/text/ch1.xhtml",
            title = "",
            html = html,
            config = canvasConfig(height = 200, lineHeight = 20f),
            breaker = oneLinePerParagraph,
            imageHref = EpubFallbackPageFactory.CanvasImageHrefResolver { _, src -> "R:$src" }
        )
        assertEquals("声明 300x150 的图应与前后文同页", 1, pages.size)
        val fragments = pages.single().fragments
        assertEquals(3, fragments.size)
        val image = fragments.filterIsInstance<EpubImageFragment>().single()
        assertEquals("图片引用必须走注入的解析器（设备侧即 EpubResourceHref 单源）", "R:../images/a.png", image.href)
        assertNull("图片块不得臆造源锚点", image.source)
        assertEquals("前后两段文本片段", 2, fragments.count { it is EpubMeasuredTextFragment })
    }

    @Test
    fun `canvasPages 图片无尺寸声明时按保守默认占位并据此分页`() {
        val html = """<p>甲</p><img src="a.png"><p>乙</p>"""
        val pages = EpubFallbackPageFactory.canvasPages(
            chapterIndex = 0,
            chapterHref = "OEBPS/text/ch1.xhtml",
            title = "",
            html = html,
            config = canvasConfig(height = 200, lineHeight = 20f),
            breaker = oneLinePerParagraph,
            imageHref = EpubFallbackPageFactory.CanvasImageHrefResolver { _, src -> src }
        )
        // 无尺寸声明 ⇒ 帧高 = 帧宽 × 默认比例（600×0.6=360）被夹到页高 200 ⇒ 图片独占一页
        assertEquals("默认占位应把图文切成三页", 3, pages.size)
        assertEquals(listOf(1, 1, 1), pages.map { it.fragments.size })
        assertTrue("第二页应是图片页", pages[1].fragments.single() is EpubImageFragment)
        assertEquals("图片页无正文文本", "", pages[1].text.toString())
    }
}