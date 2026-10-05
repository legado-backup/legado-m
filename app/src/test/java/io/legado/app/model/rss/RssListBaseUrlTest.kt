package io.legado.app.model.rss

import org.junit.Assert.assertEquals
import org.junit.Test
import java.net.MalformedURLException
import java.net.URL

/**
 * RSS 列表「相对地址基址」选择单元测试。
 *
 * 缺陷背景：`RssParserByRule.parseXML` 此前用原始 `sortUrl`（可能是 `@js:`/`<js>` 规则串或
 * 相对模板）当基址解析「下一页/规则内相对地址」，`NetworkUtils.getAbsoluteURL` 内部以
 * `URL(base)` 解析基址 ⇒ 抛 `MalformedURLException`（debug 包 `printOnDebug()` 打到 stderr），
 * 相对下一页链接无法绝对化。
 */
class RssListBaseUrlTest {

    private val resolved = "https://content.example.com/search/xvweb/k/1.html"

    // === 失败复现：非法基址确实会让 URL(base) 抛异常 ===

    @Test
    fun `规则串作基址会被 URL 解析拒绝-复现缺陷`() {
        var thrown = false
        try {
            URL("@js:(function(){return 'https://x/';})()")
        } catch (e: MalformedURLException) {
            thrown = true
        }
        assertEquals(true, thrown)
    }

    // === 契约：非绝对地址一律回落到「实际请求到的 URL」 ===

    @Test
    fun `at-js规则串回落实际请求URL`() {
        assertEquals(resolved, resolveListBaseUrl("@js:(function(){return '/a.html'})()", resolved))
    }

    @Test
    fun `尖括号js规则串回落实际请求URL`() {
        assertEquals(resolved, resolveListBaseUrl("<js>java.get('/a')</js>", resolved))
    }

    @Test
    fun `相对模板回落实际请求URL`() {
        assertEquals(resolved, resolveListBaseUrl("/b/so.asp?wd={{key}}&pg={{page}}", resolved))
    }

    @Test
    fun `空sortUrl回落实际请求URL`() {
        assertEquals(resolved, resolveListBaseUrl("", resolved))
    }

    // === 零变化：绝对地址源沿用原基址 ===

    @Test
    fun `绝对sortUrl沿用自身`() {
        val abs = "https://site.example.com/list/1.html"
        assertEquals(abs, resolveListBaseUrl(abs, resolved))
    }

    @Test
    fun `大小写不敏感识别绝对地址`() {
        val abs = "HTTP://site.example.com/list/1.html"
        assertEquals(abs, resolveListBaseUrl(abs, resolved))
    }

    // === 兜底：实际请求 URL 为空时退回原串（不返回空串） ===

    @Test
    fun `实际请求URL为空时退回原串`() {
        assertEquals("@js:1", resolveListBaseUrl("@js:1", ""))
    }
}