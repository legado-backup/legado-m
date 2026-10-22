package io.legado.app.help.http

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 日志脱敏（ng-js-source-port 复用口径）。
 *
 * JS 源调试摘要/异常信息会经 `redactFreeTextForLog` 输出，
 * 该函数必须继续屏蔽 URL 凭据参数与 Authorization 值 —— 否则脚本日志会泄露登录态。
 */
class NetworkLogRedactTest {

    @Test
    fun credentialQueryValues_areRedacted() {
        val text = "request failed: https://example.invalid/api?token=secret123&page=1"
        val safe = NetworkLog.redactFreeTextForLog(text)
        assertFalse("凭据值不得出现在日志", safe.contains("secret123"))
        assertTrue("参数名保留以便排障", safe.contains("token="))
    }

    @Test
    fun bearerToken_isRedacted() {
        val safe = NetworkLog.redactFreeTextForLog("Authorization: Bearer abcdef123456")
        assertFalse(safe.contains("abcdef123456"))
    }

    @Test
    fun plainText_isUnchanged() {
        val text = "JS源搜索完成，共3条"
        assertTrue(NetworkLog.redactFreeTextForLog(text) == text)
    }
}
