package io.legado.app.model.localBook.epubcore.facade

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 引擎不可用（渲染进程崩溃）的处置契约（epub-md-rich-rendering 阶段 2.8 配对）。
 *
 * 两层证据：
 * ①**纯判据层**（`EpubRenderFallbackPolicy`）：`ENGINE_UNAVAILABLE` 必须**跳过同级别重试**
 *   （`nextAfter(WEB_LAYOUT, ENGINE_UNAVAILABLE) → TEXT`），即"崩溃后不原地重试"是策略既定口径；
 * ②**源码接线层**（`EpubCoreFacade.paginateCanonical`）：会话崩溃时**上抛可识别错误**，
 *   且该分支必须**早于**降级写盘路径 —— 否则"崩溃"会被静默降级成"本章渲染失败"并落盘，
 *   引擎恢复后用户仍看到坏页（真实缺陷，非理论问题）。
 */
class EpubEngineUnavailableFallbackTest {

    private val facade = "model/localBook/epubcore/facade/EpubCoreFacade.kt"

    private fun text(): String = SourceFileProbe.sourceText(facade)

    @Test
    fun `引擎不可用判据跳过同级重试`() {
        val next = EpubRenderFallbackPolicy.nextAfter(
            EpubRenderFallbackPolicy.Stage.WEB_LAYOUT,
            EpubRenderFallbackPolicy.Failure.ENGINE_UNAVAILABLE
        )
        assertEquals(
            "崩溃后必须直落 TEXT（跳过 CANVAS_PAGE 同级重试），与策略注释 skipWeb 口径一致",
            EpubRenderFallbackPolicy.Stage.TEXT,
            next
        )
        assertFalse(
            "CANVAS_PAGE 不得出现在崩溃以降的链路上（同参数重试在保真链路上必失败）",
            EpubRenderFallbackPolicy.fallbackChain(
                EpubRenderFallbackPolicy.Stage.WEB_LAYOUT,
                EpubRenderFallbackPolicy.Failure.ENGINE_UNAVAILABLE
            ).contains(EpubRenderFallbackPolicy.Stage.CANVAS_PAGE)
        )
        assertTrue(
            "普通布局失败仍应逐级下探到 CANVAS_PAGE（不得因本次改动把正常降级也跳过）",
            EpubRenderFallbackPolicy.fallbackChain(
                EpubRenderFallbackPolicy.Stage.WEB_LAYOUT,
                EpubRenderFallbackPolicy.Failure.LAYOUT_ERROR
            ).contains(EpubRenderFallbackPolicy.Stage.CANVAS_PAGE)
        )
    }

    @Test
    fun `崩溃必须上抛可识别错误而非静默降级写盘`() {
        val s = text()
        assertTrue("必须消费会话的崩溃信号", s.contains("layoutSession.rendererCrashed"))
        assertTrue(
            "必须上抛 ReaderError.BackendUnavailable（宿主据此回落 canvas）",
            s.contains("throw ReaderError.BackendUnavailable(")
        )
        val thrown = s.indexOf("throw ReaderError.BackendUnavailable(")
        val degrade = s.indexOf("failure = EpubRenderFallbackPolicy.Failure.LAYOUT_ERROR")
        assertTrue("降级路径必须仍存在（普通失败不能被吞掉）", degrade > 0)
        assertTrue(
            "崩溃分支必须早于降级写盘路径（否则崩溃会被当成普通失败并落盘成坏页）",
            thrown in 1 until degrade
        )
    }

    @Test
    fun `会话实例必须被持有以读取崩溃信号`() {
        val s = text()
        assertTrue(
            "必须先用变量持有布局会话（否则无法在 null 结果后判断是否崩溃）",
            s.contains("val layoutSession = getWebLayoutSession(backgroundSlot)")
        )
        assertFalse(
            "不得退回一步式写法（拿不到会话实例 ⇒ 崩溃信号恒读不到）",
            s.contains("val document = getWebLayoutSession(backgroundSlot).layout(")
        )
    }
}