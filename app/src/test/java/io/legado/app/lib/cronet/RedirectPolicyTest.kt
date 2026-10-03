package io.legado.app.lib.cronet

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 重定向策略纯函数单测（缺陷 ID：IF-23 / spec: fix-cronet-redirect-follow）
 *
 * 覆盖 spec.md 的 R1 / R2 / R3 / R9：
 *  - R1 绝对 / 相对 / protocol-relative 三类 Location 正常解析
 *  - R2 空白 / 非法 / 非 http(s) 的 Location ⇒ null（**不得抛异常**）
 *  - R3 跨 scheme 且禁跨 ⇒ Reject
 *  - R9 相对 Location 严格以「传入 base」解析（AbsCallBack 必须传当跳响应 URL `info.url`）
 *
 * 纯 JVM，不依赖 Android / Cronet 运行时。
 */
class RedirectPolicyTest {

    // ---- R1 解析 ----

    @Test
    fun resolve_absoluteLocation_returnsAsIs() {
        assertEquals(
            "http://b.com/z",
            RedirectPolicy.resolve("http://a.com/x/y", "http://b.com/z")
        )
    }

    @Test
    fun resolve_relativeLocation_resolvedAgainstBase() {
        assertEquals(
            "http://a.com/cat/",
            RedirectPolicy.resolve("http://a.com/cat/1/", "/cat/")
        )
    }

    @Test
    fun resolve_protocolRelativeLocation_inheritsBaseScheme() {
        assertEquals(
            "http://a.com/ok",
            RedirectPolicy.resolve("http://a.com/pr", "//a.com/ok")
        )
    }

    @Test
    fun resolve_relativePathWithoutLeadingSlash_resolvedAgainstBaseDirectory() {
        assertEquals(
            "http://a.com/dir/next",
            RedirectPolicy.resolve("http://a.com/dir/page", "next")
        )
    }

    // ---- R9 严格以传入 base 解析（AbsCallBack 传当跳 URL，而非首跳 URL）----

    @Test
    fun resolve_usesGivenBase_notAnyOriginalBase() {
        // 第 2 跳：base 必须是当跳响应 URL，否则会算成 http://a.com/2/
        assertEquals(
            "http://b.com/2/",
            RedirectPolicy.resolve("http://b.com/1/", "/2/")
        )
    }

    // ---- R2 非法 / 空白 ⇒ null，且不抛 ----

    @Test
    fun resolve_blankLocation_returnsNull() {
        assertNull(RedirectPolicy.resolve("http://a.com/p", ""))
        assertNull(RedirectPolicy.resolve("http://a.com/p", "   "))
        assertNull(RedirectPolicy.resolve("http://a.com/p", null))
    }

    @Test
    fun resolve_nonHttpScheme_returnsNull() {
        assertNull(RedirectPolicy.resolve("http://a.com/p", "javascript:alert(1)"))
        assertNull(RedirectPolicy.resolve("http://a.com/p", "mailto:a@b.com"))
    }

    @Test
    fun resolve_blankOrInvalidBase_returnsNull() {
        assertNull(RedirectPolicy.resolve(null, "/x"))
        assertNull(RedirectPolicy.resolve("", "/x"))
        assertNull(RedirectPolicy.resolve("not a url", "/x"))
    }

    // ---- R3 跨 scheme ----

    @Test
    fun decide_crossScheme_whenNotAllowed_rejected() {
        val d = RedirectPolicy.decide("http://a.com/p", "https://a.com/p", allowCrossScheme = false)
        assertTrue("期望 Reject，实际 $d", d is RedirectPolicy.Decision.Reject)
    }

    @Test
    fun decide_crossScheme_whenAllowed_follows() {
        val d = RedirectPolicy.decide("http://a.com/p", "https://a.com/p", allowCrossScheme = true)
        assertTrue("期望 Follow，实际 $d", d is RedirectPolicy.Decision.Follow)
        assertEquals("https://a.com/p", (d as RedirectPolicy.Decision.Follow).url)
    }

    @Test
    fun decide_sameScheme_follows() {
        val d = RedirectPolicy.decide("http://a.com/p", "/q", allowCrossScheme = false)
        assertTrue("期望 Follow，实际 $d", d is RedirectPolicy.Decision.Follow)
        assertEquals("http://a.com/q", (d as RedirectPolicy.Decision.Follow).url)
    }

    @Test
    fun decide_invalidLocation_rejected() {
        val d = RedirectPolicy.decide("http://a.com/p", "", allowCrossScheme = true)
        assertTrue("期望 Reject，实际 $d", d is RedirectPolicy.Decision.Reject)
    }
}