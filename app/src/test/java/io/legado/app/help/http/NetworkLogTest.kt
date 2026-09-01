package io.legado.app.help.http

import okhttp3.Headers
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * NetworkLog 纯函数脱敏测试（不触碰 AppConfig，避免 Android 依赖）
 */
class NetworkLogTest {

    @Test
    fun redactUrlForLog_redactsTokenQuery() {
        val url = "https://example.com/api?access_token=secret123&page=2"
        val result = NetworkLog.redactUrlForLog(url)
        assertEquals("https://example.com/api?access_token=[已脱敏]&page=2", result)
    }

    @Test
    fun redactUrlForLog_keepsNormalUrl() {
        val url = "https://example.com/book/123?page=2"
        assertEquals(url, NetworkLog.redactUrlForLog(url))
    }

    @Test
    fun formatHeaders_redactsSensitiveHeaderNames() {
        val headers = Headers.Builder()
            .add("Authorization", "Bearer abc123")
            .add("Cookie", "session=xyz")
            .add("User-Agent", "Mozilla/5.0")
            .build()
        val result = NetworkLog.formatHeaders(headers)
        assertTrue(result.contains("Authorization: [已脱敏]"))
        assertTrue(result.contains("Cookie: [已脱敏]"))
        assertTrue(result.contains("User-Agent: Mozilla/5.0"))
        assertTrue(!result.contains("abc123"))
        assertTrue(!result.contains("xyz"))
    }

    @Test
    fun formatHeaders_redactsGeminiApiKeyHeader() {
        // P1-A1-4：Gemini 协议鉴权头 x-goog-api-key 必须脱敏，
        // 防"AI 请求头→NetworkLog 抓包记录→MCP network_log_get→外部 LLM"泄露链（P2 前置）
        val headers = Headers.Builder()
            .add("x-goog-api-key", "AIzaSyExampleKey123")
            .add("X-Goog-Api-Key", "AIzaSyUpperKey456")
            .build()
        val result = NetworkLog.formatHeaders(headers)
        assertTrue(result.contains("x-goog-api-key: [已脱敏]"))
        assertTrue(result.contains("X-Goog-Api-Key: [已脱敏]"))
        assertTrue(!result.contains("AIzaSyExampleKey123"))
        assertTrue(!result.contains("AIzaSyUpperKey456"))
    }

    @Test
    fun redactCredentialsForLog_redactsBearerAndBasic() {
        val text = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9 Basic dXNlcjpwYXNz"
        val result = NetworkLog.redactCredentialsForLog(text)
        assertTrue(result.contains("Bearer [已脱敏]"))
        assertTrue(result.contains("Basic [已脱敏]"))
        assertTrue(!result.contains("eyJhbGciOiJIUzI1NiJ9"))
        assertTrue(!result.contains("dXNlcjpwYXNz"))
    }

    @Test
    fun redactCredentialsForLog_redactsJsonCredentials() {
        val text = """{"token": "mysecret", "name": "legado"}"""
        val result = NetworkLog.redactCredentialsForLog(text)
        assertTrue(result.contains("\"token\": \"[已脱敏]\""))
        assertTrue(result.contains("legado"))
        assertTrue(!result.contains("mysecret"))
    }

    @Test
    fun redactCredentialsForLog_redactsFormCredentials() {
        val text = "password=hunter2&username=admin"
        val result = NetworkLog.redactCredentialsForLog(text)
        assertTrue(result.contains("password=[已脱敏]"))
        assertTrue(result.contains("username=admin"))
        assertTrue(!result.contains("hunter2"))
    }

    @Test
    fun displaySource_blankFallsBackToGlobal() {
        assertEquals("全局", NetworkLog.displaySource(null))
        assertEquals("全局", NetworkLog.displaySource(""))
        assertEquals("书源A", NetworkLog.displaySource("书源A"))
    }
}
