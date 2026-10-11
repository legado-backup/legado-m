package io.legado.app.ui.book.read

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * EPUB 引擎不可用时的宿主回落契约（epub-md-rich-rendering 阶段 2.8 配对）。
 *
 * 存在理由：这条路径只在**渲染进程真崩溃**时才走到（模拟器/真机都难稳定复现），属"低频但致命"
 * ——若漏接，用户看到的是「本章渲染失败」错误页且被缓存，而不是回落标准排版继续读。
 * 故把三件事钉在源码层：①崩溃不重试；②回落到 canvas 面并给用户提示；③提示文案确有资源。
 */
class EpubEngineFallbackRoutingTest {

    private val activity = "ui/book/read/ReadBookActivity.kt"

    private fun text(): String = SourceFileProbe.sourceText(activity)

    @Test
    fun `引擎不可用不重试`() {
        val s = text()
        val retry = s.indexOf("private suspend fun loadEpubCorePagesWithRetry(")
        val once = s.indexOf("private suspend fun loadEpubCorePagesOnce(")
        assertTrue("重试入口必须存在", retry >= 0 && once > retry)
        assertTrue(
            "崩溃必须直接上抛（同参数重试无意义）",
            s.substring(retry, once).contains("catch (e: ReaderError.BackendUnavailable)")
        )
    }

    @Test
    fun `引擎不可用回落 canvas 并提示`() {
        val s = text()
        val branch = s.indexOf("if (it is ReaderError.BackendUnavailable)")
        assertTrue("宿主必须识别该错误类型", branch >= 0)
        val tail = s.substring(branch, (branch + 1400).coerceAtMost(s.length))
        assertTrue("必须退出 EPUB 专用渲染面", tail.contains("switchEpubCore(false)"))
        assertTrue("必须走既有 canvas 回落（不把用户留在错误页）", tail.contains("fallback?.invoke()"))
        assertTrue("必须给用户可见提示", tail.contains("R.string.epub_render_engine_fallback"))
    }

    @Test
    fun `提示文案确有资源`() {
        val strings = SourceFileProbe.resValuesRawText("strings.xml")
        assertTrue(
            "文案 key 必须在 strings.xml 定义（否则崩溃路径本身会因缺资源再抛一次）",
            strings.contains("name=\"epub_render_engine_fallback\"")
        )
    }

    // ---- S6 / AD-28②：书级原子降级**接线**（2.4 消费治理层判据） ----

    @Test
    fun `治理层必须被持有且失败即上报`() {
        val s = text()
        assertTrue("必须持有书级治理对象", s.contains("private val renderGovernor = BookRenderGovernor()"))
        assertTrue(
            "引擎不可用必须上报治理层（否则降级只对当章生效 ⇒ 后续每章都再撞一次崩溃）",
            s.contains("renderGovernor.onChapterFailure(") &&
                s.contains("RenderFailure.ENGINE_UNAVAILABLE")
        )
        assertTrue("降级结果必须留痕（真机 L2 证据）", s.contains("EPUB 引擎不可用 ⇒ 书级降级"))
    }

    @Test
    fun `书级闸门必须覆盖两条内容漏斗与直连入口`() {
        val s = text()
        val gates = Regex("isEpubCoreMode\\(\\) && epubCoreAllowedForCurrentBook\\(\\)").findAll(s).count()
        assertTrue("upContent 与 upContentAwait 两条漏斗都要加书级闸门（当前 ${gates} 处）", gates >= 2)
        assertTrue(
            "闸门必须先查书级降级状态（真值唯一来源 = 治理层）",
            s.contains("private fun epubCoreAllowedForCurrentBook(): Boolean") &&
                s.contains("if (!isBookRenderDegradedToCanvas(ReadBook.book?.bookUrl)) return true")
        )
        assertTrue(
            "不经漏斗的直连入口也要拦（字号/页面动画重排）",
            s.contains("if (isBookRenderDegradedToCanvas(book.bookUrl)) {")
        )
        assertTrue(
            "降级后必须落到 canvas（有 fallback 交调用方，否则请 ReadBook 重载）",
            s.contains("if (canvasFallback != null) canvasFallback() else ReadBook.relayoutCurrentContent(\"governor-canvas\")")
        )
    }

    @Test
    fun `开局与释放闭环`() {
        val s = text()
        assertTrue(
            "开局必须按书登记初始后端（EPUB ⇒ DIRECT_WEB）",
            s.contains("renderGovernor.startBook(") &&
                s.contains("BackendSelectionPolicy.Backend.DIRECT_WEB")
        )
        val disposes = Regex("renderGovernor\\.dispose\\(\\)").findAll(s).count()
        assertTrue("释放点至少两处：onDestroy + 引擎开关变更（当前 ${disposes} 处）", disposes >= 2)
        assertTrue("引擎开关变更必须清降级状态（否则切引擎也粘住 canvas）", s.contains("renderGovernor.dispose()"))
    }
}