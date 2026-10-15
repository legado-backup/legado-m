package io.legado.app.ui.main.ai

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B31：`AiChatViewModel.currentContextSummary` 零调用别名退役守护。
 *
 * 退役项：`currentContextSummary()`（全仓除声明外零引用）。
 * 同语义活替代者：同文件私有 `currentSessionSummary()`（`:173` 状态刷新与 `:870` 上下文导出两处在用），
 * 公开别名只是它的转发体 ⇒ 无独立语义。
 */
class AiChatViewModelRetiredAliasTest {

    @Test
    fun `零调用公开别名已退役且私有单源仍在`() {
        val src = SourceFileProbe.sourceText("ui/main/ai/AiChatViewModel.kt")
        assertEquals("退役项不得回潮", false, src.contains("fun currentContextSummary()"))
        assertEquals("私有单源必须保留", true, src.contains("private fun currentSessionSummary() ="))
    }
}
