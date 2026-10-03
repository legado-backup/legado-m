package io.legado.app.web.utils

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 审计目标脱敏（web-mcp-productization 一期 · §3.8 / REQ-1-308）的真实行为回归。
 *
 * 这些用例锁住"审计表里不得出现明文凭证"这条**安全不变量** —— 纯函数 ⇒ 直接调真实实现，
 * 不依赖 Android 运行时。
 */
class AuditSanitizerTest {

    // ---------------------------------------------------------------- 凭证打码

    @Test
    fun masksQueryStyleSecretValues() {
        val masked = AuditSanitizer.maskSecrets("http://h/p?token=abc123&x=1")
        assertFalse("查询串里的 token 值不得落库", masked.contains("abc123"))
        assertTrue("token 须打码", masked.contains("token=***"))
        assertTrue("非敏感参数保持原样", masked.contains("x=1"))
    }

    @Test
    fun masksJsonStyleSecretValues() {
        val json = """{"bookUrl":"http://h/b","apiKey":"SECRET-9","password":"p@ss"}"""
        val masked = AuditSanitizer.maskSecrets(json)
        assertFalse(masked.contains("SECRET-9"))
        assertFalse(masked.contains("p@ss"))
        assertTrue(masked.contains("""apiKey":"***""""))
        assertTrue(masked.contains("""password":"***""""))
        assertTrue("非敏感字段保留", masked.contains("http://h/b"))
    }

    @Test
    fun masksBearerTokenRegardlessOfKeyName() {
        val masked = AuditSanitizer.maskSecrets("Authorization: Bearer AbC-123.xyz")
        assertFalse("Bearer 后的令牌不得落库", masked.contains("AbC-123.xyz"))
        assertTrue("须出现打码占位", masked.contains("***"))
    }

    @Test
    fun secretKeyMatchingIsCaseInsensitiveAndCoversVariants() {
        listOf("TOKEN", "Access_Token", "api_key", "AppKey", "client_secret", "session_id", "Sign")
            .forEach { key ->
                val masked = AuditSanitizer.maskSecrets("$key=leakme&keep=1")
                assertFalse("$key 的值不得落库", masked.contains("leakme"))
                assertTrue("$key 后须打码", masked.contains("***"))
            }
    }

    @Test
    fun nonSecretKeysAreLeftUntouched() {
        val text = "url=http://h/p&index=3&name=abc"
        assertEquals(text, AuditSanitizer.maskSecrets(text))
    }

    // ---------------------------------------------------------------- 目标抽取

    @Test
    fun extractsSourceUrlAsTarget() {
        val target = AuditSanitizer.extractTarget("""{"bookSourceUrl":"http://h/s?token=zzz","name":"n"}""")
        assertTrue("须取书源 URL 作为目标", target.contains("http://h/s"))
        assertFalse("目标里的 token 也必须打码", target.contains("zzz"))
    }

    @Test
    fun targetFieldPriorityIsStable() {
        val target = AuditSanitizer.extractTarget(
            """{"name":"n","url":"http://h/u","bookUrl":"http://h/b"}"""
        )
        assertTrue("bookUrl 优先级高于 url / name（顺序即语义）", target.contains("http://h/b"))
    }

    @Test
    fun returnsEmptyWhenNoTargetFieldExists() {
        assertEquals("", AuditSanitizer.extractTarget(null))
        assertEquals("", AuditSanitizer.extractTarget(""))
        assertEquals("", AuditSanitizer.extractTarget("""{"foo":1}"""))
    }

    @Test
    fun targetIsTruncatedToBound() {
        val longUrl = "http://h/" + "a".repeat(500)
        val target = AuditSanitizer.extractTarget("""{"bookUrl":"$longUrl"}""")
        assertTrue("target 须截断（防超大字段撑爆审计表），实长=${target.length}", target.length <= 200)
    }

    @Test
    fun escapedJsonIsUnescapedForReadability() {
        val target = AuditSanitizer.extractTarget("""{"bookUrl":"http:\/\/h\/b"}""")
        assertEquals("http://h/b", target)
    }
}
