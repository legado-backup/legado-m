package io.legado.app.service.kernel

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * JS 脚本导出的截断边界（ng-js-source-port）。
 *
 * 回归背景（2026-10-22 真机实测）：源脚本可达 889KB，而 Web 编辑器与 MCP 预览共用
 * 20,000 字符上限 ⇒ 编辑器拿到截断文本后保存会覆盖真实脚本（数据丢失）。
 * 因此 Web 端点必须用 `Int.MAX_VALUE` 取全文；MCP 预览保留截断并标记 truncated。
 */
class JsSourceExportPayloadTest {

    private val bigScript = "//" + "a".repeat(30_000)

    @Test
    fun previewLimitTruncatesAndFlagsIt() {
        val payload = JsSourceKernel.exportPayload("https://example.test/s", bigScript, 20_000)
        assertTrue("超限必须标记截断", payload["truncated"] as Boolean)
        assertEquals(bigScript.length, payload["length"])
        assertEquals("截断长度必须等于上限", 20_000, (payload["script"] as String).length)
    }

    @Test
    fun unlimitedExportReturnsWholeScript() {
        val payload = JsSourceKernel.exportPayload("https://example.test/s", bigScript, Int.MAX_VALUE)
        assertFalse("完整导出不得标记截断", payload["truncated"] as Boolean)
        assertEquals("编辑器必须拿到完整脚本", bigScript, payload["script"])
    }

    @Test
    fun exactLengthIsNotTruncated() {
        val script = "a".repeat(20_000)
        val payload = JsSourceKernel.exportPayload("https://example.test/s", script, 20_000)
        assertFalse("长度恰好等于上限时不算截断", payload["truncated"] as Boolean)
        assertEquals(script, payload["script"])
    }
}
