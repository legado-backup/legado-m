package io.legado.app.help.ai

import io.legado.app.data.entities.BookSource
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * AI 工具的书源条目投影（ng-js-source-port）。
 *
 * JS 单文件源没有 `searchUrl`，若直接 `!searchUrl.isNullOrBlank()` 会把可搜索的
 * JS 源标成 `hasSearchUrl=false`，AI 侧据此会跳过它。
 */
class AiBookSourceBriefTest {

    private fun jsSource() = BookSource(
        bookSourceUrl = "https://example.test/source",
        bookSourceName = "源A",
    ).apply {
        mainJs = "function search(key, page) { return '[]' }"
    }

    @Test
    fun jsSourceIsReportedAsSearchable() {
        val json = AiBookSourceTool.sourceBriefJson(jsSource())
        assertTrue("JS 源必须标记可搜索", json.getBoolean("hasSearchUrl"))
        assertTrue("JS 标记必须为 true", json.getBoolean("hasJs"))
        assertEquals("源A", json.getString("bookSourceName"))
    }

    @Test
    fun declarativeSourceWithoutJsIsNotMarkedAsJs() {
        val source = BookSource(
            bookSourceUrl = "https://example.test/declarative",
            bookSourceName = "源B",
        ).apply {
            searchUrl = "https://example.test/search?q={{key}}"
        }
        val json = AiBookSourceTool.sourceBriefJson(source)
        assertTrue(json.getBoolean("hasSearchUrl"))
        assertEquals(false, json.getBoolean("hasJs"))
    }
}
