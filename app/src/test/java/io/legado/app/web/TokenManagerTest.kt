package io.legado.app.web

import io.legado.app.constant.PreferKey
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * TokenManager 单测（一期 · 1.1.5 / REQ-1-101 ~ REQ-1-104）。
 *
 * 通过注入内存 [TokenManager.TokenStore] 在**纯 JVM**下验证真实行为（无需 Robolectric）：
 * 生成 / 校验 / 级别 / 撤销 / 状态列表 / 常数时间比较 / 摘要不落明文。
 */
class TokenManagerTest {

    /** 内存存储实现：既当"Preferences"，又便于断言"存进去的到底是什么"。 */
    private class MemoryStore : TokenManager.TokenStore {
        val map = HashMap<String, Any>()
        override fun getString(key: String): String? = map[key] as? String
        override fun putString(key: String, value: String) {
            map[key] = value
        }

        override fun getLong(key: String, defValue: Long): Long = map[key] as? Long ?: defValue
        override fun putLong(key: String, value: Long) {
            map[key] = value
        }

        override fun getBoolean(key: String, defValue: Boolean): Boolean =
            map[key] as? Boolean ?: defValue

        override fun remove(key: String) {
            map.remove(key)
        }
    }

    private lateinit var mem: MemoryStore

    @Before
    fun setUp() {
        mem = MemoryStore()
        TokenManager.store = mem
    }

    @After
    fun tearDown() {
        TokenManager.store = MemoryStore()
    }

    // ------------------------------------------------------------ 生成

    @Test
    fun generate_returns32CharToken_withinCharset() {
        val token = TokenManager.generate(TokenManager.Level.READONLY)
        assertEquals("明文令牌须为 32 位（REQ-1-102）", 32, token.length)
        assertTrue(
            "明文只允许取自去混淆字符集",
            token.all { TokenManager.CHARSET.contains(it) }
        )
    }

    @Test
    fun generate_storesOnlySha256Digest_notPlaintext() {
        val token = TokenManager.generate(TokenManager.Level.MANAGE)
        val stored = mem.map[PreferKey.webTokenManage] as? String
        assertEquals("存储值应为 SHA-256 十六进制摘要（64 位）", 64, stored?.length)
        assertEquals("存储值须等于该明文的 SHA-256", TokenManager.sha256Hex(token), stored)
        assertNotEquals("Preferences 中不得出现明文", token, stored)
    }

    @Test
    fun generate_distinctTokens_acrossManyCalls() {
        val tokens = (1..200).map { TokenManager.generate(TokenManager.Level.READONLY) }
        assertEquals("随机令牌不应重复", tokens.size, tokens.toSet().size)
    }

    @Test(expected = IllegalArgumentException::class)
    fun generate_NONE_throws() {
        TokenManager.generate(TokenManager.Level.NONE)
    }

    // ------------------------------------------------------------ 校验

    @Test
    fun verify_correctToken_returnsItsOwnLevel() {
        val ro = TokenManager.generate(TokenManager.Level.READONLY)
        val mg = TokenManager.generate(TokenManager.Level.MANAGE)
        val ad = TokenManager.generate(TokenManager.Level.ADMIN)
        assertEquals(TokenManager.Level.READONLY, TokenManager.verify(ro))
        assertEquals(TokenManager.Level.MANAGE, TokenManager.verify(mg))
        assertEquals(TokenManager.Level.ADMIN, TokenManager.verify(ad))
    }

    @Test
    fun verify_wrongOrMissingToken_returnsNone() {
        TokenManager.generate(TokenManager.Level.MANAGE)
        assertEquals(TokenManager.Level.NONE, TokenManager.verify("not-a-real-token"))
        assertEquals(TokenManager.Level.NONE, TokenManager.verify(null))
        assertEquals(TokenManager.Level.NONE, TokenManager.verify(""))
        assertEquals(TokenManager.Level.NONE, TokenManager.verify("   "))
    }

    @Test
    fun verify_notGeneratedLevel_returnsNone() {
        // 只生成 readonly ⇒ 用其它级别的"明文"无从校验；而任意串都不该命中
        TokenManager.generate(TokenManager.Level.READONLY)
        assertEquals(TokenManager.Level.NONE, TokenManager.verify("whatever"))
    }

