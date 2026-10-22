package io.legado.app.ui.main.explore

import io.legado.app.data.entities.BookSource
import io.legado.app.model.jsSource.hasSearchCapability
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 发现页顶部搜索入口的可见性判据（ng-js-source-port）。
 *
 * 回归背景：入口原先用 `searchUrl.isNullOrBlank()` 判定 ⇒ JS 源（无 searchUrl、
 * 搜索由脚本 `search` 函数实现）永远看不到搜索按钮。
 */
class ExploreSearchEntryTest {

    private fun canSearch(source: BookSource?) = source?.hasSearchCapability() == true

    @Test
    fun jsSourceShowsSearchEntry() {
        val source = BookSource(
            bookSourceUrl = "https://example.test/source",
            bookSourceName = "源A",
        ).apply { mainJs = "function search(key, page) { return '[]' }" }
        assertTrue(canSearch(source))
    }

    @Test
    fun sourceWithoutAnySearchShowsNoEntry() {
        val source = BookSource(
            bookSourceUrl = "https://example.test/source",
            bookSourceName = "源B",
        )
        assertFalse(canSearch(source))
        assertFalse("无选中源时不展示入口", canSearch(null))
    }
}
