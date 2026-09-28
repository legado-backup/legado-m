package io.legado.app.web.utils

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CorsPolicy 单测（一期 · 3.3 / REQ-1-303）。
 *
 * 两个口径都要锁：
 * ① **收敛**（`strict=true`）：同源放行、非白名单跨域**不回** Allow-Origin（浏览器拦截）；
 * ② **过渡兼容**（`strict=false`，默认）：仍回显任意 Origin —— 与 `webAuthStrict` 同一开关，
 *    避免"默认就打死老页"（REQ-1-113）。
 */
class CorsPolicyTest {

    private val host = "192.168.1.5:1122"

    @Test
    fun noOrigin_noHeader() {
        assertNull(CorsPolicy.allowOrigin(null, host, strict = false))
        assertNull(CorsPolicy.allowOrigin("", host, strict = true))
        assertNull(CorsPolicy.allowOrigin("   ", host, strict = true))
    }

    @Test
    fun sameOrigin_isAllowed_evenInStrictMode() {
        assertEquals(
            "http://192.168.1.5:1122",
            CorsPolicy.allowOrigin("http://192.168.1.5:1122", host, strict = true)
        )
        // 方案不参与同源判定（本服务为 http 明文，Origin 可能带 https 经代理）
        assertEquals(
            "https://192.168.1.5:1122",
            CorsPolicy.allowOrigin("https://192.168.1.5:1122", host, strict = true)
        )
        // 同源判定大小写不敏感（Host 大小写不影响结论）；回显的是请求原值
        assertEquals(
            "http://192.168.1.5:1122",
            CorsPolicy.allowOrigin("http://192.168.1.5:1122", "192.168.1.5:1122".uppercase(), strict = true)
        )
    }

    @Test
    fun crossOrigin_isRejectedInStrictMode() {
        assertNull(
            "非白名单跨域在严格模式必须不回 Allow-Origin（浏览器按 CORS 拦截）",
            CorsPolicy.allowOrigin("http://evil.example.com", host, strict = true)
        )
        assertNull(CorsPolicy.allowOrigin("http://192.168.1.5:9999", host, strict = true))
    }

    @Test
    fun crossOrigin_isEchoedInTransitionMode() {
        // strict=false 保留改造前行为，避免默认配置把老页打死
        assertEquals(
            "http://evil.example.com",
            CorsPolicy.allowOrigin("http://evil.example.com", host, strict = false)
        )
    }

    @Test
    fun malformedOriginOrMissingHost_isNotSameOrigin() {
        assertNull(CorsPolicy.allowOrigin("notaurl", host, strict = true))
        assertNull("缺 Host 时无法判同源 ⇒ 严格模式拒绝", CorsPolicy.allowOrigin("http://a:1", null, strict = true))
        assertNull(CorsPolicy.allowOrigin("http://a:1", "", strict = true))
    }

    @Test
    fun allowHeaders_mustIncludeAuthorization() {
        // 鉴权后浏览器会为 Bearer 头先发预检；缺 authorization 会让跨域带令牌请求全部失败
        assertTrue(
            "允许头必须含 authorization：${CorsPolicy.ALLOW_HEADERS}",
            CorsPolicy.ALLOW_HEADERS.contains("authorization")
        )
        assertTrue(CorsPolicy.ALLOW_HEADERS.contains("content-type"))
        assertTrue(CorsPolicy.ALLOW_METHODS.contains("OPTIONS"))
        assertTrue(CorsPolicy.ALLOW_METHODS.contains("POST"))
    }
}
