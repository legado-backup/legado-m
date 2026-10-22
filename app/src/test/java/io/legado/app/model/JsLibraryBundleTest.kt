package io.legado.app.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * jsLib 资源包（ng-js-source-port）：与老「URL 映射」格式共存的识别边界。
 *
 * 行为断言聚焦：合法 bundle 的解析结果、非 bundle 一律返回 null（走老逻辑）、
 * 超限/字段非法必须拒绝（体积门禁是安全底线，不能被静默降级绕过）。
 */
class JsLibraryBundleTest {

    private fun bundle(
        scripts: String = """["var Lib = { a: 1 };"]""",
        resources: String = """{"res.txt":"hello"}""",
        builtins: String? = null,
    ): String = buildString {
        append("""{"format":"legado.js.library/1","scripts":$scripts,"resources":$resources""")
        if (builtins != null) append(""","builtins":$builtins""")
        append("}")
    }

    @Test
    fun parse_validBundle_returnsScriptsAndResources() {
        val parsed = JsLibraryBundle.parse(bundle(builtins = """["cryptoJS"]"""))
        requireNotNull(parsed)
        assertEquals(1, parsed.scripts.size)
        assertTrue(parsed.scripts[0].contains("var Lib"))
        assertEquals("hello", parsed.resources["res.txt"])
        assertTrue(parsed.usesCryptoJs)
    }

    @Test
    fun parse_withoutBuiltins_keepsLegacyCryptoJsAutoInstall() {
        val parsed = JsLibraryBundle.parse(bundle())
        requireNotNull(parsed)
        // 旧库语义：未声明 builtins ⇒ 自动安装 CryptoJS（脚本可能依赖全局 CryptoJS）
        assertTrue(parsed.usesCryptoJs)
    }

    @Test
    fun parse_legacyUrlMap_returnsNull() {
        assertNull(JsLibraryBundle.parse("""{"lib.js":"https://example.invalid/lib.js"}"""))
    }

    @Test
    fun parse_plainScript_returnsNull() {
        assertNull(JsLibraryBundle.parse("function hello(){}"))
    }

    @Test
    fun parse_unknownFormat_throws() {
        val value = """{"format":"legado.js.library/2","scripts":[],"resources":{}}"""
        assertThrows(IllegalArgumentException::class.java) {
            JsLibraryBundle.parse(value)
        }
    }

    @Test
    fun parse_tooLarge_throws() {
        val big = "x".repeat(2_000_001)
        val value = """{"format":"legado.js.library/1","scripts":["$big"],"resources":{}}"""
        assertThrows(IllegalArgumentException::class.java) {
            JsLibraryBundle.parse(value)
        }
    }
}
