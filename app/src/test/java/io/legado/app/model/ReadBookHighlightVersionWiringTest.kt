package io.legado.app.model

import io.legado.app.testkit.SourceFileProbe
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * HL-3 接线契约 —— `ReadBook.highlightsVersion` 的**自增点必须齐**。
 *
 * 存在理由：模板面（WebView）正文的复用闸（`TemplateReuseGate`）靠这条版本号判断
 * "划线增删改了要不要重装饰重渲染"。**漏掉任一自增点**的后果都不可见：
 * 用户划了一条线、库里也有、模板正文却纹丝不动（症状＝"划了没反应"），
 * 而这类"少一行"的改动单测抓不到（闸门是纯函数、ReadBook 又是 Android 单例）。
 *
 * 故把四个变更点（载入 / 新增 / 修改 / 删除）**按数量**钉在源码层。
 */
class ReadBookHighlightVersionWiringTest {

    private val source = SourceFileProbe.sourceText("model/ReadBook.kt")

    @Test
    fun `版本号必须可被模板面读取`() {
        assertTrue(
            "必须声明非私有的 highlightsVersion（模板面闸门要读它）",
            Regex("""var highlightsVersion = 0""").containsMatchIn(source)
        )
    }

    @Test
    fun `四处划线变更点都要自增版本`() {
        assertEquals(
            "载入 / 新增 / 修改 / 删除四处必须各自 highlightsVersion++（缺一处即静默失效）",
            4,
            Regex("""highlightsVersion\+\+""").findAll(source).count()
        )
    }
}