    @Test
    fun verify_afterRegenerate_oldTokenInvalid_newTokenValid() {
        val old = TokenManager.generate(TokenManager.Level.ADMIN)
        val new = TokenManager.generate(TokenManager.Level.ADMIN)
        assertEquals("旧明文须立即失效", TokenManager.Level.NONE, TokenManager.verify(old))
        assertEquals(TokenManager.Level.ADMIN, TokenManager.verify(new))
    }

    @Test
    fun verify_formatIllegalStoredDigest_returnsNone() {
        // 摘要被写坏（非 64 位十六进制）⇒ 视为未生成，不得误判
        mem.putString(PreferKey.webTokenReadonly, "zz-not-hex")
        assertEquals(TokenManager.Level.NONE, TokenManager.verify("anything"))
    }

    // ------------------------------------------------------------ 撤销 / 状态

    @Test
    fun revoke_clearsOnlyThatLevel() {
        val ro = TokenManager.generate(TokenManager.Level.READONLY)
        val mg = TokenManager.generate(TokenManager.Level.MANAGE)
        TokenManager.revoke(TokenManager.Level.READONLY)
        assertNull("已撤销级别的摘要须被删除", mem.map[PreferKey.webTokenReadonly])
        assertEquals(TokenManager.Level.NONE, TokenManager.verify(ro))
        assertEquals("其它级别不受影响", TokenManager.Level.MANAGE, TokenManager.verify(mg))
    }

    @Test
    fun revokeAll_clearsEveryLevel() {
        val ro = TokenManager.generate(TokenManager.Level.READONLY)
        val mg = TokenManager.generate(TokenManager.Level.MANAGE)
        val ad = TokenManager.generate(TokenManager.Level.ADMIN)
        TokenManager.revokeAll()
        listOf(ro, mg, ad).forEach {
            assertEquals(TokenManager.Level.NONE, TokenManager.verify(it))
        }
        assertTrue(TokenManager.listStatus().all { it.generatedAt == null })
    }

    @Test
    fun listStatus_reportsGeneratedAtOnlyForGeneratedLevels() {
        TokenManager.generate(TokenManager.Level.MANAGE)
        val status = TokenManager.listStatus().associateBy { it.level }
        assertEquals(3, status.size)
        assertTrue("已生成级别须有生成时间", (status.getValue(TokenManager.Level.MANAGE).generatedAt ?: 0L) > 0L)
        assertNull("未生成级别须为 null", status.getValue(TokenManager.Level.READONLY).generatedAt)
        assertNull("未生成级别须为 null", status.getValue(TokenManager.Level.ADMIN).generatedAt)
    }

    @Test
    fun strict_defaultsFalse() {
        assertFalse("过渡开关默认 false（REQ-1-108）", TokenManager.strict)
    }

    // ------------------------------------------------------------ 常数时间比较 / 摘要

    @Test
    fun constantTimeEquals_equalContent_true_othersFalse() {
        val a = TokenManager.sha256("hello")
        val b = TokenManager.sha256("hello")
        val c = TokenManager.sha256("hellp")
        assertTrue(TokenManager.constantTimeEquals(a, b))
        assertFalse(TokenManager.constantTimeEquals(a, c))
        assertFalse("长度不同必须返回 false", TokenManager.constantTimeEquals(a, a.copyOf(31)))
        assertTrue("空数组相等", TokenManager.constantTimeEquals(ByteArray(0), ByteArray(0)))
    }

    @Test
    fun sha256Hex_matchesKnownVector() {
        assertEquals(
            "SHA-256(\"abc\") 标准向量",
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            TokenManager.sha256Hex("abc")
        )
    }

    @Test
    fun hasToken_reflectsStorageOnly() {
        assertFalse(TokenManager.hasToken(TokenManager.Level.ADMIN))
        TokenManager.generate(TokenManager.Level.ADMIN)
        assertTrue(TokenManager.hasToken(TokenManager.Level.ADMIN))
        TokenManager.revoke(TokenManager.Level.ADMIN)
        assertFalse(TokenManager.hasToken(TokenManager.Level.ADMIN))
    }
}
