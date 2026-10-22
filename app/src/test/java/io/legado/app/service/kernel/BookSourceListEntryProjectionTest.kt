package io.legado.app.service.kernel

import io.legado.app.data.entities.BookSource
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Web 列表投影（ng-js-source-port · C16）：剥离脚本、保留摘要。
 *
 * 列表若继续携带 `mainJs`（单源可达 889KB），5 个 JS 源就会让 `/getBookSources`
 * 响应膨胀到 4MB 级；同时列表对象回填保存会因字段缺失清空真实脚本。
 */
class BookSourceListEntryProjectionTest {

    private fun buildSource(mainJs: String?) = BookSource(
        bookSourceUrl = "https://example.test/source",
        bookSourceName = "源A",
    ).apply {
        this.mainJs = mainJs
    }

    @Test
    fun projectionDropsScriptAndKeepsSummary() {
        val script = "function search(){ return '[]' }"
        val entry = with(BookSourceKernel) { buildSource(script).toListEntry() }
        assertFalse("列表不得携带脚本全文", entry.containsKey("mainJs"))
        assertEquals(true, entry["isJsSource"])
        assertEquals(script.length, entry["mainJsLength"])
        assertEquals("https://example.test/source", entry["bookSourceUrl"])
    }

    @Test
    fun declarativeSourceIsNotMarkedAsJs() {
        val entry = with(BookSourceKernel) { buildSource(null).toListEntry() }
        assertFalse(entry.containsKey("mainJs"))
        assertEquals(false, entry["isJsSource"])
        assertEquals(0, entry["mainJsLength"])
        assertTrue("声明式字段必须保留（老 Vue 编辑页依赖）", entry.containsKey("bookSourceName"))
    }
}
