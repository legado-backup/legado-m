package io.legado.app.ui.book.source.manage

import io.legado.app.data.entities.BookSourcePart
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 书源管理页的 JS 源入口判定（ng-js-source-port）。
 *
 * `hasJs` 来自 `book_sources_part` 视图；它决定列表标识与「编辑脚本」入口，
 * 默认必须为 false（老库升级后不应把所有源误标成 JS 源）。
 */
class BookSourceJsEntryTest {

    @Test
    fun hasJs_defaultsFalseForLegacyRows() {
        assertFalse(BookSourcePart(bookSourceUrl = "u").hasJs)
        assertFalse(BookSourcePart(bookSourceUrl = "u", hasSearchUrl = true).hasJs)
    }

    @Test
    fun hasJs_survivesCopyForLocalUiRefresh() {
        val js = BookSourcePart(bookSourceUrl = "u", hasJs = true).copy(enabledExplore = false)
        assertTrue(js.hasJs)
    }

    @Test
    fun hasJs_doesNotChangeSearchCapabilityFlag() {
        val js = BookSourcePart(bookSourceUrl = "u", hasJs = true, hasSearchUrl = true)
        assertEquals(true, js.hasSearchUrl)
    }
}
