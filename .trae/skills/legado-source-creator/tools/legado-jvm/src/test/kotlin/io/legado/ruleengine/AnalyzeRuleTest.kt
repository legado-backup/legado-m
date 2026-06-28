package io.legado.ruleengine

import io.legado.app.model.analyzeRule.AnalyzeByJSoup
import io.legado.app.model.analyzeRule.AnalyzeByJSonPath
import io.legado.app.model.analyzeRule.AnalyzeByRegex
import io.legado.app.model.analyzeRule.AnalyzeByXPath
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test

// 简化说明：阶段一最小自检程序，覆盖4种解析器的正常+边界用例 | 已知上限：无网络请求测试 | 升级路径：阶段三增加完整调试器测试
class AnalyzeRuleTest {

    @Test
    fun testAnalyzeByJSoupParseHtml() {
        val html = "<html><body><div class='content'>Hello World</div></body></html>"
        val parser = AnalyzeByJSoup(html)
        val result = parser.getString("@CSS:.content@text")
        assertEquals("Hello World", result)
    }

    @Test
    fun testAnalyzeByJSoupEmptyRule() {
        val html = "<html><body><div>test</div></body></html>"
        val parser = AnalyzeByJSoup(html)
        val result = parser.getString("")
        assertNull(result)
    }

    @Test
    fun testAnalyzeByJSonPathGetString() {
        val json = """{"name":"Legado","version":"1.0"}"""
        val parser = AnalyzeByJSonPath(json)
        val result = parser.getString("$.name")
        assertEquals("Legado", result)
    }

    @Test
    fun testAnalyzeByJSonPathEmptyRule() {
        val json = """{"key":"value"}"""
        val parser = AnalyzeByJSonPath(json)
        val result = parser.getString("")
        assertNull(result)
    }

    @Test
    fun testAnalyzeByRegexGetElement() {
        val html = "<title>Test Page</title>"
        val result = AnalyzeByRegex.getElement(html, arrayOf("<title>(.*?)</title>"))
        assertNotNull(result)
        assertTrue(result!!.size >= 2)
        assertEquals("Test Page", result[1])
    }

    @Test
    fun testAnalyzeByRegexNoMatch() {
        val html = "no title here"
        val result = AnalyzeByRegex.getElement(html, arrayOf("<title>(.*?)</title>"))
        assertNull(result)
    }

    @Test
    fun testAnalyzeByXPathGetString() {
        val html = "<html><body><div id='main'>Content</div></body></html>"
        val parser = AnalyzeByXPath(html)
        val result = parser.getString("//div[@id='main']/text()")
        assertNotNull(result)
        assertEquals("Content", result?.trim())
    }

    @Test
    fun testAnalyzeByXPathNoMatch() {
        val html = "<html><body></body></html>"
        val parser = AnalyzeByXPath(html)
        val result = parser.getString("//div[@id='nonexistent']/text()")
        assertTrue(result.isNullOrEmpty())
    }
}
