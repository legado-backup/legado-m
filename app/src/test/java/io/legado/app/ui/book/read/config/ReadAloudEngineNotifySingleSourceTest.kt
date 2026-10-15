package io.legado.app.ui.book.read.config

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B31：朗读配置变更事件发布的**单源化**守护（`ReadAloudConfigChangeNotifier.notifyEngine` 接线）。
 *
 * 缺陷背景：`notifyEngine()` 定义齐备却**全仓零调用**，而两处活路径（`HttpTtsEditViewModel.save` /
 * `SpeakEngineDialog.notifyReadAloudEngineChanged`）各自**手写**同一段 `postEvent(READ_ALOUD_CONFIG_CHANGED,
 * Bundle{READ_ALOUD_CONFIG_SCOPE=..._ENGINE})` ⇒ 「封装存在、调用点重复实现」的赶工形态。
 * 本类把两处收口固化：任一处回退为手写 Bundle 即红。
 */
class ReadAloudEngineNotifySingleSourceTest {

    private fun src(rel: String) = SourceFileProbe.sourceText(rel)

    @Test
    fun `引擎变更通知必须走单源门面`() {
        listOf(
            "ui/book/read/config/HttpTtsEditViewModel.kt",
            "ui/book/read/config/SpeakEngineDialog.kt"
        ).forEach { rel ->
            val text = src(rel)
            assertEquals("$rel 必须调用 notifyEngine()", true, text.contains("ReadAloudConfigChangeNotifier.notifyEngine()"))
            assertEquals("$rel 不得再手写 ENGINE 作用域事件", false, text.contains("READ_ALOUD_CONFIG_SCOPE_ENGINE"))
            assertEquals("$rel 不得再手写该事件常量", false, text.contains("READ_ALOUD_CONFIG_CHANGED"))
        }
    }

    @Test
    fun `门面三档作用域齐备`() {
        val notifier = src("help/readaloud/ReadAloudConfigChangeNotifier.kt")
        assertEquals(true, notifier.contains("fun notifyEngine()"))
        assertEquals(true, notifier.contains("fun notifySpeech()"))
        assertEquals(true, notifier.contains("fun notifyAudio()"))
    }
}
