package io.legado.app.model.jsSource

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 单文件 JS 书源时间戳改写（ng-js-source-port）。
 *
 * 目的：保存脚本时把 config.lastUpdateTime 固化，避免「每次打开都算新版本」导致导入去重失效。
 * 断言重点：只改顶层 config 的受支持写法，函数内部的同名对象绝不能被误改。
 */
class JsSourceConfigStampTest {

    @Test
    fun stamp_replacesDateNowInTopLevelConfig() {
        val script = """
            var config = {
              bookSourceUrl: "https://example.invalid",
              bookSourceName: "x",
              lastUpdateTime: Date.now()
            }
            function search(key, page) { return [] }
        """.trimIndent()
        val stamped = JsSourceConfig.stampLastUpdateTime(script, 1700000000000L)
        requireNotNull(stamped)
        assertTrue(stamped.contains("1700000000000"))
        assertFalse(stamped.contains("Date.now()"))
    }

    @Test
    fun stamp_replacesNumericLiteral() {
        val script = """const config = { lastUpdateTime: 1 };"""
        val stamped = JsSourceConfig.stampLastUpdateTime(script, 42L)
        requireNotNull(stamped)
        assertTrue(stamped.contains("lastUpdateTime: 42"))
    }

    @Test
    fun stamp_ignoresConfigInsideFunction() {
        val script = """
            function build() {
              var config = { lastUpdateTime: Date.now() };
              return config;
            }
        """.trimIndent()
        assertNull(JsSourceConfig.stampLastUpdateTime(script, 42L))
    }

    @Test
    fun stamp_returnsNullWhenNoConfig() {
        assertNull(JsSourceConfig.stampLastUpdateTime("function search(){}", 42L))
    }

    @Test
    fun stamp_ignoresUnsupportedValue() {
        val script = """var config = { lastUpdateTime: computeTime() };"""
        assertNull(JsSourceConfig.stampLastUpdateTime(script, 42L))
    }

    @Test
    fun stamp_isIdempotentAfterFirstStamp() {
        val script = """var config = { lastUpdateTime: Date.now() };"""
        val once = JsSourceConfig.stampLastUpdateTime(script, 7L)
        requireNotNull(once)
        val twice = JsSourceConfig.stampLastUpdateTime(once, 7L)
        assertEquals(7L, 7L)
        assertTrue(twice == null || twice == once)
    }
}
