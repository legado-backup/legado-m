package io.legado.app.help.ai

import io.legado.app.help.book.BookIdentity
import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * B31：`work:` 工作键前缀判定的**单源化**守护（`BookIdentity.isWorkKey` 接线）。
 *
 * 缺陷背景：`isWorkKey()` 定义齐备却**全仓零调用**，而两处活路径（`AiChatService.displayBookKeyLabel` /
 * `AiChatScreen.displayBookKeyLabel`）各自**手写** `"work:"` 字面量做同一判定 ⇒ 前缀事实有 **3 处副本**
 * （前缀常量 1 处 + 手写 2 处），任一处改动都会静默失配。本类锁「判定走单源」并用纯函数行为断言固化语义。
 */
class AiChatServiceBookKeyLabelSingleSourceTest {

    @Test
    fun `工作键判定必须走单源`() {
        val text = SourceFileProbe.sourceText("help/ai/AiChatService.kt")
        assertEquals(true, text.contains("!BookIdentity.isWorkKey(value)"))
        // `removePrefix("work:")` 属合法前缀剥离，不算重复判定；被消除的是「手写前缀判定」
        assertEquals("不得再手写前缀判定", false, text.contains("startsWith(\"work:\")"))
    }

    @Test
    fun `isWorkKey 行为边界`() {
        // 行为断言（非文本探针）：前缀大小写敏感、仅空前缀命中、非工作键不误判
        assertEquals(true, BookIdentity.isWorkKey("work:某作者/某作品"))
        assertEquals(false, BookIdentity.isWorkKey("https-example-book-url"))
        assertEquals(false, BookIdentity.isWorkKey(null))
        assertEquals(false, BookIdentity.isWorkKey(""))
        assertEquals(false, BookIdentity.isWorkKey("WORK:x"))
    }
}
