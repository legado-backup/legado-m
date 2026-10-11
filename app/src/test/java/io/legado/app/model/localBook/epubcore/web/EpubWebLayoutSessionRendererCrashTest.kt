package io.legado.app.model.localBook.epubcore.web

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 离屏布局会话「渲染进程崩溃」信号契约（epub-md-rich-rendering 阶段 2.8 配对）。
 *
 * 存在理由：`EpubWebLayoutSession` 持有 `WebView`，**不可 JVM 实例化**；但"崩溃信号能否被上层取到"
 * 是纯接线事实，且漏接的后果很隐蔽 —— 引擎崩溃会与普通布局失败**混为一谈**，于是被静默降级成
 * "本章渲染失败"页并写盘（引擎恢复后用户仍看到坏页）。故把三件事钉在源码层：
 * ①信号有公开只读访问点；②`onRenderProcessGone` 里**置位**；③每次 `layout()` 入口**复位**
 * （否则一次崩溃会让后续所有布局都被当成崩溃，永远回落 canvas）。
 */
class EpubWebLayoutSessionRendererCrashTest {

    private val session = "model/localBook/epubcore/web/EpubWebLayoutSession.kt"

    private fun text(): String = SourceFileProbe.sourceText(session)

    @Test
    fun `崩溃信号必须可被上层读取`() {
        val s = text()
        assertTrue("必须有公开只读访问点（供门面区分引擎崩溃）", s.contains("val rendererCrashed: Boolean"))
        assertTrue("信号字段必须 volatile（跨线程可见：WebView 回调在 UI 线程，读取在 IO 线程）", s.contains("@Volatile"))
    }

    @Test
    fun `渲染进程崩溃时置位`() {
        val s = text()
        val gone = s.indexOf("override fun onRenderProcessGone")
        val flag = s.indexOf("rendererCrashedFlag = true")
        assertTrue("必须在 onRenderProcessGone 内存在", gone >= 0)
        assertTrue("置位必须落在 onRenderProcessGone 之后（证明是崩溃回调里置的）", flag > gone)
    }

    @Test
    fun `每次布局入口必须复位`() {
        val s = text()
        val layout = s.indexOf("suspend fun layout(")
        val locked = s.indexOf("private suspend fun layoutLocked(")
        assertTrue("layout 入口必须存在", layout >= 0 && locked > layout)
        val body = s.substring(layout, locked)
        assertTrue(
            "layout() 入口必须复位信号（否则首崩之后每一次布局都被误判为崩溃）",
            body.contains("rendererCrashedFlag = false")
        )
    }
}