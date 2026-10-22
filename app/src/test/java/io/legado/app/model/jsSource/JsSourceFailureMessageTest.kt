package io.legado.app.model.jsSource

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 脚本异常文案（ng-js-source-port · 2026-10-22）。
 *
 * 真机铁证：正文/目录失败时页面只显示
 * `com.script.ScriptException: Error: xxx in <Unknown Source> at line number 1`，
 * 用户无法判断是哪个契约函数、哪份脚本出的错。文案必须带函数名 + 脚本规模，并脱敏凭据。
 */
class JsSourceFailureMessageTest {

    @Test
    fun messageCarriesFunctionNameAndScriptSize() {
        val error = IllegalStateException("Error: 接口返回非 JSON 内容")
        val message = JsSourceEngine.describeScriptFailure("getChapters", 25_265, error)
        assertEquals(true, message.contains("getChapters()"))
        assertEquals(true, message.contains("25265"))
        assertTrue("必须保留原始业务消息", message.contains("接口返回非 JSON 内容"))
        assertTrue("必须带异常类型", message.contains("IllegalStateException"))
    }

    @Test
    fun messageRedactsCredentialsInUrl() {
        val error = RuntimeException("failed: https://example.test/api?token=SECRET123&page=2")
        val message = JsSourceEngine.describeScriptFailure("search", 100, error)
        assertEquals(false, message.contains("SECRET123"))
        assertTrue("脱敏后仍保留可读上下文", message.contains("example.test"))
    }

    @Test
    fun emptyMessageFallsBackToTypeName() {
        val message = JsSourceEngine.describeScriptFailure("getContent", 10, RuntimeException())
        assertTrue(message.contains("RuntimeException"))
    }
}
