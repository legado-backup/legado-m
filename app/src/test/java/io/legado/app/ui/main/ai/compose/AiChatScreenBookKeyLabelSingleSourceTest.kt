package io.legado.app.ui.main.ai.compose

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B31：`AiChatScreen` 侧「工作键标签」判定的单源化守护（与 `AiChatService` 同批，见其同名判定）。
 *
 * 退役形态：本文件原手写 `"work:"` 字面量做前缀判定 ⇒ 已收口到 `BookIdentity.isWorkKey`。
 * 断言缝：Compose 屏内私有函数不可纯 JVM 行为化（需 Compose 宿主）⇒ 以源码文本探针守护收口不回退。
 */
class AiChatScreenBookKeyLabelSingleSourceTest {

    @Test
    fun `工作键判定必须走单源`() {
        val text = SourceFileProbe.sourceText("ui/main/ai/compose/AiChatScreen.kt")
        assertEquals(true, text.contains("!BookIdentity.isWorkKey(value)"))
        // `removePrefix("work:")` 属合法前缀剥离，不算重复判定；被消除的是「手写前缀判定」
        assertEquals("不得再手写前缀判定", false, text.contains("startsWith(\"work:\")"))
    }
}
