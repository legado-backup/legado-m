package io.legado.app.model.jsSource

import io.legado.app.data.entities.BookSource
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 搜索能力判据（ng-js-source-port）：JS 单文件源没有 `searchUrl`，
 * 所有「能否搜索」的判断必须走 [hasSearchCapability]，否则换源/跨源搜书/
 * 质检模板/发现页入口都会把 JS 源误判为不可搜索。
 */
class BookSourceSearchCapabilityTest {

    private fun source(searchUrl: String? = null, mainJs: String? = null) = BookSource(
        bookSourceUrl = "https://example.test/source",
        bookSourceName = "源A",
    ).apply {
        this.searchUrl = searchUrl
        this.mainJs = mainJs
    }

    @Test
    fun declarativeSourceWithSearchUrlIsSearchable() {
        val source = source(searchUrl = "https://example.test/search?q={{key}}")
        assertTrue(source.hasSearchCapability())
        assertFalse(source.isJsSource())
    }

    @Test
    fun jsSourceWithoutSearchUrlIsSearchable() {
        val source = source(mainJs = "function search(key, page) { return '[]' }")
        assertTrue(source.isJsSource())
        assertTrue("JS 源应具备搜索能力（不依赖 searchUrl）", source.hasSearchCapability())
    }

    @Test
    fun emptySourceIsNotSearchable() {
        val source = source(searchUrl = "   ", mainJs = "")
        assertFalse(source.isJsSource())
        assertFalse(source.hasSearchCapability())
    }
}
