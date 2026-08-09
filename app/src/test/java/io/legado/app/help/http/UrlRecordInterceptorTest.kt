package io.legado.app.help.http

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * UrlRecordInterceptor 脱敏纯函数单测（precise-manage）
 *
 * 已知上限：intercept 采集链路依赖 AppConfig（appCtx.getPrefBoolean）与 appDb（Room），
 * 纯 JVM 无法执行（同 DecompressInterceptorTest 注释），采集逻辑留真机验证（tasks 2.3 L2）。
 * 此处覆盖可纯 JVM 验证的 sanitizeUrl 脱敏逻辑。
 */
class UrlRecordInterceptorTest {

    @Test
    fun sanitizeUrl_redactsTokenQuery() {
        val url = "https://example.com/api?access_token=secret123&page=2"
        val result = UrlRecordInterceptor.sanitizeUrl(url)
        assertFalse("敏感参数值应被遮挡", result.contains("secret123"))
        assertTrue("key 应保留", result.contains("access_token"))
        assertTrue("脱敏值应为 ***", result.contains("access_token=***"))
        assertTrue("非敏感参数应保留", result.contains("page=2"))
    }

    @Test
    fun sanitizeUrl_redactsPasswordAndKey() {
        val url = "https://example.com/login?username=admin&password=hunter2"
        val result = UrlRecordInterceptor.sanitizeUrl(url)
        assertTrue(result.contains("username=admin"))
        assertTrue(result.contains("password=***"))
        assertTrue(!result.contains("hunter2"))
    }

    @Test
    fun sanitizeUrl_normalUrlUnchanged() {
        val url = "https://example.com/book/12345?page=3"
        assertEquals(url, UrlRecordInterceptor.sanitizeUrl(url))
    }

    @Test
    fun sanitizeUrl_noEqualsQueryReturnsUnchanged() {
        val url = "https://example.com/search?keyword"
        assertEquals(url, UrlRecordInterceptor.sanitizeUrl(url))
    }

    @Test
    fun sanitizeUrl_invalidUrlReturnsOriginal() {
        val bad = "not a valid url://["
        assertEquals(bad, UrlRecordInterceptor.sanitizeUrl(bad))
    }
}