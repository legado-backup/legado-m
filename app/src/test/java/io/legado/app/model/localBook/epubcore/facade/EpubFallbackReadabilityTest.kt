package io.legado.app.model.localBook.epubcore.facade

import android.text.TextPaint
import io.legado.app.model.localBook.epubcore.layout.EpubCoreLayoutConfig
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 异常书可读率单测（epub-md-rich-rendering 超越验收基线 XB.1 配对；AD-16 / AD-19①）。
 *
 * 验收口径（tasks.md XB.1）：**损坏 EPUB / 旧内核 / WebView 进程崩溃 → 降级链生效、
 * 位置无损、可读率 100%**。本测试把这三条落成可断言的形式：
 * 1. **降级链生效**：三类失败都必须能沿链下探到终态 `RAW`，且 `RAW` 之后无下级；
 * 2. **可读率 100%**：终态执行体（RAW 页）**恒非空**（有内容可画 ⇒ 不白屏不崩溃）；
 * 3. **位置无损**：降级页保留章号与 href（不丢章、不跳章）。
 *
 * 注：JVM 单测下 android.jar 为 stub（`returnDefaultValues = true`）⇒ 只断言结构与文本，不断言像素。
 */
class EpubFallbackReadabilityTest {

    private fun config() = EpubCoreLayoutConfig(
        pageWidthPx = 600,
        pageHeightPx = 800,
        textPaint = TextPaint()
    )

    /** 三类异常书场景（失败原因取自 `EpubRenderFallbackPolicy.Failure`）。 */
    private val scenarios = listOf(
        "损坏 EPUB（压缩包/OPF 结构不可读）" to EpubRenderFallbackPolicy.Failure.MALFORMED_CONTENT,
        "旧内核（WebView 引擎版本不足）" to EpubRenderFallbackPolicy.Failure.ENGINE_UNAVAILABLE,
        "渲染进程崩溃（WebView 上报引擎不可用）" to EpubRenderFallbackPolicy.Failure.ENGINE_UNAVAILABLE
    )

    @Test
    fun `三类异常书均沿降级链走到终态且终态可画`() {
        scenarios.forEach { (name, failure) ->
            val chain = EpubRenderFallbackPolicy.fallbackChain(
                EpubRenderFallbackPolicy.Stage.WEB_LAYOUT,
                failure
            )
            assertTrue("$name：降级链必须非空", chain.isNotEmpty())
            assertEquals("$name：终态必须是 RAW", EpubRenderFallbackPolicy.Stage.RAW, chain.last())
            assertFalse(
                "$name：RAW 之后不得再有下级（否则会无限下探）",
                EpubRenderFallbackPolicy.hasFallback(EpubRenderFallbackPolicy.Stage.RAW, failure)
            )

            // 终态执行体：RAW 页恒非空 ⇒ 可读率 100%（有内容可画、不崩溃）
            val pages = EpubFallbackPageFactory.rawPages(
                chapterIndex = 2,
                chapterHref = "OEBPS/text/ch2.xhtml",
                reason = name,
                config = config()
            )
            assertEquals("$name：终态必须产出一页", 1, pages.size)
            assertTrue("$name：终态页不得为空（否则白屏）", pages.single().text.isNotBlank())
            assertEquals("$name：终态页必须带可绘制文本片段", 1, pages.single().fragments.size)
        }
    }

    @Test
    fun `引擎不可用与结构损坏跳过保真级不做无效重试`() {
        listOf(
            EpubRenderFallbackPolicy.Failure.MALFORMED_CONTENT,
            EpubRenderFallbackPolicy.Failure.ENGINE_UNAVAILABLE
        ).forEach { failure ->
            val chain = EpubRenderFallbackPolicy.fallbackChain(
                EpubRenderFallbackPolicy.Stage.WEB_LAYOUT,
                failure
            )
            assertFalse(
                "$failure：不得在链里再次出现 WEB_LAYOUT（重试无意义）",
                chain.contains(EpubRenderFallbackPolicy.Stage.WEB_LAYOUT)
            )
            assertEquals(
                "$failure：首级应直接落到 TEXT",
                EpubRenderFallbackPolicy.Stage.TEXT,
                EpubRenderFallbackPolicy.nextAfter(EpubRenderFallbackPolicy.Stage.WEB_LAYOUT, failure)
            )
        }
    }

    @Test
    fun `降级页保留章号与 href 实现位置无损`() {
        val text = EpubFallbackPageFactory.textPages(
            chapterIndex = 7,
            chapterHref = "OEBPS/text/ch7.xhtml",
            text = "降级正文",
            config = config()
        ).single()
        val raw = EpubFallbackPageFactory.rawPages(
            chapterIndex = 7,
            chapterHref = "OEBPS/text/ch7.xhtml",
            reason = "TIMEOUT",
            config = config()
        ).single()
        assertEquals("TEXT 级不得丢章", 7, text.chapterIndex)
        assertEquals("TEXT 级不得丢 href", "OEBPS/text/ch7.xhtml", text.chapterHref)
        assertEquals("RAW 级不得丢章", 7, raw.chapterIndex)
        assertEquals("RAW 级不得丢 href", "OEBPS/text/ch7.xhtml", raw.chapterHref)
    }

    @Test
    fun `首选级由内容态决定可重排走 canvas 快路径`() {
        assertEquals(
            "出版方控制型章节首选保真级",
            EpubRenderFallbackPolicy.Stage.WEB_LAYOUT,
            EpubRenderFallbackPolicy.initialStage(prefersPublisherLayout = true)
        )
        assertEquals(
            "可重排章节首选 canvas 快路径（AD-15）",
            EpubRenderFallbackPolicy.Stage.CANVAS_PAGE,
            EpubRenderFallbackPolicy.initialStage(prefersPublisherLayout = false)
        )
    }
}