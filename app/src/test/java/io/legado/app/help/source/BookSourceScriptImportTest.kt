package io.legado.app.help.source

import java.io.ByteArrayInputStream
import java.io.PushbackInputStream
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 书源导入的「脚本 / JSON」分流（ng-js-source-port）。
 *
 * 判定错一次就会把 JSON 合集误当脚本执行（严重安全面）或把脚本当 JSON 解析失败，
 * 故锁定：文本/流两种形态、BOM 与前导空白、回退后流内容不丢失、体积上限。
 */
class BookSourceScriptImportTest {

    @Test
    fun isScriptText_usesFirstSignificantChar() {
        assertTrue(BookSourceScriptImport.isScriptText("function search(k,p){}"))
        assertTrue(BookSourceScriptImport.isScriptText("  \uFEFFvar config = {};"))
        assertFalse(BookSourceScriptImport.isScriptText("[{\"bookSourceUrl\":\"u\"}]"))
        assertFalse(BookSourceScriptImport.isScriptText(" \n{ \"bookSourceUrl\":\"u\" }"))
        assertFalse(BookSourceScriptImport.isScriptText("   "))
    }

    @Test
    fun isScriptStream_detectsAndRestoresBytes() {
        val script = "var config = {};"
        val input = PushbackInputStream(
            ByteArrayInputStream(script.toByteArray()), BookSourceScriptImport.SNIFF_BYTES
        )
        assertTrue(BookSourceScriptImport.isScriptStream(input))
        assertEquals(script, BookSourceScriptImport.readScript(input))
    }

    @Test
    fun isScriptStream_jsonKeepsStreamIntact() {
        val json = "[{\"bookSourceUrl\":\"u\"}]"
        val input = PushbackInputStream(
            ByteArrayInputStream(json.toByteArray()), BookSourceScriptImport.SNIFF_BYTES
        )
        assertFalse(BookSourceScriptImport.isScriptStream(input))
        assertEquals(json, input.readBytes().toString(Charsets.UTF_8))
    }

    @Test
    fun readScript_rejectsOversize() {
        val big = "x".repeat(io.legado.app.model.jsSource.JsSourceUpsert.MAX_SOURCE_BYTES + 1)
        val input = ByteArrayInputStream(big.toByteArray())
        val error = runCatching { BookSourceScriptImport.readScript(input) }.exceptionOrNull()
        assertTrue(error is io.legado.app.exception.NoStackTraceException)
    }
}
